---
title: 'Creación de una instancia de Container App aprovechando el almacén de blobs, SQL y Computer Vision'
description: 'En este tutorial se muestra cómo crear una instancia de Container App aprovechando el almacén de blobs, SQL y Computer Vision.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Creación de una instancia de Container App aprovechando el almacén de blobs, SQL y Computer Vision

En esta guía, se le guiará por la implementación de los recursos necesarios para una aplicación web que permite a los usuarios emitir votos con su nombre, correo electrónico e imagen. Los usuarios pueden votar si prefieren a los gatos o a los perro utilizando una imagen de un gato o un perro que analizará nuestra infraestructura. Para que esto funcione, implementaremos recursos en varios servicios de Azure diferentes:

- **Cuenta de Azure Storage** para almacenar las imágenes
- **Azure Database for PostgreSQL** para almacenar usuarios y votos
- **Azure Computer Vision** para analizar las imágenes de gatos o perros
- **Azure Container Apps** para implementar nuestro código

Nota: Si nunca ha creado un recurso de Computer Vision antes, no podrá crear uno mediante la CLI de Azure. Debe crear el primer recurso de Computer Vision desde Azure Portal para revisar y confirmar los términos y condiciones de IA responsable. Puede hacerlo aquí: [Crear un recurso de Computer Vision](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision). Después, puede crear recursos posteriores mediante cualquier herramienta de implementación (SDK, CLI, plantilla de ARM, etc.) en la misma suscripción de Azure.

## Definición de las variables de entorno

El primer paso de este tutorial es definir variables de entorno. **Reemplace los valores de la derecha por sus propios valores únicos.** Estos valores se usarán en el tutorial para crear recursos y configurar la aplicación. Use minúsculas y no use ningún carácter especial para el nombre de la cuenta de almacenamiento.

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

## Clonación del repositorio de ejemplo

En primer lugar, vamos a clonar este repositorio en nuestras máquinas locales. Esto proporcionará el código de inicio necesario para proporcionar la funcionalidad de la aplicación sencilla descrita anteriormente. Podemos clonar con un comando git simple.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Para conservar las variables de entorno guardadas, es importante que esta ventana de terminal permanezca abierta durante la implementación.

## Iniciar sesión en Azure mediante la CLI

Para ejecutar comandos en Azure mediante [la CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), debe iniciar sesión. Esto se hace a través del comando `az login`:

## Crear un grupo de recursos

Un grupo de recursos es un contenedor para los recursos relacionados. Todos los recursos se deben colocar en un grupo de recursos. Vamos a crear uno para este tutorial. El comando siguiente crea un grupo de recursos con los parámetros $MY_RESOURCE_GROUP_NAME y $REGION definidos anteriormente.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:

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

## Creación de la cuenta de almacenamiento

Para crear una cuenta de almacenamiento en este grupo de recursos, es necesario ejecutar un comando sencillo. A este comando se pasa el nombre de la cuenta de almacenamiento, el grupo de recursos en el que se va a implementar, la región física en la que se va a implementar y la SKU de la cuenta de almacenamiento. Todos los valores se configuran mediante variables de entorno.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Resultados:

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

También es necesario almacenar una de las claves de API de la cuenta de almacenamiento en una variable de entorno para su uso posterior (para crear un contenedor y colocarla en un archivo de entorno para el código). Estamos llamando al comando `keys list` en la cuenta de almacenamiento y almacenando el primero en una variable de entorno `STORAGE_ACCOUNT_KEY`.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Creación de un contenedor en la cuenta de almacenamiento

Ejecute el siguiente comando para crear un contenedor `images` en la cuenta de almacenamiento que acabamos de crear. Las imágenes cargadas por los usuarios se almacenarán como blobs en este contenedor.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Resultados:

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Crear una base de datos

Vamos a crear un servidor flexible de Azure Database for PostgreSQL para que la aplicación almacene usuarios y sus votos. Pasamos varios argumentos al comando `create`:

- Conceptos básicos: nombre de base de datos, grupo de recursos y región física en la que se va a implementar.
- El nivel (que determina las funcionalidades del servidor) como `burstable`, que es para las cargas de trabajo que no necesitan una CPU completa continuamente.
- SKU como `Standard_B1ms`.
  - `Standard` para el nivel de rendimiento.
  - `B` para cargas de trabajo ampliables.
  - `1` para un único núcleo virtual.
  - `ms` para optimizada para memoria
