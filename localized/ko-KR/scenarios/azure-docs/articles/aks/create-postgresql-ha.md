---
title: AKS에서 고가용성 PostgreSQL 데이터베이스를 배포하기 위한 인프라 만들기
description: CloudNativePG 연산자를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스를 배포하는 데 필요한 인프라를 만듭니다.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# AKS에서 고가용성 PostgreSQL 데이터베이스를 배포하기 위한 인프라 만들기

이 문서에서는 [CNPG(CloudNativePG)](https://cloudnative-pg.io/) 연산자를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스를 배포하는 데 필요한 인프라를 만듭니다.

## 시작하기 전에

* 배포 개요를 검토하고 [Azure CLI를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스를 배포하는 방법][postgresql-ha-deployment-overview]의 모든 필수 조건을 충족하는지 확인합니다.
* 이 가이드 전체에서 사용할 [환경 변수를 설정합니다](#set-environment-variables).
* [필요한 확장을 설치합니다](#install-required-extensions).

## 환경 변수 설정

이 가이드 전체에서 사용할 다음 환경 변수를 설정합니다.

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export LOCAL_NAME="cnpg"
export TAGS="owner=user"
export RESOURCE_GROUP_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export PRIMARY_CLUSTER_REGION="westus3"
export AKS_PRIMARY_CLUSTER_NAME="aks-primary-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_MANAGED_RG_NAME="rg-${LOCAL_NAME}-primary-aksmanaged-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME="pg-primary-fedcred1-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_PG_DNSPREFIX=$(echo $(echo "a$(openssl rand -hex 5 | cut -c1-11)"))
export AKS_UAMI_CLUSTER_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_VERSION="1.29"
export PG_NAMESPACE="cnpg-database"
export PG_SYSTEM_NAMESPACE="cnpg-system"
export PG_PRIMARY_CLUSTER_NAME="pg-primary-${LOCAL_NAME}-${SUFFIX}"
export PG_PRIMARY_STORAGE_ACCOUNT_NAME="hacnpgpsa${SUFFIX}"
export PG_STORAGE_BACKUP_CONTAINER_NAME="backups"
export ENABLE_AZURE_PVC_UPDATES="true"
export MY_PUBLIC_CLIENT_IP=$(dig +short myip.opendns.com @resolver3.opendns.com)
```

## 필요한 확장 설치

`aks-preview`, `k8s-extension` 및 `amg` 확장은 Kubernetes 클러스터를 관리하고 Azure 리소스를 쿼리하는 데 더 많은 기능을 제공합니다. 다음 [`az extension add`][az-extension-add] 명령을 사용하여 이러한 확장을 설치합니다.

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

kubectl을 활용하기 위한 필수 구성 요소로서 먼저 [Krew][install-krew]를 설치한 후 [CNPG 플러그 인][cnpg-plugin]을 설치해야 합니다. 이렇게 하면 후속 명령을 사용하여 PostgreSQL 연산자를 관리할 수 있습니다.

```bash
(
  set -x; cd "$(mktemp -d)" &&
  OS="$(uname | tr '[:upper:]' '[:lower:]')" &&
  ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/\(arm\)\(64\)\?.*/\1\2/' -e 's/aarch64$/arm64/')" &&
  KREW="krew-${OS}_${ARCH}" &&
  curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" &&
  tar zxvf "${KREW}.tar.gz" &&
  ./"${KREW}" install krew
)

export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"

kubectl krew install cnpg
```

## 리소스 그룹 만들기

[`az group create`][az-group-create] 명령을 사용하여 이 가이드에서 만든 리소스를 보관할 리소스 그룹을 만듭니다.

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## 사용자 할당 관리 ID 만들기

이 섹션에서는 CNPG PostgreSQL이 AKS 워크로드 ID를 사용하여 Azure Blob Storage에 액세스할 수 있도록 UAMI(사용자가 할당한 관리 ID)를 만듭니다. 이 구성을 사용하면 AKS의 PostgreSQL 클러스터가 비밀 없이 Azure Blob Storage에 연결할 수 있습니다.

1. [`az identity create`][az-identity-create] 명령을 사용하여 사용자가 할당한 관리 ID를 만듭니다.

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. AKS 워크로드 ID를 사용하도록 설정하고 다음 명령을 사용하여 이 가이드의 뒷부분에서 사용할 서비스 계정을 생성합니다.

    ```bash
    export AKS_UAMI_WORKLOAD_OBJECTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.principalId')
    export AKS_UAMI_WORKLOAD_RESOURCEID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.id')
    export AKS_UAMI_WORKLOAD_CLIENTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.clientId')

    echo "ObjectId: $AKS_UAMI_WORKLOAD_OBJECTID"
    echo "ResourceId: $AKS_UAMI_WORKLOAD_RESOURCEID"
    echo "ClientId: $AKS_UAMI_WORKLOAD_CLIENTID"
    ```

개체 ID는 Entra ID 테넌트 내에서 *애플리케이션* 유형의 보안 주체를 고유하게 식별하는 클라이언트 ID(애플리케이션 ID라고도 함)에 대한 고유 식별자입니다. 리소스 ID는 Azure에서 리소스를 관리하고 찾을 수 있는 고유 식별자입니다. 이러한 값은 AKS 워크로드 ID를 사용하도록 설정하는 데 필요합니다.

CNPG 연산자는 PostgreSQL에서 Azure Storage로 OAuth 액세스를 가능하게 하는 페더레이션 자격 증명을 만드는 데 가이드의 뒷부분에서 사용하는 *postgres* 라는 서비스 계정을 자동으로 생성합니다.

## 주 지역에 스토리지 계정 만들기

1. [`az storage account create`][az-storage-account-create] 명령을 사용하여 주 지역에 PostgreSQL 백업을 저장할 개체 스토리지 계정을 만듭니다.

    ```bash
    az storage account create \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard_ZRS \
        --kind StorageV2 \
        --query 'provisioningState' \
        --output tsv
    ```

1. [`az storage container create`][az-storage-container-create] 명령을 사용하여 WAL(Write Ahead Logs) 및 일반 PostgreSQL 주문형 및 예약된 백업을 저장할 스토리지 컨테이너를 만듭니다.

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    예제 출력:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > 다음 오류 메시지가 표시되면: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Azure Blob Storage에 대한 사용자 권한을 확인하고 **필요한** 경우 아래 제공된 명령을 사용하고 [`az storage container create`][az-storage-container-create] 명령을 다시 시도한 후 `Storage Blob Data Owner` 데이터 소유자로 역할을 승격합니다.

    ```bash
    az role assignment list --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID --output table

    export USER_ID=$(az ad signed-in-user show --query id --output tsv)

    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    az role assignment create \
        --assignee-object-id $USER_ID \
        --assignee-principal-type User \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --role "Storage Blob Data Owner" \
        --output tsv
    ```

## 스토리지 계정에 RBAC 할당

백업을 사용하도록 설정하려면 PostgreSQL 클러스터가 개체 저장소를 읽고 써야 합니다. AKS에서 실행되는 PostgreSQL 클러스터는 워크로드 ID를 사용하여 CNPG 연산자 구성 매개 변수 [`inheritFromAzureAD`][inherit-from-azuread]를 통해 스토리지 계정에 액세스합니다.

1. [`az storage account show`][az-storage-account-show] 명령을 사용하여 스토리지 계정에 대한 기본 리소스 ID를 가져옵니다.

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. [`az role assignment create`][az-role-assignment-create] 명령을 사용하여 각 AKS 클러스터의 관리 ID와 연결된 UAMI에 대한 스토리지 계정 리소스 ID 범위를 사용하여 개체 ID에 "Storage Blob 데이터 기여자" Azure 기본 제공 역할을 할당합니다.

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## 모니터링 인프라 설정

이 섹션에서는 Azure Managed Grafana 인스턴스, Azure Monitor 작업 영역 및 Azure Monitor Log Analytics 작업 영역을 배포하여 PostgreSQL 클러스터의 모니터링을 사용하도록 설정합니다. 또한 가이드의 뒷부분에 있는 AKS 클러스터 만들기 프로세스 중에 입력으로 사용할 생성된 모니터링 인프라에 대한 참조를 저장합니다. 이 섹션을 완료하는 데 다소 시간이 걸릴 수 있습니다.

> [!NOTE]
> Azure Managed Grafana 인스턴스 및 AKS 클러스터는 독립적으로 요금이 청구됩니다. 자세한 가격 책정 정보는 [Azure Managed Grafana 가격 책정][azure-managed-grafana-pricing]을 참조하세요.

1. [`az grafana create`][az-grafana-create] 명령을 사용하여 Azure Managed Grafana 인스턴스를 만듭니다.

    ```bash
    export GRAFANA_PRIMARY="grafana-${LOCAL_NAME}-${SUFFIX}"

    export GRAFANA_RESOURCE_ID=$(az grafana create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $GRAFANA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --zone-redundancy Enabled \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $GRAFANA_RESOURCE_ID
    ```

1. [`az monitor account create`][az-monitor-account-create] 명령을 사용하여 Azure Monitor 작업 영역을 만듭니다.

    ```bash
    export AMW_PRIMARY="amw-${LOCAL_NAME}-${SUFFIX}"

    export AMW_RESOURCE_ID=$(az monitor account create \
        --name $AMW_PRIMARY \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $AMW_RESOURCE_ID
    ```

1. [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] 명령을 사용하여 Azure Monitor Analytics 작업 영역을 만듭니다.

    ```bash
    export ALA_PRIMARY="ala-${LOCAL_NAME}-${SUFFIX}"

    export ALA_RESOURCE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-name $ALA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --query "id" \
        --output tsv)

    echo $ALA_RESOURCE_ID
    ```

## PostgreSQL 클러스터를 호스트하는 AKS 클러스터 만들기

이 섹션에서는 시스템 노드 풀을 사용하여 다중 영역 AKS 클러스터를 만듭니다. AKS 클러스터는 PostgreSQL 클러스터 주 복제본과 두 개의 대기 복제본을 호스트하며, 각각 다른 가용성 영역에 맞춰 영역 중복을 사용하도록 설정합니다.

또한 AKS 클러스터에 사용자 노드 풀을 추가하여 PostgreSQL 클러스터를 호스트합니다. 별도의 노드 풀을 사용하면 PostgreSQL에 사용되는 Azure VM SKU를 제어할 수 있으며 AKS 시스템 풀이 성능 및 비용을 최적화할 수 있습니다. 이 가이드의 뒷부분에서 CNPG 연산자를 배포할 때 노드 선택에 대해 참조할 수 있는 레이블을 사용자 노드 풀에 적용합니다. 이 섹션을 완료하는 데 다소 시간이 걸릴 수 있습니다.

1. [`az aks create`][az-aks-create] 명령을 사용하여 AKS 클러스터를 만듭니다.

    ```bash
    export SYSTEM_NODE_POOL_VMSKU="standard_d2s_v3"
    export USER_NODE_POOL_NAME="postgres"
    export USER_NODE_POOL_VMSKU="standard_d4s_v3"
    
    az aks create \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --tags $TAGS \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --generate-ssh-keys \
        --node-resource-group $AKS_PRIMARY_MANAGED_RG_NAME \
        --enable-managed-identity \
        --assign-identity $AKS_UAMI_WORKLOAD_RESOURCEID \
        --network-plugin azure \
        --network-plugin-mode overlay \
        --network-dataplane cilium \
        --nodepool-name systempool \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 3 \
        --node-vm-size $SYSTEM_NODE_POOL_VMSKU \
        --enable-azure-monitor-metrics \
        --azure-monitor-workspace-resource-id $AMW_RESOURCE_ID \
        --grafana-resource-id $GRAFANA_RESOURCE_ID \
        --api-server-authorized-ip-ranges $MY_PUBLIC_CLIENT_IP \
        --tier standard \
        --kubernetes-version $AKS_CLUSTER_VERSION \
        --zones 1 2 3 \
        --output table
    ```

2. [`az aks nodepool add`][az-aks-node-pool-add] 명령을 사용하여 AKS 클러스터에 사용자 노드 풀을 추가합니다.

    ```bash
    az aks nodepool add \
        --resource-group $RESOURCE_GROUP_NAME \
        --cluster-name $AKS_PRIMARY_CLUSTER_NAME \
        --name $USER_NODE_POOL_NAME \
        --enable-cluster-autoscaler \
        --min-count 3 \
        --max-count 6 \
        --node-vm-size $USER_NODE_POOL_VMSKU \
        --zones 1 2 3 \
        --labels workload=postgres \
        --output table
    ```

> [!NOTE]
> AKS 노드 풀을 추가할 때 `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` 오류 메시지가 표시되면 AKS 클러스터 작업이 완료될 때까지 몇 분 정도 기다린 다음 `az aks nodepool add` 명령을 실행하세요.

## AKS 클러스터에 연결하고 네임스페이스 만들기

이 섹션에서는 클러스터를 인증하고 클러스터와 상호 작용할 수 있는 키 역할을 하는 AKS 클러스터 자격 증명을 가져옵니다. 연결되면 CNPG 컨트롤러 관리자 서비스에 대한 네임스페이스와 PostgreSQL 클러스터 및 관련 서비스에 대한 네임스페이스를 만듭니다.

1. [`az aks get-credentials`][az-aks-get-credentials] 명령을 사용하여 AKS 클러스터 자격 증명을 가져옵니다.

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. [`kubectl create namespace`][kubectl-create-namespace] 명령을 사용하여 CNPG 컨트롤러 관리자 서비스, PostgreSQL 클러스터 및 관련 서비스에 대한 네임스페이스를 만듭니다.

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## 모니터링 인프라 업데이트

Managed Prometheus 및 Azure Managed Grafana에 대한 Azure Monitor 작업 영역은 클러스터 생성 프로세스 중에 메트릭 및 시각화를 위해 AKS 클러스터에 자동으로 연결됩니다. 이 섹션에서는 AKS 컨테이너 인사이트를 사용하여 로그 수집을 사용하도록 설정하고 Managed Prometheus가 메트릭을 스크래핑하고 컨테이너 인사이트가 로그를 수집하고 있는지 확인합니다.

1. [`az aks enable-addons`][az-aks-enable-addons] 명령을 사용하여 AKS 클러스터에서 컨테이너 인사이트 모니터링을 사용하도록 설정합니다.

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Managed Prometheus가 메트릭을 스크래핑하고 컨테이너 인사이트가 [`kubectl get`][kubectl-get] 명령 및 [`az aks show`][az-aks-show] 명령을 사용하여 DaemonSet을 검사하여 AKS 클러스터에서 로그를 수집하고 있는지 확인합니다.

    ```bash
    kubectl get ds ama-metrics-node \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    kubectl get ds ama-logs \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    az aks show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --query addonProfiles
    ```

    다음 예제 출력과 유사해야 하며, 출력에는 총 *6*개의 노드(시스템 노드 풀 3개, PostgreSQL 노드 풀 3개)와 컨테이너 인사이트 `"enabled": true`가 표시되어야 합니다.

    ```output
    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-metrics-node   6         6         6       6            6           <none>       

    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-logs           6         6         6       6            6           <none>       

    {
      "omsagent": {
        "config": {
          "logAnalyticsWorkspaceResourceID": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-cnpg-9vbin3p8/providers/Microsoft.OperationalInsights/workspaces/ala-cnpg-9vbin3p8",
          "useAADAuth": "true"
        },
        "enabled": true,
        "identity": null
      }
    }
    ```

## PostgreSQL 클러스터 수신에 대한 공용 고정 IP 만들기

PostgreSQL 클러스터 배포의 유효성을 검사하고 *psql* 및 *PgAdmin* 같은 클라이언트 PostgreSQL 도구를 사용하려면 주 복제본과 읽기 전용 복제본을 수신에 노출해야 합니다. 이 섹션에서는 쿼리를 위해 PostgreSQL 엔드포인트를 노출하도록 나중에 Azure Load Balancer에 제공하는 Azure 공용 IP 리소스를 만듭니다.

1. [`az aks show`][az-aks-show] 명령을 사용하여 AKS 클러스터 노드 리소스 그룹의 이름을 가져옵니다.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. [`az network public-ip create`][az-network-public-ip-create] 명령을 사용하여 공용 IP 주소를 만듭니다.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_NAME="$AKS_PRIMARY_CLUSTER_NAME-pip"

    az network public-ip create \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard \
        --zone 1 2 3 \
        --allocation-method static \
        --output table
    ```

3. [`az network public-ip show`][az-network-public-ip-show] 명령을 사용하여 새로 만든 공용 IP 주소를 가져옵니다.

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. [`az group show`][az-group-show] 명령을 사용하여 노드 리소스 그룹의 리소스 ID를 가져옵니다.

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. [`az role assignment create`][az-role-assignment-create] 명령을 사용하여 노드 리소스 그룹 범위를 사용하여 UAMI 개체 ID에 "네트워크 기여자" 역할을 할당합니다.

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## AKS 클러스터에 CNPG 연산자 설치

이 섹션에서는 Helm 또는 YAML 매니페스트를 사용하여 AKS 클러스터에 CNPG 연산자를 설치합니다.

### [Helm](#tab/helm)

1. [`helm repo add`][helm-repo-add] 명령을 사용하여 CNPG Helm 리포지토리를 추가합니다.

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. CNPG Helm 리포지토리를 업그레이드하고 이를 `--install` 플래그와 함께 [`helm upgrade`][helm-upgrade] 명령을 사용하여 AKS 클러스터에 설치합니다.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. [`kubectl get`][kubectl-get] 명령을 사용하여 AKS 클러스터에 연산자 설치를 확인합니다.

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. [`kubectl apply`][kubectl-apply] 명령을 사용하여 AKS 클러스터에 CNPG 연산자를 설치합니다.

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. [`kubectl get`][kubectl-get] 명령을 사용하여 AKS 클러스터에 연산자 설치를 확인합니다.

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## 다음 단계

> [!div class="nextstepaction"]
> [AKS 클러스터에 고가용성 PostgreSQL 데이터베이스 배포][deploy-postgresql]

## 참가자

*이 문서는 Microsoft에서 유지 관리합니다. 원래 다음 기여자가 작성했습니다.*

* Ken Kilty | 수석 TPM
* Russell de Pina | 수석 TPM
* Adrian Joian | 선임 고객 엔지니어
* Jenny Hayes | 선임 콘텐츠 개발자
* Carol Smith | 선임 콘텐츠 개발자
* Erin Schaffer | 콘텐츠 개발자 2

<!-- LINKS -->
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-grafana-create]: /cli/azure/grafana#az-grafana-create
[postgresql-ha-deployment-overview]: ./postgresql-ha-overview.md
[az-extension-add]: /cli/azure/extension#az_extension_add
[az-group-create]: /cli/azure/group#az_group_create
[az-storage-account-create]: /cli/azure/storage/account#az_storage_account_create
[az-storage-container-create]: /cli/azure/storage/container#az_storage_container_create
[inherit-from-azuread]: https://cloudnative-pg.io/documentation/1.23/appendixes/object_stores/#azure-blob-storage
[az-storage-account-show]: /cli/azure/storage/account#az_storage_account_show
[az-role-assignment-create]: /cli/azure/role/assignment#az_role_assignment_create
[az-monitor-account-create]: /cli/azure/monitor/account#az_monitor_account_create
[az-monitor-log-analytics-workspace-create]: /cli/azure/monitor/log-analytics/workspace#az_monitor_log_analytics_workspace_create
[azure-managed-grafana-pricing]: https://azure.microsoft.com/pricing/details/managed-grafana/
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-node-pool-add]: /cli/azure/aks/nodepool#az_aks_nodepool_add
[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[az-aks-enable-addons]: /cli/azure/aks#az_aks_enable_addons
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-show]: /cli/azure/network/public-ip#az_network_public_ip_show
[az-group-show]: /cli/azure/group#az_group_show
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[deploy-postgresql]: ./deploy-postgresql-ha.md
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
