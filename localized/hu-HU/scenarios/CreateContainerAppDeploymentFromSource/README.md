---
title: 'Tárolóalkalmazás létrehozása a Blob Store, az SQL és a Computer Vision használatával'
description: 'Ez az oktatóanyag bemutatja, hogyan hozhat létre tárolóalkalmazást a Blob Store, az SQL és a Computer Vision használatával'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Tárolóalkalmazás létrehozása a Blob Store, az SQL és a Computer Vision használatával

Ebben az útmutatóban végigvezetjük a webalkalmazáshoz szükséges erőforrások üzembe helyezésén, amely lehetővé teszi a felhasználók számára a szavazatok leadását a nevük, e-mail-címük és képük alapján. A felhasználók szavazhatnak, hogy előnyben részesítik a macskát vagy a kutyát egy macskáról vagy egy kutyáról készült kép használatával, amelyet az infrastruktúra elemezni fog. Ahhoz, hogy ez működjön, több különböző Azure-szolgáltatásban fogunk erőforrásokat üzembe helyezni:

- **Azure Storage-fiók** a rendszerképek tárolásához
- **Azure Database for PostgreSQL** felhasználók és szavazatok tárolására
- **Az Azure Computer Vision** a macskák vagy kutyák képeinek elemzéséhez
- **Azure Container App** a kód üzembe helyezéséhez

Megjegyzés: Ha még soha nem hozott létre Computer Vision-erőforrást, nem fog tudni létrehozni egyet az Azure CLI használatával. Létre kell hoznia az első Computer Vision-erőforrást az Azure Portalról a felelős AI-feltételek áttekintéséhez és nyugtázásához. Ezt itt teheti meg: [Computer Vision-erőforrás](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision) létrehozása. Ezt követően bármely üzembehelyezési eszköz (SDK, CLI vagy ARM-sablon stb.) használatával létrehozhat további erőforrásokat ugyanabban az Azure-előfizetésben.

## Környezeti változók definiálása

