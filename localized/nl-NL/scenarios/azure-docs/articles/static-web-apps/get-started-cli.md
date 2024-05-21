---
title: 'Quickstart: Uw eerste statische site bouwen met de Azure Static Web Apps met behulp van de CLI'
description: Leer hoe u een statische site kunt implementeren in Azure Static Web Apps met behulp van Azure CLI.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Quickstart: Uw eerste statische site bouwen met behulp van de Azure CLI

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps publiceert websites naar productie door apps te bouwen vanuit een codeopslagplaats.

In deze quickstart implementeert u een webtoepassing in Azure Static Web Apps met behulp van de Azure CLI.

## Vereisten

- [GitHub-account](https://github.com) .
- [Azure-account](https://portal.azure.com).
  - Als u geen Azure-abonnement hebt, kunt [u een gratis proefaccount](https://azure.microsoft.com/free) maken.
- [Azure CLI](/cli/azure/install-azure-cli) geïnstalleerd (versie 2.29.0 of hoger).
- [Een Git-installatie](https://www.git-scm.com/downloads). 

## Omgevingsvariabelen definiëren

De eerste stap in deze quickstart is het definiëren van omgevingsvariabelen.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Een opslagplaats maken (optioneel)

(Optioneel) In dit artikel wordt een GitHub-sjabloonopslagplaats gebruikt als een andere manier om u op weg te helpen. De sjabloon bevat een starter-app die moet worden geïmplementeerd in Azure Static Web Apps.

1. Navigeer naar de volgende locatie om een nieuwe opslagplaats te maken: https://github.com/staticwebdev/vanilla-basic/generate
2. Geef uw opslagplaats `my-first-static-web-app`een naam.

> [!NOTE]
> Voor Azure Static Web Apps is minstens één HTML-bestand vereist om een web-app te maken. De opslagplaats die u in deze stap maakt, bevat één `index.html` bestand.

3. Klik op **Opslagplaats maken**.

## Een statische web-app implementeren

Implementeer de app als een statische web-app vanuit de Azure CLI.

1. Maak een resourcegroep.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Resultaten:
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

2. Implementeer een nieuwe statische web-app vanuit uw opslagplaats.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Het implementeren van een statische app heeft twee aspecten. Met de eerste bewerking worden de onderliggende Azure-resources gemaakt waaruit uw app bestaat. De tweede is een werkstroom waarmee uw toepassing wordt gebouwd en gepubliceerd.

Voordat u naar uw nieuwe statische site kunt gaan, moet de implementatie-build eerst worden uitgevoerd.

3. Ga terug naar het consolevenster en voer de volgende opdracht uit om de URL van de website weer te geven.

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

Resultaten:
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

## Een GitHub-sjabloon gebruiken

U hebt een statische web-app geïmplementeerd in Azure Static Web Apps met behulp van de Azure CLI. Nu u basiskennis hebt van het implementeren van een statische web-app, kunt u geavanceerdere functies en functionaliteit van Azure Static Web Apps verkennen.

Als u de GitHub-sjabloonopslagplaats wilt gebruiken, voert u de volgende stappen uit:

Ga naar https://github.com/login/device en voer de code in die u van GitHub krijgt om uw persoonlijke GitHub-toegangstoken te activeren en op te halen.

1. Ga naar https://github.com/login/device.
2. Voer de gebruikerscode in zoals het bericht van de console wordt weergegeven.
3. Selecteer `Continue`.
4. Selecteer `Authorize AzureAppServiceCLI`.

### De website bekijken via Git

1. Wanneer u de URL van de opslagplaats krijgt tijdens het uitvoeren van het script, kopieert u de URL van de opslagplaats en plakt u deze in uw browser.
2. Selecteer het tabblad `Actions`.

   Op dit moment maakt Azure de resources ter ondersteuning van uw statische web-app. Wacht totdat het pictogram naast de actieve werkstroom verandert in een vinkje met groene achtergrond. Het uitvoeren van deze bewerking kan enkele minuten duren.

3. Zodra het pictogram geslaagd wordt weergegeven, is de werkstroom voltooid en kunt u teruggaan naar het consolevenster.
4. Voer de volgende opdracht uit om een query uit te voeren op de URL van uw website.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Kopieer de URL naar uw browser om naar uw website te gaan.

## Resources opschonen (optioneel)

Als u deze toepassing niet wilt blijven gebruiken, verwijdert u de resourcegroep en de statische web-app met behulp van de [opdracht az group delete](/cli/azure/group#az-group-delete) .

## Volgende stappen

> [!div class="nextstepaction"]
> [Een API toevoegen](add-api.md)
