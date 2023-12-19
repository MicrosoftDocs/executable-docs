---
title: 'Blob Mağazası, SQL ve Görüntü İşleme yararlanan bir Kapsayıcı Uygulaması oluşturma'
description: 'Bu öğreticide Blob Mağazası, SQL ve Görüntü İşleme''dan yararlanan bir Kapsayıcı Uygulamasının nasıl oluşturulacağı gösterilmektedir'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Blob Mağazası, SQL ve Görüntü İşleme yararlanan bir Kapsayıcı Uygulaması oluşturma

Bu kılavuzda, kullanıcıların adlarını, e-postalarını ve görüntülerini kullanarak oy kullanmalarına olanak tanıyan bir web uygulaması için gerekli kaynakları dağıtma adımlarını inceleyeceğiz. Kullanıcılar, altyapımız tarafından analiz edilecek bir kedinin veya köpeğin görüntüsünü kullanarak kedi veya köpek tercihlerine oy verebilir. Bunun işe yarayacağı için kaynakları birkaç farklı Azure hizmeti arasında dağıtacağız:

- **Görüntüleri depolamak için Azure Depolama Hesabı**
- **** Kullanıcıları ve oyları depolamak için PostgreSQL için Azure Veritabanı
- **Kediler veya köpekler için görüntüleri analiz etmek için Azure Görüntü İşleme**
- **Kodumuzu dağıtmak için Azure Container App**

Not: Daha önce hiç Görüntü İşleme kaynağı oluşturmadıysanız Azure CLI kullanarak kaynak oluşturamazsınız. Sorumlu yapay zeka hüküm ve koşullarını gözden geçirmek ve onaylamak için Azure portalından ilk Görüntü İşleme kaynağınızı oluşturmanız gerekir. Bunu burada yapabilirsiniz: [Görüntü İşleme Kaynağı](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision) oluşturun. Bundan sonra, aynı Azure aboneliği altındaki herhangi bir dağıtım aracını (SDK, CLI veya ARM şablonu vb.) kullanarak sonraki kaynakları oluşturabilirsiniz.

## Ortam Değişkenlerini Tanımlama

Bu öğreticinin ilk adımı ortam değişkenlerini tanımlamaktır. **Sağdaki değerleri kendi benzersiz değerlerinizle değiştirin.** Bu değerler, öğretici boyunca kaynak oluşturmak ve uygulamayı yapılandırmak için kullanılır. Depolama hesabı adı için küçük harf kullanın ve özel karakter kullanmayın.

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

## Örnek depoyu kopyalama

İlk olarak bu depoyu yerel makinelerimize kopyalayacağız. Bu, yukarıda özetlenen basit uygulamanın işlevselliğini sağlamak için gereken başlangıç kodunu sağlar. Basit bir git komutuyla klonlayabiliriz.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Kaydedilen ortam değişkenlerini korumak için bu terminal penceresinin dağıtım süresi boyunca açık kalması önemlidir.

## CLI kullanarak Azure'da oturum açma

