---
title: 'Membuat Aplikasi Kontainer yang memanfaatkan Blob Store, SQL, dan Computer Vision'
description: 'Tutorial ini menunjukkan cara membuat Aplikasi Kontainer yang memanfaatkan Blob Store, SQL, dan Computer Vision'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Membuat Aplikasi Kontainer yang memanfaatkan Blob Store, SQL, dan Computer Vision

Dalam panduan ini, kita akan menelusuri penyebaran sumber daya yang diperlukan untuk aplikasi web yang memungkinkan pengguna untuk memberikan suara menggunakan nama, email, dan gambar mereka. Pengguna dapat memilih preferensi kucing atau anjing mereka, menggunakan gambar kucing atau anjing yang akan dianalisis oleh infrastruktur kami. Agar ini berfungsi, kami akan menyebarkan sumber daya di beberapa layanan Azure yang berbeda:

- **Akun** Azure Storage untuk menyimpan gambar
- **Azure Database for PostgreSQL** untuk menyimpan pengguna dan suara
- **Azure Computer Vision** untuk menganalisis gambar untuk kucing atau anjing
- **Aplikasi** Kontainer Azure untuk menyebarkan kode kami

Catatan: Jika Anda belum pernah membuat sumber daya Computer Vision sebelumnya, Anda tidak akan dapat membuatnya menggunakan Azure CLI. Anda harus membuat sumber daya Computer Vision pertama Anda dari portal Azure untuk meninjau dan mengakui syarat dan ketentuan AI yang Bertanggung Jawab. Anda dapat melakukannya di sini: [Membuat Sumber Daya](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision) Computer Vision. Setelah itu, Anda dapat membuat sumber daya berikutnya menggunakan alat penyebaran apa pun (templat SDK, CLI, atau ARM, dll) di bawah langganan Azure yang sama.

## Tentukan Variabel Lingkungan

Langkah pertama dalam tutorial ini adalah menentukan variabel lingkungan. **Ganti nilai di sebelah kanan dengan nilai unik Anda sendiri.** Nilai-nilai ini akan digunakan di seluruh tutorial untuk membuat sumber daya dan mengonfigurasi aplikasi. Gunakan huruf kecil dan tidak ada karakter khusus untuk nama akun penyimpanan.

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

## Mengkloning repositori sampel

Pertama, kita akan mengkloning repositori ini ke mesin lokal kita. Ini akan menyediakan kode pemula yang diperlukan untuk menyediakan fungsionalitas untuk aplikasi sederhana yang diuraikan di atas. Kita bisa mengkloning dengan perintah git sederhana.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Untuk mempertahankan variabel lingkungan yang disimpan, penting bahwa jendela terminal ini tetap terbuka selama durasi penyebaran.

## Masuk ke Azure menggunakan CLI

