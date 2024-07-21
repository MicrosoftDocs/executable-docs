---
title: 'Créer une application de conteneur en tirant parti du Blob Store, de SQL et de la Vision par ordinateur'
description: 'Ce tutoriel montre comment créer une application de conteneur en tirant parti du Blob Store, de SQL et de la Vision par ordinateur'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Créer une application de conteneur en tirant parti du Blob Store, de SQL et de la Vision par ordinateur

Dans ce repère, nous allons déployer les ressources nécessaires pour une application web qui permet aux utilisateurs de voter en utilisant leur nom, leur adresse e-mail et une image. Les utilisateurs peuvent voter pour leur préférence entre un chat ou un chien, en utilisant l'image d'un chat ou d'un chien qui sera analysée par notre infrastructure. Pour que cela fonctionne, nous allons déployer des ressources sur plusieurs services Azure différents :

- **Compte de stockage Azure** pour stocker les images
- **Azure Database pour PostgreSQL** pour stocker les utilisateurs et les votes
- **Vision par ordinateur Azure** pour analyser les images afin de déterminer s’il s’agit de chats ou de chiens
- **Azure Container App** pour déployer notre code

Remarque : si vous n'avez jamais créé de ressource Vision par ordinateur auparavant, vous ne pourrez pas en créer une à l'aide de l'interface de ligne de commande Azure. Vous devez créer votre première ressource Vision par ordinateur à partir du Portail Microsoft Azure pour consulter et accepter les conditions générales de l’IA responsable. Vous pouvez le faire ici : [Créer une ressource Vision par ordinateur](https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision). Après cela, vous pouvez créer d’autres ressources à l’aide de n’importe quel outil de déploiement (SDK, CLI ou modèle ARM, etc.) dans le même abonnement Azure.

## Définissez des variables d’environnement

La première étape de ce tutoriel définit des variables d’environnement. **Remplacez les valeurs de droite par vos propres valeurs uniques.** Ces valeurs seront utilisées tout au long du tutoriel pour créer des ressources et configurer l'application. Utilisez des minuscules et aucun caractère spécial pour le nom du compte de stockage.

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

## Clonez l’exemple de dépôt

Tout d'abord, nous allons cloner ce référentiel sur nos ordinateurs locaux. Vous obtiendrez ainsi le code de démarrage nécessaire à la fonctionnalité de l'application simple décrite ci-dessus. Nous pouvons cloner avec une simple commande git.

```bash
git clone https://github.com/Azure/computer-vision-nextjs-webapp.git
```

Pour préserver les variables d'environnement enregistrées, il est important que cette fenêtre de terminal reste ouverte pendant toute la durée du déploiement.

## Connectez-vous à Azure à l’aide de l’interface CLI

Pour exécuter des commandes sur Azure à l’aide de [l’interface CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), vous devez vous connecter. Pour cela, utilisez la commande `az login` :

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. Nous en créons un pour ce tutoriel. La commande suivante crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Résultats :

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

## Créer le compte de stockage

Pour créer un compte de stockage dans ce groupe de ressources, nous devons exécuter une simple commande. Nous transmettons à cette commande le nom du compte de stockage, le groupe de ressources dans lequel il doit être déployé, la région physique dans laquelle il doit être déployé et le SKU du compte de stockage. Toutes les valeurs sont configurées à l’aide de variables d’environnement.

```bash
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $REGION --sku Standard_LRS
```

Résultats :

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

Nous devons également stocker l'une des clés API du compte de stockage dans une variable d'environnement en vue d'une utilisation ultérieure (pour créer un conteneur et le placer dans un fichier d'environnement pour le code). Nous appelons la commande `keys list` sur le compte de stockage et stockons la première dans une variable d’environnement `STORAGE_ACCOUNT_KEY`.

```bash
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv)
```

## Créer un conteneur dans le compte de stockage

Utilisez la commande suivante pour créer un conteneur `images` dans le compte de stockage que nous venons de créer. Les images chargées par l'utilisateur seront stockées sous forme de blobs dans ce conteneur.

```bash
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob
```

Résultats :

<!--expected_similarity=0.5-->
```json
{
  "created": true
}
```

## Création d'une base de données

Nous allons créer un serveur flexible Azure Database pour PostgreSQL pour l'application afin de stocker les utilisateurs et leurs votes. Nous transmettons plusieurs arguments à la commande `create` :

- Les bases : nom de la base de données, groupe de ressources et région physique à déployer.
- Niveau (qui détermine les fonctionnalités du serveur) en tant que `burstable`, c’est-à-dire pour les charges de travail qui n’ont pas besoin d’un processeur complet en continu.
- La référence SKU en tant que `Standard_B1ms`.
  - `Standard` pour le niveau de performance.
  - `B` pour une charge de travail burstable.
  - `1` pour un cœur virtuel unique.
  - `ms` pour une mémoire optimisée.
- La taille de stockage, 32 Gio
- La version principale de PostgreSQL, 15
- Les informations d’identification de la base de données : nom d’utilisateur et mot de passe

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

Résultats :

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