CLI [kullanarak ](https://learn.microsoft.com/cli/azure/install-azure-cli)Azure'da komut çalıştırmak için oturum açmanız gerekir. Bu işlem şu komutla `az login` yapılır:

## Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Bu öğretici için bir tane oluşturacağız. Aşağıdaki komut, önceden tanımlanmış $MY_RESOURCE_GROUP_NAME ve $REGION parametreleriyle bir kaynak grubu oluşturur.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Sonuçlar:

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

## Depolama hesabını oluşturma

Bu kaynak grubunda depolama hesabı oluşturmak için basit bir komut çalıştırmamız gerekir. Bu komut için depolama hesabının adını, dağıtılacak kaynak grubunu, dağıtılacak fiziksel bölgeyi ve depolama hesabının SKU'sunu geçiriyoruz. Tüm değerler ortam değişkenleri kullanılarak yapılandırılır.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Sonuçlar:

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

Ayrıca depolama hesabının API anahtarlarından birini daha sonra kullanmak üzere bir ortam değişkeninde depolamamız gerekir (kapsayıcı oluşturmak ve kodun ortam dosyasına koymak için). Depolama hesabında komutunu çağırıyoruz `keys list` ve ilkini bir `STORAGE_ACCOUNT_KEY` ortam değişkeninde depoluyoruz.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Depolama hesabında kapsayıcı oluşturma

Yeni oluşturduğumuz depolama hesabında bir `images` kapsayıcı oluşturmak için aşağıdaki komutu çalıştırın. Kullanıcı tarafından karşıya yüklenen görüntüler bu kapsayıcıda blob olarak depolanır.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Sonuçlar:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

##  veritabanı oluşturun

Kullanıcıların ve oylarının depolanması için uygulama için PostgreSQL için Azure Veritabanı esnek bir sunucu oluşturacağız. Komuta birkaç bağımsız değişken `create` geçiriyoruz:

- Temel bilgiler: veritabanı adı, kaynak grubu ve dağıtılacak fiziksel bölge.
- Katman (sunucunun özelliklerini belirler) olarak `burstable`belirlenir ve sürekli olarak tam CPU'ya ihtiyaç duymayan iş yükleri için kullanılır.
- SKU olarak `Standard_B1ms`.
  - `Standard` performans katmanı için.
  - `B` iş yükü için.
  - `1` tek bir sanal çekirdek için.
  - `ms` bellek için iyileştirilmiş.
- Depolama boyutu, 32 GiB
- PostgreSQL ana sürümü, 15
- Veri tabanı kimlik bilgileri: kullanıcı adı ve parola

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

Sonuçlar:

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

Ayrıca daha sonra kullanmak üzere veritabanına bağlantı dizesi bir ortam değişkeninde depolamamız gerekir. Bu URL, yeni oluşturduğumuz kaynaktaki veritabanına erişmemize olanak sağlar.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Görüntü İşleme kaynağı oluşturma

Kullanıcıların karşıya yüklediği resimlerdeki kedileri veya köpekleri tanımlayabilmek için bir Görüntü İşleme kaynağı oluşturacağız. Görüntü İşleme kaynağı oluşturma işlemi tek bir komutla gerçekleştirilebilir. Komuta birkaç bağımsız değişken `create` geçiriyoruz:

- Temel bilgiler: kaynak adı, kaynak grubu, bölge ve Görüntü İşleme kaynağı oluşturmak.
- SKU olarak `S1`veya en uygun maliyetli ücretli performans katmanı.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Sonuçlar:

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

Görüntü işleme kaynağımıza erişmek için hem uç noktaya hem de anahtara ihtiyacımız vardır. Azure CLI ile bize gerekenleri sağlayan ve `keys list`olmak üzere iki `az cognitiveservices account` komutuna `show` erişebiliriz.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Kodu kapsayıcı uygulamasına dağıtma

Artık depolama, veritabanı ve Görüntü İşleme kaynaklarımızı ayarladığımıza göre, uygulama kodunu dağıtmaya hazırız. Bunu yapmak için Azure Container Apps'i kullanarak Next.js uygulamamızın kapsayıcılı derlemesini barındıracağız. `Dockerfile` zaten deponun kökünde oluşturulmuştur, bu nedenle tek yapmamız gereken kodu dağıtmak için tek bir komut çalıştırmaktır. Bu komutu çalıştırmadan önce Azure CLI için containerapp uzantısını yüklememiz gerekir.

```bash
az extension add --upgrade -n containerapp
```

Bu komut Docker görüntümüzü barındırmak için bir Azure Container Registry kaynağı, görüntüyü çalıştıran bir Azure Container App kaynağı ve görüntümüz için bir Azure Container App Ortamı kaynağı oluşturur. Şimdi komuta aktardığımız şeyi ayıralım.

- Temel bilgiler: kaynak adı, kaynak grubu ve bölge
- Kullanılacak veya oluşturulacak Azure Container App Ortamı kaynağının adı
- Kaynak kodun yolu

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

Komutun başarılı olduğunu şu komutu kullanarak doğrulayabiliriz:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Sonuçlar:

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

## Veritabanı güvenlik duvarı kuralı oluşturma

Varsayılan olarak, veritabanımız ip adresleri izin verilenler listesinden gelen trafiğe izin verecek şekilde yapılandırılmıştır. Yeni dağıtılan Kapsayıcı Uygulamamızın IP'sini bu izin verilenler listesine eklemeliyiz. KOMUTUndan IP'yi `az containerapp show` alacağız.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Şimdi bu IP'yi şu komutla güvenlik duvarı kuralı olarak ekleyebiliriz:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Sonuçlar:

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

## Depolama CORS kuralı oluşturma

Web tarayıcıları, web sayfasının farklı bir etki alanındaki API'leri çağırmasını engelleyen, aynı kaynak ilkesi olarak bilinen bir güvenlik kısıtlaması uygular. CORS, bir etki alanının (kaynak etki alanı) başka bir etki alanındaki API'leri çağırmasına izin vermek için güvenli bir yol sağlar. Depolama hesabımıza web uygulamamızın URL'sinde bir CORS kuralı eklemeliyiz. İlk olarak, url'yi daha önce olduğu gibi benzer `az containerapp show` bir komutla alalım.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Ardından, aşağıdaki komutla bir CORS kuralı eklemeye hazırız. Şimdi bu komutun farklı bölümlerini ayıralım.

- Kuralın ekleneceği depolama türü olarak blob hizmetini belirtiyoruz.
- Tüm işlemlerin gerçekleştirilmesine izin vermekteyiz.
- Yalnızca az önce kaydettiğimiz kapsayıcı uygulaması URL'sine izin verdik.
- Bu URL'den tüm HTTP üst bilgilerine izin verdik.
- Yaş üst sınırı, tarayıcının belirli bir istek için denetim öncesi yanıtını önbelleğe alması gereken saniye sayısıdır.
- Depolama hesabı adını ve anahtarını önceki sürümlerden geçiriyoruz.

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

İşte hepsi bu! Daha önce eklediğimiz CONTAINER_APP_URL ortam değişkenini yazdırarak tarayıcınızda yeni dağıtılan web uygulamasına erişebilirsiniz.

```bash
echo $CONTAINER_APP_URL
```

## Sonraki Adımlar

- [Azure Container Apps belgeleri](https://learn.microsoft.com/azure/container-apps/)
- [PostgreSQL için Azure Veritabanı belgeleri](https://learn.microsoft.com/azure/postgresql/)
- [Azure Blob Depolama belgeleri](https://learn.microsoft.com/azure/storage/blobs/)
- [Azure Bilgisayar (AI) Görüntü İşleme Belgeleri](https://learn.microsoft.com/azure/ai-services/computer-vision/)