Untuk menjalankan perintah terhadap Azure menggunakan [CLI ](https://learn.microsoft.com/cli/azure/install-azure-cli), Anda perlu masuk. Ini dilakukan melalui `az login` perintah:

## Buat grup sumber daya

Grup sumber daya adalah kontainer untuk sumber daya terkait. Semua sumber daya harus ditempatkan dalam grup sumber daya. Kami akan membuatnya untuk tutorial ini. Perintah berikut membuat grup sumber daya dengan parameter $MY_RESOURCE_GROUP_NAME dan $REGION yang ditentukan sebelumnya.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Hasil:

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

## Buat akun penyimpanan

Untuk membuat akun penyimpanan di grup sumber daya ini, kita perlu menjalankan perintah sederhana. Untuk perintah ini, kita meneruskan nama akun penyimpanan, grup sumber daya untuk menyebarkannya, wilayah fisik untuk menyebarkannya, dan SKU akun penyimpanan. Semua nilai dikonfigurasi menggunakan variabel lingkungan.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Hasil:

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

Kita juga perlu menyimpan salah satu kunci API untuk akun penyimpanan ke dalam variabel lingkungan untuk digunakan nanti (untuk membuat kontainer, dan memasukkannya ke dalam file lingkungan untuk kode). Kami memanggil `keys list` perintah pada akun penyimpanan dan menyimpan yang pertama dalam `STORAGE_ACCOUNT_KEY` variabel lingkungan.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Membuat kontainer di akun penyimpanan

Jalankan perintah berikut untuk membuat kontainer di akun penyimpanan yang `images` baru saja kita buat. Gambar yang diunggah pengguna akan disimpan sebagai blob dalam kontainer ini.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Hasil:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Membuat database

Kami akan membuat server fleksibel Azure Database for PostgreSQL agar aplikasi menyimpan pengguna dan suara mereka. Kami meneruskan beberapa argumen ke `create` perintah:

- Dasar-dasarnya: nama database, grup sumber daya, dan wilayah fisik untuk disebarkan.
- Tingkat (yang menentukan kemampuan server) sebagai `burstable`, yaitu untuk beban kerja yang tidak memerlukan CPU penuh terus menerus.
- SKU sebagai `Standard_B1ms`.
  - `Standard` untuk tingkat performa.
  - `B` untuk beban kerja yang dapat meledak.
  - `1` untuk satu vCore.
  - `ms` untuk memori yang dioptimalkan.
- Ukuran penyimpanan, 32 GiB
- Versi utama PostgreSQL, 15
- Kredensial datatabase: nama pengguna dan kata sandi

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

Hasil:

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

Kita juga perlu menyimpan string koneksi ke database ke dalam variabel lingkungan untuk digunakan nanti. URL ini akan memungkinkan kami mengakses database dalam sumber daya yang baru saja kami buat.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Membuat sumber daya Computer Vision

Kami akan membuat sumber daya Computer Vision untuk dapat mengidentifikasi kucing atau anjing di unggahan pengguna gambar. Membuat sumber daya Computer Vision dapat dilakukan dengan satu perintah. Kami meneruskan beberapa argumen ke `create` perintah:

- Dasar-dasarnya: nama sumber daya, grup sumber daya, wilayah, dan untuk membuat sumber daya Computer Vision.
- SKU sebagai `S1`, atau tingkat performa berbayar yang paling hemat biaya.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Hasil:

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

Untuk mengakses sumber daya visi komputer, kita memerlukan titik akhir dan kuncinya. Dengan Azure CLI, kita memiliki akses ke dua `az cognitiveservices account` perintah: `show` dan `keys list`, yang memberi kita apa yang kita butuhkan.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Menyebarkan kode ke dalam Aplikasi Kontainer

Sekarang setelah semua sumber daya penyimpanan, database, dan Computer Vision disiapkan, kami siap untuk menyebarkan kode aplikasi. Untuk melakukan ini, kita akan menggunakan Azure Container Apps untuk menghosting build kontainer aplikasi Next.js kita. `Dockerfile` sudah dibuat di akar repositori, jadi yang perlu kita lakukan adalah menjalankan satu perintah untuk menyebarkan kode. Sebelum menjalankan perintah ini, pertama-tama kita perlu menginstal ekstensi containerapp untuk Azure CLI.

```bash
az extension add --upgrade -n containerapp
```

Perintah ini akan membuat sumber daya Azure Container Registry untuk menghosting gambar Docker kami, sumber daya Aplikasi Kontainer Azure yang menjalankan gambar, dan sumber daya Azure Container App Environment untuk gambar kami. Mari kita uraikan apa yang kita lewati ke dalam perintah.

- Dasar-dasarnya: nama sumber daya, grup sumber daya, dan wilayah
- Nama sumber daya Azure Container App Environment yang akan digunakan atau dibuat
- Jalur ke kode sumber

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

Kita dapat memverifikasi bahwa perintah berhasil dengan menggunakan:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Hasil:

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

## Buat aturan firewall database

Secara default, database kami dikonfigurasi untuk memungkinkan lalu lintas dari daftar izin alamat IP. Kita perlu menambahkan IP Aplikasi Kontainer yang baru disebarkan ke daftar izin ini. Kita bisa mendapatkan IP dari `az containerapp show` perintah.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Kita sekarang dapat menambahkan IP ini sebagai aturan firewall dengan perintah ini:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Hasil:

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

## Membuat aturan CORS penyimpanan

Browser web menerapkan pembatasan keamanan yang dikenal sebagai kebijakan asal yang sama, yang mencegah halaman web memanggil API di domain yang berbeda. CORS menyediakan cara aman untuk mengizinkan satu domain (domain asal) untuk memanggil API di domain lain. Kita perlu menambahkan aturan CORS pada URL aplikasi web kita ke akun penyimpanan kita. Pertama, mari kita dapatkan URL dengan perintah serupa seperti `az containerapp show` sebelumnya.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Selanjutnya, kami siap untuk menambahkan aturan CORS dengan perintah berikut. Mari kita uraikan berbagai bagian dari perintah ini.

- Kami menentukan layanan blob sebagai jenis penyimpanan untuk menambahkan aturan.
- Kami mengizinkan semua operasi dilakukan.
- Kami hanya mengizinkan URL aplikasi kontainer yang baru saja kami simpan.
- Kami mengizinkan semua header HTTP dari URL ini.
- Usia maksimum adalah jumlah waktu, dalam detik, bahwa browser harus menyimpan respons preflight untuk permintaan tertentu.
- Kami meneruskan nama dan kunci akun penyimpanan dari sebelumnya.

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

Itu saja! Jangan ragu untuk mengakses aplikasi web yang baru disebarkan di browser Anda mencetak variabel lingkungan CONTAINER_APP_URL yang kami tambahkan sebelumnya.

```bash
echo $CONTAINER_APP_URL
```

## Langkah berikutnya

- [Dokumentasi Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Dokumentasi Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Dokumentasi Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/)
- [Dokumentasi Visi Komputer Azure (AI)](https://learn.microsoft.com/azure/ai-services/computer-vision/)
