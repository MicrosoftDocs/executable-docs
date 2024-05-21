---
title: '자습서: Azure CLI를 사용하여 AKS 클러스터에 WordPress 배포'
description: Azure Database for MySQL - 유연한 서버를 사용하여 WordPress를 AKS에 빠르게 빌드하고 배포하는 방법을 알아봅니다.
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# 자습서: Azure Database for MySQL - 유연한 서버를 사용하여 AKS에 WordPress 앱 배포

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

이 자습서에서는 Azure CLI를 사용하여 Azure Database for MySQL 유연한 서버가 있는 AKS(Azure Kubernetes Service) 클러스터에 HTTPS를 통해 보호되는 확장성 있는 WordPress 애플리케이션을 배포합니다.
**[AKS](../../aks/intro-kubernetes.md)** 는 클러스터를 빠르게 배포하고 관리할 수 있는 관리형 Kubernetes 서비스입니다. **[Azure Database for MySQL 유연한 서버](overview.md)** 는 데이터베이스 관리 기능 및 구성 설정에 대한 보다 세부적인 제어와 유연성을 제공하도록 설계된 완전 관리형 데이터베이스 서비스입니다.

> [!NOTE]
> 이 자습서에서는 Kubernetes 개념, WordPress 및 MySQL에 대한 기본적인 이해가 있다고 가정합니다.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## 필수 조건 

