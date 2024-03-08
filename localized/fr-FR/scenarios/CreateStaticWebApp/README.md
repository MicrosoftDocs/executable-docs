---
title: Créer un site statique avec Azure CLI
description: Ce tutoriel montre comment créer un site statique sur Azure.
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Démarrage rapide d’Azure Static Web Apps : création de votre premier site statique avec Azure CLI

Azure Static Web Apps publie des sites web de production en créant des applications à partir d'un référentiel de code. Dans ce guide de démarrage rapide, vous allez déployer une application web dans Azure Static Web Apps avec l’interface Azure CLI.

## Définissez des variables d’environnement

La première étape de ce tutoriel définit des variables d’environnement.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Créer un référentiel (facultatif)

(Facultatif) cet article utilise un référentiel de modèles GitHub comme autre moyen de faciliter la prise en main. Le modèle comprend une application de démarrage déployée sur Azure Static Web Apps.

- Accédez à l’emplacement suivant pour créer un nouveau référentiel : https://github.com/staticwebdev/vanilla-basic/generate
- Nommez votre référentiel `my-first-static-web-app`

> **Remarque :** Azure Static Web Apps nécessite au moins un fichier HTML pour pouvoir créer une application web. Le référentiel que vous créez lors de cette étape comprend un seul fichier `index.html`.

Sélectionnez `Create repository`.

## Déployer une application web statique

Vous pouvez déployer l’application en tant qu’application web statique depuis Azure CLI.

1. Créez un groupe de ressources.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Résultats :

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/my-swa-group",
  "location": "eastus2",
  "managedBy": null,
  "name": "my-swa-group",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

2. Déployez une application web statique à partir de votre dépôt.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Le déploiement d’une application statique comporte deux aspects. La première opération crée les ressources Azure sous-jacentes qui composent votre application. La seconde est un workflow qui génère et publie votre application.

Avant de pouvoir accéder à votre nouveau site statique, la build de déploiement doit d’abord finir de s’exécuter.

3. Revenez à votre fenêtre de console et exécutez la commande suivante pour répertorier l’URL du site web.

```bash
export MY_STATIC_WEB_APP_URL=$(az staticwebapp show --name  $MY_STATIC_WEB_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "defaultHostname" -o tsv)
```

```bash
runtime="1 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
    if curl -I -s $MY_STATIC_WEB_APP_URL > /dev/null ; then 
        curl -L -s $MY_STATIC_WEB_APP_URL 2> /dev/null | head -n 9
        break
    else 
        sleep 10
    fi;
done
```

Résultats :

<!-- expected_similarity=0.3 -->
```HTML
<!DOCTYPE html>
<html lang=en>
<head>
<meta charset=utf-8 />
<meta name=viewport content="width=device-width, initial-scale=1.0" />
<meta http-equiv=X-UA-Compatible content="IE=edge" />
<title>Azure Static Web Apps - Welcome</title>
<link rel="shortcut icon" href=https://appservice.azureedge.net/images/static-apps/v3/favicon.svg type=image/x-icon />
<link rel=stylesheet href=https://ajax.aspnetcdn.com/ajax/bootstrap/4.1.1/css/bootstrap.min.css crossorigin=anonymous />
```

```bash
echo "You can now visit your web server at https://$MY_STATIC_WEB_APP_URL"
```

## Étapes suivantes

Félicitations ! Vous avez déployé une application web statique sur Azure Static Web Apps avec Azure CLI. Maintenant que vous avez une compréhension de base de la façon de déployer une application web statique, vous pouvez explorer des fonctionnalités et des fonctionnalités plus avancées d’Azure Static Web Apps.

Si vous souhaitez utiliser le référentiel de modèles GitHub, suivez les étapes supplémentaires ci-dessous.

Accédez à https://github.com/login/device et entrez le code utilisateur 329B-3945 pour activer et récupérer votre jeton d’accès personnel GitHub.

1. Accédez à https://github.com/login/device.
2. Entrez le code utilisateur tel qu’il est affiché dans le message de votre console.
3. Sélectionnez `Continue`.
4. Sélectionnez `Authorize AzureAppServiceCLI`.

### Afficher le site web via Git

1. Lorsque vous obtenez l’URL du référentiel lors de l’exécution du script, copiez l’URL du référentiel et collez-la dans votre navigateur.
2. Sélectionnez l'onglet `Actions`.

   À ce stade, Azure crée les ressources pour prendre en charge votre application Web statique. Attendez que l’icône en regard du flux de travail en cours d’exécution devienne une coche avec un arrière-plan vert (). L’opération peut prendre quelques minutes.

3. Une fois l’icône de réussite affichée, le flux de travail est terminé et vous pouvez revenir à la fenêtre de console.
4. Exécutez la commande suivante pour interroger l’URL de votre site Web.

   afficher az staticwebapp \
     --name $MY_STATIC_WEB_APP_NAME \
     --query « defaultHostname »

5. Copiez l’URL dans votre navigateur pour accéder à votre site web.
