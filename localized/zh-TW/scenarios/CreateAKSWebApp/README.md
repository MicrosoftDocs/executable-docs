---
title: 使用 Azure CLI 部署可調整且安全的 Azure Kubernetes Service 叢集
description: 本教學課程將逐步帶您建立透過 HTTPs 保護的 Azure Kubernetes Web 應用程式。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# 快速入門：使用 Azure CLI 部署可調整且安全的 Azure Kubernetes Service 叢集

[![部署至 Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

歡迎使用本教學課程，我們將逐步逐步建立透過 HTTPs 保護的 Azure Kubernetes Web 應用程式。 本教學課程假設您已登入 Azure CLI，並已選取要搭配 CLI 使用的訂用帳戶。 它也假設您已安裝 Helm （[指示可以在這裡](https://helm.sh/docs/intro/install/)找到）。

## 定義環境變數

本教學課程的第一個步驟是定義環境變數。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## 建立資源群組

資源群組是相關資源的容器。 所有資源都必須放在資源群組中。 我們將為此教學課程建立一個。 下列命令會使用先前定義的 $MY_RESOURCE_GROUP_NAME 和 $REGION 參數來建立資源群組。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果：

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

## 建立虛擬網路和子網路

虛擬網路是 Azure 中私人網路的基礎建置區塊。 Azure 虛擬網路可讓 Azure 資源 (例如 VM) 彼此安全地通訊，以及與網際網路安全地通訊。

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

結果：

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

## 向 AKS Azure 資源提供者註冊

確認您的訂用帳戶上已註冊 Microsoft.OperationsManagement 和 Microsoft.OperationalInsights 提供者。 這些是支援 [容器深入解析](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview)所需的 Azure 資源提供者。 若要檢查註冊狀態，請執行下列命令

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## 建立 AKS 叢集

使用 az aks create 命令搭配 --enable-addons 監視參數來建立 AKS 叢集，以啟用容器深入解析。 下列範例會建立已啟用自動調整的可用性區域叢集。

這需要幾分鐘的時間。

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

## 連線至叢集

若要管理 Kubernetes 叢集，請使用 Kubernetes 命令列用戶端 kubectl。 如果您使用 Azure Cloud Shell，則已安裝 kubectl。

1. 使用 az aks install-cli 命令在本機安裝 az aks CLI

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. 將 kubectl 設定為使用 az aks get-credentials 命令連線到 Kubernetes 叢集。 下列命令：

   - 下載憑證並設定 Kubernetes CLI 以供使用。
   - 使用 ~/.kube/config，這是 Kubernetes 組態檔的預設位置。 使用 --file 引數，為您的 Kubernetes 組態檔指定不同的位置。

   > [!WARNING]
   > 這會以相同的專案覆寫任何現有的認證

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. 使用 kubectl get nodes 命令來確認與叢集的連線。 此命令會傳回叢集節點的清單。

   ```bash
   kubectl get nodes
   ```

## 安裝 NGINX 輸入控制器

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

## 部署應用程式

Kubernetes 資訊清單檔會定義叢集所需的狀態，例如要執行哪些容器映像。

在本快速入門中，您可以使用資訊清單來建立執行 Azure Vote 應用程式所需的所有物件。 此資訊清單包含兩個 Kubernetes 部署：

- 範例 Azure Vote Python 應用程式。
- Redis 執行個體。

也會建立兩個 Kubernetes Services：

- Redis 執行個體的內部服務。
- 從網際網路存取 Azure Vote 應用程式的外部服務。

最後，會建立輸入資源，以將流量路由傳送至 Azure 投票應用程式。

測試投票應用程式 YML 檔案已備妥。 若要部署此應用程式，請執行下列命令

```bash
kubectl apply -f azure-vote-start.yml
```

## 測試應用程式

造訪公用IP或應用程式URL來驗證應用程式是否正在執行。 您可以執行下列命令來找到應用程式 URL：

> [!Note]
> 建立POD通常需要2-3分鐘的時間，且網站可透過 HTTP 連線

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

結果：

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

## 將 HTTPS 終止新增至自訂網域

在本教學課程中，您有一個 AKS Web 應用程式搭配 NGINX 作為輸入控制器，以及可用來存取應用程式的自定義網域。 下一個步驟是將SSL憑證新增至網域，讓使用者可以透過 HTTPS 安全地連線到您的應用程式。

## 設定 Cert Manager

為了新增 HTTPS，我們將使用 Cert Manager。 Cert Manager 是 開放原始碼 工具，可用來取得和管理 Kubernetes 部署的 SSL 憑證。 憑證管理員會從各種簽發者取得憑證，包括熱門的公用簽發者以及私人簽發者，並確保憑證有效且最新，而且會在到期前嘗試在設定的某個時間更新憑證。

1. 若要安裝 cert-manager，我們必須先建立命名空間來執行它。 本教學課程會將 cert-manager 安裝到 cert-manager 命名空間。 您可以在不同的命名空間中執行 cert-manager，不過您必須對部署指令清單進行修改。

   ```bash
   kubectl create namespace cert-manager
   ```

2. 我們現在可以安裝 cert-manager。 所有資源都包含在單一 YAML 指令清單檔案中。 您可以執行下列命令來安裝：

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. 執行下列命令，將 certmanager.k8s.io/disable-validation：“true” 標籤新增至 cert-manager 命名空間。 這可讓憑證管理員在自己的命名空間中建立啟動 TLS 所需的系統資源。

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## 透過 Helm 圖表取得憑證

Helm 是 Kubernetes 部署工具，可將應用程式和服務的建立、封裝、組態和部署自動化至 Kubernetes 叢集。

Cert-manager 提供 Helm 圖表作為 Kubernetes 上安裝的一流方法。

1. 新增 Jetstack Helm 存放庫

   此存放庫是唯一支援的憑證管理員圖表來源。 因特網上有一些其他鏡像和複本，但這些鏡像是完全非官方的，而且可能會造成安全性風險。

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. 更新本機 Helm Chart 存放庫快取

   ```bash
   helm repo update
   ```

3. 執行下列命令，透過 helm 安裝 Cert-Manager 附加元件：

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. 套用憑證簽發者 YAML 檔案

   ClusterIssuers 是 Kubernetes 資源，代表能夠藉由接受憑證簽署要求來產生已簽署憑證的證書頒發機構單位 （CA）。 所有憑證管理員憑證都需要處於就緒條件的參考簽發者，才能嘗試接受要求。
   我們所使用的簽發者可以在 中找到 `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. 更新投票應用程式應用程式，以使用 Cert-Manager 取得 SSL 憑證。

   您可以在 中找到完整的 YAML 檔案 `azure-vote-nginx-ssl.yml`

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

## 瀏覽透過 HTTPS 保護的 AKS 部署

執行下列命令以取得應用程式的 HTTPS 端點：

> [!Note]
> SSL 憑證通常會需要 2-3 分鐘的時間，才能透過 HTTPS 來傳播和網站。

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

## 後續步驟

- [Azure Kubernetes Service 文件](https://learn.microsoft.com/azure/aks/)
- [建立 Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [在 AKS 中調整 Applciation](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [在 AKS 中更新您的應用程式](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)