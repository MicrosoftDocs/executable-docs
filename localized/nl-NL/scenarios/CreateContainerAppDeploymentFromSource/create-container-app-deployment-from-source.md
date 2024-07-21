---
title: 'Een container-app maken die gebruikmaakt van Blob Store, SQL en Computer Vision'
description: 'Deze zelfstudie laat zien hoe u een container-app maakt die gebruikmaakt van Blob Store, SQL en Computer Vision'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Een container-app maken die gebruikmaakt van Blob Store, SQL en Computer Vision

In deze handleiding doorlopen we het implementeren van de benodigde resources voor een web-app waarmee gebruikers stemmen kunnen uitbrengen met hun naam, e-mail en een afbeelding. Gebruikers kunnen stemmen op hun voorkeur voor kat of hond, met behulp van een afbeelding van een kat of een hond die door onze infrastructuur wordt geanalyseerd. Dit werkt alleen als we resources implementeren in verschillende Azure-services:

- **Azure Storage-account** voor het opslaan van de installatiekopieën
- **Azure Database for PostgreSQL** voor het opslaan van gebruikers en stemmen
- **Azure Computer Vision** voor het analyseren van de afbeeldingen voor katten of honden
- **Azure Container App** voor het implementeren van onze code

Opmerking: als u nog nooit een Computer Vision-resource hebt gemaakt, kunt u er geen maken met behulp van de Azure CLI. U moet uw eerste Computer Vision-resource maken vanuit Azure Portal om de voorwaarden voor verantwoorde AI te controleren en te bevestigen. U kunt dit hier doen: [Een Computer Vision-resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision) maken. Daarna kunt u volgende resources maken met behulp van elk implementatieprogramma (SDK, CLI of ARM-sjabloon, enzovoort) onder hetzelfde Azure-abonnement.

## Omgevingsvariabelen definiëren

De eerste stap in deze zelfstudie is het definiëren van omgevingsvariabelen. **Vervang de waarden aan de rechterkant door uw eigen unieke waarden.** Deze waarden worden in de zelfstudie gebruikt om resources te maken en de toepassing te configureren. Gebruik kleine letters en geen speciale tekens voor de naam van het opslagaccount.

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

## De voorbeeldopslagplaats klonen

Eerst gaan we deze opslagplaats klonen naar onze lokale machines. Hiermee beschikt u over de starterscode die nodig is om de functionaliteit voor de hierboven beschreven eenvoudige toepassing te bieden. We kunnen klonen met een eenvoudige Git-opdracht.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Als u opgeslagen omgevingsvariabelen wilt behouden, is het belangrijk dat dit terminalvenster geopend blijft voor de duur van de implementatie.

## Aanmelden bij Azure met behulp van de CLI