Nous devons également stocker la chaîne de connexion à la base de données dans une variable d'environnement pour une utilisation ultérieure. Cette URL nous permettra d'accéder à la base de données dans la ressource que nous venons de créer.

```bash
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME"
```

## Créer une ressource Vision par ordinateur

Nous allons créer une ressource Vision par ordinateur pour pouvoir identifier les chats ou les chiens dans les images que les utilisateurs chargent. La création d'une ressource Vision par ordinateur peut être réalisée à l'aide d'une seule commande. Nous transmettons plusieurs arguments à la commande `create` :

- Les bases : le nom de la ressource, le groupe de ressources, la région et la création d'une ressource Vision par ordinateur.
- Référence SKU en tant que `S1`, ou le niveau de performance payant le plus économique.

```bash
az cognitiveservices account create \
    --name $MY_COMPUTER_VISION_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --kind ComputerVision \
    --sku S1 \
    --yes
```

Résultats :

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

Pour accéder à notre ressource de vision par ordinateur, nous avons besoin du point de terminaison et de la clé. Avec Azure CLI, nous avons accès à deux commandes `az cognitiveservices account` : `show` et `keys list`, qui nous donnent ce dont nous avons besoin.

```bash
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv)
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)
```

## Déployer le code dans un conteneur d’application

Maintenant que nous avons mis en place nos ressources de stockage, de base de données et de Vision par ordinateur, nous sommes prêts à déployer le code de l'application. Pour ce faire, nous allons utiliser Azure Container Apps pour héberger une version conteneurisée de notre application Next.js. Le fichier `Dockerfile` est déjà créé à la racine du référentiel. Il nous suffit donc d’exécuter une seule commande pour déployer le code. Avant d'exécuter cette commande, nous devons d'abord installer l'extension containerapp pour Azure CLI.

```bash
az extension add --upgrade -n containerapp
```

Cette commande créera une ressource Azure Container Registry pour héberger notre image Docker, une ressource Azure Container App qui exécute l'image et une ressource Azure Container App Environment pour notre image. Décortiquons ce que nous transmettons à la commande.

- Les bases : nom de ressource, groupe de ressources et région
- Le nom de la ressource Azure Container App Environment à utiliser ou à créer
- Le chemin du code source

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

Nous pouvons vérifier que la commande a réussi en utilisant :

```bash
az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```

Résultats :

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

## Créer une règle de pare-feu de base de données

Par défaut, notre base de données est configurée pour autoriser le trafic à partir d'une liste d'adresses IP. Nous devons ajouter l'adresse IP de notre application conteneurisée récemment déployée à cette liste d'autorisations. Nous pouvons obtenir l’adresse IP à partir de la commande `az containerapp show`.

```bash
export CONTAINER_APP_IP=$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.outboundIpAddresses[0]" --output tsv)
```

Nous pouvons maintenant ajouter cette adresse IP en tant que règle de pare-feu à l'aide de cette commande :

```bash
az postgres flexible-server firewall-rule create \
  --name $MY_DATABASE_SERVER_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --rule-name allow-container-app \
  --start-ip-address $CONTAINER_APP_IP \
  --end-ip-address $CONTAINER_APP_IP
```

Résultats :

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

## Créer une règle CORS pour le stockage

Les navigateurs web implémentent une restriction de sécurité, appelée stratégie de même origine, qui empêche une page web d’appeler des API dans un domaine différent. CORS fournit une méthode sécurisée autorisant un domaine (le domaine d’origine) à appeler les API d’un autre domaine. Nous devons ajouter une règle CORS sur l'URL de notre application web vers notre compte de stockage. Tout d’abord, obtenons l’URL avec une commande `az containerapp show` similaire comme précédemment.

```bash
export CONTAINER_APP_URL=https://$(az containerapp show --name $MY_CONTAINER_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.configuration.ingress.fqdn" --output tsv)
```

Ensuite, nous sommes prêts à ajouter une règle CORS avec la commande suivante. Décortiquons les différentes parties de cette commande.

- Nous spécifions le service blob comme type de stockage auquel ajouter la règle.
- Nous autorisons à toutes les opérations.
- Nous n'autorisons que l'URL de l'application conteneur que nous venons d'enregistrer.
- Nous autorisons tous les en-têtes HTTP de cette URL.
- L'âge maximum est la durée, en secondes, pendant laquelle un navigateur doit mettre en cache la réponse du contrôle en amont pour une requête spécifique.
- Nous transmettons le nom et la clé du compte de stockage que nous avons utilisés précédemment.

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

Et voilà ! N'hésitez pas à accéder à l'application web nouvellement déployée dans votre navigateur en imprimant la variable d'environnement CONTAINER_APP_URL que nous avons ajoutée plus tôt.

```bash
echo $CONTAINER_APP_URL
```

## Étapes suivantes

- [Documentation Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Documentation relative à Azure Database pour PostgreSQL](https://learn.microsoft.com/azure/postgresql/)
- [Documentation sur Stockage Blob Azure](https://learn.microsoft.com/azure/storage/blobs/)
- [Documentation Azure (IA) sur la vision par ordinateur](https://learn.microsoft.com/azure/ai-services/computer-vision/)
