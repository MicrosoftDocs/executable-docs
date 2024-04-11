---
title: Vytvoření clusteru PostgreSQL s vysokou dostupností v Azure Red Hat OpenShiftu
description: 'Tento kurz ukazuje, jak vytvořit cluster PostgreSQL s vysokou dostupností v Azure Red Hat OpenShift (ARO) pomocí operátoru CloudNativePG.'
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/02/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Vytvoření clusteru PostgreSQL s vysokou dostupností v Azure Red Hat OpenShiftu

## Přihlášení k Azure pomocí rozhraní příkazového řádku

Pokud chcete spouštět příkazy v Azure pomocí rozhraní příkazového řádku, musíte se přihlásit. To se provádí velmi jednoduše, i když příkaz `az login` :

## Kontrola požadovaných součástí

Dále zkontrolujte požadavky. Tato část kontroluje následující požadavky: RedHat OpenShift a kubectl. 

### RedHat OpenShift 
    
```bash
az provider register -n Microsoft.RedHatOpenShift --wait
```

### Kubectl

```bash
az aks install-cli
```

## Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Pro účely tohoto kurzu ho vytvoříme. Následující příkaz vytvoří skupinu prostředků s dříve definovanými parametry $RG_NAME, $LOCATION a $RGTAGS.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

Výsledky:
    
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

## Vytvoření virtuální sítě

V této části vytvoříte virtuální síť v Azure. Začněte definováním několika proměnných prostředí. Tyto proměnné budou obsahovat názvy virtuální sítě a podsítí a blok CIDR pro vaši virtuální síť. Dále pomocí příkazu az network vnet create vytvořte virtuální síť se zadaným názvem a blokem CIDR ve vaší skupině prostředků. Tento proces může trvat několik minut.
    
```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Výsledky:

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
## Vytvoření podsítě hlavních uzlů
    
V této části vytvoříte podsíť hlavních uzlů se zadaným názvem a blokem CIDR v rámci dříve vytvořené virtuální sítě. Začněte spuštěním příkazu az network vnet subnet create. Tento proces může trvat několik minut. Po úspěšném vytvoření podsítě budete připraveni nasadit prostředky do této podsítě.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Výsledky:

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

## Vytvoření podsítě pracovních uzlů

V této části vytvoříte podsíť pro pracovní uzly se zadaným názvem a blokem CIDR v rámci dříve vytvořené virtuální sítě. Začněte spuštěním příkazu az network vnet subnet create. Po úspěšném vytvoření podsítě budete připraveni nasadit pracovní uzly do této podsítě.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Výsledky:

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

## Vytvoření instančního objektu pro cluster ARO

V této části vytvoříte instanční objekt pro cluster Azure Red Hat OpenShift (ARO). Proměnná SP_NAME bude obsahovat název instančního objektu. Proměnná SUBSCRIPTION_ID, která se dá načíst pomocí příkazu az account show, uloží ID vašeho předplatného Azure. Toto ID je nezbytné pro přiřazení rolí k instančnímu objektu. Potom pomocí příkazu az ad sp create-for-rbac vytvořte instanční objekt. Nakonec extrahujte ID a tajný kód instančního objektu z proměnné servicePrincipalInfo, výstup jako objekt JSON. Tyto hodnoty se později použijí k ověření clusteru ARO v Azure.

```bash
export SP_NAME="sp-aro-${LOCAL_NAME}-${SUFFIX}"
export SUBSCRIPTION_ID=$(az account show --query id --output tsv)
servicePrincipalInfo=$(az ad sp create-for-rbac -n $SP_NAME --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME --output json)
SP_ID=$(echo $servicePrincipalInfo | jq -r '.appId')
SP_SECRET=$(echo $servicePrincipalInfo | jq -r '.password')
```

## Nasazení clusteru ARO

V této části nasadíte cluster Azure Red Hat OpenShift (ARO). Proměnná ARO_CLUSTER_NAME bude obsahovat název clusteru ARO. Příkaz az aro create nasadí cluster ARO se zadaným názvem, skupinou prostředků, virtuální sítí, podsítěmi a instančním objektem. Dokončení tohoto procesu může trvat přibližně 30 minut.
    
```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
echo ${YELLOW} "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --client-id ${SP_ID} --client-secret ${SP_SECRET}
```

Výsledky:

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
