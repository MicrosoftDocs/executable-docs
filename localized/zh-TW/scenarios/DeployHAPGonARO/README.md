---
title: 在 Azure Red Hat OpenShift 上建立高可用性 PostgreSQL 叢集
description: 本教學課程說明如何使用 CloudNativePG 操作員在 Azure Red Hat OpenShift （ARO） 上建立高可用性 PostgreSQL 叢集
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/30/2024
ms.custom: 'innovation-engine, linux-related content'
---

# 在 Azure Red Hat OpenShift 上建立高可用性 PostgreSQL 叢集

## 使用 CLI 登入 Azure

若要使用 CLI 對 Azure 執行命令，您需要登入。 這樣做很簡單，但 `az login` 命令如下：

## 檢查必要條件

接下來，檢查必要條件。 執行下列命令即可完成此動作：

- RedHat OpenShift： `az provider register -n Microsoft.RedHatOpenShift --wait`
- kubectl： `az aks install-cli`
- Openshift 用戶端： `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## 建立資源群組

資源群組是相關資源的容器。 所有資源都必須放在資源群組中。 我們將為此教學課程建立一個。 下列命令會使用先前定義的 $RG_NAME、$LOCATION 和 $RGTAGS 參數來建立資源群組。

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export RG_NAME="rg-arodemo-perm"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

結果：
<!-- expected_similarity=0.3 -->
```json
{
"id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/xx-xxxxx-xxxxx",
"location": "westus",
"managedBy": null,
"name": "xx-xxxxx-xxxxx",
"properties": {
    "provisioningState": "Succeeded"
},
"tags": {
    "owner": "xxx xxxx"
},
"type": "Microsoft.Resources/resourceGroups"
}
```

## 建立 VNet

在本節中，您將在 Azure 中建立 虛擬網絡 （VNet）。 首先，定義數個環境變數。 這些變數會保存 VNet 和子網的名稱，以及 VNet 的 CIDR 區塊。 接下來，使用 az network vnet create 命令，在您的資源群組中建立具有指定名稱和 CIDR 區塊的 VNet。 此程序可能需要幾分鐘的時間。

```bash
export VNET_NAME="vnet-${LOCAL_NAME}"
export SUBNET1_NAME="sn-main"
export SUBNET2_NAME="sn-worker"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

結果：

<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "xx.x.x.x/xx"
      ]
    },
    "enableDdosProtection": false,
    "etag": "W/\"xxxxx-xxxxx-xxxxx-xxxxx\"",
    "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxxxx/resourceGroups/xx-xxxxx-xxxxx/providers/Microsoft.Network/virtualNetworks/vnet-xx-xxxxx-xxxxx",
    "location": "westus",
    "name": "xxxxx-xxxxx-xxxxx-xxxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "xx-xxxxx-xxxxx",
    "resourceGuid": "xxxxx-xxxxx-xxxxx-xxxxx",
    "subnets": [],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## 建立主要節點子網

在本節中，您會在先前建立的 虛擬網絡 （VNet） 內，建立具有指定名稱和 CIDR 區塊的主要節點子網。 從執行 az network vnet subnet create 命令開始。 此程序可能需要幾分鐘的時間。 成功建立子網之後，您就可以準備將資源部署到此子網。

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

結果：

<!-- expected_similarity=0.3 -->
```json
{
  "addressPrefix": "xx.x.x.x/xx",
  "delegations": [],
  "etag": "W/\"xxxxx-xxxxx-xxxxx-xxxxx\"",
  "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxxxx/resourceGroups/xx-xxxxx-xxxxx/providers/Microsoft.Network/virtualNetworks/vnet-xx-xxxxx-xxxxx/subnets/sn-main-xxxxx",
  "name": "sn-main-xxxxx",
  "privateEndpointNetworkPolicies": "Disabled",
  "privateLinkServiceNetworkPolicies": "Enabled",
  "provisioningState": "Succeeded",
  "resourceGroup": "xx-xxxxx-xxxxx",
  "type": "Microsoft.Network/virtualNetworks/subnets"
}
```

## 建立背景工作節點子網

在本節中，您會在先前建立的 虛擬網絡 （VNet） 內，為背景工作節點建立具有指定名稱和 CIDR 區塊的子網。 從執行 az network vnet subnet create 命令開始。 成功建立子網之後，您就可以將背景工作節點部署至此子網。

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

結果：