시작 전에 Azure CLI에 로그인하고 CLI와 함께 사용할 구독을 선택했는지 확인합니다. [Helm이 설치되어 있는지](https://helm.sh/docs/intro/install/) 확인합니다.

> [!NOTE]
> Azure Cloud Shell 대신 로컬로 이 자습서의 명령을 실행하는 경우 관리자 권한으로 명령을 실행합니다.

## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## 리소스 그룹 만들기

Azure 리소스 그룹은 Azure 리소스가 배포되고 관리되는 논리 그룹입니다. 모든 리소스는 리소스 그룹에 배치되어야 합니다. 다음 명령은 이전에 정의된 `$MY_RESOURCE_GROUP_NAME` 및 `$REGION` 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

결과:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

> [!NOTE]
> 리소스 그룹의 위치는 리소스 그룹 메타데이터가 저장되는 위치입니다. 또한 리소스를 만드는 동안 다른 지역을 지정하지 않은 경우 리소스가 Azure에서 실행되는 위치이기도 합니다.

## 가상 네트워크 및 서브넷 만들기

가상 네트워크는 Azure에서 개인 네트워크의 기본 구성 요소입니다. Azure Virtual Network를 통해 VM과 같은 Azure 리소스가 상호 간 및 인터넷과 안전하게 통신할 수 있습니다.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Results:
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Azure Database for MySQL 유연한 서버 인스턴스 만들기

Azure Database for MySQL 유연한 서버는 클라우드에서 고가용성 MySQL 서버를 실행, 관리 및 크기 조정하는 데 사용할 수 있는 관리되는 서비스입니다. [az mysql flexible-server create](/cli/azure/mysql/flexible-server) 명령을 사용하여 Azure Database for MySQL 유연한 서버 인스턴스를 만듭니다. 서버는 여러 데이터베이스를 포함할 수 있습니다. 다음 명령은 Azure CLI의 로컬 컨텍스트에 있는 서비스 기본값 및 변수 값을 사용하여 서버를 만듭니다.

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

Results:
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

생성된 서버에는 다음과 같은 특성이 있습니다.

- 새 빈 데이터베이스가 서버를 처음 프로비저닝하면 이 데이터베이스가 만들어집니다.
- 서버 이름, 관리 사용자 이름, 관리 사용자 암호, 리소스 그룹 이름 및 위치는 이미 Cloud Shell의 로컬 컨텍스트 환경에 지정되어 있으며 리소스 그룹 및 기타 Azure 구성 요소와 동일한 위치에 있습니다.
- 나머지 서버 구성의 서비스 기본값은 컴퓨팅 계층(Burstable), 컴퓨팅 크기/SKU(Standard_B2s), 백업 보존 기간(7일) 및 MySQL 버전(8.0.21)입니다.
- 기본 연결 방법은 연결된 가상 네트워크 및 자동 생성된 서브넷을 사용한 프라이빗 액세스(가상 네트워크 통합)입니다.

> [!NOTE]
> 서버를 만든 후에는 연결 방법을 변경할 수 없습니다. 예를 들어, 만드는 동안 `Private access (VNet Integration)`을 선택한 경우 만들기 후에는 `Public access (allowed IP addresses)`로 변경할 수 없습니다. VNet 통합을 사용하여 서버에 안전하게 액세스하려면 프라이빗 액세스 권한이 있는 서버를 만드는 것이 좋습니다. [개념 문서](./concepts-networking-vnet.md)에서 프라이빗 액세스에 대해 자세히 알아보세요.

기본값을 변경하려는 경우 구성 가능한 CLI 매개 변수의 전체 목록에 대한 Azure CLI [참조 설명서](/cli/azure//mysql/flexible-server)를 참조하세요.

## Azure Database for MySQL - 유연한 서버 상태 확인

Azure Database for MySQL - 유연한 서버 및 지원 리소스를 만드는 데 몇 분 정도 걸립니다.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Azure Database for MySQL - 유연한 서버에서 서버 매개 변수 구성

서버 매개 변수를 사용하여 Azure Database for MySQL - 유연한 서버 구성을 관리할 수 있습니다. 서버 매개 변수는 서버를 만들 때 기본/권장 값으로 구성됩니다.

서버의 특정 매개 변수에 대한 세부 정보를 표시하려면 [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) 명령을 실행합니다.

### Azure Database for MySQL 사용 안 함 - WordPress 통합을 위한 유연한 서버 SSL 연결 매개 변수

특정 서버 매개 변수의 값을 수정하여 MySQL 서버 엔진의 기본 구성 값을 업데이트할 수도 있습니다. 서버 매개 변수를 업데이트하려면 [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) 명령을 사용합니다.

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Results:
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## AKS 클러스터 만들기

컨테이너 인사이트를 사용하여 AKS 클러스터를 만들려면 **--enable-addons** 모니터링 매개 변수와 함께 [az aks create](/cli/azure/aks#az-aks-create) 명령을 사용합니다. 다음 예에서는 **myAKSCluster**라는 자동 크기 조정, 가용성 영역 지원 클러스터를 만듭니다.

이 작업은 몇 분 정도 걸립니다.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> AKS 클러스터를 만들 때 AKS 리소스를 저장하기 위해 두 번째 리소스 그룹이 자동으로 만들어집니다. [AKS를 통해 두 개의 리소스 그룹이 만들어지는 이유는 무엇인가요?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)를 참조하세요.

## 클러스터에 연결

Kubernetes 클러스터를 관리하려면 Kubernetes 명령줄 클라이언트인 [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/)을 사용하세요. Azure Cloud Shell을 사용하는 경우 `kubectl`이 이미 설치되어 있습니다. 다음 예에서는 [az aks install-cli](/cli/azure/aks#az-aks-install-cli) 명령을 사용하여 로컬로 `kubectl`을 설치합니다. 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

다음으로, [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) 명령을 사용하여 Kubernetes 클러스터에 연결하도록 `kubectl`을 구성합니다. 이 명령은 자격 증명을 다운로드하고 Kubernetes CLI가 해당 자격 증명을 사용하도록 구성합니다. 이 명령은 [Kubernetes 구성 파일](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)의 기본 위치인 `~/.kube/config`를 사용합니다. **--file** 인수를 사용하여 Kubernetes 구성 파일의 다른 위치를 지정할 수 있습니다.

> [!WARNING]
> 이 명령은 기존 자격 증명을 동일한 항목으로 덮어씁니다.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

클러스터에 대한 연결을 확인하려면 [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) 명령을 사용하여 클러스터 노드 목록을 반환합니다.

```bash
kubectl get nodes
```

## NGINX 수신 컨트롤러 설치

고정 공용 IP 주소로 수신 컨트롤러를 구성할 수 있습니다. 수신 컨트롤러를 삭제해도 고정 공용 IP 주소는 그대로 유지됩니다. AKS 클러스터를 삭제하면 IP 주소가 남지 않습니다.
수신 컨트롤러를 업그레이드할 때 수신 컨트롤러 서비스가 할당될 부하 분산 장치를 인식하도록 Helm 릴리스에 매개 변수를 전달해야 합니다. HTTPS 인증서가 올바르게 작동하려면 DNS 레이블을 사용하여 수신 컨트롤러 IP 주소에 대한 FQDN(정규화된 도메인 이름)을 구성합니다. FQDN은 $MY_DNS_LABEL.AZURE_REGION_NAME.cloudapp.azure.com 형식을 따라야 합니다.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

다음으로 ingress-nginx Helm 리포지토리를 추가하고, 로컬 Helm 차트 리포지토리 캐시를 업데이트하고, Helm을 통해 ingress-nginx 추가 기능을 설치합니다. --set controller.service.annotations를 **사용하여 DNS 레이블을 설정할 수 있습니다." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** 매개 변수는 수신 컨트롤러를 처음 배포할 때 또는 나중에 배포합니다. 이 예제에서는 --set controller.service.loadBalancerIP="<STATIC_IP>" 매개 변수**를 **사용하여 이전 단계에서 만든 고유한 공용 IP 주소를 지정합니다.

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## 사용자 지정 도메인에 HTTPS 종료 추가

자습서의 이 시점에서는 NGINX를 수신 컨트롤러로 사용하는 AKS 웹앱과 애플리케이션에 액세스하는 데 사용할 수 있는 사용자 지정 도메인이 있습니다. 다음 단계는 사용자가 https를 통해 안전하게 애플리케이션에 접근할 수 있도록 도메인에 SSL 인증서를 추가하는 것입니다.

### 인증서 관리자 설정

HTTPS를 추가하기 위해 인증서 관리자를 사용할 예정입니다. 인증서 관리자는 Kubernetes 배포를 위한 SSL 인증서를 가져오고 관리하기 위한 오픈 소스 도구입니다. 인증서 관리자는 널리 사용되는 공용 발급자 및 프라이빗 발급자로부터 인증서를 가져오고, 인증서가 유효하고 최신인지 확인하고, 만료되기 전에 구성된 시간에 인증서 갱신을 시도합니다.

1. cert-manager를 설치하려면 먼저 이를 실행할 네임스페이스를 만들어야 합니다. 이 자습서에서는 cert-manager 네임스페이스에 cert-manager를 설치합니다. 다른 네임스페이스에서 cert-manager를 실행할 수 있지만 배포 매니페스트를 수정해야 합니다.

    ```bash
    kubectl create namespace cert-manager
    ```

2. 이제 cert-manager를 설치할 수 있습니다. 모든 리소스는 단일 YAML 매니페스트 파일에 포함됩니다. 다음 명령을 사용하여 매니페스트 파일을 설치합니다.

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. 다음을 실행하여 cert-manager 네임스페이스에 `certmanager.k8s.io/disable-validation: "true"` 레이블을 추가합니다. 이를 통해 cert-manager가 TLS를 부트스트랩하는 데 필요한 시스템 리소스를 자체 네임스페이스에 만들 수 있습니다.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Helm Charts를 통해 인증서 가져오기

Helm은 Kubernetes 클러스터에 대한 애플리케이션 및 서비스의 만들기, 패키지, 구성 및 배포를 자동화하기 위한 Kubernetes 배포 도구입니다.

Cert-manager는 Kubernetes에 대한 최고 수준의 설치 방법으로 Helm 차트를 제공합니다.

1. Jetstack Helm 리포지토리를 추가합니다. 이 리포지토리는 cert-manager 차트의 유일하게 지원되는 원본입니다. 인터넷에는 다른 미러와 복사본이 있지만 이는 비공식적이며 보안 위험을 초래할 수 있습니다.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. 로컬 Helm 차트 리포지토리 캐시를 업데이트합니다.

    ```bash
    helm repo update
    ```

3. Helm을 통해 Cert-Manager 추가 기능을 설치합니다.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 인증서 발급자 YAML 파일을 적용합니다. ClusterIssuers는 인증서 서명 요청을 수락하여 서명된 인증서를 생성할 수 있는 CA(인증 기관)을 나타내는 Kubernetes 리소스입니다. 모든 cert-manager 인증서에는 요청을 이행할 준비가 되어 있는 참조 발급자가 필요합니다. `cluster-issuer-prod.yml file`에서 해당 발급자를 찾을 수 있습니다.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## 사용자 지정 스토리지 클래스 만들기

기본 스토리지 클래스는 가장 일반적인 시나리오에 적합하지만, 일부는 아닙니다. 경우에 따라 고유한 매개 변수를 사용하여 고유 스토리지 클래스를 사용자 지정해야 할 수 있습니다. 예를 들어, 다음 매니페스트를 사용하여 파일 공유의 **mountOptions**를 구성합니다.
**fileMode** 및 **dirMode**의 기본값은 Kubernetes 탑재 파일 공유의 경우 **0755**입니다. 스토리지 클래스 개체에 다른 탑재 옵션을 지정할 수 있습니다.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## AKS 클러스터에 WordPress 배포

이 자습서에서는 Bitnami에서 빌드한 WordPress용 기존 Helm 차트를 사용합니다. Bitnami Helm 차트는 로컬 MariaDB를 데이터베이스로 사용하므로 Azure Database for MySQL에서 앱을 사용하려면 이러한 값을 재정의해야 합니다. `helm-wp-aks-values.yaml` 파일의 값과 사용자 지정 설정을 재정의할 수 있습니다.

1. Wordpress Bitnami Helm 리포지토리를 추가합니다.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. 로컬 Helm 차트 리포지토리 캐시를 업데이트합니다.

    ```bash
    helm repo update
    ```

3. Helm을 통해 Wordpress 워크로드를 설치합니다.

    ```bash
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

Results:
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## HTTPS를 통해 보호되는 AKS 배포 찾아보기

다음 명령을 실행하여 애플리케이션에 대한 HTTPS 엔드포인트를 가져옵니다.

> [!NOTE]
> SSL 인증서가 전파되는 데 2~3분이 소요되고, 모든 WordPress POD 복제본이 준비되고 https를 통해 사이트에 완전히 연결되는 데 약 5분이 소요되는 경우가 많습니다.

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

다음 명령을 사용하여 WordPress 콘텐츠가 올바르게 전달되는지 확인합니다.

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Results:
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

다음 URL을 통해 웹 사이트를 참조하세요.

```bash
echo "You can now visit your web server at https://$FQDN"
```

## 리소스 정리(선택 사항)

Azure 요금을 방지하려면 불필요한 리소스를 정리해야 합니다. 클러스터가 더 이상 필요하지 않으면 [az group delete](/cli/azure/group#az-group-delete) 명령을 사용하여 리소스 그룹, 컨테이너 서비스 및 모든 관련 리소스를 제거합니다. 

> [!NOTE]
> 클러스터를 삭제해도 AKS 클러스터에서 사용하는 Microsoft Entra 서비스 주체는 제거되지 않습니다. 서비스 주체를 제거하는 방법에 대한 단계는 [AKS 서비스 주체 고려 사항 및 삭제](../../aks/kubernetes-service-principal.md#other-considerations)를 참조하세요. 관리 ID를 사용하는 경우 ID는 플랫폼에 의해 관리되며 제거할 필요가 없습니다.

## 다음 단계

- AKS 클러스터에 대한 [Kubernetes 웹 대시보드에 액세스](../../aks/kubernetes-dashboard.md)하는 방법 알아보기
- [클러스터 크기를 조정](../../aks/tutorial-kubernetes-scale.md)하는 방법 알아보기
- [Azure Database for MySQL 유연한 서버 인스턴스](./quickstart-create-server-cli.md)를 관리하는 방법을 알아봅니다.
- 데이터베이스 서버에 대한 [서버 매개 변수를 구성](./how-to-configure-server-parameters-cli.md)하는 방법 알아보기
