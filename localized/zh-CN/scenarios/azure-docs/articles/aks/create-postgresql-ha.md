---
title: 创建基础结构以在 AKS 上部署高可用性 PostgreSQL 数据库
description: 使用 CloudNativePG 运算符创建在 AKS 上部署高可用性 PostgreSQL 数据库所需的基础结构。
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# 创建基础结构以在 AKS 上部署高可用性 PostgreSQL 数据库

在本文中，使用 [CloudNativePG (CNPG)](https://cloudnative-pg.io/) 运算符创建在 AKS 上部署高可用性 PostgreSQL 数据库所需的基础结构。

## 开始之前

* 查看部署概述，并确保满足“[如何使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 数据库][postgresql-ha-deployment-overview]”中的所有先决条件。
* [设置环境变量](#set-environment-variables)以在本指南中使用。
* [安装所需的扩展](#install-required-extensions)。

## 设置环境变量。

设置以下环境变量以在本指南中使用：

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

## 安装所需的扩展

`aks-preview`、`k8s-extension` 和 `amg` 扩展提供了用于管理 Kubernetes 群集和查询 Azure 资源的更多功能。 使用以下 [`az extension add`][az-extension-add] 命令安装这些扩展：

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

作为使用 kubectl 的先决条件，必须先安装 [Krew][install-krew]，然后安装 [CNPG 插件][cnpg-plugin]。 这将允许使用后续命令管理 PostgreSQL 运算符。

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

## 创建资源组

使用 [`az group create`][az-group-create] 命令创建一个资源组以保存在本指南中创建的资源。

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## 创建用户分配的托管标识

在本节中，创建用户分配的托管标识 (UAMI)，以允许 CNPG PostgreSQL 使用 AKS 工作负载标识访问 Azure Blob 存储。 此配置允许 AKS 上的 PostgreSQL 群集在没有机密的情况下连接到 Azure Blob 存储。

1. 使用 [`az identity create`][az-identity-create] 命令创建用户分配的托管标识。

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. 使用以下命令启用 AKS 工作负载标识并生成服务帐户，以在本指南的后面部分使用：

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

对象 ID 是客户端 ID（也称为应用程序 ID）的唯一标识符，用于唯一标识 Entra ID 租户中“应用程序”类型的安全主体**。 资源 ID 是一个唯一标识符，用于管理和查找 Azure 中的资源。 启用 AKS 工作负载标识需要这些值。

CNPG 运算符自动生成一个名为 postgres 的服务帐户，稍后你在指南中使用该帐户创建一个联合凭据，以支持从 PostgreSQL 到 Azure 存储的 OAuth 访问**。

## 在主要区域中创建存储帐户

1. 使用 [`az storage account create`][az-storage-account-create] 命令创建一个对象存储帐户，将 PostgreSQL 备份存储在主要区域中。

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

1. 使用 [`az storage container create`][az-storage-container-create] 命令创建存储容器，以存储预写日志 (WAL) 和常规 PostgreSQL 按需备份和计划备份。

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    示例输出：

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > 如果遇到错误消息：`The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`。 请验证用户对 Azure Blob 存储的权限，如必要，使用下面提供的命令将角色提升为 `Storage Blob Data Owner`，然后重试 [`az storage container create`][az-storage-container-create] 命令****。

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

## 将 RBAC 分配到存储帐户

若要启用备份，PostgreSQL 群集需要读取和写入对象存储。 在 AKS 上运行的 PostgreSQL 群集使用工作负载标识，通过 CNPG 运算符配置参数 [`inheritFromAzureAD`][inherit-from-azuread] 访问存储帐户。

1. 使用 [`az storage account show`][az-storage-account-show] 命令获取存储帐户的主资源 ID。

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. 使用 [`az role assignment create`][az-role-assignment-create] 命令将 Azure 内置角色“存储 Blob 数据参与者”分配到 UAMI 的存储帐户资源 ID 范围与每个 AKS 群集托管标识相关联的对象 ID。

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## 设置监视基础结构

在本节中，部署 Azure 托管 Grafana、Azure Monitor 工作区和 Azure Monitor Log Analytics 工作区的实例，以实现对 PostgreSQL 群集的监视。 此外，在本指南后面的 AKS 群集创建过程中，存储对创建的监视基础结构的引用，以用作输入。 本节可能需要一些时间才能完成。

> [!NOTE]
> Azure 托管 Grafana 实例和 AKS 群集单独计费。 有关更多定价信息，请参阅 [Azure 托管 Grafana 定价][azure-managed-grafana-pricing]。

1. 使用 [`az grafana create`][az-grafana-create] 命令创建 Azure 托管 Grafana 实例。

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

1. 使用 [`az monitor account create`][az-monitor-account-create] 命令创建 Azure Monitor 工作区。

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

1. 使用 [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] 命令创建 Azure Monitor Log Analytics 工作区。

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

## 创建 AKS 群集以托管 PostgreSQL 群集

在本节中，使用系统节点池创建多区域 AKS 群集。 AKS 群集托管 PostgreSQL 群集主要副本和两个备用副本，每个副本都与不同的可用性区域保持一致，以实现区域冗余。

还可将用户节点池添加到 AKS 群集，以托管 PostgreSQL 群集。 使用单独的节点池可控制用于 PostgreSQL 的 Azure VM SKU，并使 AKS 系统池能够优化性能和成本。 将标签应用于用户节点池，在本指南后面部署 CNPG 运算符时，可引用该标签进行节点选择。 本节可能需要一些时间才能完成。

1. 使用 [`az aks create`][az-aks-create] 命令创建 AKS 群集。

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

2. 使用 [`az aks nodepool add`][az-aks-node-pool-add] 命令将用户节点池添加到 AKS 群集。

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
> 如果在添加 AKS 节点池时收到错误消息 `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."`，请等待几分钟，让 AKS 群集操作完成，然后运行 `az aks nodepool add` 命令。

## 连接到 AKS 群集并创建命名空间

在本节中，获取 AKS 群集凭据，这些凭据充当允许你进行身份验证并与群集交互的密钥。 连接后，创建两个命名空间：一个用于 CNPG 控制器管理器服务，一个用于 PostgreSQL 群集及其相关服务。

1. 使用 [`az aks get-credentials`][az-aks-get-credentials] 命令获取 AKS 群集凭据。

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. 使用 [`kubectl create namespace`][kubectl-create-namespace] 命令为 CNPG 控制器管理器服务、PostgreSQL 群集及其相关服务创建命名空间。

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## 更新监视基础结构

在群集创建过程中，适用于托管 Prometheus 的 Azure Monitor 工作区和 Azure 托管 Grafana 自动链接到 AKS 群集，以实现指标和可视化。 在本节中，使用 AKS 容器见解启用日志收集，并验证托管 Prometheus 是否正在抓取指标，并且容器见解正在引入日志。

1. 使用 [`az aks enable-addons`][az-aks-enable-addons] 命令在 AKS 群集上启用容器见解监视。

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. 使用 [`kubectl get`][kubectl-get] 命令和 [`az aks show`][az-aks-show] 命令检查 DaemonSet，验证托管 Prometheus 是否正在抓取指标，且容器见解是否正在从 AKS 群集引入日志。

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

    输出应类似于以下示例输出，共 6 个节点（3 个用于系统节点池，3 个用于 PostgreSQL 节点池），且容器见解显示 `"enabled": true`**：

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

## 为 PostgreSQL 群集入口创建公共静态 IP

若要验证 PostgreSQL 群集的部署并使用客户端 PostgreSQL 工具（如 psql 和 PgAdmin），需要向入口公开主要副本和只读副本****。 在本节中，创建一个 Azure 公共 IP 资源，稍后你会将该资源提供给 Azure 负载均衡器，以公开 PostgreSQL 终结点以供查询。

1. 使用 [`az aks show`][az-aks-show] 命令获取 AKS 群集节点资源组的名称。

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. 使用 [`az network public-ip create`][az-network-public-ip-create] 命令创建公共 IP 地址。

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

3. 使用 [`az network public-ip show`][az-network-public-ip-show] 命令获取新创建的公共 IP 地址。

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. 使用 [`az group show`][az-group-show] 命令获取节点资源组的资源 ID。

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. 使用 [`az role assignment create`][az-role-assignment-create] 命令，通过节点资源组范围将“网络参与者”角色分配到 UAMI 对象 ID。

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## 在 AKS 群集中安装 CNPG 运算符

在本节中，使用 Helm 或 YAML 清单在 AKS 群集中安装 CNPG 运算符。

### [Helm](#tab/helm)

1. 使用 [`helm repo add`][helm-repo-add] 命令添加 CNPG Helm 存储库。

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. 升级 CNPG Helm 存储库，并使用带有 `--install` 标志的 [`helm upgrade`][helm-upgrade] 命令在 AKS 群集上安装它。

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. 使用 [`kubectl get`][kubectl-get] 命令验证 AKS 群集上的运算符安装。

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. 使用 [`kubectl apply`][kubectl-apply] 命令在 AKS 群集上安装 CNPG 运算符。

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. 使用 [`kubectl get`][kubectl-get] 命令验证 AKS 群集上的运算符安装。

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## 后续步骤

> [!div class="nextstepaction"]
> [在 AKS 群集上部署高可用性 PostgreSQL 数据库][deploy-postgresql]

## 供稿人

*本文由Microsoft维护。它最初由以下参与者*编写：

* Ken Kilty | 首席 TPM
* Russell de Pina | 首席 TPM
* Adrian Joian | 高级客户工程师
* Jenny Hayes | 高级内容开发人员
* Carol Smith | 高级内容开发人员
* Erin Schaffer | 内容开发人员 2

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