Az oktatóanyag első lépése a környezeti változók definiálása. **Cserélje le a jobb oldali értékeket a saját egyedi értékeire.** Ezek az értékek az oktatóanyag során erőforrások létrehozására és az alkalmazás konfigurálására szolgálnak. Használjon kisbetűs karaktereket, és ne használjon speciális karaktereket a tárfiók nevéhez.

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export MY_RESOURCE_GROUP_NAME=rg$SUFFIX
export REGION=westus
export MY_STORAGE_ACCOUNT_NAME=storage$SUFFIX
export MY_DATABASE_SERVER_NAME=dbserver$SUFFIX
export MY_DATABASE_NAME=db$SUFFIX
export MY_DATABASE_USERNAME=dbuser$SUFFIX
export MY_DATABASE_PASSWORD=dbpass$SUFFIX
export MY_COMPUTER_VISION_NAME=computervision$SUFFIX
export MY_CONTAINER_APP_NAME=containerapp$SUFFIX
export MY_CONTAINER_APP_ENV_NAME=containerappenv$SUFFIX
```

## A mintaadattár klónozása

Először klónozni fogjuk ezt az adattárat a helyi gépeinkre. Ez biztosítja a fent vázolt egyszerű alkalmazás funkcióinak biztosításához szükséges kezdőkódot. Klónozhatunk egy egyszerű Git-paranccsal.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

A mentett környezeti változók megőrzése érdekében fontos, hogy ez a terminálablak az üzembe helyezés időtartamáig nyitva maradjon.

## Bejelentkezés az Azure-ba a parancssori felület használatával

Ahhoz, hogy parancsokat futtasson az Azure-on a parancssori felülettel[](https://learn.microsoft.com/cli/azure/install-azure-cli), be kell jelentkeznie. Ez a parancs ellenére `az login` történik:

## Erőforráscsoport létrehozása

Az erőforráscsoportok a kapcsolódó erőforrások tárolói. Minden erőforrást egy erőforráscsoportba kell helyezni. Létrehozunk egyet ehhez az oktatóanyaghoz. A következő parancs létrehoz egy erőforráscsoportot a korábban definiált $MY_RESOURCE_GROUP_NAME és $REGION paraméterekkel.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "id": "/subscriptions/ab9d8365-2f65-47a4-8df4-7e40db70c8d2/resourceGroups/$MY_RESOURCE_GROUP_NAME",
  "location": "$REGION",
  "managedBy": null,
  "name": "$MY_RESOURCE_GROUP_NAME",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## A tárfiók létrehozása

Ha tárfiókot szeretne létrehozni ebben az erőforráscsoportban, egy egyszerű parancsot kell futtatnia. Ehhez a parancshoz átadjuk a tárfiók nevét, a központilag üzembe helyezendő erőforráscsoportot, a központi telepítéshez szükséges fizikai régiót és a tárfiók termékváltozatát. Minden érték környezeti változók használatával van konfigurálva.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "accessTier": "Hot",
  "allowBlobPublicAccess": false,
  "allowCrossTenantReplication": null,
  "allowSharedKeyAccess": null,
  "allowedCopyScope": null,
  "azureFilesIdentityBasedAuthentication": null,
  "blobRestoreStatus": null,
  "creationTime": "2023-08-10T14:37:41.276351+00:00",
  "customDomain": null,
  "defaultToOAuthAuthentication": null,
  "dnsEndpointType": null,
  "enableHttpsTrafficOnly": true,
  "enableNfsV3": null,
  "encryption": {
    "encryptionIdentity": null,
    "keySource": "Microsoft.Storage",
    "keyVaultProperties": null,
    "requireInfrastructureEncryption": null,
    "services": {
      "blob": {
        "enabled": true,
        "keyType": "Account",
        "lastEnabledTime": "2023-08-10T14:37:41.370163+00:00"
      },
      "file": {
        "enabled": true,
        "keyType": "Account",
        "lastEnabledTime": "2023-08-10T14:37:41.370163+00:00"
      },
      "queue": null,
      "table": null
    }
  },
  "extendedLocation": null,
  "failoverInProgress": null,
  "geoReplicationStats": null,
  "id": "/subscriptions/ab9d8365-2f65-47a4-8df4-7e40db70c8d2/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.Storage/storageAccounts/$MY_STORAGE_ACCOUNT_NAME",
  "identity": null,
  "immutableStorageWithVersioning": null,
  "isHnsEnabled": null,
  "isLocalUserEnabled": null,
  "isSftpEnabled": null,
  "keyCreationTime": {
    "key1": "2023-08-10T14:37:41.370163+00:00",
    "key2": "2023-08-10T14:37:41.370163+00:00"
  },
  "keyPolicy": null,
  "kind": "StorageV2",
  "largeFileSharesState": null,
  "lastGeoFailoverTime": null,
  "location": "$REGION",
  "minimumTlsVersion": "TLS1_0",
  "name": "$MY_STORAGE_ACCOUNT_NAME",
  "networkRuleSet": {
    "bypass": "AzureServices",
    "defaultAction": "Allow",
    "ipRules": [],
    "resourceAccessRules": null,
    "virtualNetworkRules": []
  },
  "primaryEndpoints": {
    "blob": "https://$MY_STORAGE_ACCOUNT_NAME.blob.core.windows.net/",
    "dfs": "https://$MY_STORAGE_ACCOUNT_NAME.dfs.core.windows.net/",
    "file": "https://$MY_STORAGE_ACCOUNT_NAME.file.core.windows.net/",
    "internetEndpoints": null,
    "microsoftEndpoints": null,
    "queue": "https://$MY_STORAGE_ACCOUNT_NAME.queue.core.windows.net/",
    "table": "https://$MY_STORAGE_ACCOUNT_NAME.table.core.windows.net/",
    "web": "https://$MY_STORAGE_ACCOUNT_NAME.z22.web.core.windows.net/"
  },
  "primaryLocation": "$REGION",
  "privateEndpointConnections": [],
  "provisioningState": "Succeeded",
  "publicNetworkAccess": null,
  "resourceGroup": "$MY_RESOURCE_GROUP_NAME",
  "routingPreference": null,
  "sasPolicy": null,
  "secondaryEndpoints": null,
  "secondaryLocation": null,
  "sku": {
    "name": "Standard_LRS",
    "tier": "Standard"
  },
  "statusOfPrimary": "available",
  "statusOfSecondary": null,
  "storageAccountSkuConversionStatus": null,
  "tags": {},
  "type": "Microsoft.Storage/storageAccounts"
}
```

