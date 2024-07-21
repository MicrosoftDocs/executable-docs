---
title: Blob ストア、SQL、Computer Vision を利用してコンテナー アプリを作成する
description: このチュートリアルでは、BLOB ストア、SQL、Computer Vision を利用してコンテナー アプリを作成する方法について説明します
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Blob ストア、SQL、Computer Vision を利用してコンテナー アプリを作成する

このガイドでは、ユーザーが自分の名前、メール アドレス、画像を使用して投票できる Web アプリに必要なリソースのデプロイについて説明します。 ユーザーは、インフラストラクチャによって分析される猫または犬の画像を使用して、猫または犬どちらが好みか投票できます。 これを機能させるには、複数の異なる Azure サービスにリソースをデプロイします。

- 画像を格納するための **Azure Storage アカウント**
- ユーザーと投票を格納するための **Azure Database for PostgreSQL**
- 猫または犬の画像を分析するための **Azure Computer Vision**
- コードをデプロイするための **Azure Container App**

注: これまでに Computer Vision リソースを作成したことがない場合は、Azure CLI を使用して作成することはできません。 責任ある AI のご契約条件を確認して承認するには、最初の Computer Vision リソースを Azure portal から作成する必要があります。 これは、「[Computer Vision リソースを作成する](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision)」から実施できます。 その後、同じ Azure サブスクリプションの下で任意のデプロイ ツール (SDK、CLI、または ARM テンプレートなど) を使用して、後続のリソースを作成できます。

## 環境変数を定義する

このチュートリアルの最初の手順は、環境変数を定義することです。 **右側の値を独自の一意の値に置き換えます。** これらの値はチュートリアル全体を通して、リソースの作成とアプリケーションの構成に使用されます。 ストレージ アカウント名には小文字を使用し、特殊文字は使用しません。

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

## サンプル リポジトリをクローンする

まず、このリポジトリをローカル コンピューターに複製します。 これにより、上記のシンプルなアプリケーションの機能を提供するために必要なスターター コードが提供されます。 リポジトリはシンプルな git コマンドで複製できます。

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

保存した環境変数を保持するには、デプロイしている間、このターミナル ウィンドウを開いたままにすることが重要です。

## CLI を使用して Azure にログインします

