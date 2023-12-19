---
title: 'Erstellen einer Container-App unter Verwendung von Blob Store, SQL und maschinellem Sehen'
description: 'Dieses Tutorial veranschaulicht, wie Sie eine Container-App unter Verwendung von Blob Store, SQL und maschinellem Sehen erstellen.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Erstellen einer Container-App unter Verwendung von Blob Store, SQL und maschinellem Sehen

In diesem Leitfaden werden Sie schrittweise durch die Bereitstellung der erforderlichen Ressourcen für eine Web-App geführt, mit der Benutzer*innen ihre Stimme mit ihrem Namen, ihrer E-Mail und einem Bild abgeben können. Benutzer*innen können für ihre Vorliebe für Katze oder Hund abstimmen, indem sie ein Bild einer Katze oder eines Hundes verwenden, das von unserer Infrastruktur analysiert wird. Damit dies funktioniert, stellen wir Ressourcen in verschiedenen Azure-Diensten bereit:

- **Azure Storage-Konto** zum Speichern der Bilder
- **Azure Database for PostgreSQL** zum Speichern der Benutzer*innen und Stimmen
- **Azure Computer Vision** zum Analysieren der Bilder für Katzen oder Hunde
- **Azure Container App** zum Bereitstellen unseres Codes

Hinweis: Wenn Sie noch nie eine Ressource für maschinelles Sehen erstellt haben, können Sie diese nicht mithilfe der Azure CLI erstellen. Sie müssen Ihre erste Ressource für maschinelles Sehen im Azure-Portal erstellen, damit Sie die Geschäftsbedingungen für verantwortungsvolle KI überprüfen und bestätigen können. Sie können dies hier tun: [Erstellen einer Ressource für maschinelles Sehen](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision) Anschließend können Sie nachfolgende Ressourcen mit einem beliebigen Bereitstellungstool (SDK, CLI oder ARM-Vorlage usw.) unter demselben Azure-Abonnement erstellen.

## Umgebungsvariablen definieren

Der erste Schritt in diesem Tutorial besteht darin, Umgebungsvariablen zu definieren. **Ersetzen Sie die Werte auf der rechten Seite durch ihre eigenen eindeutigen Werte.** Diese Werte werden im gesamten Tutorial verwendet, um Ressourcen zu erstellen und die Anwendung zu konfigurieren. Verwenden Sie Kleinbuchstaben und keine Sonderzeichen im Namen des Speicherkontos.

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

## Klonen des Beispielrepositorys

Zunächst klonen wir dieses Repository auf unseren lokalen Computer. Dadurch wird der Startcode bereitgestellt, der für die Bereitstellung der Funktionalität für die oben beschriebene einfache Anwendung erforderlich ist. Wir können mit einem einfachen Git-Befehl klonen.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Damit gespeicherte Umgebungsvariablen beibehalten werden, ist es wichtig, dass dieses Terminalfenster für die Dauer der Bereitstellung geöffnet bleibt.

## Anmelden bei Azure mit der CLI

Um Befehle für Azure mithilfe [der CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) auszuführen, müssen Sie sich anmelden. Dies geschieht mit dem Befehl `az login`:

## Erstellen einer Ressourcengruppe

Eine Ressourcengruppe ist ein Container für zugehörige Ressourcen. Alle Ressourcen müssen in einer Ressourcengruppe platziert werden. In diesem Tutorial erstellen wir eine Ressourcengruppe. Mit dem folgenden Befehl wird eine Ressourcengruppe mit den zuvor definierten Parametern $MY_RESOURCE_GROUP_NAME und $REGION erstellt.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Ergebnisse:

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

## Erstellen des Speicherkontos

Um ein Speicherkonto in dieser Ressourcengruppe zu erstellen, müssen wir einen einfachen Befehl ausführen. In diesem Befehl übergeben wir den Namen des Speicherkontos, die Ressourcengruppe, in der es bereitgestellt werden soll, die physische Region, in der es bereitgestellt werden soll, und die SKU des Speicherkontos. Alle anderen Werte werden mithilfe von Umgebungsvariablen konfiguriert.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Ergebnisse:

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

Außerdem müssen wir einen der API-Schlüssel für das Speicherkonto für die spätere Verwendung in einer Umgebungsvariable speichern (um einen Container zu erstellen und in eine Umgebungsdatei für den Code einzufügen). Wir rufen den Befehl `keys list` für das Speicherkonto auf und speichern den ersten Schlüssel in einer `STORAGE_ACCOUNT_KEY`-Umgebungsvariable.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Erstellen eines Containers im Speicherkonto

Führen Sie den folgenden Befehl aus, um einen `images`-Container in dem gerade erstellten Speicherkonto zu erstellen. Von Benutzer*innen hochgeladene Bilder werden in diesem Container als Blobs gespeichert.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Ergebnisse:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Erstellen einer Datenbank

Wir werden eine Instanz von Azure Database for PostgreSQL – Flexibler Server für die Anwendung erstellen, um Benutzer*innen und deren Stimmen zu speichern. Wir übergeben dem Befehl `create` mehrere Argumente:

