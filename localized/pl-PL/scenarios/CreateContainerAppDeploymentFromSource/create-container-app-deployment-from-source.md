---
title: 'Tworzenie aplikacji kontenera korzystającej z magazynu obiektów blob, bazy danych SQL i przetwarzanie obrazów'
description: 'W tym samouczku pokazano, jak utworzyć aplikację kontenera korzystającą z usługi Blob Store, SQL i przetwarzanie obrazów'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Tworzenie aplikacji kontenera korzystającej z magazynu obiektów blob, bazy danych SQL i przetwarzanie obrazów

W tym przewodniku przejdziemy przez proces wdrażania niezbędnych zasobów dla aplikacji internetowej, która umożliwia użytkownikom oddanie głosów przy użyciu ich nazwy, poczty e-mail i obrazu. Użytkownicy mogą głosować na swoje preferencje dotyczące kota lub psa, używając obrazu kota lub psa, który będzie analizowany przez naszą infrastrukturę. W tym celu będziemy wdrażać zasoby w kilku różnych usługach platformy Azure:

- **Konto** usługi Azure Storage do przechowywania obrazów
- **Usługa Azure Database for PostgreSQL** do przechowywania użytkowników i głosów
- **Usługa Azure przetwarzanie obrazów** do analizowania obrazów dla kotów lub psów
- **Aplikacja** kontenera platformy Azure w celu wdrożenia naszego kodu

Uwaga: Jeśli wcześniej nigdy nie utworzono zasobu przetwarzanie obrazów, nie będzie można go utworzyć przy użyciu interfejsu wiersza polecenia platformy Azure. Aby przejrzeć i potwierdzić warunki i postanowienia dotyczące odpowiedzialnej sztucznej inteligencji, musisz utworzyć swój pierwszy zasób przetwarzanie obrazów z witryny Azure Portal. Możesz to zrobić tutaj: [Utwórz zasób](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision) przetwarzanie obrazów. Następnie możesz utworzyć kolejne zasoby przy użyciu dowolnego narzędzia wdrażania (zestawu SDK, interfejsu wiersza polecenia lub szablonu usługi ARM itp.) w ramach tej samej subskrypcji platformy Azure.

## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych. **Zastąp wartości po prawej stronie własnymi unikatowymi wartościami.** Te wartości będą używane w całym samouczku do tworzenia zasobów i konfigurowania aplikacji. Użyj małych liter i bez znaków specjalnych dla nazwy konta magazynu.

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

## Klonowanie przykładowego repozytorium

Najpierw sklonujemy to repozytorium na nasze maszyny lokalne. Zapewni to kod początkowy wymagany do zapewnienia funkcjonalności prostej aplikacji opisanej powyżej. Możemy sklonować za pomocą prostego polecenia git.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Aby zachować zapisane zmienne środowiskowe, ważne jest, aby to okno terminalu było otwarte przez czas trwania wdrożenia.

## Logowanie do platformy Azure przy użyciu interfejsu wiersza polecenia

