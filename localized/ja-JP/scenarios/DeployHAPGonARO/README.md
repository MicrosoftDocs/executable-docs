---
title: Azure Red Hat OpenShift で高可用性 PostgreSQL クラスターを作成する
description: このチュートリアルでは、CloudNativePG オペレーターを使用して、Azure Red Hat OpenShift (ARO) で高可用性 PostgreSQL クラスターを作成する方法について説明します
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/02/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Azure Red Hat OpenShift で高可用性 PostgreSQL クラスターを作成する

## CLI を使用して Azure にログインします

CLI を使用して Azure に対してコマンドを実行するには、ログインする必要があります。 これを実行するには、`az login` コマンドを使用するだけです。

## 前提条件を検査する

次に、前提条件を検査します。 このセクションでは、前提条件である RedHat OpenShift と kubectl を確認します。 

### RedHat OpenShift 
    
```bash
az provider register -n Microsoft.RedHatOpenShift --wait
```

### kubectl

```bash
az aks install-cli
```

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

## ARO クラスターのサービス プリンシパルを作成する

このセクションでは、Azure Red Hat OpenShift (ARO) クラスターのサービス プリンシパルを作成します。 SP_NAME 変数には、サービス プリンシパルの名前が保持されます。 SUBSCRIPTION_ID 変数 (az account show コマンドを使用して取得できます) には、Azure サブスクリプション ID が格納されます。 この ID は、サービス プリンシパルにロールを割り当てるために必要です。 その後、az ad sp create-for-rbac コマンドを使用してサービス プリンシパルを作成します。 最後に、servicePrincipalInfo 変数からサービス プリンシパルの ID とシークレットを抽出し、JSON オブジェクトとして出力します。 これらの値は、後で Azure で ARO クラスターを認証するために使用されます。

```bash
export SP_NAME="sp-aro-${LOCAL_NAME}-${SUFFIX}"
export SUBSCRIPTION_ID=$(az account show --query id --output tsv)
servicePrincipalInfo=$(az ad sp create-for-rbac -n $SP_NAME --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME --output json)
SP_ID=$(echo $servicePrincipalInfo | jq -r '.appId')
SP_SECRET=$(echo $servicePrincipalInfo | jq -r '.password')
```

## ARO クラスターをデプロイする

このセクションでは、Azure Red Hat OpenShift (ARO) クラスターをデプロイします。 ARO_CLUSTER_NAME 変数には、ARO クラスターの名前が保持されます。 az aro create コマンドは、指定された名前、リソース グループ、仮想ネットワーク、サブネット、サービス プリンシパルを持つ ARO クラスターをデプロイします。 このプロセスは、完了までに 30 分程かかる場合があります。
    
```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
echo ${YELLOW} "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --client-id ${SP_ID} --client-secret ${SP_SECRET}
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
