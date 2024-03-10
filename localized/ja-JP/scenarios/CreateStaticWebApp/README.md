---
title: Azure CLI を使用して静的サイトを作成する
description: このチュートリアルでは、Azure で静的サイトを作成する方法を示します。
author: namanparikh
ms.author: namanparikh
ms.topic: article
ms.date: 02/06/2024
ms.custom: innovation-engine
ms.service: Azure
---

# Azure Static Web Apps クイック スタート: Azure CLI を使用して静的サイトを初めて構築する

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps は、コード リポジトリからアプリをビルドすることによって、Web サイトを運用環境に発行します。 このクイックスタートでは、Azure CLI を使用して、Web アプリケーションを Azure Static Web Apps にデプロイします。

## 環境変数を定義する

このチュートリアルの最初の手順は、環境変数を定義することです。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## リポジトリを作成する (省略可能)

(省略可能) この記事では、簡単に作業を始められるもう 1 つの方法として、GitHub テンプレート リポジトリを使います。 テンプレートには、Azure Static Web Apps にデプロイするスターター アプリが含まれます。

- 次の場所に移動して、新しいリポジトリを作ります: https://github.com/staticwebdev/vanilla-basic/generate
- リポジトリに `my-first-static-web-app` という名前を付けます

> **注:** Azure Static Web Apps で Web アプリを作成するには、少なくとも 1 つの HTML ファイルが必要です。 このステップで作成するリポジトリには、1 つの `index.html` ファイルが含まれます。

[`Create repository`] を選択します。

## 静的 Web アプリをデプロイする

Azure CLI から静的 Web アプリとしてアプリをデプロイできます。

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

## 次のステップ

お疲れさまでした。 Azure CLI を使って、静的 Web アプリを Azure Static Web Apps に無事にデプロイできました。 静的 Web アプリの基本的なデプロイ方法がわかったので、Azure Static Web Apps のさらに高度な機能を調べることができます。

GitHub テンプレート リポジトリを使いたい場合は、次の追加手順のようにします。

https://github.com/login/device に移動し、ユーザー コード 329B-3945 を入力してアクティブ化し、GitHub の個人用アクセス トークンを取得します。

1. 「 https://github.com/login/device 」を参照してください。
2. コンソールのメッセージに表示されているユーザー コードを入力します。
3. [`Continue`] を選択します。
4. [`Authorize AzureAppServiceCLI`] を選択します。

### Git を介して Web サイトを表示する

1. スクリプトの実行中にリポジトリの URL を取得したら、リポジトリの URL をコピーしてブラウザーに貼り付けます。
2. [`Actions`](アクション) タブを選択します。

   この時点で、静的な Web アプリをサポートするリソースが Azure によって作成されています。 実行中のワークフローの横のアイコンが、緑の背景のチェックマークに変わるまで待ちます ()。 この操作では、実行に数分かかる場合があります。

3. 成功アイコンが表示されたら、ワークフローは完了しており、コンソール ウィンドウに戻ることができます。
4. 次のコマンドを実行して、Web サイトの URL のクエリを実行します。

   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"

5. URL をブラウザーにコピーして Web サイトに移動します。
