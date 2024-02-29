---
title: Skapa en statisk webbplats med hjälp av Azure CLI
description: Den här självstudien visar hur du skapar en statisk webbplats i Azure.
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Snabbstart för Azure Static Web Apps: Skapa din första statiska webbplats med hjälp av Azure CLI

Azure Static Web Apps publicerar webbplatser till produktion genom att skapa appar från en kodlagringsplats. I den här snabbstarten distribuerar du ett webbprogram till Azure Static Web Apps med hjälp av Azure CLI.

## Definiera miljövariabler

Det första steget i den här självstudien är att definiera miljövariabler.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Skapa en lagringsplats (valfritt)

(Valfritt) Den här artikeln använder en GitHub-malllagringsplats som ett annat sätt att göra det enkelt för dig att komma igång. Mallen har en startapp som ska distribueras till Azure Static Web Apps.

- Gå till följande plats för att skapa en ny lagringsplats: https://github.com/staticwebdev/vanilla-basic/generate
- Namnge din lagringsplats `my-first-static-web-app`

> **** Obs! Azure Static Web Apps kräver minst en HTML-fil för att skapa en webbapp. Lagringsplatsen som du skapar i det här steget innehåller en enda `index.html` fil.

Välj `Create repository`.

## Distribuera en statisk webbapp

Du kan distribuera appen som en statisk webbapp från Azure CLI.

1. Skapa en resursgrupp.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Resultat:

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

2. Distribuera en ny statisk webbapp från lagringsplatsen.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Det finns två aspekter för att distribuera en statisk app. Den första åtgärden skapar de underliggande Azure-resurser som utgör din app. Det andra är ett arbetsflöde som skapar och publicerar ditt program.

Innan du kan gå till den nya statiska platsen måste distributionsversionen först slutföras.

3. Gå tillbaka till konsolfönstret och kör följande kommando för att visa webbplatsens URL.

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

Resultat:

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

## Nästa steg

Grattis! Du har distribuerat en statisk webbapp till Azure Static Web Apps med hjälp av Azure CLI. Nu när du har en grundläggande förståelse för hur du distribuerar en statisk webbapp kan du utforska mer avancerade funktioner i Azure Static Web Apps.

Om du vill använda GitHub-malllagringsplatsen följer du de ytterligare stegen nedan.

Gå till https://github.com/login/device och ange användarkoden 329B-3945 för att aktivera och hämta din personliga GitHub-åtkomsttoken.

1. Gå till https://github.com/login/device.
2. Ange användarkoden som visas i konsolens meddelande.
3. Välj `Continue`.
4. Välj `Authorize AzureAppServiceCLI`.

### Visa webbplatsen via Git

1. När du hämtar lagringsplatsens URL när du kör skriptet kopierar du lagringsplatsens URL och klistrar in den i webbläsaren.
2. Välj `Actions`-fliken.

   Nu skapar Azure resurserna för att stödja din statiska webbapp. Vänta tills ikonen bredvid arbetsflödet som körs förvandlas till en bockmarkering med grön bakgrund ( ). Den här åtgärden kan ta några minuter att slutföra.

3. När framgångsikonen visas är arbetsflödet klart och du kan återgå till konsolfönstret.
4. Kör följande kommando för att fråga efter webbplatsens URL.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. Kopiera URL:en till webbläsaren för att gå till webbplatsen.