- Grundlagen: Datenbankname, Ressourcengruppe und physische Region, in der sie bereitgestellt werden sollen.
- Die Dienstebene (welche die Funktionen des Servers bestimmt) `burstable` für Workloads, die nicht die volle CPU kontinuierlich benötigen.
- Die SKU als `Standard_B1ms`.
  - `Standard` für die Leistungsstufe.
  - `B` für eine burstfähige Workload.
  - `1` für einen einzelnen virtuellen Kern.
  - `ms` für arbeitsspeicheroptimiert.
- Die Speichergröße: 32 GiB
- Die PostgreSQL-Hauptversion: 15
- Die Datenbankanmeldeinformationen: Benutzername und Kennwort

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

Ergebnisse:

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

Außerdem müssen wir die Verbindungszeichenfolge für die Datenbank zur späteren Verwendung in einer Umgebungsvariable speichern. Diese URL ermöglicht uns den Zugriff auf die Datenbank innerhalb der soeben erstellten Ressource.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Erstellen einer Ressource für maschinelles Sehen

Wir werden eine Ressource für maschinelles Sehen erstellen, um in den von den Benutzer*innen hochgeladenen Bildern Katzen oder Hunde identifizieren zu können. Das Erstellen einer Ressource für maschinelles Sehen kann mit einem einzigen Befehl erfolgen. Wir übergeben dem Befehl `create` mehrere Argumente:

- Grundlagen: Ressourcenname, Ressourcengruppe, Region und Erstellen einer Ressource für maschinelles Sehen.
- Die SKU als `S1` bzw. die kostengünstigste kostenpflichtige Leistungsstufe.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Ergebnisse:

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

Um auf unsere Ressource für maschinelles Sehen zuzugreifen, benötigen wir sowohl den Endpunkt als auch den Schlüssel. Mit der Azure CLI haben wir Zugriff auf zwei `az cognitiveservices account`-Befehle: `show` und `keys list`, die für unsere Zwecke genügen.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Bereitstellen des Codes in einer Container-App

Nachdem wir nun über unseren Speicher, unsere Datenbank und unsere Ressource für maschinelles Sehen verfügen, sind wir bereit, den Anwendungscode bereitzustellen. Wir verwenden hierzu Azure Container Apps, um einen containerisierten Build unserer Next.js-App zu hosten. Da die `Dockerfile` bereits im Stammverzeichnis des Repositorys erstellt worden ist, müssen wir nur einen einzigen Befehl ausführen, um den Code bereitzustellen. Bevor Sie diesen Befehl ausführen, müssen wir zunächst die Container-App-Erweiterung für die Azure CLI installieren.

```bash
az extension add --upgrade -n containerapp
```

Mit diesem Befehl wird eine Azure Container Registry-Ressource erstellt, die unser Docker-Image, eine Azure Container App-Ressource, die das Image ausführt, und eine Azure Container App Environment-Ressource für unser Image hostet. Sehen wir uns genauer an, was wir dem Befehl im Einzelnen übergeben.

- Grundlagen: Ressourcenname, Ressourcengruppe und Region
- Der Name der Azure Container Apps-Umgebungsressource, die verwendet oder erstellt werden soll
- Pfad zum Quellcode

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

Wir können wie folgt überprüfen, ob der Befehl erfolgreich war:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Ergebnisse:

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

## Erstellen einer Datenbankfirewallregel

Standardmäßig ist unsere Datenbank so konfiguriert, dass Datenverkehr von einer Zulassungsliste von IP-Adressen zugelassen wird. Wir müssen der Zulassungsliste die IP-Adresse unserer neu bereitgestellten Container-App hinzufügen. Wir können die IP-Adresse mit dem Befehl `az containerapp show` abrufen.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Nun können wir mit diesem Befehl diese IP-Adresse als Firewallregel hinzufügen:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Ergebnisse:

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

## Erstellen einer CORS-Speicherregel

In Webbrowser ist eine Sicherheitseinschränkung implementiert, die als „Same Origin Policy“ bekannt ist und verhindert, dass eine Webseite APIs in einer anderen Domäne aufruft. CORS bietet eine sichere Möglichkeit, um einer Domäne den Aufruf von APIs in einer anderen Domäne zu erlauben. Wir müssen eine CORS-Regel für die URL unserer Webanwendung zu unserem Speicherkonto hinzufügen. Als Erstes rufen wir die URL mit einem ähnlichen `az containerapp show`-Befehl wie zuvor ab.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Als Nächstes können wir mit dem folgenden Befehl eine CORS-Regel hinzufügen. Lassen Sie uns die verschiedenen Teile dieses Befehls betrachten.

- Wir geben Blob-Dienst als Speichertyp an, dem die Regel hinzugefügt werden soll.
- Wir lassen die Ausführung aller Vorgänge zu.
- Wir lassen nur die soeben gespeicherte Container-App-URL zu.
- Wir lassen alle HTTP-Header von dieser URL zu.
- Das maximale Alter ist die Zeitspanne in Sekunden, über die ein Browser die Preflight-Antwort für eine bestimmte Anforderung zwischenspeichern soll.
- Wir übergeben den Namen und Schlüssel des Speicherkontos.

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

Das ist alles! Sie können auf die neu bereitgestellte Web-App in Ihrem Browser zugreifen, um die zuvor hinzugefügte Umgebungsvariable CONTAINER_APP_URL zu drucken.

```bash
echo $CONTAINER_APP_URL
```

## Nächste Schritte

- [Dokumentation zu Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Dokumentation zu Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Dokumentation zu Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/)
- [Dokumentation zu Azure (KI) Computer Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/)
