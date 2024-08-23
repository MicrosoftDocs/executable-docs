---
title: 'Schnellstart: Erstellen Ihrer ersten statischen Website mit Azure Static Web Apps und der CLI'
description: 'Erfahren Sie, wie Sie mit der Azure CLI eine statische Website für Azure Static Web Apps bereitstellen'
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Schnellstart: Erstellen Ihrer ersten statischen Website mithilfe der Azure CLI

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps veröffentlicht Websites in der Produktion, indem Apps aus einem Coderepository erstellt werden.

In dieser Schnellstartanleitung stellen Sie über die Azure CLI eine Web-Anwendung in Azure Static Web Apps bereit.

## Voraussetzungen

- [GitHub-Konto](https://github.com).
- [Azure](https://portal.azure.com)-Konto.
  - Wenn Sie über kein Azure-Abonnement verfügen, können Sie [ein kostenloses Testkonto erstellen](https://azure.microsoft.com/free).
- [Installation der Azure-Befehlszeilenschnittstelle](/cli/azure/install-azure-cli) (Version 2.29.0 oder höher).
- [Ein Git-Setup](https://www.git-scm.com/downloads). 

## Definieren von Umgebungsvariablen

Der erste Schritt in diesem Schnellstart besteht darin, Umgebungsvariablen zu definieren.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Erstellen eines Repositorys (optional)

(Optional) In diesem Artikel wird ein GitHub-Vorlagen-Repository als eine andere Möglichkeit verwendet, um Ihnen den Einstieg zu erleichtern. Die Vorlage enthält eine Starter-App zur Bereitstellung in Azure Static Web Apps.

1. Navigieren Sie zum folgenden Speicherort, um ein neues Repository zu erstellen: https://github.com/staticwebdev/vanilla-basic/generate.
2. Nennen Sie das Repository `my-first-static-web-app`.

> [!NOTE]
> Für Azure Static Web Apps wird mindestens eine HTML-Datei benötigt, um eine Web-App zu erstellen. Das in diesem Schritt erstellte Repository enthält nur eine Datei vom Typ `index.html`.

3. Klicken Sie auf **Create repository** (Repository erstellen).

## Bereitstellen einer Static Web App

Stellen Sie die App als statische Web-App über die Azure CLI bereit.

1. Erstellen Sie eine Ressourcengruppe.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Ergebnisse:
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

2. Stellen Sie eine neue statische Web-App aus Ihrem Repository bereit.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Für die Bereitstellung einer statischen App gelten zwei Aspekte. Der erste Vorgang erstellt die zugrunde liegenden Azure-Ressourcen, aus denen Ihre App besteht. Der zweite besteht aus einem Workflow, mit dem Ihre Anwendung erstellt und veröffentlicht wird.

Bevor Sie zu Ihrer neuen statischen Website navigieren können, muss zuvor der Buildvorgang für die Bereitstellung abgeschlossen sein.

3. Kehren Sie zum Konsolenfenster zurück, und führen Sie den folgenden Befehl aus, um die URL der Website auflisten zu können.

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

Ergebnisse:
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

## Verwenden Sie eine GitHub-Vorlage

Sie haben erfolgreich eine statische Web-App mithilfe der Azure CLI in Azure Static Web Apps bereitgestellt. Nachdem Sie nun ein grundlegendes Verständnis für die Bereitstellung einer statischen Web-App haben, können Sie erweiterte Features und Funktionen von Azure Static Web Apps erkunden.

Wenn Sie das GitHub-Vorlagenrepository verwenden möchten, führen Sie die folgenden Schritte aus:

Navigieren Sie zu https://github.com/login/device, und geben Sie den von GitHub erhaltenen Code ein, um Ihr persönliches GitHub-Zugriffstoken zu aktivieren und abzurufen.

1. Wechseln Sie zu https://github.com/login/device.
2. Geben Sie den Benutzercode wie in der Meldung Ihrer Konsole angezeigt ein.
3. Wählen Sie `Continue` aus.
4. Wählen Sie `Authorize AzureAppServiceCLI` aus.

### Anzeigen der Website über Git

1. Wenn Sie die Repository-URL beim Ausführen des Skripts erhalten, kopieren Sie die Repository-URL und fügen Sie sie in Ihren Browser ein.
2. Wählen Sie die Registerkarte `Actions` aus.

   An diesem Punkt erstellt Azure die Ressourcen zur Unterstützung Ihrer statischen Web-App. Warten Sie, bis sich das Symbol neben dem ausgeführten Workflow in ein Häkchen mit grünem Hintergrund ändert. Dieser Vorgang kann einige Minuten in Anspruch nehmen.

3. Sobald das Erfolgssymbol angezeigt wird, ist der Workflow abgeschlossen, und Sie können zu Ihrem Konsolenfenster zurückkehren.
4. Führen Sie den folgenden Befehl aus, um die URL Ihrer Website abzufragen.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Kopieren Sie die URL in Ihren Browser, und navigieren Sie zu Ihrer Website.

## Bereinigen von Ressourcen (optional)

Falls Sie diese Anwendung nicht weiter nutzen möchten, löschen Sie die Ressourcengruppe und die statische Webanwendung anhand des [az group delete](/cli/azure/group#az-group-delete)-Befehls.

## Nächste Schritte

> [!div class="nextstepaction"]
> [Hinzufügen einer API zu Azure Static Web Apps (Vorschauversion) mit Azure Functions](add-api.md)
