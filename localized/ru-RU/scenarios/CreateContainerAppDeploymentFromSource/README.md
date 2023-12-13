---
title: 'Создание приложения-контейнера с использованием хранилища BLOB-объектов, SQL и Компьютерное зрение'
description: 'В этом руководстве показано, как создать приложение контейнера с использованием хранилища BLOB-объектов, SQL и Компьютерное зрение'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Создание приложения-контейнера с использованием хранилища BLOB-объектов, SQL и Компьютерное зрение

В этом руководстве мы рассмотрим развертывание необходимых ресурсов для веб-приложения, которое позволяет пользователям голосовать с помощью имени, электронной почты и изображения. Пользователи могут голосовать за свое предпочтение кота или собаки, используя изображение кошки или собаки, которая будет анализироваться нашей инфраструктурой. Для этого мы будем развертывать ресурсы в нескольких разных службах Azure:

- **служба хранилища Azure учетная запись** для хранения изображений
- **** База данных Azure для PostgreSQL для хранения пользователей и голосов
- **Azure Компьютерное зрение** для анализа изображений для кошек или собак
- **Приложение-контейнер** Azure для развертывания нашего кода

Примечание. Если вы еще не создали ресурс Компьютерное зрение, вы не сможете создать его с помощью Azure CLI. Необходимо создать первый ресурс Компьютерное зрение из портал Azure для проверки и подтверждения условий ответственного ИИ. Это можно сделать здесь: [создание ресурса Компьютерное зрение](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision). После этого можно создать последующие ресурсы с помощью любого средства развертывания (SDK, CLI, шаблон ARM и т. д.) в пределах одной подписки Azure.

## Определение переменных среды

Первым шагом в этом руководстве является определение переменных среды. **Замените значения справа собственными уникальными значениями.** Эти значения будут использоваться во всем руководстве для создания ресурсов и настройки приложения. Используйте строчные буквы и не специальные символы для имени учетной записи хранения.

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

## Клонирование примера репозитория

Сначала мы клонируем этот репозиторий на локальные компьютеры. Это обеспечит начальный код, необходимый для предоставления функциональных возможностей для простого приложения, описанного выше. Клонировать можно с помощью простой команды Git.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Чтобы сохранить сохраненные переменные среды, важно, чтобы это окно терминала оставалось открытым в течение длительности развертывания.

## Вход в Azure с помощью интерфейса командной строки

