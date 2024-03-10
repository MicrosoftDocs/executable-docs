---
title: 在 AKS 上部署可調整且安全的 WordPress 實例
description: 本教學課程示範如何透過 CLI 在 AKS 上部署可調整且安全的 WordPress 實例
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# 快速入門：在 AKS 上部署可調整且安全的 WordPress 實例

[![部署至 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

歡迎使用本教學課程，我們將逐步逐步建立透過 HTTPs 保護的 Azure Kubernetes Web 應用程式。 本教學課程假設您已登入 Azure CLI，並已選取要搭配 CLI 使用的訂用帳戶。 它也假設您已安裝 Helm （[指示可以在這裡](https://helm.sh/docs/intro/install/)找到）。

## 定義環境變數

本教學課程的第一個步驟是定義環境變數。

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

## 建立資源群組

資源群組是相關資源的容器。 所有資源都必須放在資源群組中。 我們將為此教學課程建立一個。 下列命令會使用先前定義的 $MY_RESOURCE_GROUP_NAME 和 $REGION 參數來建立資源群組。

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

結果：

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

## 建立 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器

適用於 MySQL 的 Azure 資料庫 - 彈性伺服器是受控服務，可用來在雲端中執行、管理及調整高可用性 MySQL 伺服器。 使用 [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) 命令建立彈性伺服器。 伺服器可以包含多個資料庫。 下列命令會使用 Azure CLI 本機環境的服務預設值和變數值來建立伺服器：

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

結果：

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

建立的伺服器具有下列屬性：

- 伺服器名稱、管理員使用者名稱、系統管理員密碼、資源組名、位置已在CloudShell的本機內容環境中指定，而且會建立在與您是資源群組和其他 Azure 元件相同的位置。
- 其餘伺服器組態的服務預設值：計算層（高載）、計算大小/SKU（Standard_B2s）、備份保留期間（7 天），以及 MySQL 版本（8.0.21）
- 默認連線方法是私人存取（VNet 整合）與連結的虛擬網路和自動產生的子網。

> [!NOTE]
> 建立伺服器之後，無法變更連線方法。 例如，如果您在建立期間選取 `Private access (VNet Integration)` ，則無法在建立之後變更為 `Public access (allowed IP addresses)` 。 強烈建議建立具有私人存取權的伺服器，以使用 VNet 整合安全地存取您的伺服器。 在概念文章[中](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet)深入瞭解私人存取。

如果您想要變更任何預設值，請參閱 Azure CLI [參考檔](https://learn.microsoft.com/cli/azure//mysql/flexible-server) ，以取得可設定 CLI 參數的完整清單。

## 檢查 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器狀態

建立 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器和支持資源需要幾分鐘的時間。

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## 在 適用於 MySQL 的 Azure 資料庫 中設定伺服器參數 - 彈性伺服器

您可以使用伺服器參數來管理 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器組態。 當您建立伺服器時，伺服器參數會設定為預設值和建議的值。

顯示伺服器參數詳細數據 若要顯示伺服器特定參數的詳細數據，請執行 [az mysql flexible-server 參數 show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) 命令。

### 停用 適用於 MySQL 的 Azure 資料庫 - WordPress 整合的彈性伺服器 SSL 連線參數

您也可以修改特定伺服器參數的值，以更新 MySQL 伺服器引擎的基礎組態值。 若要更新伺服器參數，請使用 [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) 命令。

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

結果：

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

## 建立 AKS 叢集

使用 az aks create 命令搭配 --enable-addons 監視參數來建立 AKS 叢集，以啟用容器深入解析。 下列範例會建立名為 myAKSCluster 的自動調整可用性區域已啟用叢集：

這需要幾分鐘的時間

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

## 連線至叢集

若要管理 Kubernetes 叢集，請使用 Kubernetes 命令行用戶端 kubectl。 如果您使用 Azure Cloud Shell，則已安裝 kubectl。

1. 使用 az aks install-cli 命令在本機安裝 az aks CLI

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. 將 kubectl 設定為使用 az aks get-credentials 命令連線到 Kubernetes 叢集。 下列命令：

    - 下載認證並設定 Kubernetes CLI 以使用認證。
    - 使用 ~/.kube/config，這是 Kubernetes 組態檔的預設位置。 使用 --file 自變數指定 Kubernetes 組態檔的不同位置。

    > [!WARNING]
    > 這會以相同的專案覆寫任何現有的認證

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. 使用 kubectl get 命令確認叢集的連線。 此命令會傳回叢集節點的清單。

    ```bash
    kubectl get nodes
    ```

## 安裝 NGINX 輸入控制器

您可以使用靜態公用IP位址來設定輸入控制器。 如果您刪除輸入控制器，靜態公用IP位址會維持不變。 如果您刪除 AKS 叢集，IP 位址不會保留。
當您升級輸入控制器時，必須將參數傳遞至 Helm 版本，以確保輸入控制器服務知道將配置給它的負載平衡器。 若要讓 HTTPS 憑證正常運作，您可以使用 DNS 標籤來設定輸入控制器 IP 位址的 FQDN。
您的 FQDN 應遵循下列格式：$MY_DNS_LABEL。AZURE_REGION_NAME.cloudapp.azure.com。

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

新增 --set controller.service.annotations。」service\.beta\.kubernetes\.io/azure-dns-label-name“=”<DNS_LABEL>“ 參數。 當輸入控制器第一次部署時，可以設定 DNS 標籤，也可以稍後進行設定。 新增 --set controller.service.loadBalancerIP=“<STATIC_IP>” 參數。 指定在上一個步驟中建立的您自己的公用IP位址。

1. 新增 ingress-nginx Helm 存放庫

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. 更新本機 Helm Chart 存放庫快取

    ```bash
    helm repo update
    ```

3. 執行下列命令，透過 Helm 安裝 ingress-nginx 附加元件：

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## 將 HTTPS 終止新增至自訂網域

在本教學課程中，您有一個 AKS Web 應用程式搭配 NGINX 作為輸入控制器，以及可用來存取應用程式的自定義網域。 下一個步驟是將SSL憑證新增至網域，讓使用者可以透過 HTTPs 安全地連線到您的應用程式。

## 設定 Cert Manager

為了新增 HTTPS，我們將使用 Cert Manager。 Cert Manager 是一種 開放原始碼 工具，可用來取得和管理 Kubernetes 部署的 SSL 憑證。 憑證管理員會從各種簽發者取得憑證，包括熱門的公用簽發者以及私人簽發者，並確保憑證有效且最新，而且會在到期前嘗試在設定的某個時間更新憑證。

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

3. 執行下列命令，透過 Helm 安裝 Cert-Manager 附加元件：

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 套用憑證簽發者 YAML 檔案

    ClusterIssuers 是 Kubernetes 資源，代表能夠藉由接受憑證簽署要求來產生已簽署憑證的證書頒發機構單位 （CA）。 所有憑證管理員憑證都需要處於就緒條件的參考簽發者，才能嘗試接受要求。
    我們所使用的簽發者可以在 中找到 `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## 建立自定義儲存類別

默認記憶體類別符合最常見的案例，但並非全部。 在某些情況下，您可能想要使用自己的參數自定義自己的記憶體類別。 例如，使用下列指令清單來設定檔案共用的 mountOptions。
fileMode 和 dirMode 的預設值是 0755，適用於 Kubernetes 掛接的檔案共用。 您可以在記憶體類別物件上指定不同的掛接選項。

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## 將 WordPress 部署至 AKS 叢集

在本檔中，我們使用 Bitnami 建置的現有 WordPress Helm Chart。 例如，Bitnami Helm 圖表使用本機 MariaDB 作為資料庫，我們需要覆寫這些值，以搭配 適用於 MySQL 的 Azure 資料庫 使用應用程式。 所有覆寫值 您可以覆寫值，您可以在檔案中找到自定義設定 `helm-wp-aks-values.yaml`

1. 新增 Wordpress Bitnami Helm 存放庫

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. 更新本機 Helm Chart 存放庫快取

    ```bash
    helm repo update
    ```

3. 執行下列命令，透過 Helm 安裝 Wordpress 工作負載：

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

結果：

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

## 瀏覽透過 HTTPS 保護的 AKS 部署

執行下列命令以取得應用程式的 HTTPS 端點：

> [!NOTE]
> SSL 憑證通常會需要 2-3 分鐘的時間才能進行傳播，大約 5 分鐘才能讓所有 WordPress POD 複本準備就緒，且網站可透過 HTTPs 完全連線。

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

檢查 WordPress 內容是否已正確傳遞。

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

結果：

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

您可以遵循下列 URL 來瀏覽網站：

```bash
echo "You can now visit your web server at https://$FQDN"
```