Als u opdrachten wilt uitvoeren voor Azure met behulp van [de CLI ](https://learn.microsoft.com/cli/azure/install-azure-cli), moet u zich aanmelden. Dit wordt gedaan via de `az login` opdracht:

## Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. We maken er een voor deze zelfstudie. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde parameters $MY_RESOURCE_GROUP_NAME en $REGION parameters.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultaten:

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

## Het opslagaccount maken

Als u een opslagaccount in deze resourcegroep wilt maken, moet u een eenvoudige opdracht uitvoeren. Voor deze opdracht geven we de naam van het opslagaccount, de resourcegroep door waarin het moet worden geïmplementeerd, de fysieke regio waarin het moet worden geïmplementeerd en de SKU van het opslagaccount. Alle waarden worden geconfigureerd met behulp van omgevingsvariabelen.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Resultaten:

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

We moeten ook een van de API-sleutels voor het opslagaccount opslaan in een omgevingsvariabele voor later gebruik (om een container te maken en in een omgevingsbestand voor de code te plaatsen). We roepen de `keys list` opdracht aan in het opslagaccount en slaan de eerste op in een `STORAGE_ACCOUNT_KEY` omgevingsvariabele.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Een container maken in het opslagaccount

Voer de volgende opdracht uit om een `images` container te maken in het opslagaccount dat we zojuist hebben gemaakt. Door de gebruiker geüploade installatiekopieën worden opgeslagen als blobs in deze container.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Resultaten:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Een -database maken

We maken een flexibele Azure Database for PostgreSQL-server voor de toepassing om gebruikers en hun stemmen op te slaan. We geven verschillende argumenten door aan de `create` opdracht:

- De basisprincipes: databasenaam, resourcegroep en fysieke regio waarin u wilt implementeren.
- De laag (die de mogelijkheden van de server bepaalt) als `burstable`, wat is voor workloads die niet continu volledige CPU nodig hebben.
- De SKU als `Standard_B1ms`.
  - `Standard` voor de prestatielaag.
  - `B` voor burstable workload.
  - `1` voor één vCore.
  - `ms` voor geoptimaliseerd geheugen.
- De opslaggrootte, 32 GiB
- De primaire versie van PostgreSQL, 15
- De datatabase-referenties: gebruikersnaam en wachtwoord

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

Resultaten:

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

We moeten de verbindingsreeks ook opslaan in de database in een omgevingsvariabele voor later gebruik. Met deze URL hebben we toegang tot de database binnen de resource die we zojuist hebben gemaakt.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Een Computer Vision-resource maken

We maken een Computer Vision-resource om katten of honden te identificeren in de foto's die gebruikers uploaden. U kunt een Computer Vision-resource maken met één opdracht. We geven verschillende argumenten door aan de `create` opdracht:

- De basisbeginselen: resourcenaam, resourcegroep, regio en om een Computer Vision-resource te maken.
- De SKU als `S1`, of de meest rendabele betaalde prestatielaag.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Resultaten:

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

Voor toegang tot onze Computer Vision-resource hebben we zowel het eindpunt als de sleutel nodig. Met de Azure CLI hebben we toegang tot twee `az cognitiveservices account` opdrachten: `show` en `keys list`, die ons geven wat we nodig hebben.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## De code implementeren in een container-app

Nu de opslag-, database- en Computer Vision-resources zijn ingesteld, zijn we klaar om de toepassingscode te implementeren. Hiervoor gebruiken we Azure Container Apps om een container-build van onze Next.js-app te hosten. De `Dockerfile` code is al gemaakt in de hoofdmap van de opslagplaats, dus u hoeft alleen maar één opdracht uit te voeren om de code te implementeren. Voordat u deze opdracht uitvoert, moet u eerst de containerapp-extensie voor de Azure CLI installeren.

```bash
az extension add --upgrade -n containerapp
```

Met deze opdracht maakt u een Azure Container Registry-resource voor het hosten van onze Docker-installatiekopie, een Azure Container App-resource die de installatiekopie uitvoert en een Azure Container App Environment-resource voor onze installatiekopie. Laten we eens uitsplitsen wat we in de opdracht doorgeven.

- De basisbeginselen: resourcenaam, resourcegroep en de regio
- De naam van de Azure Container App Environment-resource die u wilt gebruiken of maken
- Het pad naar de broncode

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

We kunnen controleren of de opdracht is geslaagd met behulp van:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Resultaten:

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

## Een firewallregel voor een database maken

Onze database is standaard geconfigureerd om verkeer vanaf een acceptatielijst met IP-adressen toe te staan. We moeten het IP-adres van de zojuist geïmplementeerde container-app toevoegen aan deze acceptatielijst. We kunnen het IP-adres ophalen uit de `az containerapp show` opdracht.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

We kunnen dit IP-adres nu toevoegen als firewallregel met deze opdracht:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Resultaten:

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

## Een CORS-regel voor opslag maken

Webbrowsers implementeren een beveiligingsbeperking die bekend staat als same-origin-beleid waarmee wordt voorkomen dat een webpagina API's in een ander domein aanroept. CORS biedt een veilige manier om toe te staan dat één domein (het oorspronkelijke domein) API's in een ander domein aanroept. We moeten een CORS-regel toevoegen aan de URL van onze web-app aan ons opslagaccount. Laten we eerst de URL ophalen met een vergelijkbare `az containerapp show` opdracht als eerder.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Vervolgens kunt u een CORS-regel toevoegen met de volgende opdracht. Laten we de verschillende onderdelen van deze opdracht opsplitsen.

- We geven de blobservice op als het opslagtype waaraan de regel moet worden toegevoegd.
- We staan toe dat alle bewerkingen worden uitgevoerd.
- We staan alleen de URL van de container-app toe die we zojuist hebben opgeslagen.
- We staan alle HTTP-headers van deze URL toe.
- De maximale leeftijd is de hoeveelheid tijd, in seconden, dat een browser de preflight-reactie voor een specifieke aanvraag in de cache moet opslaan.
- We geven de naam en sleutel van het opslagaccount door van eerder.

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

Dat is het! U kunt de zojuist geïmplementeerde web-app openen in uw browser om de omgevingsvariabele CONTAINER_APP_URL die we eerder hebben toegevoegd, af te drukken.

```bash
echo $CONTAINER_APP_URL
```

## Volgende stappen

- [Documentatie voor Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Documentatie voor Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Documentatie voor Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/)
- [Documentatie voor Azure Computer (AI) Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/)