A tárfiók egyik API-kulcsát is el kell tárolnunk egy környezeti változóban későbbi használatra (tároló létrehozásához és a kód környezeti fájljában való elhelyezéséhez). Meghívjuk a `keys list` parancsot a tárfiókon, és az elsőt egy `STORAGE_ACCOUNT_KEY` környezeti változóban tároljuk.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Tároló létrehozása a tárfiókban

Futtassa a következő parancsot egy `images` tároló létrehozásához az imént létrehozott tárfiókban. A felhasználó által feltöltött képek blobokként lesznek tárolva ebben a tárolóban.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## -adatbázis létrehozása

Rugalmas Azure Database for PostgreSQL-kiszolgálót hozunk létre az alkalmazás számára a felhasználók és szavazataik tárolásához. Több argumentumot adunk át a `create` parancsnak:

- Az alapok: az adatbázis neve, az erőforráscsoport és a fizikai régió, amelyben üzembe helyezhető.
- A szint (amely meghatározza a kiszolgáló képességeit) olyan `burstable`számítási feladatokhoz tartozik, amelyek nem igényelnek teljes cpu-t folyamatosan.
- Az SKU mint `Standard_B1ms`.
  - `Standard` a teljesítményszinthez.
  - `B` a kipukkanható számítási feladatokhoz.
  - `1` egyetlen virtuális maghoz.
  - `ms` memóriaoptimalizált.
- A tárterület mérete, 32 GiB
- A PostgreSQL főverziója, 15
- Az adattabase hitelesítő adatai: felhasználónév és jelszó

```bash
az postgres flexible-server create \
  --name $MY_DATABASE_SERVER_NAME \
  --database-name $MY_DATABASE_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $REGION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --yes
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "connectionString": "postgresql://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_NAME.postgres.database.azure.com/flexibleserverdb?sslmode=require",
  "databaseName": "$MY_DATABASE_NAME",
  "firewallName": "FirewallIPAddress_2023-8-10_10-53-21",
  "host": "$MY_DATABASE_NAME.postgres.database.azure.com",
  "id": "/subscriptions/ab9d8365-2f65-47a4-8df4-7e40db70c8d2/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.DBforPostgreSQL/flexibleServers/$MY_DATABASE_NAME",
  "location": "$REGION",
  "password": "$MY_DATABASE_PASSWORD",
  "resourceGroup": "$MY_RESOURCE_GROUP_NAME",
  "skuname": "Standard_B1ms",
  "username": "$MY_DATABASE_USERNAME",
  "version": "15"
}
```

A kapcsolati sztring egy környezeti változóban is tárolnunk kell az adatbázisba későbbi használatra. Ez az URL-cím lehetővé teszi az adatbázis elérését az imént létrehozott erőforráson belül.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Computer Vision-erőforrás létrehozása

Létrehozunk egy Computer Vision-erőforrást, amely képes lesz azonosítani a felhasználók által feltöltött képeken lévő macskákat vagy kutyákat. A Computer Vision-erőforrás létrehozása egyetlen paranccsal végezhető el. Több argumentumot adunk át a `create` parancsnak:

