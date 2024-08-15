---
title: 建立基礎結構以在 AKS 上部署高可用性 PostgreSQL 資料庫
description: 使用 CloudNativePG 運算子建立在 AKS 上部署高可用性 PostgreSQL 資料庫所需的基礎結構。
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# 建立基礎結構以在 AKS 上部署高可用性 PostgreSQL 資料庫

在本文中，您會使用 [CloudNativePG (CNPG)](https://cloudnative-pg.io/) 運算子，建立在 AKS 上部署高可用性 PostgreSQL 資料庫所需的基礎結構。

## 開始之前

* 檢閱部署概觀，並確定您符合[如何使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 資料庫][postgresql-ha-deployment-overview]中的所有必要條件。
* [設定環境變數](#set-environment-variables)，以在整個指南中使用。
* [安裝必要的延伸模組](#install-required-extensions)。

## 設定環境變數

設定下列環境變數，以在整個指南中使用：

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

## 安裝必要的延伸模組

`aks-preview`、 `k8s-extension` 及 `amg` 延伸模組提供更多功能來管理 Kubernetes 叢集和查詢 Azure 資源。 使用下列 [`az extension add`][az-extension-add] 命令安裝這些延伸模組：

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

作為使用 kubectl 的必要條件，必須先安裝 [Krew][install-krew]，然後安裝 [CNPG 外掛程式][cnpg-plugin]。 這會使用後續命令來啟用 PostgreSQL 運算子的管理。

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

## 建立資源群組

使用 [`az group create`][az-group-create] 命令，建立資源群組以保存您在本指南中建立的資源。

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## 建立使用者指派的受控識別

在本節中，您會建立使用者指派的受控識別 (UAMI)， 以允許 CNPG PostgreSQL 使用 AKS 工作負載身分識別來存取 Azure Blob 儲存體。 此設定可讓 AKS 上的 PostgreSQL 叢集在沒有秘密的情況下連線到 Azure Blob 儲存體。

1. 使用 [`az identity create`][az-identity-create] 命令建立使用者指派的受控識別。

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. 使用下列命令，啟用 AKS 工作負載身分識別並產生服務帳戶，以供本指南稍後使用：

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

物件識別碼是用戶端識別碼的唯一識別碼 (也稱為應用程式識別碼)，可唯一識別 Entra ID 租用戶內*應用程式*類型的安全性主體。 資源識別碼是用來管理和尋找 Azure 中資源的唯一識別碼。 啟用 AKS 工作負載身分識別需要這些值。

CNPG 操作員會自動產生名為 *postgres* 的服務帳戶，您稍後在指南中用來建立同盟認證，以啟用從 PostgreSQL 到 Azure 儲存體的 OAuth 存取。

## 在主要區域中建立儲存體帳戶

1. 使用 [`az storage account create`][az-storage-account-create] 命令，建立物件儲存體帳戶，以將 PostgreSQL 備份儲存在主要區域中。

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

1. 建立儲存體容器，以使用 [`az storage container create`][az-storage-container-create] 命令來儲存「預先寫入記錄」(WAL) 和一般 PostgreSQL 隨選和排程備份。

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    範例輸出：

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > 如果您遇到錯誤訊息 `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`。 請確認 Azure Blob 儲存體的使用者權限，如果**有需要**，請使用下列和重試 [`az storage container create`][az-storage-container-create] 命令之後，將您的角色提升至 `Storage Blob Data Owner`。

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

## 將 RBAC 指派給儲存體帳戶

若要啟用備份，PostgreSQL 叢集必須讀取和寫入物件存放區。 在 AKS 上執行的 PostgreSQL 叢集會使用工作負載識別，透過 CNPG 運算子設定參數 [`inheritFromAzureAD`][inherit-from-azuread] 來存取儲存體帳戶。

1. 使用 [`az storage account show`][az-storage-account-show] 命令取得儲存體帳戶的主要資源識別碼。

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. 使用 [`az role assignment create`][az-role-assignment-create] 命令，將「儲存體 Blob 資料參與者」Azure 內建角色指派給具有與每個 AKS 叢集受控識別相關聯之 UAMI 儲存體帳戶資源識別碼範圍的物件識別碼。

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## 設定監視基礎結構

在本節中，您會部署 Azure 受控 Grafana、Azure 監視器工作區及 Azure 監視器 Log Analytics 工作區的執行個體，以啟用 PostgreSQL 叢集的監視。 您也會在本指南稍後的 AKS 叢集建立流程期間儲存所建立監視基礎結構的參考，以作為輸入。 本節可能需要一些時間才能完成。

> [!NOTE]
> Azure 受控 Grafana 執行個體和 AKS 叢集會獨立計費。 如需詳細資訊，請參閱 [Azure 受控 Grafana 定價][azure-managed-grafana-pricing]。

1. 使用 [`az grafana create`][az-grafana-create] 命令建立 Azure 受控 Grafana 執行個體。

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

1. 使用 [`az monitor account create`][az-monitor-account-create] 命令建立 Azure 監視器工作區。

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

1. 使用 [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] 命令建立 Azure 監視器 Log Analytics 工作區。

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

## 建立 AKS 叢集以裝載 PostgreSQL 叢集

在本節中，您會使用系統節點集區建立多區域 AKS 叢集。 AKS 叢集裝載 PostgreSQL 叢集主要複本和兩個待命複本，每個復本都與不同的可用性區域對齊，以啟用區域性備援。

您也可以將用戶節點集區新增至 AKS 叢集，以裝載 PostgreSQL 叢集。 使用個別節點集區可讓您控制用於 PostgreSQL 的 Azure VM SKU，並讓 AKS 系統集區將效能和成本最佳化。 您會將標籤套用至使用者節點集區，您可以在本指南稍後部署 CNPG 運算子時參考節點選項。 本節可能需要一些時間才能完成。

1. 使用 [`az aks create`][az-aks-create] 命令建立 AKS 叢集。

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

2. 使用 [`az aks nodepool add`][az-aks-node-pool-add] 命令，將使用者節點集區新增至 AKS 叢集。

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
> 如果您在新增 AKS 節點集區時收到錯誤訊息 `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."`，請等候幾分鐘，讓 AKS 叢集作業完成，然後執行 `az aks nodepool add` 命令。

## 連線到 AKS 叢集並建立命名空間

在本節中，您會取得 AKS 叢集認證，其做為金鑰，可讓您使用叢集進行驗證與互動。 連線之後，您會建立兩個命名空間：一個用於 CNPG 控制器管理員服務，另一個用於 PostgreSQL 叢集及其相關服務。

1. 使用 [`az aks get-credentials`][az-aks-get-credentials] 命令以取得 ASK 叢集認證。

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. 使用 [`kubectl create namespace`][kubectl-create-namespace] 命令，建立 CNPG 控制器管理員服務的命名空間、PostgreSQL 叢集及其相關服務。

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## 更新監視基礎結構

受控 Prometheus 和 Azure Managed Grafana 的 Azure 監視器工作區會自動連結至 AKS 叢集，以取得叢集建立流程期間的計量和視覺效果。 在本節中，您會使用 AKS 容器深入解析來啟用記錄收集，並驗證受控 Prometheus 正在擷取計量，而容器深入解析正在擷取記錄。

1. 使用 [`az aks enable-addons`][az-aks-enable-addons] 命令，在 AKS 叢集上啟用容器深入解析監視。

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. 使用 [`kubectl get`][kubectl-get] 命令和 [`az aks show`][az-aks-show] 命令來檢查 DaemonSet，驗證受控 Prometheus 正在擷取計量，而容器深入解析正在從 AKS 叢集內嵌記錄。

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

    您的輸出應該類似下列範例輸出，其中總共*六個*節點 (系統節點集區有三個，PostgreSQL 節點集區有三個)，以及顯示 `"enabled": true` 的容器深入解析：

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

## 建立 PostgreSQL 叢集輸入的公用靜態 IP

若要驗證 PostgreSQL 叢集的部署，並使用用戶端 PostgreSQL 工具，例如 *psql* 和 *PgAdmin*，您必須公開主要和唯讀複本以輸入。 在本節中，您會建立 Azure 公用 IP 資源，以供稍後提供給 Azure 負載平衡器，以公開 PostgreSQL 端點以供查詢。

1. 使用 [`az aks show`][az-aks-show] 命令取得 AKS 叢集節點資源群組的名稱。

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. 使用 [`az network public-ip create`][az-network-public-ip-create] 命令建立公用 IP 位址。

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

3. 使用 [`az network public-ip show`][az-network-public-ip-show] 命令取得新建立的公用 IP 位址。

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. 使用 [`az group show`][az-group-show] 命令取得節點資源群組的資源識別碼。

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. 使用節點資源群組範圍，使用 [`az role assignment create`][az-role-assignment-create] 命令，將「網路參與者」角色指派給 UAMI 物件識別碼。

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## 在 AKS 叢集中安裝 CNPG 運算子

在本節中，您會使用 Helm 或 YAML 指令清單，在 AKS 叢集中安裝 CNPG 運算子。

### [Helm](#tab/helm)

1. 使用 [`helm repo add`][helm-repo-add] 命令新增 CNPG Helm 存放庫。

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. 升級 CNPG Helm 存放庫，並使用具有 `--install` 旗標的 [`helm upgrade`][helm-upgrade] 命令，將其安裝在 AKS 叢集上。

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. 使用 [`kubectl get`][kubectl-get] 命令，確認 AKS 叢集上的運算子安裝。

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. 使用 [`kubectl apply`][kubectl-apply] 命令，在 AKS 叢集上安裝 CNPG 運算子。

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. 使用 [`kubectl get`][kubectl-get] 命令，確認 AKS 叢集上的運算子安裝。

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## 下一步

> [!div class="nextstepaction"]
> [在 AKS 叢集上部署高可用性 PostgreSQL 資料庫][deploy-postgresql]

## 參與者

*本文由 Microsoft 維護。它最初是由下列參與者*所撰寫：

* Ken Kilty | 首席 TPM
* Russell de Pina | 首席 TPM
* Adrian Joian |資深客戶工程師
* Jenny Hayes | 資深內容開發人員
* Carol Smith | 資深內容開發人員
* Erin Schaffer |內容開發人員 2

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
