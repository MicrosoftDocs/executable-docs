---
title: Tworzenie witryny statycznej przy użyciu interfejsu wiersza polecenia platformy Azure
description: 'W tym samouczku pokazano, jak utworzyć statyczną witrynę na platformie Azure.'
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Przewodnik Szybki start dotyczący usługi Azure Static Web Apps: tworzenie pierwszej statycznej witryny przy użyciu interfejsu wiersza polecenia platformy Azure

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Usługa Azure Static Web Apps publikuje witryny internetowe w środowisku produkcyjnym, tworząc aplikacje z repozytorium kodu. W tym przewodniku Szybki start wdrożysz aplikację internetową w usłudze Azure Static Web Apps przy użyciu interfejsu wiersza polecenia platformy Azure.

## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Tworzenie repozytorium (opcjonalnie)

(Opcjonalnie) W tym artykule użyto repozytorium szablonów usługi GitHub jako innego sposobu, aby ułatwić rozpoczęcie pracy. Szablon zawiera początkową aplikację do wdrożenia w usłudze Azure Static Web Apps.

- Przejdź do następującej lokalizacji, aby utworzyć nowe repozytorium: https://github.com/staticwebdev/vanilla-basic/generate
- Nazwij repozytorium `my-first-static-web-app`

> **Uwaga:** usługa Azure Static Web Apps wymaga co najmniej jednego pliku HTML do utworzenia aplikacji internetowej. Repozytorium utworzone w tym kroku zawiera jeden `index.html` plik.

Wybierz opcję `Create repository`.

## Wdrażanie statycznej aplikacji internetowej

Aplikację można wdrożyć jako statyczną aplikację internetową z poziomu interfejsu wiersza polecenia platformy Azure.

1. Utwórz grupę zasobów.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Wyniki:

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

2. Wdróż nową statyczną aplikację internetową z repozytorium.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Istnieją dwa aspekty wdrażania aplikacji statycznej. Pierwsza operacja tworzy bazowe zasoby platformy Azure tworzące aplikację. Drugi to przepływ pracy, który kompiluje i publikuje aplikację.

Przed przejściem do nowej witryny statycznej kompilacja wdrożenia musi najpierw zakończyć działanie.

3. Wróć do okna konsoli i uruchom następujące polecenie, aby wyświetlić adres URL witryny internetowej.

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

Wyniki:

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

## Następne kroki

Gratulacje! Pomyślnie wdrożono statyczną aplikację internetową w usłudze Azure Static Web Apps przy użyciu interfejsu wiersza polecenia platformy Azure. Teraz, gdy masz podstawową wiedzę na temat wdrażania statycznej aplikacji internetowej, możesz zapoznać się z bardziej zaawansowanymi funkcjami i funkcjami usługi Azure Static Web Apps.

Jeśli chcesz użyć repozytorium szablonów Usługi GitHub, wykonaj poniższe dodatkowe kroki.

Przejdź do https://github.com/login/device strony i wprowadź kod użytkownika 329B-3945, aby aktywować i pobrać osobisty token dostępu usługi GitHub.

1. Przejdź do https://github.com/login/device.
2. Wprowadź kod użytkownika wyświetlany w komunikacie konsoli.
3. Wybierz opcję `Continue`.
4. Wybierz opcję `Authorize AzureAppServiceCLI`.

### Wyświetlanie witryny internetowej za pośrednictwem usługi Git

1. Po otrzymaniu adresu URL repozytorium podczas uruchamiania skryptu skopiuj adres URL repozytorium i wklej go w przeglądarce.
2. Wybierz kartę `Actions`.

   Na tym etapie platforma Azure tworzy zasoby do obsługi statycznej aplikacji internetowej. Poczekaj, aż ikona obok uruchomionego przepływu pracy zmieni się w znacznik wyboru z zielonym tłem ( ). Wykonanie tej operacji może potrwać kilka minut.

3. Po pojawieniu się ikony powodzenia przepływ pracy zostanie ukończony i możesz wrócić do okna konsoli.
4. Uruchom następujące polecenie, aby wykonać zapytanie dotyczące adresu URL witryny internetowej.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. Skopiuj adres URL do przeglądarki, aby przejść do witryny internetowej.
