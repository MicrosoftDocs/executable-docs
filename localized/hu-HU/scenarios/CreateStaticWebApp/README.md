---
title: Statikus webhely létrehozása az Azure CLI használatával
description: 'Ez az oktatóanyag bemutatja, hogyan hozhat létre statikus webhelyet az Azure-ban.'
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Az Azure Static Web Apps rövid útmutatója: Az első statikus webhely létrehozása az Azure CLI használatával

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Az Azure Static Web Apps egy kódtárból származó alkalmazások létrehozásával teszi közzé a webhelyeket az éles környezetben. Ebben a rövid útmutatóban üzembe helyez egy webalkalmazást az Azure Static Web Appsben az Azure CLI használatával.

## Környezeti változók definiálása

Az oktatóanyag első lépése a környezeti változók definiálása.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Adattár létrehozása (nem kötelező)

(Nem kötelező) Ez a cikk egy GitHub-sablontárházat használ, amely megkönnyíti az első lépéseket. A sablon tartalmaz egy kezdőalkalmazást, amely üzembe helyezhető az Azure Static Web Appsben.

- Új adattár létrehozásához lépjen a következő helyre: https://github.com/staticwebdev/vanilla-basic/generate
- Az adattár elnevezése `my-first-static-web-app`

> **Megjegyzés:** Az Azure Static Web Appsnek legalább egy HTML-fájlra van szüksége egy webalkalmazás létrehozásához. Az ebben a lépésben létrehozott adattár egyetlen `index.html` fájlt tartalmaz.

Válassza ki `Create repository`.

## Statikus webalkalmazás üzembe helyezése

Az alkalmazást statikus webalkalmazásként is üzembe helyezheti az Azure CLI-ből.

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

## Következő lépések

Gratulálunk! Sikeresen üzembe helyezett egy statikus webalkalmazást az Azure Static Web Appsben az Azure CLI használatával. Most, hogy alapszintű ismeretekkel rendelkezik a statikus webalkalmazások üzembe helyezéséről, megismerheti az Azure Static Web Apps fejlettebb funkcióit és funkcióit.

Ha a GitHub-sablontárházat szeretné használni, kövesse az alábbi további lépéseket.

Nyissa meg https://github.com/login/device és írja be a 329B-3945 felhasználói kódot a GitHub személyes hozzáférési jogkivonatának aktiválásához és lekéréséhez.

1. Odamegy https://github.com/login/device.
2. Adja meg a felhasználói kódot a konzol üzenetének megfelelően.
3. Válassza ki `Continue`.
4. Válassza ki `Authorize AzureAppServiceCLI`.

### A webhely megtekintése a Giten keresztül

1. Amikor a szkript futtatása közben megkapja az adattár URL-címét, másolja ki az adattár URL-címét, és illessze be a böngészőbe.
2. Válassza ki a(z) `Actions` lapot.

   Ezen a ponton az Azure létrehozza az erőforrásokat a statikus webalkalmazás támogatásához. Várja meg, amíg a futó munkafolyamat melletti ikon zöld háttérrel () pipává változik. A művelet végrehajtása eltarthat néhány percig.

3. A sikeresség ikon megjelenése után a munkafolyamat befejeződött, és visszatérhet a konzolablakba.
4. Futtassa a következő parancsot a webhely URL-címének lekérdezéséhez.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. Másolja az URL-címet a böngészőbe a webhelyre való ugráshoz.
