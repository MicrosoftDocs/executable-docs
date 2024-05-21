---
title: '빠른 시작: CLI를 사용하여 Azure Static Web Apps를 통해 첫 번째 정적 사이트 빌드'
description: Azure CLI를 사용하여 정적 사이트를 Azure Static Web Apps에 배포하는 방법을 알아봅니다.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# 빠른 시작: Azure CLI를 사용하여 첫 번째 정적 사이트 빌드

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps는 코드 리포지토리에서 앱을 빌드하여 프로덕션 환경에 웹 사이트를 게시합니다.

이 빠른 시작에서는 Azure CLI를 사용하여 웹 애플리케이션을 Azure Static 웹앱에 배포합니다.

## 필수 조건

- [GitHub 계정](https://github.com).
- [Azure](https://portal.azure.com) 계정.
  - Azure 구독이 없는 경우 [무료 평가판 계정을 만들 수 있습니다](https://azure.microsoft.com/free).
- [Azure CLI](/cli/azure/install-azure-cli)가 설치됨(2.29.0 버전 이상)
- [Git 설정](https://www.git-scm.com/downloads) 

## 환경 변수 정의

이 빠른 시작의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## 리포지토리 만들기(선택 사항)

(선택 사항) 이 문서에서는 쉽게 시작할 수 있도록 하는 또 다른 방법으로 GitHub 템플릿 리포지토리를 사용합니다. 이 템플릿에는 Azure Static Web Apps에 배포할 스타터 앱이 있습니다.

1. 다음 위치로 이동하여 새 리포지토리를 만듭니다. https://github.com/staticwebdev/vanilla-basic/generate 
2. 리포지토리 이름을 `my-first-static-web-app`으로 지정합니다.

> [!NOTE]
> Azure Static Web Apps에는 웹앱을 만들기 위한 하나 이상의 HTML 파일이 필요합니다. 이 단계에서 만드는 리포지토리에는 단일 `index.html` 파일이 포함됩니다.

3. **리포지토리 만들기**를 선택합니다.

## 정적 웹앱을 배포합니다.

Azure CLI에서 앱을 정적 웹앱으로 배포합니다.

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

Results:
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

## GitHub 템플릿 사용

Azure CLI를 사용하여 Azure Static Web Apps에 정적 웹앱을 성공적으로 배포했습니다. 이제 정적 웹앱을 배포하는 방법에 대한 기본 사항을 이해했으므로 Azure Static Web Apps의 유용한 기능을 탐색할 수 있습니다.

GitHub 템플릿 리포지토리를 사용하려면 다음 단계를 따릅니다.

https://github.com/login/device로 이동하여 GitHub에서 가져오는 코드를 입력하여 GitHub 개인용 액세스 토큰을 활성화하고 검색합니다.

1. https://github.com/login/device(으)로 이동합니다.
2. 콘솔의 메시지에 표시된 대로 사용자 코드를 입력합니다.
3. `Continue`를 선택합니다.
4. `Authorize AzureAppServiceCLI`를 선택합니다.

### Git을 통해 웹 사이트 보기

1. 스크립트를 실행하는 동안 리포지토리 URL을 가져오면 리포지토리 URL을 복사하여 브라우저에 붙여넣습니다.
2. `Actions` 탭을 선택합니다.

   이 시점에서 Azure는 정적 웹앱을 지원하기 위한 리소스를 만듭니다. 실행 중인 워크플로 옆의 아이콘이 녹색 배경의 확인 표시로 바뀔 때까지 기다립니다. 이 작업을 실행하는 데 몇 분 정도 걸릴 수 있습니다.

3. 성공 아이콘이 표시되면 워크플로가 완료되고 콘솔 창으로 돌아갈 수 있습니다.
4. 다음 명령을 실행하여 웹 사이트의 URL을 쿼리합니다.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. URL을 브라우저에 복사하여 웹 사이트로 이동합니다.

## 리소스 정리(선택 사항)

이 애플리케이션을 계속 사용하지 않으려면 [az group delete](/cli/azure/group#az-group-delete) 명령을 사용하여 리소스 그룹과 정적 웹앱을 삭제합니다.

## 다음 단계

> [!div class="nextstepaction"]
> [API 추가](add-api.md)
