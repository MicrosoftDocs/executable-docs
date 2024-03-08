---
title: Azure CLI를 사용하여 정적 사이트 만들기
description: 이 자습서에서는 Azure에서 정적 사이트를 만드는 방법을 보여줍니다.
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Azure Static Web Apps 빠른 시작: Azure CLI를 사용하여 첫 번째 정적 사이트 빌드

Azure Static Web Apps는 코드 리포지토리에서 앱을 빌드하여 프로덕션 환경에 웹 사이트를 게시합니다. 이 빠른 시작에서는 Azure CLI를 사용하여 Azure Static Web Apps에 웹 애플리케이션을 배포합니다.

## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## 리포지토리 만들기(선택 사항)

(선택 사항) 이 문서에서는 GitHub 템플릿 리포지토리를 다른 방법으로 사용하여 쉽게 시작할 수 있습니다. 이 템플릿에는 Azure Static Web Apps에 배포할 스타터 앱이 있습니다.

- 다음 위치로 이동하여 새 리포지토리를 만듭니다. https://github.com/staticwebdev/vanilla-basic/generate 
- 리포지토리 이름 지정 `my-first-static-web-app`

> **참고:** 웹앱을 만들려면 Azure Static Web Apps에 하나 이상의 HTML 파일이 필요합니다. 이 단계에서 만드는 리포지토리에는 단일 `index.html` 파일이 포함됩니다.

`Create repository`를 선택합니다.

## 정적 웹앱 배포

Azure CLI에서 정적 웹앱으로 앱을 배포할 수 있습니다.

1. 리소스 그룹을 만듭니다.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Results:

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

2. 리포지토리에서 새 정적 웹앱을 배포합니다.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

정적 앱을 배포하는 데는 두 가지 측면이 있습니다. 첫 번째 작업은 앱을 구성하는 기본 Azure 리소스를 만듭니다. 두 번째는 애플리케이션을 빌드하고 게시하는 워크플로입니다.

새 정적 사이트로 이동하려면 먼저 배포 빌드가 실행을 완료해야 합니다.

3. 콘솔 창으로 돌아가서 다음 명령을 실행하여 웹 사이트의 URL을 나열합니다.

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

결과:

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

## 다음 단계

축하합니다! Azure CLI를 사용하여 정적 웹앱을 Azure Static Web Apps에 성공적으로 배포했습니다. 이제 정적 웹앱을 배포하는 방법을 기본적으로 이해했으므로 Azure Static Web Apps의 고급 기능과 기능을 살펴볼 수 있습니다.

GitHub 템플릿 리포지토리를 사용하려는 경우 아래의 추가 단계를 수행합니다.

https://github.com/login/device로 이동해 사용자 코드 329B-3945를 입력하여 GitHub 개인용 액세스 토큰을 활성화하고 검색합니다.

1. https://github.com/login/device(으)로 이동합니다.
2. 콘솔의 메시지에 표시된 대로 사용자 코드를 입력합니다.
3. `Continue`를 선택합니다.
4. `Authorize AzureAppServiceCLI`를 선택합니다.

### Git을 통해 웹 사이트 보기

1. 스크립트를 실행하는 동안 리포지토리 URL을 가져올 때 리포지토리 URL을 복사하여 브라우저에 붙여넣습니다.
2. `Actions` 탭을 선택합니다.

   이 시점에서 Azure는 정적 웹앱을 지원하기 위한 리소스를 만듭니다. 실행 중인 워크플로 옆의 아이콘이 녹색 배경()의 확인 표시로 바뀔 때까지 기다립니다. 이 작업을 실행하는 데 몇 분 정도 걸릴 수 있습니다.

3. 성공 아이콘이 표시되면 워크플로가 완료되고 콘솔 창으로 돌아갈 수 있습니다.
4. 다음 명령을 실행하여 웹 사이트의 URL을 쿼리합니다.

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. URL을 브라우저에 복사하여 웹 사이트로 이동합니다.