Aby uruchamiać polecenia na platformie Azure przy użyciu [interfejsu wiersza polecenia ](https://learn.microsoft.com/cli/azure/install-azure-cli), musisz się zalogować. Odbywa się to jednak za pomocą `az login` polecenia :

## Tworzenie grupy zasobów

Grupa zasobów to kontener powiązanych zasobów. Wszystkie zasoby należy umieścić w grupie zasobów. Utworzymy go na potrzeby tego samouczka. Następujące polecenie tworzy grupę zasobów z wcześniej zdefiniowanymi parametrami $MY_RESOURCE_GROUP_NAME i $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Wyniki:

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

## Tworzenie konta magazynu

Aby utworzyć konto magazynu w tej grupie zasobów, musimy uruchomić proste polecenie. W tym poleceniu przekazujemy nazwę konta magazynu, grupę zasobów do jej wdrożenia, region fizyczny, w którym ma zostać wdrożony, oraz jednostkę SKU konta magazynu. Wszystkie wartości są konfigurowane przy użyciu zmiennych środowiskowych.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Wyniki:

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

Musimy również przechowywać jeden z kluczy interfejsu API dla konta magazynu w zmiennej środowiskowej do późniejszego użycia (aby utworzyć kontener i umieścić go w pliku środowiskowym dla kodu). Wywołujemy `keys list` polecenie na koncie magazynu i zapisujemy pierwszy w zmiennej środowiskowej `STORAGE_ACCOUNT_KEY` .

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Tworzenie kontenera na koncie magazynu

Uruchom następujące polecenie, aby utworzyć `images` kontener na właśnie utworzonym koncie magazynu. Przekazane przez użytkownika obrazy będą przechowywane jako obiekty blob w tym kontenerze.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Wyniki:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Utwórz bazę danych 

Utworzymy elastyczny serwer usługi Azure Database for PostgreSQL dla aplikacji do przechowywania użytkowników i ich głosów. Przekazujemy kilka argumentów do `create` polecenia:

- Podstawowe informacje: nazwa bazy danych, grupa zasobów i region fizyczny do wdrożenia.
- Warstwa (która określa możliwości serwera) jako `burstable`, która dotyczy obciążeń, które nie wymagają pełnego procesora CPU w sposób ciągły.
- Jednostka SKU jako `Standard_B1ms`.
  - `Standard` dla warstwy wydajności.
  - `B` w przypadku obciążenia z możliwością rozszerzenia.
  - `1` dla pojedynczego rdzenia wirtualnego.
  - `ms` zoptymalizowane pod kątem pamięci.
- Rozmiar magazynu, 32 GiB
- Wersja główna bazy danych PostgreSQL, 15
- Poświadczenia bazy danych: nazwa użytkownika i hasło

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

Wyniki:

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

Musimy również przechowywać parametry połączenia w bazie danych w zmiennej środowiskowej do późniejszego użycia. Ten adres URL umożliwi nam dostęp do bazy danych w właśnie utworzonym zasobie.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Tworzenie zasobu przetwarzania obrazów

Utworzymy zasób przetwarzanie obrazów, aby móc identyfikować koty lub psy na zdjęciach przekazywanych przez użytkowników. Tworzenie zasobu przetwarzanie obrazów można wykonać za pomocą jednego polecenia. Przekazujemy kilka argumentów do `create` polecenia:

- Podstawowe informacje: nazwa zasobu, grupa zasobów, region i aby utworzyć zasób przetwarzanie obrazów.
- Jednostka SKU jako `S1`, lub najbardziej opłacalna płatna warstwa wydajności.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Wyniki:

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

Aby uzyskać dostęp do zasobu przetwarzania obrazów, potrzebujemy zarówno punktu końcowego, jak i klucza. Za pomocą interfejsu wiersza polecenia platformy Azure mamy dostęp do dwóch `az cognitiveservices account` poleceń: `show` i `keys list`, które dają nam to, czego potrzebujemy.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Wdrażanie kodu w aplikacji kontenera

Teraz, gdy mamy już skonfigurowany magazyn, bazę danych i przetwarzanie obrazów zasoby, możemy przystąpić do wdrażania kodu aplikacji. W tym celu użyjemy usługi Azure Container Apps do hostowania konteneryzowanej kompilacji naszej aplikacji Next.js. Element `Dockerfile` jest już tworzony w katalogu głównym repozytorium, więc wszystko, co musimy zrobić, to uruchomienie jednego polecenia w celu wdrożenia kodu. Przed uruchomieniem tego polecenia najpierw należy zainstalować rozszerzenie containerapp dla interfejsu wiersza polecenia platformy Azure.

```bash
az extension add --upgrade -n containerapp
```

To polecenie spowoduje utworzenie zasobu usługi Azure Container Registry w celu hostowania obrazu platformy Docker, zasobu aplikacji kontenera platformy Azure, który uruchamia obraz, oraz zasobu usługi Azure Container App Environment dla naszego obrazu. Podzielmy to, co przekazujemy do polecenia .

- Podstawowe informacje: nazwa zasobu, grupa zasobów i region
- Nazwa zasobu usługi Azure Container App Environment do użycia lub utworzenia
- Ścieżka do kodu źródłowego

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

Możemy sprawdzić, czy polecenie zakończyło się pomyślnie, używając następującego polecenia:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Wyniki:

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

## Tworzenie reguły zapory bazy danych

Domyślnie nasza baza danych jest skonfigurowana tak, aby zezwalała na ruch z listy dozwolonych adresów IP. Musimy dodać adres IP nowo wdrożonej aplikacji kontenera do tej listy dozwolonych. Adres IP można pobrać z `az containerapp show` polecenia .

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Teraz możemy dodać ten adres IP jako regułę zapory za pomocą tego polecenia:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Wyniki:

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

## Tworzenie reguły CORS magazynu

Przeglądarki internetowe implementują ograniczenie zabezpieczeń znane jako zasady pochodzenia tego samego, które uniemożliwia stronie internetowej wywoływanie interfejsów API w innej domenie. Mechanizm CORS zapewnia bezpieczny sposób zezwalania jednej domenie (domenie pochodzenia) na wywoływanie interfejsów API w innej domenie. Musimy dodać regułę CORS na adres URL naszej aplikacji internetowej do konta magazynu. Najpierw pobierzmy adres URL za pomocą podobnego `az containerapp show` polecenia, jak wcześniej.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Następnie możemy dodać regułę CORS za pomocą następującego polecenia. Przeanalizujmy różne części tego polecenia.

- Określamy usługę blob jako typ magazynu, do których ma zostać dodana reguła.
- Zezwalamy na wykonywanie wszystkich operacji.
- Zezwalamy tylko na zapisany adres URL aplikacji kontenera.
- Zezwalamy na wszystkie nagłówki HTTP z tego adresu URL.
- Maksymalny wiek to czas w sekundach, przez który przeglądarka powinna buforować odpowiedź wstępną dla określonego żądania.
- Przekazujemy wcześniej nazwę i klucz konta magazynu.

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

I już! Możesz uzyskać dostęp do nowo wdrożonej aplikacji internetowej w przeglądarce, drukuj CONTAINER_APP_URL zmiennej środowiskowej, która została dodana wcześniej.

```bash
echo $CONTAINER_APP_URL
```

## Następne kroki

- [Dokumentacja usługi Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Dokumentacja usługi Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Dokumentacja usługi Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/)
- [Dokumentacja usługi Azure Computer (AI) Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/)