- Tamaño de almacenamiento, 32 GiB.
- La versión principal de PostgreSQL, 15.
- Credenciales de la base de datos: nombre de usuario y contraseña.

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

Resultados:

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

También es necesario almacenar la cadena de conexión a la base de datos en una variable de entorno para su uso posterior. Esta dirección URL nos permitirá acceder a la base de datos dentro del recurso que acabamos de crear.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Cree un recurso de Computer Vision

Vamos a crear un recurso de Computer Vision para poder identificar gatos o perros en las imágenes que los usuarios cargan. La creación de un recurso de Computer Vision se puede realizar con un solo comando. Pasamos varios argumentos al comando `create`:

- Conceptos básicos: nombre del recurso, grupo de recursos, la región y para crear un recurso de Computer Vision.
- SKU como `S1`, o el nivel de rendimiento de pago más rentable.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Resultados:

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

Para acceder a nuestro recurso de Computer Vision, necesitamos tanto el punto de conexión como la clave. Con la CLI de Azure, tenemos acceso a dos comandos `az cognitiveservices account`: `show` y `keys list`, que nos proporcionan lo que necesitamos.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Implementación del código en una instancia de Container App

Ahora que tenemos configurados todos los recursos de almacenamiento, base de datos y Computer Vision, estamos listos para implementar el código de la aplicación. Para ello, vamos a usar Azure Container Apps para hospedar una compilación en contenedor de nuestra aplicación Next.js. Ya se ha creado `Dockerfile` en la raíz del repositorio, por lo que todo lo que necesitamos hacer es ejecutar un único comando para implementar el código. Antes de ejecutar este comando, primero es necesario instalar la extensión containerapp para la CLI de Azure.

```bash
az extension add --upgrade -n containerapp
```

Este comando creará un recurso de Azure Container Registry para hospedar nuestra imagen de Docker, un recurso de Azure Container Apps que ejecuta la imagen y un recurso de entorno de Azure Container App para nuestra imagen. Vamos a desglosar lo que estamos pasando al comando.

- Conceptos básicos: nombre de recurso, grupo de recursos y región
- Nombre del recurso de entorno de Azure Container App que se va a usar o crear.
- La ruta de acceso al código fuente.

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

Podemos comprobar que el comando se realizó correctamente mediante:

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Resultados:

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

## Crear una regla de firewall de base de datos

De forma predeterminada, nuestra base de datos está configurada para permitir el tráfico desde una lista de direcciones IP permitidas. Es necesario agregar la dirección IP de la instancia de Container App recién implementada a esta lista de permitidos. Podemos obtener la dirección IP del comando `az containerapp show`.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Ahora podemos agregar esta dirección IP como regla de firewall con este comando:

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Resultados:

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

## Creación de una regla de CORS de almacenamiento

Los exploradores web implementan una restricción de seguridad que se conoce como directiva de mismo origen que impide que una página web realice llamadas API en un dominio diferente. CORS proporciona un modo de seguro para permitir que un dominio (el dominio original) llame a las API de otro dominio. Es necesario agregar una regla de CORS en la dirección URL de la aplicación web a nuestra cuenta de almacenamiento. En primer lugar, vamos a obtener la dirección URL con un comando `az containerapp show` similar al anterior.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

A continuación, estamos listos para agregar una regla de CORS con el siguiente comando. Vamos a desglosar las distintas partes de este comando.

- Especificamos Blob service como el tipo de almacenamiento al que agregar la regla.
- Permitimos que se realicen todas las operaciones.
- Solo permitimos la dirección URL de la aplicación de contenedor que acabamos de guardar.
- Permitimos todos los encabezados HTTP de esta dirección URL.
- La antigüedad máxima es la cantidad de tiempo, en segundos, que un explorador debe almacenar en caché la respuesta de comprobaciones preparatorias de una solicitud específica.
- Pasamos el nombre y la clave de la cuenta de almacenamiento anteriores.

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

Eso es todo. No dude en acceder a la aplicación web recién implementada en el explorador imprimiendo la variable de entorno CONTAINER_APP_URL que hemos agregado anteriormente.

```bash
echo $CONTAINER_APP_URL
```

## Pasos siguientes

- [Documentación de Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Documentación de Azure Database for PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Documentación de Azure Blob Storage](https://learn.microsoft.com/azure/storage/blobs/)
- [Documentación de Azure Computer (AI) Vision](https://learn.microsoft.com/azure/ai-services/computer-vision/)