Чтобы выполнить команды в Azure с помощью [интерфейса командной строки ](https://learn.microsoft.com/cli/azure/install-azure-cli), необходимо войти в систему. Это делается, хотя `az login` команда:

## Создание или изменение группы ресурсов

Группа ресурсов — это контейнер для связанных ресурсов. Все ресурсы должны быть помещены в группу ресурсов. Мы создадим его для этого руководства. Следующая команда создает группу ресурсов с ранее определенными параметрами $MY_RESOURCE_GROUP_NAME и $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Результаты.

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

## Создание учетной записи хранения

Чтобы создать учетную запись хранения в этой группе ресурсов, необходимо выполнить простую команду. Для этой команды мы передаваем имя учетной записи хранения, группу ресурсов для его развертывания, физический регион для его развертывания и номер SKU учетной записи хранения. Все значения настраиваются с помощью переменных среды.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Результаты.

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

Кроме того, необходимо сохранить один из ключей API для учетной записи хранения в переменную среды для последующего использования (чтобы создать контейнер и поместить его в файл среды для кода). Мы вызываем `keys list` команду в учетной записи хранения и сохраняем первую в переменной `STORAGE_ACCOUNT_KEY` среды.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Создание контейнера в учетной записи хранения

Выполните следующую команду, чтобы создать контейнер в созданной учетной `images` записи хранения. Отправленные пользователем образы будут храниться в виде больших двоичных объектов в этом контейнере.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Результаты.

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Создание базы данных

Мы создадим База данных Azure для PostgreSQL гибкий сервер для приложения для хранения пользователей и их голосов. Мы передаваем в команду несколько аргументов `create` :

- Основы: имя базы данных, группа ресурсов и физический регион для развертывания.
- Уровень (который определяет возможности сервера) как `burstable`, который предназначен для рабочих нагрузок, которые не требуют полного ЦП непрерывно.
- Номер SKU как `Standard_B1ms`.
  - `Standard` для уровня производительности.
  - `B` для рабочей нагрузки с возможностью ускорения.
  - `1` для одного виртуального ядра.
  - `ms` для оптимизированной памяти.
- Размер хранилища, 32 ГиБ
- Основная версия PostgreSQL, 15
- Учетные данные базы данных: имя пользователя и пароль

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

Результаты.

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

Кроме того, необходимо сохранить строка подключения в базу данных в переменную среды для последующего использования. Этот URL-адрес позволит нам получить доступ к базе данных в только что созданном ресурсе.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Создание ресурса API компьютерного зрения

Мы создадим Компьютерное зрение ресурс для идентификации кошек или собак в фотографиях, отправленных пользователями. Создание ресурса Компьютерное зрение можно выполнить с помощью одной команды. Мы передаваем в команду несколько аргументов `create` :

- Основы: имя ресурса, группа ресурсов, регион и создание ресурса Компьютерное зрение.
- Номер SKU как `S1`или самый экономичный платный уровень производительности.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Результаты.

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

Чтобы получить доступ к ресурсу компьютерного зрения, нам потребуется как конечная точка, так и ключ. С помощью Azure CLI у нас есть доступ к двум `az cognitiveservices account` командам: `show` и `keys list`которые дают нам необходимые сведения.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Развертывание кода в приложении-контейнере

Теперь, когда у нас есть хранилище, база данных и Компьютерное зрение ресурсы, все настроенные, мы готовы развернуть код приложения. Для этого мы будем использовать приложения контейнеров Azure для размещения контейнерной сборки приложения Next.js. Он `Dockerfile` уже создан в корне репозитория, поэтому все, что нам нужно сделать, — выполнить одну команду для развертывания кода. Перед выполнением этой команды сначала необходимо установить расширение containerapp для Azure CLI.

```bash
az extension add --upgrade -n containerapp
```

Эта команда создаст ресурс Реестр контейнеров Azure для размещения образа Docker, ресурса приложения контейнера Azure, запускающего образ, и ресурса среды приложения контейнеров Azure для нашего образа. Давайте разберем то, что мы передаваем в команду.

- Основы: имя ресурса, группа ресурсов и регион
- Имя ресурса среды приложения контейнера Azure для использования или создания
- Путь к исходному коду

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

Мы можем убедиться, что команда успешно выполнена с помощью:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Результаты.

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

## Создание правила брандмауэра базы данных

По умолчанию наша база данных настроена для разрешения трафика из списка разрешенных IP-адресов. Нам нужно добавить IP-адрес только что развернутого приложения-контейнера в этот список разрешений. Мы можем получить IP-адрес из `az containerapp show` команды.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Теперь этот IP-адрес можно добавить в качестве правила брандмауэра с помощью этой команды:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Результаты.

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

## Создание правила CORS хранилища

В веб-браузерах реализовано ограничение безопасности, известное как политика одного источника. Оно не позволяет веб-странице  вызывать API-интерфейсы в другом домене. CORS позволяет одному домену (домену источника) безопасно вызывать API-интерфейсы в другом домене. Нам нужно добавить правило CORS по URL-адресу веб-приложения в нашу учетную запись хранения. Сначала давайте получим URL-адрес с аналогичной `az containerapp show` командой, как и ранее.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Затем мы готовы добавить правило CORS со следующей командой. Давайте разберем различные части этой команды.

- Мы указываем службу BLOB-объектов в качестве типа хранилища для добавления правила.
- Мы разрешаем выполнять все операции.
- Мы разрешаем только URL-адрес приложения-контейнера, который мы только что сохранили.
- Мы разрешаем все заголовки HTTP из этого URL-адреса.
- Максимальный возраст — это время в секундах, в течение которых браузер должен кэшировать предварительный ответ для конкретного запроса.
- Мы передаваем имя учетной записи хранения и ключ из более ранних версий.

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

Вот и все! Вы можете получить доступ к недавно развернутом веб-приложению в браузере, чтобы распечатать добавленную ранее переменную среды CONTAINER_APP_URL.

```bash
echo $CONTAINER_APP_URL
```

## Next Steps

- [Документация по приложениям контейнеров Azure](https://learn.microsoft.com/azure/container-apps/)
- [Документация по Базе данных Azure для PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Документация по хранилищу BLOB-объектов Azure](https://learn.microsoft.com/azure/storage/blobs/).
- [Документация по визуальному распознаванию компьютеров Azure (ИИ)](https://learn.microsoft.com/azure/ai-services/computer-vision/)
