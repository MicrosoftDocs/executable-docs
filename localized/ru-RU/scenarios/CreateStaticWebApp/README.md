---
title: Краткое руководство. Создание первого статического сайта с помощью Статические веб-приложения Azure с помощью интерфейса командной строки
description: "Узнайте, как развернуть статический сайт в службе \"Статические веб-приложения Azure\" с помощью Azure\_CLI."
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Краткое руководство. Создание первого статического сайта с помощью Azure CLI

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Статические веб-приложения Azure публикует веб-сайты в рабочей среде путем создания приложений из репозитория кода.

В этом кратком руководстве рассказывается о том, как развернуть веб-приложение в службе "Статические веб-приложения Azure" с помощью Azure CLI.

## Необходимые компоненты

- [Учетная запись GitHub](https://github.com) .
- [учетная запись Azure;](https://portal.azure.com)
  - Если у вас нет подписки Azure, можно [создать бесплатную пробную учетную запись](https://azure.microsoft.com/free).
- [Azure CLI](/cli/azure/install-azure-cli) установлен (версия 2.29.0 или более поздней версии).
- [Настройка](https://www.git-scm.com/downloads) Git. 

## Определение переменных среды

Первым шагом в этом кратком руководстве является определение переменных среды.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Создание репозитория (необязательно)

(Необязательно) В этой статье используется репозиторий шаблонов GitHub в качестве другого способа упростить работу. Шаблон содержит начальное приложение для развертывания в Статические веб-приложения Azure.

1. Перейдите к следующему расположению, чтобы создать новый репозиторий: https://github.com/staticwebdev/vanilla-basic/generate
2. Присвойте репозиторию `my-first-static-web-app`имя.

> [!NOTE]
> Для создания веб-приложения Статическим веб-приложениям Azure требуется по крайней мере один HTML-файл. Репозиторий, создаваемый на этом шаге, включает один `index.html` файл.

3. Щелкните **Create repository** (Создать репозиторий).

## Развертывание статического веб-приложения

Разверните приложение как статическое веб-приложение из Azure CLI.

1. Создать группу ресурсов.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Результаты.
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

2. Разверните новое статическое веб-приложение из репозитория.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

При развертывании статического приложения следует учитывать два фактора. Первая операция создает базовые ресурсы Azure, из которых состоит приложение. Второй — это рабочий процесс, который создает и публикует приложение.

Прежде чем перейти на новый статический сайт, сборка развертывания должна сначала завершить работу.

3. Вернитесь в окно консоли и выполните следующую команду, чтобы получить список URL-адреса веб-сайта.

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

Результаты.
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

## Использование шаблона GitHub

Вы успешно развернули статическое веб-приложение для Статические веб-приложения Azure с помощью Azure CLI. Теперь, когда у вас есть базовое представление о развертывании статического веб-приложения, вы можете изучить более сложные функции и функциональные возможности Статические веб-приложения Azure.

Если вы хотите использовать репозиторий шаблонов GitHub, выполните следующие действия.

https://github.com/login/device Перейдите к коду, который вы получаете из GitHub, чтобы активировать и получить личный маркер доступа GitHub.

1. Переход к https://github.com/login/device.
2. Введите код пользователя, как показано в сообщении в консоли.
3. Выберите `Continue`.
4. Выберите `Authorize AzureAppServiceCLI`.

### Просмотр веб-сайта с помощью Git

1. По мере получения URL-адреса репозитория во время выполнения скрипта скопируйте URL-адрес репозитория и вставьте его в браузер.
2. Выберите вкладку `Actions`.

   На этом этапе Azure создает ресурсы для поддержки статического веб-приложения. Дождитесь, пока значок рядом с запущенным рабочим процессом превращается в проверка знак с зеленым фоном. Выполнение этой операции может занять несколько минут.

3. Когда появится значок успешного выполнения, рабочий процесс завершится, и вы сможете вернуться в окно консоли.
4. Выполните приведенную ниже команду, чтобы запросить URL-адрес веб-сайта.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Скопируйте URL-адрес в браузер, чтобы перейти на веб-сайт.

## Очистка ресурсов (необязательно)

Если вы не собираетесь продолжать использовать это приложение, удалите группу ресурсов и статическое веб-приложение с помощью [команды az group delete](/cli/azure/group#az-group-delete) .

## Следующие шаги

> [!div class="nextstepaction"]
> [Добавление API](add-api.md)