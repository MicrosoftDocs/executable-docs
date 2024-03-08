---
title: Создание статического сайта с помощью Azure CLI
description: 'В этом руководстве показано, как создать статический сайт в Azure.'
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# краткое руководство по Статические веб-приложения Azure. Создание первого статического сайта с помощью Azure CLI

Статические веб-приложения Azure публикует веб-сайты в рабочей среде путем создания приложений из репозитория кода. В этом кратком руководстве вы развернете веб-приложение для Статические веб-приложения Azure с помощью Azure CLI.

## Определение переменных среды

Первым шагом в этом руководстве является определение переменных среды.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Создание репозитория (необязательно)

(Необязательно) В этой статье используется репозиторий шаблонов GitHub в качестве другого способа упростить работу. Шаблон содержит начальное приложение для развертывания в Статические веб-приложения Azure.

- Перейдите к следующему расположению, чтобы создать новый репозиторий: https://github.com/staticwebdev/vanilla-basic/generate
- Имя репозитория `my-first-static-web-app`

> **Примечание.** Статические веб-приложения Azure для создания веб-приложения требуется по крайней мере один HTML-файл. Репозиторий, создаваемый на этом шаге, включает один `index.html` файл.

Выберите `Create repository`.

## Развертывание статического веб-приложения

Приложение можно развернуть как статическое веб-приложение из Azure CLI.

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

## Next Steps

Поздравляем! Вы успешно развернули статическое веб-приложение для Статические веб-приложения Azure с помощью Azure CLI. Теперь, когда у вас есть базовое представление о развертывании статического веб-приложения, вы можете изучить более сложные функции и функциональные возможности Статические веб-приложения Azure.

Если вы хотите использовать репозиторий шаблонов GitHub, выполните следующие действия.

https://github.com/login/device Перейдите и введите пользовательский код 329B-3945, чтобы активировать и получить личный маркер доступа GitHub.

1. Переход к https://github.com/login/device.
2. Введите код пользователя, как показано в сообщении в консоли.
3. Выберите `Continue`.
4. Выберите `Authorize AzureAppServiceCLI`.

### Просмотр веб-сайта с помощью Git

1. По мере получения URL-адреса репозитория во время выполнения скрипта скопируйте URL-адрес репозитория и вставьте его в браузер.
2. Выберите вкладку `Actions`.

   На этом этапе Azure создает ресурсы для поддержки статического веб-приложения. Дождитесь, пока значок рядом с запущенным рабочим процессом превращается в проверка метку с зеленым фоном (). Выполнение этой операции может занять несколько минут.

3. Когда появится значок успешного выполнения, рабочий процесс завершится, и вы сможете вернуться в окно консоли.
4. Выполните приведенную ниже команду, чтобы запросить URL-адрес веб-сайта.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. Скопируйте URL-адрес в браузер, чтобы перейти на веб-сайт.
