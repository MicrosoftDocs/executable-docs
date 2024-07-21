---
title: 'Vytvoření kontejnerové aplikace využívající Úložiště objektů blob, SQL a Počítačové zpracování obrazu'
description: 'V tomto kurzu se dozvíte, jak vytvořit kontejnerovou aplikaci využívající Úložiště objektů blob, SQL a Počítačové zpracování obrazu'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Vytvoření kontejnerové aplikace využívající Úložiště objektů blob, SQL a Počítačové zpracování obrazu

V této příručce si projdeme nasazení potřebných prostředků pro webovou aplikaci, které uživatelům umožní přetypovat hlasy pomocí jména, e-mailu a obrázku. Uživatelé mohou hlasovat pro své preference kočky nebo psa pomocí obrázku kočky nebo psa, který bude analyzován naší infrastrukturou. Aby to fungovalo, budeme nasazovat prostředky napříč několika různými službami Azure:

- **Účet** služby Azure Storage pro ukládání imagí
- **Azure Database for PostgreSQL** pro ukládání uživatelů a hlasů
- **Azure Počítačové zpracování obrazu** k analýze obrázků pro kočky nebo psy
- **Azure Container App** pro nasazení našeho kódu

Poznámka: Pokud jste předtím nikdy nevytvořili Počítačové zpracování obrazu prostředek, nebudete ho moct vytvořit pomocí Azure CLI. Abyste mohli zkontrolovat a potvrdit podmínky a ujednání zodpovědné umělé inteligence, musíte na webu Azure Portal vytvořit první Počítačové zpracování obrazu prostředek. Můžete to udělat tady: [Vytvořte prostředek Počítačové zpracování obrazu](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision). Potom můžete vytvořit další prostředky pomocí libovolného nástroje pro nasazení (sdk, rozhraní příkazového řádku nebo šablony ARM atd.) v rámci stejného předplatného Azure.

## Definování proměnných prostředí

Prvním krokem v tomto kurzu je definování proměnných prostředí. **Nahraďte hodnoty na pravé straně vlastními jedinečnými hodnotami.** Tyto hodnoty se použijí v průběhu kurzu k vytváření prostředků a konfiguraci aplikace. Pro název účtu úložiště používejte malá písmena a žádné speciální znaky.

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

## Klonování ukázkového úložiště

Nejprve naklonujeme toto úložiště na místní počítače. Tím poskytnete počáteční kód potřebný k poskytnutí funkcí pro jednoduchou aplikaci uvedenou výše. Můžeme klonovat pomocí jednoduchého příkazu Git.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Pokud chcete zachovat uložené proměnné prostředí, je důležité, aby toto okno terminálu zůstalo otevřené po dobu trvání nasazení.

## Přihlášení k Azure pomocí rozhraní příkazového řádku

