---
title: 使用 Azure CLI 部署可缩放的安全 Azure Kubernetes 服务群集
description: 本教程逐步介绍如何创建通过 https 保护的 Azure Kubernetes Web 应用程序。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# 快速入门：使用 Azure CLI 部署可缩放且安全的 Azure Kubernetes 服务群集

[![部署到 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

欢迎学习本教程，我们会逐步介绍如何创建通过 https 保护的 Azure Kubernetes Web 应用程序。 本教程假定你已登录到 Azure CLI，并已选择要与 CLI 一起使用的订阅。 它还假定你已安装 Helm（[说明可在此处找到](https://helm.sh/docs/intro/install/)）。

## 定义环境变量

本教程的第一步是定义环境变量。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## 创建资源组

资源组是相关资源的容器。 所有资源都必须在资源组中部署。 我们将为本教程创建一个资源组。 以下命令创建具有前面定义的 $MY_RESOURCE_GROUP_NAME 和 $REGION 参数的资源组。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

结果：

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
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

```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.xxx.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx",
    "location": "eastus",
    "name": "myVNetxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myAKSResourceGroupxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.xxx.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx/subnets/mySNxxx",
        "name": "mySNxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myAKSResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## 注册到 AKS Azure 资源提供程序

验证是否已在订阅中注册 Microsoft.OperationsManagement 和 Microsoft.OperationalInsights 提供程序。 这些是支持[容器简介](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview)所需的 Azure 资源提供程序。 若要检查注册状态，请运行以下命令

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## 创建 AKS 群集

使用带有 --enable-addons monitoring 参数的 az aks create 命令创建 AKS 群集，以启用 容器见解。 以下示例创建启用自动缩放的可用性区域群集。

这需要几分钟时间。

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
  --zones 1 2 3
```

## 连接到群集

若要管理 Kubernetes 群集，请使用 Kubernetes 命令行客户端 kubectl。 如果使用的是 Azure Cloud Shell，则 kubectl 已安装。

1. 使用 az aks install-cli 命令在本地安装 az aks CLI

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. 使用 az aks get-credentials 命令将 kubectl 配置为连接到 Kubernetes 群集。 以下命令：

   - 下载凭据，并将 Kubernetes CLI 配置为使用这些凭据。
   - 使用 ~/.kube/config，这是 Kubernetes 配置文件的默认位置。 使用 --file 参数指定 Kubernetes 配置文件的其他位置。

   > [!WARNING]
   > 这将覆盖具有相同条目的任何现有凭据

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. 使用 kubectl get 命令验证与群集之间的连接。 此命令将返回群集节点的列表。

   ```bash
   kubectl get nodes
   ```

## 安装 NGINX 入口控制器

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
  --set controller.service.loadBalancerIP=$MY_STATIC_IP \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --wait
```

## 部署应用程序

Kubernetes 清单文件定义群集的所需状态，例如，要运行哪些容器映像。

在本快速入门中，你将使用清单来创建运行 Azure Vote 应用程序所需的所有对象。 此清单包含两个 Kubernetes 部署：

- 示例 Azure Vote Python 应用程序。
- 一个 Redis 实例。

此外，还会创建两个 Kubernetes 服务：

- Redis 实例的内部服务。
- 用于通过 Internet 访问 Azure Vote 应用程序的外部服务。

最后，将创建入口资源以将流量路由到 Azure Vote 应用程序。

测试投票应用 YML 文件已准备好。 若要部署此应用，请运行以下命令

```bash
kubectl apply -f azure-vote-start.yml
```

## 测试应用程序

通过访问公共 IP 或应用程序 URL 来验证应用程序是否正在运行。 可以通过运行以下命令找到应用程序 URL：

> [!Note]
> 通常需要 2-3 分钟才能创建 POD 并通过 HTTP 访问站点

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get pods -l app=azure-vote-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}'); echo $STATUS;
   if [ "$STATUS" == 'True' ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
curl "http://$FQDN"
```

结果：

<!-- expected_similarity=0.3 -->

```HTML
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/default.css">
    <title>Azure Voting App</title>

    <script language="JavaScript">
        function send(form){
        }
    </script>

</head>
<body>
    <div id="container">
        <form id="form" name="form" action="/"" method="post"><center>
        <div id="logo">Azure Voting App</div>
        <div id="space"></div>
        <div id="form">
        <button name="vote" value="Cats" onclick="send()" class="button button1">Cats</button>
        <button name="vote" value="Dogs" onclick="send()" class="button button2">Dogs</button>
        <button name="vote" value="reset" onclick="send()" class="button button3">Reset</button>
        <div id="space"></div>
        <div id="space"></div>
        <div id="results"> Cats - 0 | Dogs - 0 </div>
        </form>
        </div>
    </div>
</body>
</html>
```

## 将 HTTPS 终止添加到自定义域

本教程进行到此，你有一个 AKS Web 应用，其中 NGINX 作为入口控制器，还有一个可用于访问应用程序的自定义域。 下一步是将 SSL 证书添加到域，以便用户可以通过 HTTPS 安全地访问应用程序。

## 设置证书管理器

为了添加 HTTPS，我们将使用证书管理器。 证书管理器是一种开源工具，用于获取和管理用于 Kubernetes 部署的 SSL 证书。 证书管理器将从各种颁发者（常用公共颁发者以及专用颁发者）获取证书，并确保证书有效且最新，并会在到期前于配置时间尝试续订证书。

1. 若要安装证书管理器，必须先创建一个命名空间来运行它。 本教程将证书管理器安装到证书管理器命名空间中。 可以在不同的命名空间中运行证书管理器，不过需要对部署清单进行修改。

   ```bash
   kubectl create namespace cert-manager
   ```

2. 现在可以安装证书管理器了。 所有资源都包含在单个 YAML 清单文件中。 可以通过运行以下命令来安装此文件：

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. 运行以下命令，将 certmanager.k8s.io/disable-validation：“true”标签添加到证书管理器命名空间。 这样，就可以在自己的命名空间中创建 cert-manager 引导 TLS 所需的系统资源。

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## 通过 Helm 图表获取证书

Helm 是一种 Kubernetes 部署工具，用于应用程序和服务的自动创建、打包、配置，以及自动将应用程序和服务部署到 Kubernetes 群集。

Cert-manager 提供 Helm 图表，作为在 Kubernetes 上安装的一级方法。

1. 添加 Jetstack Helm 存储库

   此存储库是唯一受支持的 cert-manager 图表源。 Internet 上还有其他一些镜像和副本，但这些镜像是完全非官方的，可能会带来安全风险。

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. 更新本地 Helm Chart 存储库缓存

   ```bash
   helm repo update
   ```

3. 通过 helm 安装 Cert-Manager 加载项，方法是运行以下命令：

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. 应用证书颁发者 YAML 文件

   ClusterIssuers 是表示证书颁发机构 (CA) 的 Kubernetes 资源，这些资源能够通过遵循证书签名请求来生成签名的证书。 所有证书管理器证书都需要一个已引用的颁发者，该颁发者处于就绪状态以尝试遵循请求。
   可在 `cluster-issuer-prod.yml file` 中找到正在使用的颁发者

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. 启动投票应用应用程序，以使用 Cert-Manager 获取 SSL 证书。

   可以在 `azure-vote-nginx-ssl.yml` 中找到完整的 YAML 文件

   ```bash
   azure_vote_nginx_ssl_variables=$(<azure-vote-nginx-ssl.yml)
   echo "${azure_vote_nginx_ssl_variables//\$FQDN/$FQDN}" | kubectl apply -f -
   ```

<!--## Validate application is working

Wait for the SSL certificate to issue. The following command will query the 
status of the SSL certificate for 3 minutes. In rare occasions it may take up to 
15 minutes for Lets Encrypt to issue a successful challenge and 
the ready state to be 'True'

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(kubectl get certificate --output jsonpath={..status.conditions[0].status}); echo $STATUS; if [ "$STATUS" = 'True' ]; then break; else sleep 10; fi; done
```

Validate SSL certificate is True by running the follow command:

```bash
kubectl get certificate --output jsonpath={..status.conditions[0].status}
```

Results:

<!-- expected_similarity=0.3 -->
<!--
```ASCII
True
```
-->

## 浏览通过 HTTPS 保护的 AKS 部署

运行以下命令以获取应用程序的 HTTPS 终结点：

> [!Note]
> 通常需要 2-3 分钟，SSL 证书才能传播，且站点才能通过 HTTPS 进行访问。

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get svc --namespace=ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}');
   echo $STATUS;
   if [ "$STATUS" == "$MY_STATIC_IP" ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
echo "You can now visit your web server at https://$FQDN"
```

## 后续步骤

- [Azure Kubernetes 服务文档](https://learn.microsoft.com/azure/aks/)
- [创建 Azure 容器注册表](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [在 AKS 中缩放应用程序](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [在 AKS 中更新应用程序](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)
