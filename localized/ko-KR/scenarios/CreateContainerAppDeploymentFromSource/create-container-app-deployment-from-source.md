---
title: 'Blob Store, SQL 및 Computer Vision을 활용하는 컨테이너 앱 만들기'
description: '이 자습서에서는 Blob Store, SQL 및 Computer Vision을 활용하는 컨테이너 앱을 만드는 방법을 보여 줍니다.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Blob Store, SQL 및 Computer Vision을 활용하는 컨테이너 앱 만들기

이 가이드에서는 사용자가 이름, 전자 메일 및 이미지를 사용하여 투표를 할 수 있도록 하는 웹앱에 필요한 리소스를 배포하는 방법을 안내합니다. 사용자는 인프라에서 분석할 고양이 또는 강아지의 이미지를 사용하여 고양이 또는 개에 대한 선호도에 투표할 수 있습니다. 이 작업이 작동하려면 여러 다른 Azure 서비스에 리소스를 배포합니다.

- **이미지를 저장할 Azure Storage 계정**
- **Azure Database for PostgreSQL** 을 사용하여 사용자 및 투표 저장
- **고양이 또는 개에 대한 이미지를 분석하는 Azure Computer Vision**
- **코드를 배포하는 Azure Container App**

참고: 이전에 Computer Vision 리소스를 만든 적이 없는 경우 Azure CLI를 사용하여 리소스를 만들 수 없습니다. 책임 있는 AI 사용 약관을 검토하고 승인하려면 Azure Portal에서 첫 번째 Computer Vision 리소스를 만들어야 합니다. 여기서는 [Computer Vision 리소스](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision)를 만들 수 있습니다. 그런 다음, 동일한 Azure 구독에서 모든 배포 도구(SDK, CLI 또는 ARM 템플릿 등)를 사용하여 후속 리소스를 만들 수 있습니다.

## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다. **오른쪽의 값을 고유한 값으로 바꿉 있습니다.** 이러한 값은 자습서 전체에서 리소스를 만들고 애플리케이션을 구성하는 데 사용됩니다. 스토리지 계정 이름에는 소문자와 특수 문자를 사용하지 않습니다.

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

## 샘플 리포지토리 복제

먼저 이 리포지토리를 로컬 머신에 복제합니다. 이렇게 하면 위에서 설명한 간단한 애플리케이션에 대한 기능을 제공하는 데 필요한 시작 코드가 제공됩니다. 간단한 git 명령을 사용하여 복제할 수 있습니다.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

저장된 환경 변수를 유지하려면 배포 기간 동안 이 터미널 창을 열어 두는 것이 중요합니다.

## CLI를 사용하여 Azure에 로그인