Pokud chcete spouštět příkazy v Azure pomocí [rozhraní příkazového řádku ](https://learn.microsoft.com/cli/azure/install-azure-cli), musíte se přihlásit. To se provádí pomocí `az login` příkazu:

## Vytvoření skupiny zdrojů

Skupina prostředků je kontejner pro související prostředky. Všechny prostředky musí být umístěné ve skupině prostředků. Pro účely tohoto kurzu ho vytvoříme. Následující příkaz vytvoří skupinu prostředků s dříve definovanými parametry $MY_RESOURCE_GROUP_NAME a $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Výsledky:

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

## Vytvoření účtu úložiště

K vytvoření účtu úložiště v této skupině prostředků musíme spustit jednoduchý příkaz. K tomuto příkazu předáváme název účtu úložiště, skupinu prostředků pro její nasazení, fyzickou oblast, do které se má nasadit, a skladovou položku účtu úložiště. Všechny hodnoty se konfigurují pomocí proměnných prostředí.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Výsledky:

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

Potřebujeme také uložit jeden z klíčů rozhraní API pro účet úložiště do proměnné prostředí pro pozdější použití (k vytvoření kontejneru a jeho vložení do souboru prostředí pro kód). Voláme `keys list` příkaz pro účet úložiště a ukládáme první příkaz do `STORAGE_ACCOUNT_KEY` proměnné prostředí.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Vytvoření kontejneru v účtu úložiště

Spuštěním následujícího příkazu vytvořte `images` kontejner v účtu úložiště, který jsme právě vytvořili. Obrázky nahrané uživatelem budou uloženy jako objekty blob v tomto kontejneru.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Výsledky:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Vytvořit databázi 

Vytvoříme flexibilní server Azure Database for PostgreSQL pro aplikaci pro ukládání uživatelů a jejich hlasů. Do příkazu předáváme několik argumentů `create` :

- Základy: název databáze, skupina prostředků a fyzická oblast, do které se má nasadit.
- Úroveň (která určuje možnosti serveru) jako `burstable`pro úlohy, které nepotřebují nepřetržitě plný procesor.
- Skladová položka jako `Standard_B1ms`.
  - `Standard` pro úroveň výkonu.
  - `B` pro nárazové zatížení.
  - `1` pro jedno virtuální jádro.
  - `ms` pro optimalizováno pro paměť.
- Velikost úložiště 32 GiB
- Hlavní verze PostgreSQL, 15
- Přihlašovací údaje k datové databázi: uživatelské jméno a heslo

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

Výsledky:

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

Potřebujeme také uložit připojovací řetězec do databáze do proměnné prostředí pro pozdější použití. Tato adresa URL nám umožní přístup k databázi v rámci prostředku, který jsme právě vytvořili.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Vytvoření prostředku Počítačové zpracování obrazu

Vytvoříme Počítačové zpracování obrazu prostředek, který bude schopen identifikovat kočky nebo psy v fotkách, které uživatelé nahrají. Vytvoření Počítačové zpracování obrazu prostředku lze provést jedním příkazem. Do příkazu předáváme několik argumentů `create` :

- Základy: název prostředku, skupina prostředků, oblast a vytvoření Počítačové zpracování obrazu prostředku.
- Skladová položka ( `S1`SKU) nebo nákladově nejefektivnější placená úroveň výkonu.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Výsledky:

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

Pro přístup k prostředku počítačového zpracování obrazu potřebujeme koncový bod i klíč. Pomocí Azure CLI máme přístup ke dvěma `az cognitiveservices account` příkazům: `show` a `keys list`, které nám poskytují to, co potřebujeme.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Nasazení kódu do kontejnerové aplikace

Teď, když máme naše úložiště, databázi a Počítačové zpracování obrazu prostředky, jsme připraveni nasadit kód aplikace. K tomu použijeme Azure Container Apps k hostování kontejnerizovaného sestavení naší Next.js aplikace. Ten `Dockerfile` už je vytvořený v kořenovém adresáři úložiště, takže stačí spustit jeden příkaz pro nasazení kódu. Před spuštěním tohoto příkazu musíme nejprve nainstalovat rozšíření containerapp pro Azure CLI.

```bash
az extension add --upgrade -n containerapp
```

Tento příkaz vytvoří prostředek Služby Azure Container Registry pro hostování image Dockeru, prostředku aplikace kontejneru Azure, který tuto image spouští, a prostředku Azure Container App Environment pro naši image. Pojďme se rozdělit na to, co předáváme do příkazu.

- Základy: název prostředku, skupina prostředků a oblast
- Název prostředku Azure Container App Environment, který se má použít nebo vytvořit
- Cesta ke zdrojovému kódu

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

Pomocí následujícího příkazu můžeme ověřit, že příkaz proběhl úspěšně:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Výsledky:

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

## Vytvoření pravidla brány firewall databáze

Ve výchozím nastavení je naše databáze nakonfigurovaná tak, aby povolovala provoz ze seznamu povolených IP adres. Do tohoto seznamu povolených musíme přidat IP adresu nově nasazené kontejnerové aplikace. IP adresu můžeme získat z `az containerapp show` příkazu.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Teď můžeme tuto IP adresu přidat jako pravidlo brány firewall pomocí tohoto příkazu:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Výsledky:

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

## Vytvoření pravidla CORS úložiště

Webové prohlížeče implementují omezení zabezpečení známé jako zásady stejného původu, které brání webové stránce v volání rozhraní API v jiné doméně. CORS poskytuje bezpečný způsob, jak povolit, aby jedna doména (původní doména) volala rozhraní API v jiné doméně. Potřebujeme přidat pravidlo CORS na adresu URL naší webové aplikace do účtu úložiště. Nejprve získáme adresu URL pomocí podobného `az containerapp show` příkazu jako dříve.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Dále jsme připraveni přidat pravidlo CORS pomocí následujícího příkazu. Pojďme rozdělit různé části tohoto příkazu.

- Jako typ úložiště zadáváme službu Blob Service, do které se má pravidlo přidat.
- Povolujeme provádění všech operací.
- Povolujeme jenom adresu URL aplikace kontejneru, které jsme právě uložili.
- Povolujeme všechna hlavička HTTP z této adresy URL.
- Maximální stáří je doba v sekundách, po kterou by měl prohlížeč ukládat předběžnou odpověď na konkrétní požadavek do mezipaměti.
- Předáváme název a klíč účtu úložiště z dřívější verze.

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

A je to! Neváhejte získat přístup k nově nasazené webové aplikaci v prohlížeči s tiskem proměnné prostředí CONTAINER_APP_URL, která jsme přidali dříve.

```bash
echo $CONTAINER_APP_URL
```

## Další kroky

- [Dokumentace ke službě Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Dokumentace k Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Dokumentace ke službě Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/)
- [Dokumentace ke zpracování obrazu ve službě Azure Computer (AI)](https://learn.microsoft.com/azure/ai-services/computer-vision/)