- Az alapok: az erőforrás neve, az erőforráscsoport, a régió és egy Computer Vision-erőforrás létrehozása.
- A termékváltozat mint `S1`, vagy a legköltséghatékonyabb fizetős teljesítményszint.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "etag": "\"090ac83c-0000-0700-0000-64d4fcd80000\"",
  "id": "/subscriptions/ab9d8365-2f65-47a4-8df4-7e40db70c8d2/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.CognitiveServices/accounts/$MY_COMPUTER_VISION_NAME",
  "identity": null,
  "kind": "ComputerVision",
  "location": "$REGION",
  "name": "$MY_COMPUTER_VISION_NAME",
  "properties": {
    "allowedFqdnList": null,
    "apiProperties": null,
    "callRateLimit": {
      "count": null,
      "renewalPeriod": null,
      "rules": [
        {
          "count": 30.0,
          "dynamicThrottlingEnabled": true,
          "key": "vision.recognizeText",
          "matchPatterns": [
            {
              "method": "POST",
              "path": "vision/recognizeText"
            },
            {
              "method": "GET",
              "path": "vision/textOperations/*"
            },
            {
              "method": "*",
              "path": "vision/read/*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        },
        {
          "count": 15.0,
          "dynamicThrottlingEnabled": true,
          "key": "vision",
          "matchPatterns": [
            {
              "method": "*",
              "path": "vision/*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        },
        {
          "count": 500.0,
          "dynamicThrottlingEnabled": null,
          "key": "container.billing",
          "matchPatterns": [
            {
              "method": "*",
              "path": "billing/*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 10.0
        },
        {
          "count": 20.0,
          "dynamicThrottlingEnabled": true,
          "key": "default",
          "matchPatterns": [
            {
              "method": "*",
              "path": "*"
            }
          ],
          "minCount": null,
          "renewalPeriod": 1.0
        }
      ]
    },
    "capabilities": [
      {
        "name": "DynamicThrottling",
        "value": null
      },
      {
        "name": "VirtualNetworks",
        "value": null
      },
      {
        "name": "Container",
        "value": "ComputerVision.VideoAnalytics,ComputerVision.ComputerVisionRead,ComputerVision.ocr,ComputerVision.readfile,ComputerVision.readfiledsd,ComputerVision.recognizetext,ComputerVision.ComputerVision,ComputerVision.ocrlayoutworker,ComputerVision.ocrcontroller,ComputerVision.ocrdispatcher,ComputerVision.ocrbillingprocessor,ComputerVision.ocranalyzer,ComputerVision.ocrpagesplitter,ComputerVision.ocrapi,ComputerVision.ocrengineworker"
      }
    ],
    "customSubDomainName": null,
    "dateCreated": "2023-08-10T15:06:00.4272845Z",
    "deletionDate": null,
    "disableLocalAuth": null,
    "dynamicThrottlingEnabled": null,
    "encryption": null,
    "endpoint": "https://$REGION.api.cognitive.microsoft.com/",
    "endpoints": {
      "Computer Vision": "https://$REGION.api.cognitive.microsoft.com/",
      "Container": "https://$REGION.api.cognitive.microsoft.com/"
    },
    "internalId": "93645816f9594fe49a8f4023c0bf34b4",
    "isMigrated": false,
    "migrationToken": null,
    "networkAcls": null,
    "privateEndpointConnections": [],
    "provisioningState": "Succeeded",
    "publicNetworkAccess": "Enabled",
    "quotaLimit": null,
    "restore": null,
    "restrictOutboundNetworkAccess": null,
    "scheduledPurgeDate": null,
    "skuChangeInfo": null,
    "userOwnedStorage": null
  },
  "resourceGroup": "$MY_RESOURCE_GROUP_NAME",
  "sku": {
    "capacity": null,
    "family": null,
    "name": "S1",
    "size": null,
    "tier": null
  },
  "systemData": {
    "createdAt": "2023-08-10T15:06:00.107300+00:00",
    "createdBy": "username@domain.com",
    "createdByType": "User",
    "lastModifiedAt": "2023-08-10T15:06:00.107300+00:00",
    "lastModifiedBy": "username@domain.com",
    "lastModifiedByType": "User"
  },
  "tags": null,
  "type": "Microsoft.CognitiveServices/accounts"
}
```

A computer vision erőforrás eléréséhez a végpontra és a kulcsra is szükségünk van. Az Azure CLI-vel két `az cognitiveservices account` parancshoz férhetünk hozzá: `show` és `keys list`ezek adják meg, amire szükségünk van.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## A kód üzembe helyezése tárolóalkalmazásban

Most, hogy beállítottuk a tárolási, adatbázis- és Computer Vision-erőforrásokat, készen állunk az alkalmazáskód üzembe helyezésére. Ehhez az Azure Container Apps használatával fogjuk üzemeltetni a Next.js-alkalmazás tárolóalapú buildét. A `Dockerfile` rendszer már létrehozta az adattár gyökerét, ezért mindössze egyetlen parancsot kell futtatnunk a kód üzembe helyezéséhez. A parancs futtatása előtt először telepíteni kell az Azure CLI containerapp bővítményét.

```bash
az extension add --upgrade -n containerapp
```

Ez a parancs létrehoz egy Azure Container Registry-erőforrást a Docker-rendszerkép üzemeltetéséhez, egy Azure Container App-erőforrást, amely a lemezképet futtatja, valamint egy Azure Container App Environment-erőforrást a rendszerképhez. Bontsuk le, amit átadunk a parancsnak.

- Az alapok: erőforrás neve, erőforráscsoport és régió
- A használni vagy létrehozni kívánt Azure Container App Environment-erőforrás neve
- A forráskód elérési útja

```bash
az containerapp up \
  --name $MY_CONTAINER_APP_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $REGION \
  --environment $MY_CONTAINER_APP_ENV_NAME \
  --context-path computer-vision-nextjs-webapp \
  --source computer-vision-nextjs-webapp \
  --target-port 3000 \
  --ingress external \
  --env-vars \
    AZURE_DATABASE_URL=$DATABASE_URL \
    AZURE_COMPUTER_VISION_KEY=$COMPUTER_VISION_KEY \
    AZURE_COMPUTER_VISION_ENDPOINT=$COMPUTER_VISION_ENDPOINT \
    AZURE_STORAGE_ACCOUNT_NAME=$MY_STORAGE_ACCOUNT_NAME \
    AZURE_STORAGE_ACCOUNT_KEY=$STORAGE_ACCOUNT_KEY
```

A parancs sikerességét a következő paranccsal ellenőrizheti:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "id": "/subscriptions/fake3265-2f64-47a4-8df4-7e41ab70c8dh/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.App/containerapps/$MY_CONTAINER_APP_NAME",
  "identity": {
    "type": "None"
  },
  "location": "West US",
  "name": "$MY_CONTAINER_APP_NAME",
  "properties": {
    "configuration": {
      "activeRevisionsMode": "Single",
      "dapr": null,
      "ingress": {
        "allowInsecure": false,
        "clientCertificateMode": null,
        "corsPolicy": null,
        "customDomains": null,
        "exposedPort": 0,
        "external": true,
        "fqdn": "$MY_CONTAINER_APP_NAME.kindocean-a506af76.$REGION.azurecontainerapps.io",
        "ipSecurityRestrictions": null,
        "stickySessions": null,
        "targetPort": 3000,
        "traffic": [
          {
            "latestRevision": true,
            "weight": 100
          }
        ],
        "transport": "Auto"
      },
      "maxInactiveRevisions": null,
      "registries": null,
      "secrets": null,
      "service": null
    },
    "customDomainVerificationId": "06C64CD176439F8B6CCBBE1B531758828A5CACEABFB30B4DC9750641532924F6",
    "environmentId": "/subscriptions/fake3265-2f64-47a4-8df4-7e41ab70c8dh/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.App/managedEnvironments/$MY_CONTAINER_APP_ENV_NAME",
    "eventStreamEndpoint": "https://$REGION.azurecontainerapps.dev/subscriptions/eb9d8265-2f64-47a4-8df4-7e41db70c8d8/resourceGroups/$MY_RESOURCE_GROUP_NAME/containerApps/$MY_CONTAINER_APP_NAME/eventstream",
    "latestReadyRevisionName": "$MY_CONTAINER_APP_NAME--jl6fh75",
    "latestRevisionFqdn": "$MY_CONTAINER_APP_NAME--jl6fh75.kindocean-a506af76.$REGION.azurecontainerapps.io",
    "latestRevisionName": "$MY_CONTAINER_APP_NAME--jl6fh75",
    "managedEnvironmentId": "/subscriptions/eb9d8265-2f64-47a4-8df4-7e41db70c8d8/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.App/managedEnvironments/$MY_CONTAINER_APP_ENV_NAME",
    "outboundIpAddresses": ["20.237.221.47"],
    "provisioningState": "Succeeded",
    "runningStatus": "Running",
    "template": {
      "containers": [
        {
          "env": [
            {
              "name": "AZURE_DATABASE_URL",
              "value": "$DATABASE_URL"
            },
            {
              "name": "AZURE_COMPUTER_VISION_KEY",
              "value": "$COMPUTER_VISION_KEY"
            },
            {
              "name": "AZURE_COMPUTER_VISION_ENDPOINT",
              "value": "$COMPUTER_VISION_ENDPOINT"
            },
            {
              "name": "AZURE_STORAGE_ACCOUNT_NAME",
              "value": "$MY_STORAGE_ACCOUNT_NAME"
            },
            {
              "name": "AZURE_STORAGE_ACCOUNT_KEY",
              "value": "$STORAGE_ACCOUNT_KEY"
            }
          ],
          "image": "ralphr123/cn-app",
          "name": "$MY_CONTAINER_APP_NAME",
          "resources": {
            "cpu": 0.5,
            "ephemeralStorage": "2Gi",
            "memory": "1Gi"
          }
        }
      ],
      "initContainers": null,
      "revisionSuffix": "",
      "scale": {
        "maxReplicas": 10,
        "minReplicas": null,
        "rules": null
      },
      "serviceBinds": null,
      "terminationGracePeriodSeconds": null,
      "volumes": null
    },
    "workloadProfileName": null
  },
  "resourceGroup": "$MY_RESOURCE_GROUP_NAME",
  "systemData": {
    "createdAt": "2023-08-10T21:50:07.2125698",
    "createdBy": "username@domain.com",
    "createdByType": "User",
    "lastModifiedAt": "2023-08-10T21:50:07.2125698",
    "lastModifiedBy": "username@domain.com",
    "lastModifiedByType": "User"
  },
  "type": "Microsoft.App/containerApps"
}
```

## Tűzfalszabály létrehozása az adatbázishoz

Az adatbázis alapértelmezés szerint úgy van konfigurálva, hogy engedélyezze az IP-címek engedélyezési listájából érkező forgalmat. Ehhez az engedélyezési listához hozzá kell adnunk az újonnan üzembe helyezett tárolóalkalmazás IP-címét. A parancsból lekérhetjük az `az containerapp show` IP-címet.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Ezt az IP-címet most már hozzáadhatjuk tűzfalszabályként az alábbi paranccsal:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Eredmények:

<!--expected_similarity=0.5-->
```json
{
  "endIpAddress": "20.237.221.47",
  "id": "/subscriptions/ab9d8365-2f65-47a4-8df4-7e40db70c8d2/resourceGroups/$MY_RESOURCE_GROUP_NAME/providers/Microsoft.DBforPostgreSQL/flexibleServers/$MY_DATABASE_SERVER_NAME/firewallRules/allow-container-app",
  "name": "allow-container-app",
  "resourceGroup": "$MY_RESOURCE_GROUP_NAME",
  "startIpAddress": "20.237.221.47",
  "systemData": null,
  "type": "Microsoft.DBforPostgreSQL/flexibleServers/firewallRules"
}
```

## Tárolási CORS-szabály létrehozása

A webböngészők olyan, azonos eredetű szabályzatként ismert biztonsági korlátozást vezetnek be, amely megakadályozza, hogy egy weblap más tartományban hívja meg az API-kat. A CORS biztonságos módot biztosít arra, hogy az egyik tartomány (a forrástartomány) meghívhassa az API-kat egy másik tartományban. Hozzá kell adnunk egy CORS-szabályt a webalkalmazás URL-címéhez a tárfiókunkhoz. Először is szerezzük be az URL-címet egy hasonló `az containerapp show` paranccsal, mint korábban.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Ezután készen állunk egy CORS-szabály hozzáadására a következő paranccsal. Bontsuk le a parancs különböző részeit.

- A blobszolgáltatást tártípusként írjuk be a szabály hozzáadásához.
- Minden műveletet engedélyezünk.
- Csak az imént mentett tárolóalkalmazás URL-címét engedélyezzük.
- Minden HTTP-fejlécet engedélyezünk ebből az URL-címből.
- A maximális életkor az az idő másodpercben, amellyel a böngészőnek gyorsítótáraznia kell egy adott kérésre adott elővizsgálati választ.
- Átadjuk a tárfiók nevét és kulcsát a korábbiakból.

```bash
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT PATCH \
  --origins $CONTAINER_APP_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY
```

Ennyi az egész! Nyugodtan hozzáférhet az újonnan üzembe helyezett webalkalmazáshoz a böngészőben, és kinyomtathatja a korábban hozzáadott CONTAINER_APP_URL környezeti változót.

```bash
echo $CONTAINER_APP_URL
```

## Következő lépések

- [Az Azure Container Apps dokumentációja](https://learn.microsoft.com/azure/container-apps/)
- [Az Azure Database for PostgreSQL dokumentációja](https://learn.microsoft.com/azure/postgresql/)
- [Az Azure Blob Storage dokumentációja](https://learn.microsoft.com/azure/storage/blobs/)
- [Az Azure Computer (AI) Vision dokumentációja](https://learn.microsoft.com/azure/ai-services/computer-vision/)
