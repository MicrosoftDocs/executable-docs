---
title: Magas rendelkezésre állású PostgreSQL-fürt létrehozása az Azure Red Hat OpenShiften
description: 'Ez az oktatóanyag bemutatja, hogyan hozhat létre magas rendelkezésre állású PostgreSQL-fürtöt az Azure Red Hat OpenShiftben (ARO) a CloudNativePG operátorral'
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/02/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Magas rendelkezésre állású PostgreSQL-fürt létrehozása az Azure Red Hat OpenShiften

## Bejelentkezés az Azure-ba a parancssori felület használatával

Ahhoz, hogy parancsokat futtasson az Azure-on a parancssori felülettel, be kell jelentkeznie. Ez nagyon egyszerűen történik, bár a `az login` parancs:

## Előfeltételek ellenőrzése

Ezután ellenőrizze az előfeltételeket. Ez a szakasz a következő előfeltételeket ellenőrzi: RedHat OpenShift és kubectl. 

### RedHat OpenShift 
    
```bash
az provider register -n Microsoft.RedHatOpenShift --wait
```

### Kubectl

```bash
az aks install-cli
```

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Létrehozunk egyet ehhez az oktatóanyaghoz. Az alábbi parancs létrehoz egy erőforráscsoportot a korábban definiált $RG_NAME, $LOCATION és $RGTAGS paraméterekkel.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

Eredmények:
    
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

## Virtuális hálózat létrehozása

Ebben a szakaszban virtuális hálózatot (VNetet) fog létrehozni az Azure-ban. Először is definiáljon több környezeti változót. Ezek a változók a virtuális hálózat és az alhálózatok nevét, valamint a virtuális hálózat CIDR-blokkját fogják tárolni. Ezután hozza létre a megadott névvel és CIDR-blokktal rendelkező virtuális hálózatot az erőforráscsoportban az az network vnet create paranccsal. Ez a folyamat eltarthat néhány percig.
    
```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Eredmények:

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
## Fő csomópontok alhálózatának létrehozása
    
Ebben a szakaszban a korábban létrehozott virtuális hálózaton (VNet) belül hozza létre a fő csomópontok alhálózatát a megadott névvel és CIDR-blokktal. Először futtassa az az network vnet subnet create parancsot. Ez a folyamat eltarthat néhány percig. Az alhálózat sikeres létrehozása után készen áll az erőforrások ebben az alhálózatban való üzembe helyezésére.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Eredmények:

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

## Feldolgozó csomópontok alhálózatának létrehozása

Ebben a szakaszban egy alhálózatot fog létrehozni a munkavégző csomópontokhoz a korábban létrehozott virtuális hálózaton (VNet) belül a megadott névvel és CIDR-blokktal. Először futtassa az az network vnet subnet create parancsot. Az alhálózat sikeres létrehozása után készen áll arra, hogy üzembe helyezze a feldolgozó csomópontokat ebben az alhálózatban.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Eredmények:

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

## Szolgáltatásnév létrehozása az ARO-fürthöz

Ebben a szakaszban egy szolgáltatásnevet fog létrehozni az Azure Red Hat OpenShift (ARO) fürthöz. A SP_NAME változó a szolgáltatásnév nevét fogja tárolni. Az az account show paranccsal lekérhető SUBSCRIPTION_ID változó tárolja az Azure-előfizetés azonosítóját. Ez az azonosító szükséges a szerepkörök szolgáltatásnévhez való hozzárendeléséhez. Ezután hozza létre a szolgáltatásnevet az az ad sp create-for-rbac paranccsal. Végül nyerje ki a szolgáltatásnév azonosítóját és titkos kódját a servicePrincipalInfo változóból, amely JSON-objektumként jelenik meg. Ezeket az értékeket később használjuk az ARO-fürt Azure-ral való hitelesítéséhez.

```bash
export SP_NAME="sp-aro-${LOCAL_NAME}-${SUFFIX}"
export SUBSCRIPTION_ID=$(az account show --query id --output tsv)
servicePrincipalInfo=$(az ad sp create-for-rbac -n $SP_NAME --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME --output json)
SP_ID=$(echo $servicePrincipalInfo | jq -r '.appId')
SP_SECRET=$(echo $servicePrincipalInfo | jq -r '.password')
```

## Az ARO-fürt üzembe helyezése

Ebben a szakaszban egy Azure Red Hat OpenShift (ARO) fürtöt fog üzembe helyezni. A ARO_CLUSTER_NAME változó az ARO-fürt nevét fogja tárolni. Az az aro create parancs a megadott névvel, erőforráscsoporttal, virtuális hálózattal, alhálózatokkal és szolgáltatásnévvel telepíti az ARO-fürtöt. Ez a folyamat körülbelül 30 percet vehet igénybe.
    
```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
echo ${YELLOW} "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --client-id ${SP_ID} --client-secret ${SP_SECRET}
```

Eredmények:

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