<!-- expected_similarity=0.3 -->
```json
{
  "addressPrefix": "xx.x.x.x/xx",
  "delegations": [],
  "etag": "W/\"xxxxx-xxxxx-xxxxx-xxxxx\"",
  "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxxxx/resourceGroups/xx-xxxxx-xxxxx/providers/Microsoft.Network/virtualNetworks/vnet-xx-xxxxx-xxxxx/subnets/sn-worker-xxxxx",
  "name": "sn-worker-xxxxx",
  "privateEndpointNetworkPolicies": "Disabled",
  "privateLinkServiceNetworkPolicies": "Enabled",
  "provisioningState": "Succeeded",
  "resourceGroup": "xx-xxxxx-xxxxx",
  "type": "Microsoft.Network/virtualNetworks/subnets"
}
```

## 建立 儲存體 帳戶

此代碼段會執行下列步驟：

1. 將`STORAGE_ACCOUNT_NAME`環境變數設定為的`stor``LOCAL_NAME`串連 ，（轉換成小寫）。
2. 將 `BARMAN_CONTAINER_NAME` 環境變數設定為 `"barman"`。
3. 使用指定 `STORAGE_ACCOUNT_NAME` 資源群組中指定的 建立記憶體帳戶。
4. 使用已建立的記憶體帳戶中指定的 建立記憶體容器 `BARMAN_CONTAINER_NAME` 。

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## 部署 ARO 叢集

在本節中，您將部署 Azure Red Hat OpenShift （ARO） 叢集。 ARO_CLUSTER_NAME變數會保留 ARO 叢集的名稱。 az aro create 命令會部署具有指定名稱、資源群組、虛擬網路、子網和您先前下載並儲存在 金鑰保存庫 中的 RedHat OpenShift 提取秘密的 ARO 叢集。 此程式可能需要大約 30 分鐘才能完成。

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AroPullSecret --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_ID=$(az keyvault secret show --name arodemo-sp-id --vault-name kv-rdp-dev --query value -o tsv)
export ARO_SP_PASSWORD=$(az keyvault secret show --name arodemo-sp-password --vault-name kv-rdp-dev --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET} --client-id ${ARO_SP_ID} --client-secret ${ARO_SP_PASSWORD}
```

結果：
<!-- expected_similarity=0.3 -->
```json
{
  "apiserverProfile": {
    "ip": "xx.xxx.xx.xxx",
    "url": "https://api.xxxxx.xxxxxx.aroapp.io:xxxx/",
    "visibility": "Public"
  },
  "clusterProfile": {
    "domain": "xxxxxx",
    "fipsValidatedModules": "Disabled",
    "pullSecret": null,
    "resourceGroupId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourcegroups/xxxxxx-xxxxxx",
    "version": "4.12.25"
  },
  "consoleProfile": {
    "url": "https://console-openshift-console.apps.xxxxxx.xxxxxx.aroapp.io/"
  },
  "id": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.RedHatOpenShift/openShiftClusters/aro-arodemo-xxxxxx",
  "ingressProfiles": [
    {
      "ip": "xx.xxx.xx.xxx",
      "name": "default",
      "visibility": "Public"
    }
  ],
  "location": "westus",
  "masterProfile": {
    "diskEncryptionSetId": null,
    "encryptionAtHost": "Disabled",
    "subnetId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.Network/virtualNetworks/vnet-arodemo-xxxxxx/subnets/sn-main-jffspl",
    "vmSize": "Standard_D8s_v3"
  },
  "name": "aro-arodemo-xxxxxx",
  "networkProfile": {
    "outboundType": "Loadbalancer",
    "podCidr": "xx.xxx.xx.xxx/xx",
    "preconfiguredNsg": "Disabled",
    "serviceCidr": "xx.xxx.xx.xxx/xx"
  },
  "provisioningState": "Succeeded",
  "resourceGroup": "rg-arodemo-xxxxxx",
  "servicePrincipalProfile": {
    "clientId": "xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx",
    "clientSecret": null
  },
  "systemData": {
    "createdAt": "xxxxxx-xx-xxxxxx:xx:xx.xxxxxx+xx:xx",
    "createdBy": "xxxxxx@xxxxxx.xxx",
    "createdByType": "User",
    "lastModifiedAt": "xxxxxx-xx-xxxxxx:xx:xx.xxxxxx+xx:xx",
    "lastModifiedBy": "xxxxxx@xxxxxx.xxx",
    "lastModifiedByType": "User"
  },
  "tags": {
    "Demo": "",
    "owner": "ARO"
  },
  "type": "Microsoft.RedHatOpenShift/openShiftClusters",
  "workerProfiles": [
    {
      "count": 3,
      "diskEncryptionSetId": null,
      "diskSizeGb": 128,
      "encryptionAtHost": "Disabled",
      "name": "worker",
      "subnetId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.Network/virtualNetworks/vnet-arodemo-xxxxxx/subnets/sn-worker-xxxxxx",
      "vmSize": "Standard_D4s_v3"
    }
  ],
  "workerProfilesStatus": [
    {
      "count": 3,
      "diskEncryptionSetId": null,
      "diskSizeGb": 128,
      "encryptionAtHost": "Disabled",
      "name": "aro-arodemo-xxxxxx-xxxxxx-worker-westus",
      "subnetId": "/subscriptions/xxxxxx-xxxxxx-xxxxxx-xxxxxx-xxxxxx/resourceGroups/rg-arodemo-xxxxxx/providers/Microsoft.Network/virtualNetworks/vnet-arodemo-xxxxxx/subnets/sn-worker-xxxxxx",
      "vmSize": "Standard_D4s_v3"
    }
  ]
}
```

## 取得叢集認證和登入

此程式代碼會使用 Azure CLI 擷取 Azure Red Hat OpenShift （ARO） 叢集的 API 伺服器 URL 和登入認證。

此命令 `az aro show` 可用來藉由提供資源組名和 ARO 叢集名稱來取得 API 伺服器 URL。 `--query`參數是用來擷`apiserverProfile.url`取 屬性，而 `-o tsv` 選項會用來輸出結果做為索引卷標分隔值。

`az aro list-credentials`命令是用來取得 ARO 叢集的登入認證。 參數 `--name` 會指定 ARO 叢集名稱，而 `--resource-group` 參數會指定資源組名。 `--query`參數是用來擷`kubeadminPassword`取 屬性，而 `-o tsv` 選項會用來輸出結果做為索引卷標分隔值。

最後， `oc login` 命令是用來使用擷取的API伺服器URL、 `kubeadmin` 使用者名稱和登入認證登入 ARO 叢集。

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## 將運算元新增至 ARO

將命名空間設定為將運算子安裝至內建命名空間 `openshift-operators`。

```bash
export NAMESPACE="openshift-operators"
```

Cloud Native Postgresql 操作員

```bash
channelspec=$(oc get packagemanifests cloud-native-postgresql -o jsonpath="{range .status.channels[*]}Channel: {.name} currentCSV: {.currentCSV}{'\n'}{end}" | grep "stable-v1.22")
IFS=" " read -r -a array <<< "${channelspec}"
channel=${array[1]}
csv=${array[3]}

