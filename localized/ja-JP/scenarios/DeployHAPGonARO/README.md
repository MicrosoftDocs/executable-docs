---
title: Azure Red Hat OpenShift で高可用性 PostgreSQL クラスターを作成する
description: このチュートリアルでは、CloudNativePG オペレーターを使用して、Azure Red Hat OpenShift (ARO) で高可用性 PostgreSQL クラスターを作成する方法について説明します
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/16/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Azure Red Hat OpenShift で高可用性 PostgreSQL クラスターを作成する

## CLI を使用して Azure にログインします

CLI を使用して Azure に対してコマンドを実行するには、ログインする必要があります。 これを実行するには、`az login` コマンドを使用するだけです。

## 前提条件を検査する

次に、前提条件を検査します。 これを行うには、次のコマンドを実行します。

- RedHat OpenShift: `az provider register -n Microsoft.RedHatOpenShift --wait`
- kubectl: `az aks install-cli`
- Openshift クライアント: `mkdir ~/ocp ; wget -q https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-client-linux.tar.gz -O ~/ocp/openshift-client-linux.tar.gz ; tar -xf ~/ocp/openshift-client-linux.tar.gz ; export PATH="$PATH:~/ocp"`

## リソース グループの作成

リソース グループとは、関連リソース用のコンテナーです。 すべてのリソースをリソース グループに配置する必要があります。 このチュートリアルに必要なものを作成します。 次のコマンドは、事前定義済みの $RG_NAME、$LOCATION、$RGTAGS パラメーターを使用してリソース グループを作成します。

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

結果:

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

## VNet を作成します

このセクションでは、Azure で Virtual Network (VNet) を作成します。 まず、いくつかの環境変数を定義します。 これらの変数には、VNet とサブネットの名前、および VNet の CIDR ブロックが保持されます。 次に、az network vnet create コマンドを使用して、指定した名前と CIDR ブロックを持つ VNet をリソース グループに作成します。 このプロセスには数分かかることがあります。

```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

結果:

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

## メイン ノードのサブネットを作成する

このセクションでは、前に作成した Virtual Network (VNet) 内に、指定した名前と CIDR ブロックを持つメイン ノードのサブネットを作成します。 まず、az network vnet subnet create コマンドを実行します。. このプロセスには数分かかることがあります。 サブネットが正常に作成されたら、このサブネットにリソースをデプロイする準備が整います。

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

結果:

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

## ワーカー ノードのサブネットを作成する

このセクションでは、前に作成した Virtual Network (VNet) 内に、指定した名前と CIDR ブロックを持つワーカー ノードのサブネットを作成します。 まず、az network vnet subnet create コマンドを実行します。. サブネットが正常に作成されたら、このサブネットにワーカー ノードをデプロイする準備が整います。

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

結果:

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

## ストレージ アカウントの作成

このコード スニペットでは、次の手順を実行します。

1. 環境変数を `STORAGE_ACCOUNT_NAME` 、(小文字に変換)、 `LOCAL_NAME` および `SUFFIX` (小文字に変換) の連結`stor`に設定します。
2. 環境変数を > に`"barman"`設定します`BARMAN_CONTAINER_NAME`。
3. 指定したリソース グループに指定された `STORAGE_ACCOUNT_NAME` ストレージ アカウントを作成します。
4. 作成されたストレージ アカウントで指定された `BARMAN_CONTAINER_NAME` ストレージ コンテナーを作成します。

```bash
export STORAGE_ACCOUNT_NAME="stor${LOCAL_NAME,,}${SUFFIX,,}"
export BARMAN_CONTAINER_NAME="barman"