CLI[를 사용하여 ](https://learn.microsoft.com/cli/azure/install-azure-cli)Azure에 대해 명령을 실행하려면 로그인해야 합니다. 이 작업은 다음 명령을 통해 수행됩니다.`az login`

## 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치되어야 합니다. 이 자습서에 대해 만들겠습니다. 다음 명령은 이전에 정의된 $MY_RESOURCE_GROUP_NAME 및 $REGION 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

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

## 스토리지 계정 만들기

이 리소스 그룹에서 스토리지 계정을 만들려면 간단한 명령을 실행해야 합니다. 이 명령에는 스토리지 계정의 이름, 이를 배포할 리소스 그룹, 배포할 물리적 지역 및 스토리지 계정의 SKU를 전달합니다. 모든 값은 환경 변수를 사용하여 구성됩니다.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Results:

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

또한 나중에 사용할 수 있도록 스토리지 계정에 대한 API 키 중 하나를 환경 변수에 저장해야 합니다(컨테이너를 만들고 코드에 대한 환경 파일에 배치하려면). 스토리지 계정에서 `keys list` 명령을 호출하고 첫 번째 명령을 환경 변수에 `STORAGE_ACCOUNT_KEY` 저장합니다.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## 스토리지 계정에 컨테이너 만들기

다음 명령을 실행하여 방금 만든 스토리지 계정에 컨테이너를 만듭니 `images` 다. 사용자가 업로드한 이미지는 이 컨테이너에 Blob으로 저장됩니다.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Results:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## 데이터베이스 만들기

애플리케이션에서 사용자와 해당 투표를 저장할 수 있도록 Azure Database for PostgreSQL 유연한 서버를 만듭니다. 명령에 몇 가지 인수를 전달합니다.`create`

- 기본 사항: 배포할 데이터베이스 이름, 리소스 그룹 및 물리적 지역입니다.
- 전체 CPU가 지속적으로 필요하지 않은 워크로드에 대한 계층(서버의 기능을 결정) `burstable`입니다.
- SKU를 .로 지정 `Standard_B1ms`합니다.
  - `Standard` 성능 계층의 경우
  - `B` 버스트 가능한 워크로드의 경우
  - `1` 단일 vCore의 경우
  - `ms` 메모리 최적화를 위한 것입니다.
- 스토리지 크기, 32GiB
- PostgreSQL 주 버전, 15
- datatabase 자격 증명: 사용자 이름 및 암호

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

Results:

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

또한 나중에 사용하기 위해 데이터베이스에 대한 연결 문자열 환경 변수에 저장해야 합니다. 이 URL을 사용하면 방금 만든 리소스 내의 데이터베이스에 액세스할 수 있습니다.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Computer Vision 리소스 만들기

사용자가 업로드하는 사진에서 고양이 또는 개를 식별할 수 있는 Computer Vision 리소스를 만들 것입니다. Computer Vision 리소스 만들기는 단일 명령으로 수행할 수 있습니다. 명령에 몇 가지 인수를 전달합니다.`create`

- 기본 사항: 리소스 이름, 리소스 그룹, 지역 및 Computer Vision 리소스를 만듭니다.
- SKU as `S1`또는 가장 비용 효율적인 유료 성능 계층입니다.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Results:

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

Computer Vision 리소스에 액세스하려면 엔드포인트와 키가 모두 필요합니다. Azure CLI를 사용하면 두 `az cognitiveservices account` 가지 명령에 액세스할 수 있습니다. `show` 이 `keys list`명령은 필요한 것을 제공합니다.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## 컨테이너 앱에 코드 배포

이제 스토리지, 데이터베이스 및 Computer Vision 리소스가 모두 설정되었으므로 애플리케이션 코드를 배포할 준비가 되었습니다. 이를 위해 Azure Container Apps를 사용하여 Next.js 앱의 컨테이너화된 빌드를 호스트합니다. `Dockerfile` 리포지토리의 루트에서 이미 만들어지므로 코드를 배포하기 위해 단일 명령을 실행하기만 하면됩니다. 이 명령을 실행하기 전에 먼저 Azure CLI용 containerapp 확장을 설치해야 합니다.

```bash
az extension add --upgrade -n containerapp
```

이 명령은 Docker 이미지를 호스트하는 Azure Container Registry 리소스, 이미지를 실행하는 Azure Container App 리소스 및 이미지에 대한 Azure Container App Environment 리소스를 만듭니다. 명령으로 전달되는 내용을 세어 보겠습니다.

- 기본 사항: 리소스 이름, 리소스 그룹 및 지역
- 사용하거나 만들 Azure Container App Environment 리소스의 이름
- 소스 코드의 경로

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

다음을 사용하여 명령이 성공했는지 확인할 수 있습니다.

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Results:

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

## 데이터베이스 방화벽 규칙 만들기

기본적으로 데이터베이스는 IP 주소 허용 목록의 트래픽을 허용하도록 구성됩니다. 이 허용 목록에 새로 배포된 컨테이너 앱의 IP를 추가해야 합니다. 명령에서 IP를 `az containerapp show` 가져올 수 있습니다.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

이제 다음 명령을 사용하여 이 IP를 방화벽 규칙으로 추가할 수 있습니다.

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Results:

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

## 스토리지 CORS 규칙 만들기

웹 브라우저는 웹 페이지가 다른 도메인의 API를 호출하지 못하게 하는 동일 원본 정책이라고 하는 보안 제한을 구현합니다. CORS는 한 도메인(원본 도메인)이 다른 도메인의 API를 호출할 수 있게 해주는 안전한 방법을 제공합니다. 웹앱의 URL에 CORS 규칙을 스토리지 계정에 추가해야 합니다. 먼저 이전과 비슷한 `az containerapp show` 명령으로 URL을 가져옵니다.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

다음으로, 다음 명령을 사용하여 CORS 규칙을 추가할 준비가 된 것입니다. 이 명령의 다른 부분을 분해해 보겠습니다.

- Blob 서비스를 스토리지 유형으로 지정하여 규칙을 추가합니다.
- 모든 작업을 수행할 수 있습니다.
- 방금 저장한 컨테이너 앱 URL만 허용합니다.
- 이 URL의 모든 HTTP 헤더를 허용합니다.
- 최대 기간은 브라우저가 특정 요청에 대한 실행 전 응답을 캐시해야 하는 시간(초)입니다.
- 이전의 스토리지 계정 이름 및 키를 전달합니다.

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

정말 간단하죠. 이전에 추가한 CONTAINER_APP_URL 환경 변수를 인쇄하는 브라우저에서 새로 배포된 웹앱에 자유롭게 액세스할 수 있습니다.

```bash
echo $CONTAINER_APP_URL
```

## 다음 단계

- [Azure Container Apps 설명서](https://learn.microsoft.com/azure/container-apps/)
- [Azure Database for PostgreSQL 설명서](https://learn.microsoft.com/azure/postgresql/)
- [Azure Blob Storage 설명서](https://learn.microsoft.com/azure/storage/blobs/)
- [Azure Computer(AI) Vision 설명서](https://learn.microsoft.com/azure/ai-services/computer-vision/)