[CLI ](https://learn.microsoft.com/cli/azure/install-azure-cli)を使用して Azure に対してコマンドを実行するには、ログインする必要があります。 これは、次の `az login` コマンドによって実行されます。

## リソース グループの作成

リソース グループとは、関連リソース用のコンテナーです。 すべてのリソースをリソース グループに配置する必要があります。 このチュートリアルに必要なものを作成します。 次のコマンドは、事前定義済みの $MY_RESOURCE_GROUP_NAME パラメーターと $REGION パラメーターを使用してリソース グループを作成します。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果:

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

## ストレージ アカウントを作成する

このリソース グループにストレージ アカウントを作成するには、シンプルなコマンドを実行する必要があります。 このコマンドに、ストレージ アカウントの名前、デプロイするリソース グループ、デプロイする物理リージョン、ストレージ アカウントの SKU を渡します。 すべての値は、環境変数を使用して構成されます。

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

結果:

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

また、後で使用するために、ストレージ アカウントの API キーの 1 つを環境変数に格納する必要があります (コンテナーを作成し、コードの環境ファイルに配置するため)。 ストレージ アカウントで `keys list` コマンドを呼び出し、最初のコマンドを `STORAGE_ACCOUNT_KEY` 環境変数に格納しています。

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## ストレージ アカウントにコンテナーを作成する

次のコマンドを実行して、先ほど作成したストレージ アカウントに `images` コンテナーを作成します。 ユーザーがアップロードした画像は、このコンテナーに BLOB として格納されます。

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

結果:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## データベースの作成

アプリケーションがユーザーとその投票を格納するための Azure Database for PostgreSQL フレキシブル サーバーを作成します。 `create` コマンドに複数の引数を渡しています。

- 基本: デプロイするデータベース名、リソース グループ、物理リージョン。
- `burstable` と呼ばれる層 (サーバーの機能を決定する) は、CPU のフル稼働を継続的に必要としないワークロード用です。
- `Standard_B1ms` と呼ばれる SKU。
  - パフォーマンス レベルのための `Standard`。
  - バースト可能なワークロードのための `B`。
  - シングル仮想コアのための `1`。
  - メモリ最適化のための `ms`。
- ストレージ サイズ (32 GiB)
- PostgreSQL のメジャー バージョン (15)
- データベースの資格情報: ユーザー名とパスワード

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

結果:

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

また、後で使用するために、データベースへの接続文字列を環境変数に格納する必要があります。 この URL を使用すると、先ほど作成したリソース内のデータベースにアクセスできるようになります。

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Computer Vision リソースを作成

ユーザーがアップロードした画像に写っている猫や犬を識別できるように Computer Vision リソースを作成します。 Computer Vision リソースの作成は、1 つのコマンドで行うことができます。 `create` コマンドに複数の引数を渡しています。

- 基本: リソース名、リソース グループ、リージョン、Computer Vision リソースの作成。
- `S1` と呼ばれる SKU、または最も費用対効果の高い有料パフォーマンス レベル。

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

結果:

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

Computer Vision リソースにアクセスするには、エンドポイントとキーの両方が必要です。 Azure CLI を使用すると、必要なものを提供する次の `show` コマンドと `keys list` コマンドという 2 つの `az cognitiveservices account` コマンドにアクセスできます。

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## コードをコンテナー アプリにデプロイする

これでストレージ、データベース、Computer Vision リソースをすべて設定完了したので、アプリケーション コードをデプロイする準備ができました。 これを行うには、Azure Container Apps を使用して、Next.js アプリのコンテナー化されたビルドをホストします。 `Dockerfile` はリポジトリのルートに既に作成されているため、残りの必要な作業としてはコードをデプロイするための 1 つのコマンドを実行するのみとなります。 このコマンドを実行する前に、まず Azure CLI の containerapp 拡張機能をインストールする必要があります。

```bash
az extension add --upgrade -n containerapp
```

このコマンドを実行すると、Docker イメージをホストする Azure Container Registry リソース、イメージを実行する Azure Container App リソース、およびイメージ用の Azure Container App Environment リソースが作成されます。 コマンドに渡しているものを分解してみましょう。

- 基本: リソース名、リソース グループ、リージョン
- 使用または作成する Azure Container App 環境リソースの名前
- ソース コードへのパス

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

コマンドが成功したことを確認するには、次のコマンドを使用します。

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

結果:

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

## データベースのファイアウォール規則を作成する

既定では、データベースは IP アドレスの許可リストからのトラフィックを許可するように構成されています。 この許可リストに新しくデプロイされたコンテナー アプリの IP を追加する必要があります。 `az containerapp show` コマンドから IP を取得できます。

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

この IP をファイアウォール規則として追加するには、次のコマンドを使用します。

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

結果:

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

## ストレージ CORS ルールを作成する

Web ブラウザーでは、Web ページから別のドメインの API を呼び出すことを防ぐために、同一オリジン ポリシーと呼ばれるセキュリティ制限が実装されています。 CORS により、あるドメイン (元のドメイン) で別のドメイン内にある API を呼び出せるようにする安全な方法が提供されます。 Web アプリの URL に対する CORS ルールをストレージ アカウントに追加する必要があります。 まず、前と同様の `az containerapp show` コマンドを使用して URL を取得します。

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

次に、以下のコマンドを使用して CORS ルールを追加する準備ができました。 このコマンドのさまざまな部分を分解してみましょう。

- ルールを追加するストレージの種類として BLOB サービスを指定しています。
- すべての操作の実行を許可しています。
- 先ほど保存したコンテナー アプリの URL のみを許可しています。
- この URL からすべての HTTP ヘッダーを許可しています。
- 最長有効期間は、ブラウザーが特定の要求のプリフライト応答をキャッシュする時間を秒単位で表したものです。
- 先ほどのストレージ アカウント名とキーを渡しています。

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

これで完了です。 先ほど追加した CONTAINER_APP_URL 環境変数を使用して、ブラウザーで新しくデプロイされた Web アプリにアクセスしてください。

```bash
echo $CONTAINER_APP_URL
```

## 次のステップ

- [Azure Container Apps のドキュメント](https://learn.microsoft.com/azure/container-apps/)
- [Azure Database for PostgreSQL のドキュメント](https://learn.microsoft.com/azure/postgresql/)
- [Azure Blob Storage のドキュメント](https://learn.microsoft.com/azure/storage/blobs/)
- [Azure Computer (AI) Vision のドキュメント](https://learn.microsoft.com/azure/ai-services/computer-vision/)
