---
title: 使用 Azure CLI 建立靜態網站
description: 本教學課程示範如何在 Azure 上建立靜態網站。
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Azure Static Web Apps 快速入門：使用 Azure CLI 建置您的第一個靜態網站

Azure Static Web Apps 會透過從程式代碼存放庫建置應用程式，將網站發佈至生產環境。 在本快速入門中，您會使用 Azure CLI 將 Web 應用程式部署至 Azure Static Web Apps。

## 定義環境變數

本教學課程的第一個步驟是定義環境變數。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## 建立存放庫 （選擇性）

（選擇性）本文使用 GitHub 範本存放庫作為另一種方式，讓您輕鬆開始使用。 此範本包含要部署至 Azure Static Web Apps 的入門應用程式。

- 瀏覽至下列位置以建立新的存放庫： https://github.com/staticwebdev/vanilla-basic/generate
- 為您的存放庫命名 `my-first-static-web-app`

> **注意：** Azure Static Web Apps 需要至少一個 HTML 檔案才能建立 Web 應用程式。 您在此步驟中建立的存放庫包含單 `index.html` 一檔案。

選取 `Create repository`。

## 部署靜態 Web 應用程式

您可以從 Azure CLI 將應用程式部署為靜態 Web 應用程式。

1. 建立資源群組。

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

結果：

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

2. 從您的存放庫部署新的靜態 Web 應用程式。

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

部署靜態應用程式有兩個層面。 第一個作業會建立構成您應用程式的基礎 Azure 資源。 第二個是建置和發佈應用程式的工作流程。

您必須先完成執行部署組建，才能移至新的靜態月臺。

3. 返回主控台視窗，然後執行下列命令以列出網站的URL。

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

結果：

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

## 後續步驟

恭喜！ 您已使用 Azure CLI 成功將靜態 Web 應用程式部署至 Azure Static Web Apps。 既然您已基本瞭解如何部署靜態 Web 應用程式，您可以探索 Azure Static Web Apps 的更進階特性和功能。

如果您想要使用 GitHub 範本存放庫，請遵循下列步驟。

移至 https://github.com/login/device 並輸入用戶代碼 329B-3945 以啟動並擷取您的 GitHub 個人存取令牌。

1. 移至 https://github.com/login/device。
2. 輸入顯示主控台訊息的用戶代碼。
3. 選取 `Continue`。
4. 選取 `Authorize AzureAppServiceCLI`。

### 透過 Git 檢視網站

1. 當您在執行文稿時取得存放庫 URL 時，請複製存放庫 URL 並將它貼到瀏覽器中。
2. 選取 [`Actions`] 索引標籤。

   此時，Azure 會建立資源以支援靜態 Web 應用程式。 等到執行中工作流程旁的圖示變成具有綠色背景的複選標記 （）。 此作業可能需要幾分鐘的時間才能執行。

3. 成功圖示出現之後，工作流程就會完成，而且您可以返回控制台視窗。
4. 執行下列命令來查詢網站的 URL。

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query “defaultHostname”

5. 將 URL 複製到瀏覽器以移至您的網站。
