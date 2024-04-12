---
title: 教學課程：使用 Azure CLI 在 AKS 叢集上部署 WordPress
description: 瞭解如何使用 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器在 AKS 上快速建置及部署 WordPress。
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# 教學課程：使用 適用於 MySQL 的 Azure 資料庫 在 AKS 上部署 WordPress 應用程式 - 彈性伺服器

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![部署至 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

在本教學課程中，您會在 Azure Kubernetes Service （AKS） 叢集上部署可調整的 WordPress 應用程式，並使用 Azure CLI 搭配 適用於 MySQL 的 Azure 資料庫 彈性伺服器來保護。
**[AKS](../../aks/intro-kubernetes.md)** 是受控 Kubernetes 服務，可讓您快速部署和管理叢集。 **[適用於 MySQL 的 Azure 資料庫 彈性伺服器](overview.md)** 是完全受控的資料庫服務，其設計目的是要針對資料庫管理功能和組態設定提供更細微的控制與彈性。

> [!NOTE]
> 本教學課程假設對 Kubernetes 概念、WordPress 和 MySQL 有基本的瞭解。

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## 必要條件 

開始之前，請確定您已登入 Azure CLI，並已選取要搭配 CLI 使用的訂用帳戶。 請確定您已安裝 [](https://helm.sh/docs/intro/install/)Helm。

> [!NOTE]
> 如果您在本教學課程中執行命令，而不是 Azure Cloud Shell，請以系統管理員身分執行命令。

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

Azure 資源群組是部署及管理 Azure 資源所在的邏輯群組。 所有資源都必須放在資源群組中。 下列命令會使用先前定義的 `$MY_RESOURCE_GROUP_NAME` 和 `$REGION` 參數來建立資源群組。

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

> [!NOTE]
> 資源群組的位置是儲存資源群組元數據的位置。 如果您未在資源建立期間指定另一個區域，您也可以在 Azure 中執行資源。

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

## 建立 適用於 MySQL 的 Azure 資料庫 彈性伺服器實例

適用於 MySQL 的 Azure 資料庫 彈性伺服器是受控服務，可用來在雲端中執行、管理及調整高可用性 MySQL 伺服器。 使用 [az mysql flexible-server create](/cli/azure/mysql/flexible-server) 命令建立 適用於 MySQL 的 Azure 資料庫 彈性伺服器實例。 伺服器可以包含多個資料庫。 下列命令會使用 Azure CLI 本機內容中的服務預設值和變數值來建立伺服器：

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

- 第一次布建伺服器時，會建立新的空白資料庫。
- 伺服器名稱、管理員用戶名稱、管理員密碼、資源組名和位置已指定於 Cloud Shell 的本機內容環境中，且與資源群組和其他 Azure 元件位於相同的位置。
- 其餘伺服器組態的服務預設值為計算層（高載）、計算大小/SKU（Standard_B2s）、備份保留期間（7 天），以及 MySQL 版本（8.0.21）。
- 默認連線方法是私人存取（虛擬網路整合）與連結的虛擬網路和自動產生的子網。

> [!NOTE]
> 建立伺服器之後，無法變更連線方法。 例如，如果您在建立期間選取 `Private access (VNet Integration)` ，則無法在建立之後變更為 `Public access (allowed IP addresses)` 。 強烈建議建立具有私人存取權的伺服器，以使用 VNet 整合安全地存取您的伺服器。 在概念文章[中](./concepts-networking-vnet.md)深入瞭解私人存取。

如果您想要變更任何預設值，請參閱 Azure CLI [參考檔](/cli/azure//mysql/flexible-server) ，以取得可設定 CLI 參數的完整清單。

## 檢查 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器狀態

建立 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器和支持資源需要幾分鐘的時間。

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## 在 適用於 MySQL 的 Azure 資料庫 中設定伺服器參數 - 彈性伺服器

您可以使用伺服器參數來管理 適用於 MySQL 的 Azure 資料庫 - 彈性伺服器組態。 當您建立伺服器時，伺服器參數會設定為預設值和建議值。

若要顯示伺服器特定參數的詳細數據，請執行 [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) 命令。

### 停用 適用於 MySQL 的 Azure 資料庫 - WordPress 整合的彈性伺服器 SSL 連線參數

您也可以修改特定伺服器參數的值，以更新 MySQL 伺服器引擎的基礎組態值。 若要更新伺服器參數，請使用 [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) 命令。

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

若要使用 Container Insights 建立 AKS 叢集，請使用 [az aks create](/cli/azure/aks#az-aks-create) 命令搭配 **--enable-addons** 監視參數。 下列範例會建立名為 **myAKSCluster** 的自動調整可用性區域啟用叢集：

此動作需要幾分鐘的時間。

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
> 建立 AKS 叢集時，會自動建立第二個資源群組來儲存 AKS 資源。 請參閱 [為什麼使用 AKS 建立兩個資源群組？](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## 連線至叢集

若要管理 Kubernetes 叢集，請使用 Kubernetes 命令列用戶端：[kubectl](https://kubernetes.io/docs/reference/kubectl/overview/)。 如果您使用 Azure Cloud Shell，則 `kubectl` 已安裝。 下列範例會使用 [az aks install-cli](/cli/azure/aks#az-aks-install-cli) 命令在本機安裝`kubectl`。 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

接下來，將 設定 `kubectl` 為使用 [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) 命令連線到 Kubernetes 叢集。 此命令會下載憑證並設定 Kubernetes CLI 以供使用。 此命令會使用 `~/.kube/config`，這是 Kubernetes 組態檔[的預設位置](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)。 您可使用 **--file** 引數，為您的 Kubernetes 組態檔指定不同的位置。

> [!WARNING]
> 此命令會以相同的專案覆寫任何現有的認證。

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

若要驗證針對您叢集的連線，請使用 [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) 命令來傳回叢集節點的清單。

```bash
kubectl get nodes
```

## 安裝 NGINX 輸入控制器

您可以使用靜態公用 IP 位址來設定輸入控制器。 如果您刪除輸入控制器，則仍會保留靜態公用 IP 位址。 如果您刪除 AKS 叢集，則「不」會保留 IP 位址。
當您升級輸入控制器時，必須將參數傳遞至 Helm 版本，確保輸入控制器服務知道將對其進行配置的負載平衡器。 若要讓 HTTPS 憑證正常運作，請使用 DNS 標籤來設定輸入控制器 IP 位址的完整功能變數名稱 （FQDN）。 您的 FQDN 應遵循下列格式：$MY_DNS_LABEL。AZURE_REGION_NAME.cloudapp.azure.com。

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

接下來，您會新增ingress-nginx Helm存放庫、更新本機 Helm 圖表存放庫快取，以及透過 Helm 安裝 ingress-nginx 附加元件。 您可以使用 --set controller.service.annotations 來設定 DNS 卷標 **。當您第一次部署輸入控制器或更新版本時，service\.beta\.kubernetes\.io/azure-dns-label-name“=”<DNS_LABEL>“** 參數。 在此範例中，您會使用 --set controller.service.loadBalancerIP=“<STATIC_IP>” 參數 **，指定您在上一個步驟**中建立的公用 IP 位址。

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

## 將 HTTPS 終止新增至自訂網域

在本教學課程中，您有 AKS Web 應用程式作為輸入控制器，以及可用來存取應用程式的自定義網域。 下一個步驟是將SSL憑證新增至網域，讓使用者可以透過 HTTPs 安全地連線到您的應用程式。

### 設定 Cert Manager

若要新增 HTTPS，我們將使用 Cert Manager。 Cert Manager 是用來取得和管理 Kubernetes 部署 SSL 憑證的 開放原始碼 工具。 Cert Manager 會從熱門的公用簽發者和私人簽發者取得憑證、確保憑證有效且最新，並嘗試在到期前的設定時間更新憑證。

1. 若要安裝 cert-manager，我們必須先建立命名空間來執行它。 本教學課程會將 cert-manager 安裝至 cert-manager 命名空間。 您可以在不同的命名空間中執行 cert-manager，但您必須修改部署指令清單。

    ```bash
    kubectl create namespace cert-manager
    ```

2. 我們現在可以安裝 cert-manager。 所有資源都包含在單一 YAML 指令清單檔案中。 使用下列指令安裝指令清單檔：

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. 執行下列命令，將標籤 `certmanager.k8s.io/disable-validation: "true"` 新增至 cert-manager 命名空間。 這可讓憑證管理員需要的系統資源在自己的命名空間中建立啟動 TLS。

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## 透過 Helm 圖表取得憑證

Helm 是 Kubernetes 部署工具，可將應用程式和服務的建立、封裝、組態和部署自動化至 Kubernetes 叢集。

Cert-manager 提供 Helm 圖表作為 Kubernetes 上安裝的一流方法。

1. 新增 Jetstack Helm 存放庫。 此存放庫是唯一支援的憑證管理員圖表來源。 因特網上有其他鏡像和複本，但這些鏡像是非官方的，而且可能會造成安全性風險。

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. 更新本機 Helm Chart 存放庫快取。

    ```bash
    helm repo update
    ```

3. 透過 Helm 安裝 Cert-Manager 附加元件。

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 套用憑證簽發者 YAML 檔案。 ClusterIssuers 是 Kubernetes 資源，代表可藉由接受憑證簽署要求來產生已簽署憑證的證書頒發機構單位 （CA）。 所有憑證管理員憑證都需要處於就緒條件的參考簽發者，才能嘗試接受要求。 您可以在 中找到我們在 中的 `cluster-issuer-prod.yaml file`簽發者。

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## 建立自訂儲存類別

預設儲存類別符合最常見的案例，但並非全部。 在某些情況下，您可能想要使用自有參數來自訂自己的儲存類別。 例如，使用下列指令清單來設定 **檔案共用的 mountOptions** 。
fileMode** 和 dirMode** 的**預設值是 **0755**，適用於 Kubernetes 掛接的檔案**共用。 您可以在儲存類別物件上指定不同的掛接選項。

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## 將 WordPress 部署至 AKS 叢集

在本教學課程中，我們會針對 Bitnami 所建置的 WordPress 使用現有的 Helm 圖表。 Bitnami Helm 圖表會使用本機 MariaDB 作為資料庫，因此我們需要覆寫這些值，以搭配 適用於 MySQL 的 Azure 資料庫 使用應用程式。 您可以覆寫值和檔案的 `helm-wp-aks-values.yaml` 自訂設定。

1. 新增 Wordpress Bitnami Helm 存放庫。

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. 更新本機 Helm 圖表存放庫快取。

    ```bash
    helm repo update
    ```

3. 透過 Helm 安裝 Wordpress 工作負載。

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
> SSL 憑證傳播需要 2-3 分鐘的時間，大約 5 分鐘才能讓所有 WordPress POD 複本準備就緒，且網站可透過 HTTPs 完全連線。

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

使用下列命令檢查 WordPress 內容是否已正確傳遞：

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

透過下列 URL 瀏覽網站：

```bash
echo "You can now visit your web server at https://$FQDN"
```

## 清除資源 （選擇性）

若要避免 Azure 費用，您應該清除不需要的資源。 當您不再需要叢集時，請使用 [az group delete](/cli/azure/group#az-group-delete) 命令來移除資源群組、容器服務和所有相關資源。 

> [!NOTE]
> 當您刪除叢集時，系統不會移除 AKS 叢集所使用的 Microsoft Entra 服務主體。 如需有關如何移除服務主體的步驟，請參閱 [AKS 服務主體的考量和刪除](../../aks/kubernetes-service-principal.md#other-considerations)。 如果您使用受控識別，則身分識別會由平台負責管理，您不需要刪除。

## 下一步

- 瞭解如何[存取 AKS 叢集的 Kubernetes Web 儀錶板](../../aks/kubernetes-dashboard.md)
- 瞭解如何 [調整叢集規模](../../aks/tutorial-kubernetes-scale.md)
- 瞭解如何管理 [適用於 MySQL 的 Azure 資料庫 彈性伺服器實例](./quickstart-create-server-cli.md)
- 瞭解如何[設定資料庫伺服器的伺服器參數](./how-to-configure-server-parameters-cli.md)