az storage account create --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RG_NAME}" --sku Standard_LRS
az storage container create --name "${BARMAN_CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}"
```

## ARO クラスターをデプロイする

このセクションでは、Azure Red Hat OpenShift (ARO) クラスターをデプロイします。 ARO_CLUSTER_NAME 変数には、ARO クラスターの名前が保持されます。 az aro create コマンドは、指定した名前、リソース グループ、仮想ネットワーク、サブネット、および以前にダウンロードして Key Vault に保存した RedHat OpenShift プル シークレットを持つ ARO クラスターをデプロイします。 このプロセスは、完了までに 30 分程かかる場合があります。

```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
export ARO_PULL_SECRET=$(az keyvault secret show --name AROPullSecret --vault-name AROKeyVault --query value -o tsv)
echo "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --pull-secret ${ARO_PULL_SECRET}
```

結果:
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

## クラスターの資格情報とログインを取得する

このコードでは、Azure CLI を使用して、Azure Red Hat OpenShift (ARO) クラスターの API サーバー URL とログイン資格情報を取得します。

この `az aro show` コマンドは、リソース グループ名と ARO クラスター名を指定して API サーバーの URL を取得するために使用されます。 パラメーターを `--query` 使用してプロパティを `apiserverProfile.url` 抽出し、オプションを `-o tsv` 使用して結果をタブ区切りの値として出力します。

この `az aro list-credentials` コマンドは、ARO クラスターのログイン資格情報を取得するために使用されます。 このパラメーターは `--name` ARO クラスター名を指定し、パラメーターは `--resource-group` リソース グループ名を指定します。 パラメーターを `--query` 使用してプロパティを `kubeadminPassword` 抽出し、オプションを `-o tsv` 使用して結果をタブ区切りの値として出力します。

最後に、この `oc login` コマンドを使用して、取得した API サーバーの URL、ユーザー名、ログイン資格情報を `kubeadmin` 使用して ARO クラスターにログインします。

```bash
export apiServer=$(az aro show -g $RG_NAME -n $ARO_CLUSTER_NAME --query apiserverProfile.url -o tsv)
export loginCred=$(az aro list-credentials --name $ARO_CLUSTER_NAME --resource-group $RG_NAME --query "kubeadminPassword" -o tsv)

oc login $apiServer -u kubeadmin -p $loginCred --insecure-skip-tls-verify
```

## ARO に演算子を追加する

組み込みの名前空間に演算子をインストールするように名前空間を設定します `openshift-operators`。

```bash
export NAMESPACE="openshift-operators"
```

Cloud Native Postgresql オペレーター

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

RedHat Keycloak 演算子

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

結果:
<!-- expected_similarity=0.3 -->
```text
subscription.operators.coreos.com/rhbk-operator created
```

## ARO PosgreSQL データベースを作成する

Key Vault からシークレットをフェッチし、ARO データベース ログイン シークレット オブジェクトを作成します。

```bash
pgUserName=$(az keyvault secret show --name AroPGUser --vault-name AROKeyVault --query value -o tsv)
pgPassword=$(az keyvault secret show --name AroPGPassword --vault-name AROKeyVault --query value -o tsv)

oc create secret generic app-auth --from-literal=username=${pgUserName} --from-literal=password=${pgPassword} -n ${NAMESPACE}
```

結果:
<!-- expected_similarity=0.3 -->
```text
secret/app-auth created
```

Azure Storage にバックアップするためのシークレットを作成する

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT_NAME} --resource-group ${RG_NAME} --query "[0].value" --output tsv)
oc create secret generic azure-storage-secret --from-literal=storage-account-name=${STORAGE_ACCOUNT_NAME} --from-literal=storage-account-key=${STORAGE_ACCOUNT_KEY} --namespace ${NAMESPACE}
```

結果:
<!-- expected_similarity=0.3 -->
```text
secret/azure-storage-secret created
```

Postgres クラスターを作成する

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

結果:
<!-- expected_similarity=0.3 -->
```text
cluster.postgresql.k8s.enterprisedb.io/cluster-arodemo created
```

## ARO Keycloak インスタンスを作成する

OpenShift クラスターに Keycloak インスタンスをデプロイします。 このコマンドを `oc apply` 使用して、Keycloak リソースを定義する YAML 構成ファイルを適用します。
YAML 構成では、データベース、ホスト名、HTTP 設定、イングレス、インスタンス数、トランザクション設定など、Keycloak インスタンスのさまざまな設定を指定します。
Keycloak をデプロイするには、必要なアクセス許可と OpenShift クラスターへのアクセス権を持つシェル環境でこのコード ブロックを実行します。
注: 変数 `$apiServer`、 `$kc_hosts`およびデータベース資格情報 (`passwordSecret` および `usernameSecret`) の値は、実際の環境に適した値に置き換えてください。

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

結果:
<!-- expected_similarity=0.3 -->
```text
keycloak.k8s.keycloak.org/kc001 created
```

ワークロードにアクセスする

```bash
URL=$(ooc get ingress kc001-ingress -o json | jq -r '.spec.rules[0].host')
curl -Iv https://$URL
```

結果:
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
