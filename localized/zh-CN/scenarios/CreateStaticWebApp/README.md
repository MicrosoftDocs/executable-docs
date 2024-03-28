---
title: 使用 Azure CLI 创建静态站点
description: 本教程介绍如何在 Azure 上创建静态站点。
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Azure Static Web Apps 快速入门：使用 Azure CLI 生成你的第一个静态站点

[![部署到 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps 通过从代码存储库生成应用来将网站发布到生产环境。 在此快速入门中，你会使用 Azure CLI 将 Web 应用部署到 Azure Static Web Apps。

## 定义环境变量

本教程的第一步是定义环境变量。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## 创建存储库（可选）

（可选）本文使用 GitHub 模板存储库作为另一种方法，使你能够轻松入门。 该模板具有一个部署到 Azure Static Web Apps 的入门应用。

- 导航到以下位置以创建新存储库：https://github.com/staticwebdev/vanilla-basic/generate
- 将存储库命名为 `my-first-static-web-app`

> **注意：** Azure Static Web Apps 需要至少一个 HTML 文件来创建 Web 应用。 在此步骤中创建的存储库包括单个 `index.html` 文件。

选择 `Create repository`。

## 部署静态 Web 应用

可以从 Azure CLI 将应用部署为静态 Web 应用。

1. 创建资源组。

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

结果：

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

2. 从存储库部署新的静态 Web 应用。

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

通过两个方面来部署静态应用。 第一个操作创建构成应用的基础 Azure 资源。 第二是生成和发布应用程序的工作流。

在转到新静态站点之前，必须先完成部署生成的运行。

3. 返回控制台窗口，并运行以下命令以列出网站 URL。

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

结果：

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

## 后续步骤

祝贺你！ 已使用 Azure CLI 成功将静态 Web 应用部署到 Azure Static Web Apps。 了解如何部署静态 Web 应用后，可以探索 Azure Static Web Apps 的更高级的特性和功能。

若要使用 GitHub 模板存储库，请按照下面的其他步骤操作。

转到 https://github.com/login/device，输入用户代码 329B-3945 以激活和检索你的 GitHub 个人访问令牌。

1. 转到  https://github.com/login/device 。
2. 输入控制台消息中显示的用户代码。
3. 选择 `Continue`。
4. 选择 `Authorize AzureAppServiceCLI`。

### 通过 Git 查看网站

1. 运行脚本的同时获取存储库 URL 时，请复制存储库 URL，并将其粘贴到浏览器中。
2. 选择“`Actions`”选项卡。

   此时，Azure 正在创建资源以支持你的静态 Web 应用。 等待正在运行的工作流旁边的图标变成带有绿色背景的勾选标记 ()。 此操作可能需要几分钟才能完成执行。

3. 出现成功图标即表示工作流已完成，你可以返回控制台窗口。
4. 运行以下命令以查询网站的 URL。

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. 将该 URL 复制到浏览器中并转到网站。
