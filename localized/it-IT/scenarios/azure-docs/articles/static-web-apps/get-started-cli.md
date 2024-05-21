---
title: 'Guida introduttiva: Creazione del primo sito statico con il App Web statiche di Azure usando l''interfaccia della riga di comando'
description: Informazioni su come distribuire un sito statico in App Web statiche di Azure con l'interfaccia della riga di comando di Azure.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Guida introduttiva: Creazione del primo sito statico con l'interfaccia della riga di comando di Azure

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

App Web statiche di Azure pubblica siti Web in produzione creando app da un repository di codice.

In questa guida di avvio rapido si distribuisce un'applicazione Web in App Web statiche di Azure usando l'interfaccia della riga di comando di Azure.

## Prerequisiti

- [Account GitHub](https://github.com) .
- [Account Azure](https://portal.azure.com).
  - Se non si ha una sottoscrizione di Azure, è possibile [creare un account](https://azure.microsoft.com/free) di valutazione gratuito.
- [Interfaccia della riga di comando](/cli/azure/install-azure-cli) di Azure installata (versione 2.29.0 o successiva).
- [Configurazione di Git](https://www.git-scm.com/downloads). 

## Definire le variabili di ambiente

Il primo passaggio di questa guida introduttiva consiste nel definire le variabili di ambiente.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Creare un repository (facoltativo)

(Facoltativo) Questo articolo usa un repository di modelli GitHub come un altro modo per semplificare l'avvio. Il modello include un'app iniziale da distribuire in App Web statiche di Azure.

1. Passare al percorso seguente per creare un nuovo repository: https://github.com/staticwebdev/vanilla-basic/generate.
2. Assegnare al repository `my-first-static-web-app`il nome .

> [!NOTE]
> Con App Web statiche di Azure è necessario almeno un file HTML per creare un'app Web. Il repository creato in questo passaggio include un singolo `index.html` file.

3. Selezionare **Create repository**.

## Distribuire un'app Web statica

Distribuire l'app come app Web statica dall'interfaccia della riga di comando di Azure.

1. Crea un gruppo di risorse.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Risultati:
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

2. Distribuire una nuova app Web statica dal repository.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

La distribuzione di un'app statica è un processo in due passaggi. La prima operazione crea le risorse di Azure sottostanti che costituiscono l'app. Il secondo è un flusso di lavoro che compila e pubblica l'applicazione.

Prima di poter passare al nuovo sito statico, la compilazione della distribuzione deve prima terminare l'esecuzione.

3. Tornare alla finestra della console ed eseguire il comando seguente per elencare l'URL del sito Web.

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

Risultati:
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

## Usare un modello GitHub

È stata distribuita correttamente un'app Web statica in App Web statiche di Azure usando l'interfaccia della riga di comando di Azure. Ora che si ha una conoscenza di base di come distribuire un'app Web statica, è possibile esplorare funzionalità e funzionalità più avanzate di App Web statiche di Azure.

Se si vuole usare il repository di modelli GitHub, seguire questa procedura:

Passare a https://github.com/login/device e immettere il codice ottenuto da GitHub per attivare e recuperare il token di accesso personale di GitHub.

1. Vai a https://github.com/login/device.
2. Immettere il codice utente come visualizzato nel messaggio della console.
3. Selezionare `Continue`.
4. Selezionare `Authorize AzureAppServiceCLI`.

### Visualizzare il sito Web tramite Git

1. Quando si ottiene l'URL del repository durante l'esecuzione dello script, copiare l'URL del repository e incollarlo nel browser.
2. Selezionare la scheda `Actions`.

   A questo punto, Azure sta creando le risorse per supportare l'app Web statica. Attendere fino a quando l'icona accanto al flusso di lavoro in esecuzione diventa un segno di spunta con sfondo verde. L'esecuzione di questa operazione potrebbe richiedere alcuni minuti.

3. Quando viene visualizzata l'icona di operazione riuscita, il flusso di lavoro è completo ed è possibile tornare alla finestra della console.
4. Eseguire il comando seguente per eseguire una query sull'URL del sito Web.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Copiare l'URL nel browser per passare al sito Web.

## Pulire le risorse (facoltativo)

Se non si intende continuare a usare questa applicazione, eliminare il gruppo di risorse e l'app Web statica usando il [comando az group delete](/cli/azure/group#az-group-delete) .

## Passaggi successivi

> [!div class="nextstepaction"]
> [Aggiungere un'API](add-api.md)