catalogSource=$(oc get packagemanifests cloud-native-postgresql -o jsonpath="{.status.catalogSource}")
catalogSourceNamespace=$(oc get packagemanifests cloud-native-postgresql -o jsonpath="{.status.catalogSourceNamespace}")

cat <<EOF | oc apply -f -
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: cloud-native-postgresql
  namespace: ${NAMESPACE}
spec:
    channel: $channel
    name: cloud-native-postgresql
    source: $catalogSource
    sourceNamespace: $catalogSourceNamespace
    installPlanApproval: Automatic
    startingCSV: $csv
EOF
```

RedHat Keycloak 運算符

```bash
channelspec_kc=$(oc get packagemanifests rhbk-operator -o jsonpath="{range .status.channels[*]}Channel: {.name} currentCSV: {.currentCSV}{'\n'}{end}" | grep "stable-v22")
IFS=" " read -r -a array <<< "${channelspec_kc}"
channel_kc=${array[1]}
csv_kc=${array[3]}

catalogSource_kc=$(oc get packagemanifests rhbk-operator -o jsonpath="{.status.catalogSource}")
catalogSourceNamespace_kc=$(oc get packagemanifests rhbk-operator -o jsonpath="{.status.catalogSourceNamespace}")

cat <<EOF | oc apply -f -
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: rhbk-operator
  namespace: ${NAMESPACE}
spec:
  channel: $channel_kc
  name: rhbk-operator
  source: $catalogSource_kc
  sourceNamespace: $catalogSourceNamespace_kc
  startingCSV: $csv_kc
