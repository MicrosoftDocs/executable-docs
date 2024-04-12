---
title: 'クイックスタート: CLI を使用して Azure Static Web Apps で最初の静的サイトを構築する'
description: Azure CLI を使用して、静的サイトを Azure Static Web Apps にデプロイする方法について説明します。
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# クイックスタート: Azure CLI を使用して最初の静的サイトを構築する

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps は、コード リポジトリからアプリをビルドすることによって、Web サイトを運用環境に発行します。

このクイックスタートでは、Azure CLI を使用して、Web アプリケーションを Azure Static Web Apps にデプロイします。

## 前提条件

- [GitHub](https://github.com) アカウント。
- [Azure](https://portal.azure.com) アカウント。
  - Azure サブスクリプションがない場合、[無料試用版アカウントを作成](https://azure.microsoft.com/free)できます。
- [Azure CLI](/cli/azure/install-azure-cli) のインストール (バージョン 2.29.0 以上)。
- [Git のセットアップ](https://www.git-scm.com/downloads)。 

## 環境変数を定義する

このクイックスタートの最初の手順は、環境変数を定義することです。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## リポジトリを作成する (省略可能)

(省略可能) この記事では、簡単に作業を始められるもう 1 つの方法として、GitHub テンプレート リポジトリを使います。 テンプレートには、Azure Static Web Apps にデプロイするスターター アプリが含まれます。

1. 次の場所に移動して、新しいリポジトリを作成します: https://github.com/staticwebdev/vanilla-basic/generate。
2. リポジトリに `my-first-static-web-app` という名前を付けます。

> [!NOTE]
> Azure Static Web Apps で Web アプリを作成するには、少なくとも 1 つの HTML ファイルが必要です。 このステップで作成するリポジトリには、1 つの `index.html` ファイルが含まれます。

3. **[Create repository]** (リポジトリの作成) を選択します。

## 静的 Web アプリをデプロイする

Azure CLI から静的 Web アプリとしてアプリをデプロイします。

1. リソース グループを作成する。

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

結果:
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

2. リポジトリから新しい静的 Web アプリをデプロイします。

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

静的アプリのデプロイには 2 つの側面があります。 最初の操作で、アプリを構成する基になる Azure リソースを作成します。 次は、アプリケーションをビルドして発行するワークフローです。

新しい静的サイトに移動する前にまず、デプロイ ビルドの実行が完了している必要があります。

3. コンソール ウィンドウに戻り、次のコマンドを実行して、Web サイトの URL の一覧を取得します。

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

結果:
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

## GitHub テンプレートを使う

Azure CLI を使って、静的 Web アプリを Azure Static Web Apps に無事にデプロイできました。 静的 Web アプリの基本的なデプロイ方法がわかったので、Azure Static Web Apps のさらに高度な機能を調べることができます。

GitHub テンプレート リポジトリを使う場合は、次の手順に従います。

https://github.com/login/device に移動し、GitHub から取得したコードを入力してアクティブ化し、GitHub の個人用アクセス トークンを取得します。

1. 「 https://github.com/login/device 」を参照してください。
2. コンソールのメッセージに表示されているユーザー コードを入力します。
3. [`Continue`] を選択します。
4. [`Authorize AzureAppServiceCLI`] を選択します。

### Git を介して Web サイトを表示する

1. スクリプトの実行中にリポジトリの URL を取得したら、リポジトリの URL をコピーしてブラウザーに貼り付けます。
2. [`Actions`](アクション) タブを選択します。

   この時点で、静的な Web アプリをサポートするリソースが Azure によって作成されています。 実行中のワークフローの横のアイコンが、緑の背景のチェックマークに変わるまで待ちます。 この操作では、実行に数分かかる場合があります。

3. 成功アイコンが表示されたら、ワークフローは完了しており、コンソール ウィンドウに戻ることができます。
4. 次のコマンドを実行して、Web サイトの URL のクエリを実行します。
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. URL をブラウザーにコピーして Web サイトに移動します。

## リソースをクリーンアップする (省略可能)

このアプリケーションを引き続き使用しない場合は、[az group delete](/cli/azure/group#az-group-delete) コマンドを使ってリソース グループと静的 Web アプリを削除します。

## 次のステップ

> [!div class="nextstepaction"]
> [API を追加する](add-api.md)