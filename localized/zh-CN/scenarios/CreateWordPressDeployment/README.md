---
title: 教程：使用 Azure CLI 在 AKS 群集上部署 WordPress
description: 了解如何使用 Azure Database for MySQL 灵活服务器在 AKS 上快速构建和部署 WordPress。
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# 教程：使用 Azure Database for MySQL 灵活服务器在 AKS 上部署 WordPress 应用

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![部署到 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

在本教程中，你将使用 Azure CLI 通过 Azure Kubernetes 服务 (AKS) 群集上的 HTTPS 保护的可缩放 WordPress 应用程序部署到 Azure Database for MySQL 灵活服务器。
[AKS](../../aks/intro-kubernetes.md) 是可用于快速部署和管理群集的托管式 Kubernetes 服务。 **[Azure Database for MySQL 灵活服务器](overview.md)** 是一种完全托管的数据库服务，旨在针对数据库管理功能和配置设置提供更精细的控制和更大的灵活性。

> [!NOTE]
> 本快速入门假设读者基本了解 Kubernetes 的概念以及 WordPress 和 MySQL。

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## 先决条件 

在开始之前，请确保已登录到 Azure CLI，并选择了要与 CLI 一起使用的订阅。 请确保[已安装 Helm](https://helm.sh/docs/intro/install/)。

> [!NOTE]
> 如果在本地而不是 Azure Cloud Shell 中运行本教程中的命令，请以管理员身份运行命令。

## 定义环境变量

本教程的第一步是定义环境变量。

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

## 创建资源组

Azure 资源组是用于部署和管理 Azure 资源的逻辑组。 所有资源都必须在资源组中部署。 以下命令使用前面定义的 `$MY_RESOURCE_GROUP_NAME` 和 `$REGION` 参数创建一个资源组。

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

结果：
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
> 此位置是资源组元数据的存储位置。 如果在资源创建期间未指定另一个区域，则它还是你的资源在 Azure 中的运行位置。

## 创建虚拟网络和子网

虚拟网络是 Azure 中专用网络的基本构建块。 Azure 虚拟网络能让 Azure 资源（例如 VM）互相安全通信以及与 Internet 通信。

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

结果：
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

## 创建 Azure Database for MySQL 灵活服务器实例

Azure Database for MySQL 灵活服务器是一种托管服务，可用于在云中运行、管理和缩放具有高可用性的 MySQL 服务器。 使用 [az mysql flexible-server create](/cli/azure/mysql/flexible-server) 命令创建 Azure Database for MySQL 灵活服务器实例。 一个服务器可以包含多个数据库。 以下命令使用服务默认值和 Azure CLI 本地上下文中的变量值创建服务器：

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

结果：
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

创建的服务器具有以下属性：

- 首次预配服务器时，将创建一个新的空数据库。
- 服务器名称、管理员用户名、管理员密码、资源组名称和位置已在 Cloud shell 的本地上下文环境中指定，并且与资源组和其他 Azure 组件位于同一位置。
- 其余服务器配置的服务默认值为计算层（可突发）、计算大小/SKU (Standard_B2s)、备份保留期（7 天）和 MySQL 版本 (8.0.21)。
- 默认连接方法是使用链接的虚拟网络和自动生成的子网进行专用访问（虚拟网络集成）。

> [!NOTE]
> 创建服务器后，无法更改连接方法。 例如，如果在创建过程中选择了 `Private access (VNet Integration)`，则无法在创建后更改为 `Public access (allowed IP addresses)`。 强烈建议创建采用专用访问的服务器，以使用 VNet 集成安全地访问你的服务器。 若要详细了解专用访问，请参阅[概念文章](./concepts-networking-vnet.md)。

如果要更改任何默认设置，请参阅 Azure CLI [参考文档](/cli/azure//mysql/flexible-server)，以获取可配置 CLI 参数的完整列表。

## 检查 Azure Database for MySQL 灵活服务器状态

创建 Azure Database for MySQL 灵活服务器和支持资源需要几分钟时间。

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## 配置 Azure Database for MySQL 灵活服务器中的服务器参数

你可以使用服务器参数管理 Azure Database for MySQL 灵活服务器配置。 创建服务器时，将使用默认值和推荐值配置服务器参数。

若要显示服务器的某个特定参数的详细信息，请运行 [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) 命令。

### 为 WordPress 集成禁用 Azure Database for MySQL 灵活服务器 SSL 连接参数

还可以修改某些服务器参数的值，以更新 MySQL 服务器引擎的基础配置值。 若要更新服务器参数，请使用 [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) 命令。

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

结果：
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

## 创建 AKS 群集

若要使用 Container Insights 创建 AKS 群集，请使用 [az aks create](/cli/azure/aks#az-aks-create) 命令和 --enable-addons 监视参数****。 以下示例创建名为 myAKSCluster 的自动缩放的可用性区域群集：****

此操作需要几分钟时间。

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
> 创建 AKS 群集时，会自动创建另一个资源组来存储 AKS 资源。 请参阅[为什么使用 AKS 创建两个资源组？](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## 连接到群集

若要管理 Kubernetes 群集，请使用 Kubernetes 命令行客户端 [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/)。 如果使用的是 Azure Cloud Shell，则 `kubectl` 已安装。 以下示例使用 [az aks install-cli](/cli/azure/aks#az-aks-install-cli) 命令在本地安装 `kubectl`。 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

接下来，使用 [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) 命令将 `kubectl` 配置为连接到你的 Kubernetes 群集。 此命令将下载凭据，并将 Kubernetes CLI 配置为使用这些凭据。 该命令使用 `~/.kube/config`，即 [Kubernetes 配置文件](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)的默认位置。 可以使用 **--file** 参数为你的 Kubernetes 配置文件指定其他位置。

> [!WARNING]
> 此命令将覆盖具有相同条目的任何现有凭据。

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

若要验证与群集的连接，请使用 kubectl get 命令返回群集节点列表。

```bash
kubectl get nodes
```

## 安装 NGINX 入口控制器

可使用静态公共 IP 地址创建入口控制器。 如果删除入口控制器，静态公共 IP 地址仍存在。 如果删除 AKS 群集，IP 地址不会保留。
升级入口控制器时，必须将参数传递给 Helm 版本，以确保入口控制器服务知道将分配给它的负载均衡器。 若要使 HTTPS 证书正常工作，请使用 DNS 标签为入口控制器 IP 地址配置完全限定的域名 (FQDN)。 FQDN 应遵循以下形式：$MY_DNS_LABEL.AZURE_REGION_NAME.cloudapp.azure.com。

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

接下来，添加 ingress-nginx Helm 存储库，更新本地 Helm 图表存储库缓存，并通过 Helm 安装 ingress-nginx 加载项。 可在首次部署入口控制器会之后，使用 **--set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** 参数设置 DNS 标签。 在本示例中，使用 **--set controller.service.loadBalancerIP="<STATIC_IP>" 参数**指定在上一步中创建的自己的公共 IP 地址。

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

## 将 HTTPS 终止添加到自定义域

在本教程的这一步，你有一个使用 NGINX 作为入口控制器的 AKS Web 应用，以及一个可用于访问应用程序的自定义域。 下一步是将 SSL 证书添加到域，以便用户可通过 https 安全地访问应用程序。

### 设置证书管理器

若要添加 HTTPS，我们将使用证书管理器。 证书管理器是一种开源工具，用于获取和管理 Kubernetes 部署的 SSL 证书。 证书管理器从常用的公共颁发者和专用颁发者处获取证书，确保证书有效且最新，并尝试在证书到期前的配置时间续订证书。

1. 若要安装证书管理器，必须先创建一个命名空间来运行它。 本教程将证书管理器安装到证书管理器命名空间中。 可以在不同的命名空间中运行证书管理器，但必须对部署清单进行修改。

    ```bash
    kubectl create namespace cert-manager
    ```

2. 现在可以安装证书管理器了。 所有资源都包含在单个 YAML 清单文件中。 使用以下命令安装清单文件：

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. 通过运行以下命令将 `certmanager.k8s.io/disable-validation: "true"` 标签添加到证书管理器命名空间。 这样，证书管理器可以在其自己的命名空间中创建启动 TLS 所需的系统资源。

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## 通过 Helm 图表获取证书

Helm 是一种 Kubernetes 部署工具，用于自动创建、打包、配置应用程序和服务以及将其部署到 Kubernetes 群集。

Cert-manager 提供 Helm 图表，作为在 Kubernetes 上安装的一级方法。

1. 添加 Jetstack Helm 存储库。 此存储库是唯一受支持的 cert-manager 图表源。 Internet 上还有其他镜像和副本，但这些都是非官方的，可能会带来安全风险。

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. 更新本地 Helm 图表存储库缓存。

    ```bash
    helm repo update
    ```

3. 通过 Helm 安装证书管理器加载项。

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 应用证书颁发者 YAML 文件。 ClusterIssuers 是代表证书颁发机构 (CA) 的 Kubernetes 资源，这些资源可以通过遵循证书签名请求来生成签名的证书。 所有证书管理器证书都需要一个已引用的颁发者，该颁发者处于就绪状态以尝试遵循请求。 可以通过 `cluster-issuer-prod.yaml file` 找到我们使用的颁发者。

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## 创建自定义存储类

默认存储类适合最常见的方案，但并非适合所有方案。 在某些情况下，你可能想要使用自己的参数来自定义自己的存储类。 例如，使用以下清单来配置文件共享的 mountOptions。****
对于 Kubernetes 装载的文件共享，fileMode 和 dirMode 的默认值为 0755。************ 可以在存储类对象中指定不同的装载选项。

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## 将 WordPress 部署到 AKS 群集

在本教程中，我们使用由 Bitnami 为 WordPress 生成的现有 Helm 图表。 Bitnami Helm 图表使用本地 MariaDB 作为数据库，因此我们需要重写这些值，以便将应用与 Azure Database for MySQL 配合使用。 可以覆盖文件的值和自定义设置 `helm-wp-aks-values.yaml` 文件。

1. 添加 Wordpress Bitnami Helm 存储库。

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. 更新本地 Helm 图表存储库缓存。

    ```bash
    helm repo update
    ```

3. 通过 Helm 安装 Wordpress 工作负载。

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

结果：
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

## 浏览通过 HTTPS 保护的 AKS 部署

运行以下命令以获取应用程序的 HTTPS 终结点：

> [!NOTE]
> SSL 证书传播通常需要 2-3 分钟，大约需要 5 分钟才能让所有 WordPress POD 副本准备就绪，并且站点可通过 https 完全访问。

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

使用以下命令检查 WordPress 内容是否已正确传送：

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

结果：
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

通过以下 URL 访问网站：

```bash
echo "You can now visit your web server at https://$FQDN"
```

## 清理资源（可选）

若要避免 Azure 费用，应清除不需要的资源。 如果不再需要群集，可以使用 [az group delete](/cli/azure/group#az-group-delete) 命令删除资源组、容器服务及所有相关资源。 

> [!NOTE]
> 删除群集时，AKS 群集使用的 Microsoft Entra 服务主体不会被删除。 有关如何删除服务主体的步骤，请参阅 [AKS 服务主体的注意事项和删除](../../aks/kubernetes-service-principal.md#other-considerations)。 如果你使用了托管标识，则该标识由平台托管，不需要删除。

## 后续步骤

- 了解如何[访问 AKS 群集的 Kubernetes Web 仪表板](../../aks/kubernetes-dashboard.md)
- 了解如何[缩放群集](../../aks/tutorial-kubernetes-scale.md)
- 了解如何管理 [Azure Database for MySQL 灵活服务器实例](./quickstart-create-server-cli.md)
- 了解如何为数据库服务器[配置服务器参数](./how-to-configure-server-parameters-cli.md)