EOF
```

結果：
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## 建立 ARO Posgre SQL 資料庫

從 金鑰保存庫 擷取秘密，並建立 ARO 資料庫登入秘密物件。

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name kv-rdp-dev --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name kv-rdp-dev --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

結果：
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

建立要備份至 Azure 儲存體的秘密

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

結果：
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

建立 Postgres 叢集

```bash
cat <<EOF | oc apply -f -
---
apiVersion: postgresql.k8s.enterprisedb.io/v1
kind: Cluster
metadata:
  name: cluster-arodemo
  namespace: ${NAMESPACE}
spec:
  description: "HA Postgres Cluster Demo for ARO"
  # Choose your PostGres Database Version
  imageName: ghcr.io/cloudnative-pg/postgresql:15.2
  # Number of Replicas
  instances: 3
  startDelay: 300
  stopDelay: 300
  replicationSlots:
    highAvailability:
      enabled: true
    updateInterval: 300
  primaryUpdateStrategy: unsupervised
  postgresql:
    parameters:
      shared_buffers: 256MB
      pg_stat_statements.max: '10000'
      pg_stat_statements.track: all
      auto_explain.log_min_duration: '10s'
    pg_hba:
      # - hostssl app all all cert
      - host app app all password
  logLevel: debug
  # Choose the right storageclass for type of workload.
  storage:
    storageClass: managed-csi
    size: 1Gi
  walStorage:
    storageClass: managed-csi
    size: 1Gi
  monitoring:
    enablePodMonitor: true
  bootstrap:
    initdb: # Deploying a new cluster
      database: WorldDB
      owner: app
      secret:
        name: app-auth
  backup:
    barmanObjectStore:
      # For backup, we use a blob container in an Azure Storage Account to store data.
      # On this Blueprint, we get the account and container name from the environment variables.
      destinationPath: https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net/${BARMAN_CONTAINER_NAME}/
      azureCredentials:
        storageAccount:
          name: azure-storage-secret
          key: storage-account-name
        storageKey:
          name: azure-storage-secret
          key: storage-account-key
      wal:
        compression: gzip
        maxParallel: 8
    retentionPolicy: "30d"

  affinity:
    enablePodAntiAffinity: true
    topologyKey: failure-domain.beta.kubernetes.io/zone

  nodeMaintenanceWindow:
    inProgress: false
    reusePVC: false
EOF
```

結果：
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## 建立 ARO Keycloak 實例

在 OpenShift 叢集上部署 Keycloak 實例。 它會使用 `oc apply` 命令來套用定義 Keycloak 資源的 YAML 組態檔。
YAML 組態會指定Keycloak實例的各種設定，包括資料庫、主機名、HTTP 設定、輸入、實例數目和交易設定。
若要部署 Keycloak，請使用必要的許可權和 OpenShift 叢集的存取權，在殼層環境中執行此程式碼區塊。
注意：請務必將變數 `$apiServer`、 `$kc_hosts`和資料庫認證的值取代`passwordSecret``usernameSecret`為您環境的適當值。

```bash
export kc_hosts=$(echo $apiServer | sed -E 's/\/\/api\./\/\/apps./' | sed -En 's/.*\/\/([^:]+).*/\1/p' )

cat <<EOF | oc apply -f -
apiVersion: k8s.keycloak.org/v2alpha1
kind: Keycloak
metadata:
  labels:
    app: sso
  name: kc001
  namespace: ${NAMESPACE}
spec:
  db:
    database: WorldDB
    host: cluster-arodemo-rw
    passwordSecret:
      key: password
      name: app-auth
    port: 5432
    usernameSecret:
      key: username
      name: app-auth
    vendor: postgres
  hostname:
    hostname: kc001.${kc_hosts}
  http:
    httpEnabled: true
  ingress:
    enabled: true
  instances: 1
  transaction:
    xaEnabled: false
EOF
```

結果：
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

存取工作負載

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

結果：
<!-- expected_similarity=0.3 -->
```text
*   Trying 104.42.132.245:443...
* Connected to kc001.apps.foppnyl9.westus.aroapp.io (104.42.132.245) port 443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
*  CAfile: /etc/ssl/certs/ca-certificates.crt
*  CApath: /etc/ssl/certs
* TLSv1.0 (OUT), TLS header, Certificate Status (22):
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.2 (IN), TLS header, Certificate Status (22):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
```
