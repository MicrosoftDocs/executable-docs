---
title: 'Rövid útmutató: Az első statikus webhely létrehozása az Azure Static Web Apps használatával a parancssori felület használatával'
description: 'Ismerje meg, hogyan helyezhet üzembe statikus webhelyet az Azure Static Web Appsben az Azure CLI-vel.'
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Rövid útmutató: Az első statikus webhely létrehozása az Azure CLI használatával

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Az Azure Static Web Apps egy kódtárból származó alkalmazások létrehozásával teszi közzé a webhelyeket az éles környezetben.

Ebben a rövid útmutatóban egy webalkalmazást helyez üzembe az Azure Static Web Appsben az Azure CLI használatával.

## Előfeltételek

- [GitHub-fiók](https://github.com) .
- [Egy Azure-fiók](https://portal.azure.com).
  - Ha nem rendelkezik Azure-előfizetéssel, [létrehozhat egy ingyenes próbaverziós fiókot](https://azure.microsoft.com/free).
- [Telepített Azure CLI](/cli/azure/install-azure-cli) (2.29.0-s vagy újabb verzió).
- [Egy Git-beállítás](https://www.git-scm.com/downloads). 

## Környezeti változók definiálása

A rövid útmutató első lépése a környezeti változók definiálása.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Adattár létrehozása (nem kötelező)

(Nem kötelező) Ez a cikk egy GitHub-sablontárházat használ, amely megkönnyíti az első lépéseket. A sablon tartalmaz egy kezdőalkalmazást, amely üzembe helyezhető az Azure Static Web Appsben.

1. Új adattár létrehozásához lépjen a következő helyre: https://github.com/staticwebdev/vanilla-basic/generate.
2. Nevezze el az adattárat `my-first-static-web-app`.

> [!NOTE]
> Az Azure Static Web Apps használatához legalább egy HTML-fájl szükséges egy webalkalmazás létrehozásához. Az ebben a lépésben létrehozott adattár egyetlen `index.html` fájlt tartalmaz.

3. Válassza a **Create repository** (Adattár létrehozása) gombot.

## Statikus webalkalmazás üzembe helyezése

Az alkalmazás üzembe helyezése statikus webalkalmazásként az Azure CLI-ből.

1. Hozzon létre egy erőforráscsoportot.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Eredmények:
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

2. Új statikus webalkalmazás üzembe helyezése az adattárból.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

A statikus alkalmazások üzembe helyezésének két aspektusa van. Az első művelet létrehozza az alkalmazást alkotó mögöttes Azure-erőforrásokat. A második egy munkafolyamat, amely létrehozza és közzéteszi az alkalmazást.

Mielőtt megnyithatja az új statikus helyet, az üzembe helyezési buildnek először futnia kell.

3. Térjen vissza a konzolablakba, és futtassa a következő parancsot a webhely URL-címének listázásához.

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

Eredmények:
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

## GitHub-sablon használata

Sikeresen üzembe helyezett egy statikus webalkalmazást az Azure Static Web Appsben az Azure CLI használatával. Most, hogy alapszintű ismeretekkel rendelkezik a statikus webalkalmazások üzembe helyezéséről, megismerheti az Azure Static Web Apps fejlettebb funkcióit és funkcióit.

Ha a GitHub-sablontárházat szeretné használni, kövesse az alábbi lépéseket:

Nyissa meg https://github.com/login/device és adja meg a GitHubról kapott kódot a GitHub személyes hozzáférési jogkivonatának aktiválásához és lekéréséhez.

1. Odamegy https://github.com/login/device.
2. Adja meg a felhasználói kódot a konzol üzenetének megfelelően.
3. Válassza ki `Continue`.
4. Válassza ki `Authorize AzureAppServiceCLI`.

### A webhely megtekintése a Giten keresztül

1. Amikor a szkript futtatása közben megkapja az adattár URL-címét, másolja ki az adattár URL-címét, és illessze be a böngészőbe.
2. Válassza ki a(z) `Actions` lapot.

   Ezen a ponton az Azure létrehozza az erőforrásokat a statikus webalkalmazás támogatásához. Várja meg, amíg a futó munkafolyamat melletti ikon zöld háttérrel rendelkező pipává válik. A művelet végrehajtása eltarthat néhány percig.

3. A sikeresség ikon megjelenése után a munkafolyamat befejeződött, és visszatérhet a konzolablakba.
4. Futtassa a következő parancsot a webhely URL-címének lekérdezéséhez.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Másolja az URL-címet a böngészőbe a webhelyre való ugráshoz.

## Erőforrások törlése (nem kötelező)

Ha nem folytatja az alkalmazás használatát, törölje az erőforráscsoportot és a statikus webalkalmazást az [az group delete](/cli/azure/group#az-group-delete) paranccsal.

## Következő lépések

> [!div class="nextstepaction"]
> [API hozzáadása](add-api.md)
