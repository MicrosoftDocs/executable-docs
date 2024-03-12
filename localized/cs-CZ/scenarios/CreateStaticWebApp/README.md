---
title: Vytvoření statického webu pomocí Azure CLI
description: 'V tomto kurzu se dozvíte, jak vytvořit statický web v Azure.'
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Rychlý start azure Static Web Apps: Vytvoření prvního statického webu pomocí Azure CLI

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps publikuje weby do produkčního prostředí vytvořením aplikací z úložiště kódu. V tomto rychlém startu nasadíte webovou aplikaci do Azure Static Web Apps pomocí Azure CLI.

## Definování proměnných prostředí

Prvním krokem v tomto kurzu je definování proměnných prostředí.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Vytvoření úložiště (volitelné)

(Volitelné) Tento článek používá úložiště šablon GitHubu jako jiný způsob, jak snadno začít. Šablona obsahuje úvodní aplikaci pro nasazení do Azure Static Web Apps.

- Přejděte do následujícího umístění a vytvořte nové úložiště: https://github.com/staticwebdev/vanilla-basic/generate
- Pojmenujte úložiště. `my-first-static-web-app`

> **Poznámka:** Azure Static Web Apps k vytvoření webové aplikace vyžaduje alespoň jeden soubor HTML. Úložiště, které vytvoříte v tomto kroku, obsahuje jeden `index.html` soubor.

Vyberte možnost `Create repository`.

## Nasazení statické webové aplikace

Aplikaci můžete nasadit jako statickou webovou aplikaci z Azure CLI.

1. Vytvořte skupinu prostředků.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Výsledky:

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

2. Nasaďte novou statickou webovou aplikaci z úložiště.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Nasazení statické aplikace má dva aspekty. První operace vytvoří základní prostředky Azure, které tvoří vaši aplikaci. Druhým je pracovní postup, který sestaví a publikuje vaši aplikaci.

Než budete moct přejít na novou statickou lokalitu, musí se sestavení nasazení nejprve dokončit.

3. Vraťte se do okna konzoly a spuštěním následujícího příkazu zobrazte seznam adres URL webu.

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

Výsledky:

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

## Další kroky

Gratulujeme! Úspěšně jste nasadili statickou webovou aplikaci do Azure Static Web Apps pomocí Azure CLI. Teď, když máte základní znalosti o tom, jak nasadit statickou webovou aplikaci, můžete prozkoumat pokročilejší funkce a funkce Azure Static Web Apps.

V případě, že chcete použít úložiště šablon GitHubu, postupujte podle dalších kroků níže.

Přejděte na https://github.com/login/device a zadejte uživatelský kód 329B-3945, který aktivuje a načte osobní přístupový token GitHubu.

1. Umožňuje přejít na https://github.com/login/device.
2. Zadejte uživatelský kód tak, jak se zobrazí zpráva konzoly.
3. Vyberte možnost `Continue`.
4. Vyberte možnost `Authorize AzureAppServiceCLI`.

### Zobrazení webu přes Git

1. Jakmile při spuštění skriptu získáte adresu URL úložiště, zkopírujte adresu URL úložiště a vložte ji do prohlížeče.
2. Vyberte kartu `Actions`.

   V tuto chvíli Azure vytváří prostředky pro podporu vaší statické webové aplikace. Počkejte, až se ikona vedle spuštěného pracovního postupu změní na značku zaškrtnutí se zeleným pozadím (). Provedení této operace může trvat několik minut.

3. Jakmile se zobrazí ikona úspěchu, pracovní postup se dokončí a můžete se vrátit zpět do okna konzoly.
4. Spuštěním následujícího příkazu zadejte dotaz na adresu URL vašeho webu.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query defaultHostname

5. Zkopírujte adresu URL do prohlížeče a přejděte na svůj web.
