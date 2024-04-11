---
title: Een PostgreSQL-cluster met hoge beschikbaarheid maken in Azure Red Hat OpenShift
description: Deze zelfstudie laat zien hoe u een PostgreSQL-cluster met hoge beschikbaarheid maakt in Azure Red Hat OpenShift (ARO) met behulp van de CloudNativePG-operator
author: russd2357
ms.author: rdepina
ms.topic: article
ms.date: 04/02/2024
ms.custom: 'innovation-engine, linux-related content'
---

# Een PostgreSQL-cluster met hoge beschikbaarheid maken in Azure Red Hat OpenShift

## Aanmelden bij Azure met behulp van de CLI

Als u opdrachten wilt uitvoeren voor Azure met behulp van de CLI, moet u zich aanmelden. Dit wordt gedaan, heel eenvoudig, hoewel de `az login` opdracht:

## Controleren op vereisten

Controleer vervolgens op vereisten. In deze sectie wordt gecontroleerd op de volgende vereisten: RedHat OpenShift en kubectl. 

### RedHat OpenShift 
    
```bash
az provider register -n Microsoft.RedHatOpenShift --wait
```

### Kubectl

```bash
az aks install-cli
```

## Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. We maken er een voor deze zelfstudie. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde parameters $RG_NAME, $LOCATION en $RGTAGS.

```bash
export RGTAGS="owner=ARO Demo"
export LOCATION="westus"
export LOCAL_NAME="arodemo"
export SUFFIX=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 6; echo)
export RG_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
az group create -n $RG_NAME -l $LOCATION --tags $RGTAGS
```

Resultaten:
    
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

## VNet maken

In deze sectie maakt u een virtueel netwerk (VNet) in Azure. Begin met het definiëren van verschillende omgevingsvariabelen. Deze variabelen bevatten de namen van uw VNet en subnetten, evenals het CIDR-blok voor uw VNet. Maak vervolgens het VNet met de opgegeven naam en het CIDR-blok in uw resourcegroep met behulp van de opdracht az network vnet create. Dit proces kan enkele minuten in beslag nemen.
    
```bash
export VNET_NAME="vnet-${LOCAL_NAME}-${SUFFIX}"
export SUBNET1_NAME="sn-main-${SUFFIX}"
export SUBNET2_NAME="sn-worker-${SUFFIX}"
export VNET_CIDR="10.0.0.0/22"
az network vnet create -g $RG_NAME -n $VNET_NAME --address-prefixes $VNET_CIDR
```

Resultaten:

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
## Hoofdknooppuntensubnet maken
    
In deze sectie maakt u het subnet van de hoofdknooppunten met de opgegeven naam en het CIDR-blok binnen het eerder gemaakte virtuele netwerk (VNet). Begin met het uitvoeren van de opdracht az network vnet subnet create. Dit proces kan enkele minuten in beslag nemen. Nadat het subnet is gemaakt, bent u klaar om resources in dit subnet te implementeren.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET1_NAME --address-prefixes 10.0.0.0/23
```

Resultaten:

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

## Subnet Werkknooppunten maken

In deze sectie maakt u een subnet voor uw werkknooppunten met de opgegeven naam en het CIDR-blok binnen het eerder gemaakte virtuele netwerk (VNet). Begin met het uitvoeren van de opdracht az network vnet subnet create. Nadat het subnet is gemaakt, bent u klaar om uw werkknooppunten in dit subnet te implementeren.

```bash
az network vnet subnet create -g $RG_NAME --vnet-name $VNET_NAME -n $SUBNET2_NAME --address-prefixes 10.0.2.0/23
```

Resultaten:

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

## Een service-principal maken voor het ARO-cluster

In deze sectie maakt u een service-principal voor uw Azure Red Hat OpenShift-cluster (ARO). De variabele SP_NAME bevat de naam van uw service-principal. De SUBSCRIPTION_ID variabele, die kan worden opgehaald met behulp van de opdracht az account show, slaat uw Azure-abonnements-id op. Deze id is nodig voor het toewijzen van rollen aan uw service-principal. Maak daarna de service-principal met behulp van de opdracht az ad sp create-for-rbac. Pak ten slotte de id en het geheim van de service-principal uit de variabele servicePrincipalInfo, uitvoer als een JSON-object. Deze waarden worden later gebruikt om uw ARO-cluster te verifiëren met Azure.

```bash
export SP_NAME="sp-aro-${LOCAL_NAME}-${SUFFIX}"
export SUBSCRIPTION_ID=$(az account show --query id --output tsv)
servicePrincipalInfo=$(az ad sp create-for-rbac -n $SP_NAME --role Contributor --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME --output json)
SP_ID=$(echo $servicePrincipalInfo | jq -r '.appId')
SP_SECRET=$(echo $servicePrincipalInfo | jq -r '.password')
```

## Het ARO-cluster implementeren

In deze sectie implementeert u een ARO-cluster (Azure Red Hat OpenShift). De ARO_CLUSTER_NAME variabele bevat de naam van uw ARO-cluster. Met de opdracht az aro create wordt het ARO-cluster geïmplementeerd met de opgegeven naam, resourcegroep, virtueel netwerk, subnetten en service-principal. Dit proces kan ongeveer 30 minuten duren.
    
```bash
export ARO_CLUSTER_NAME="aro-${LOCAL_NAME}-${SUFFIX}"
echo ${YELLOW} "This will take about 30 minutes to complete..." 
az aro create -g $RG_NAME -n $ARO_CLUSTER_NAME --vnet $VNET_NAME --master-subnet $SUBNET1_NAME --worker-subnet $SUBNET2_NAME --tags $RGTAGS --client-id ${SP_ID} --client-secret ${SP_SECRET}
```

Resultaten:

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
