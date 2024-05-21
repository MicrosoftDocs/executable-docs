---
title: "Démarrage rapide\_: Création de votre premier site statique avec le service Azure Static Web Apps à l’aide de l’interface CLI"
description: Apprenez à déployer un site statique sur Azure Static Web Apps avec l’interface Azure CLI.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Démarrage rapide : Création de votre premier site statique à l’aide de l’interface Azure CLI

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps publie des sites web de production en créant des applications à partir d'un référentiel de code.

Dans ce guide de démarrage rapide, vous déployez une application web dans Azure Static Web Apps à l’aide de l’interface Azure CLI.

## Prérequis

- Compte [GitHub](https://github.com).
- Compte [Azure](https://portal.azure.com).
  - Si vous n’avez pas d’abonnement Azure, vous pouvez [créer un compte Azure gratuit](https://azure.microsoft.com/free).
- [Azure CLI](/cli/azure/install-azure-cli) version 2.29.0 ou ultérieure installée.
- [Une configuration Git](https://www.git-scm.com/downloads). 

## Définissez des variables d’environnement

La première étape de ce guide de démarrage rapide consiste à définir des variables d’environnement.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Créer un référentiel (facultatif)

(Facultatif) cet article utilise un référentiel de modèles GitHub comme autre moyen de faciliter la prise en main. Le modèle comprend une application de démarrage déployée sur Azure Static Web Apps.

1. Accédez à l’emplacement suivant pour créer un nouveau référentiel : https://github.com/staticwebdev/vanilla-basic/generate.
2. Nommez votre dépôt `my-first-static-web-app`.

> [!NOTE]
> Azure Static Web Apps nécessite au moins un fichier HTML pour pouvoir créer une application web. Le référentiel que vous créez lors de cette étape comprend un seul fichier `index.html`.

3. Cliquez sur **Create repository** (Créer le dépôt).

## Déployer une application web statique

Déployez l’application en tant qu’application web statique depuis Azure CLI.

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

## Utilisez un modèle GitHub

Vous avez réussi à déployer une application web statique sur Azure Static Web Apps avec Azure CLI. Maintenant que vous avez une compréhension de base de la façon de déployer une application web statique, vous pouvez explorer des fonctionnalités et des fonctionnalités plus avancées d’Azure Static Web Apps.

Si vous souhaitez utiliser le référentiel de modèles GitHub, suivez ces étapes :

Accédez à https://github.com/login/device et entrez le code que vous obtenez sur GitHub pour activer et récupérer votre jeton d’accès personnel GitHub.

1. Accédez à https://github.com/login/device.
2. Entrez le code utilisateur tel qu’il est affiché dans le message de votre console.
3. Sélectionnez `Continue`.
4. Sélectionnez `Authorize AzureAppServiceCLI`.

### Afficher le site web via Git

1. Lorsque vous obtenez l’URL du référentiel lors de l’exécution du script, copiez l’URL du référentiel et collez-la dans votre navigateur.
2. Sélectionnez l'onglet `Actions`.

   À ce stade, Azure crée les ressources pour prendre en charge votre application Web statique. Attendez que l’icône en regard du flux de travail en cours d’exécution devienne une coche avec un arrière-plan vert. L’opération peut prendre quelques minutes.

3. Une fois l’icône de réussite affichée, le flux de travail est terminé et vous pouvez revenir à la fenêtre de console.
4. Exécutez la commande suivante pour interroger l’URL de votre site Web.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Copiez l’URL dans votre navigateur pour accéder à votre site web.

## Nettoyez les ressources (facultatif)

Si vous ne comptez pas continuer à utiliser cette application, supprimez le groupe de ressources et l’application Web statique en exécutant la commande [az group delete](/cli/azure/group#az-group-delete).

## Étapes suivantes

> [!div class="nextstepaction"]
> [Ajouter une API](add-api.md)
