---
title: Inspektor Gadget を Azure Kubernetes Service クラスターにデプロイする
description: このチュートリアルでは、Inspektor Gadget を AKS クラスターにデプロイする方法を説明します
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# クイック スタート: Inspektor Gadget を Azure Kubernetes Service クラスターにデプロイする

このチュートリアルでは、kubectl プラグイン `gadget` を使って Azure Kubernetes Service (AKS) クラスターに [Inspektor Gadget](https://www.inspektor-gadget.io/) をデプロイする手順を説明します。 このチュートリアルは、既に Azure CLI にログインしており、CLI で使用するサブスクリプションが選択されていることを前提としています。

## 環境変数を定義する

このチュートリアルでは最初に、環境変数を定義します。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## リソース グループの作成

リソース グループとは、関連リソース用のコンテナーです。 すべてのリソースをリソース グループに配置する必要があります。 このチュートリアルに必要なものを作成します。 次のコマンドは、事前定義済みの $MY_RESOURCE_GROUP_NAME パラメーターと $REGION パラメーターを使用してリソース グループを作成します。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myResourceGroup210",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## AKS クラスターを作成

az aks create コマンドを使用して、AKS クラスターを作成します。

この処理には数分かかります。

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## クラスターに接続する

Kubernetes クラスターを管理するには、Kubernetes のコマンドライン クライアントである kubectl を使います。 Azure Cloud Shell を使用している場合、kubectl は既にインストールされています。

1. az aks install-cli コマンドを使用して az aks CLI をローカルにインストールする

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. az aks get-credentials コマンドを使用して、Kubernetes クラスターに接続するように kubectl を構成します。 次のコマンドで、以下を行います。
    - 資格情報をダウンロードし、それを使用するように Kubernetes CLI を構成します。
    - ~/.kube/config (Kubernetes 構成ファイルの既定の場所) を使用します。 Kubernetes 構成ファイルに対して別の場所を指定するには、--file 引数を使用します。

    > [!WARNING]
    > これにより、同じエントリを使用して既存の資格情報が上書きされます

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. kubectl get コマンドを使用して、ご利用のクラスターへの接続を確認します。 このコマンドでは、クラスター ノードの一覧が返されます。

    ```bash
    kubectl get nodes
    ```

## Inspektor Gadget をインストールする

Inspektor Gadget のインストールは、次の 2 つのステップで構成されます。

1. ユーザーのシステムへの kubectl プラグインのインストール。
2. クラスターへの Inspektor Gadget のインストール。

    > [!NOTE]
    > Inspektor Gadget のデプロイと利用には複数の追加メカニズムがあり、それぞれが特定のユース ケースと要件に合わせて調整されています。 `kubectl gadget` プラグインを使うと、それらの多くがカバーされますが、すべてではありません。 たとえば、`kubectl gadget` プラグインでの Inspektor Gadget のデプロイは、Kubernetes API サーバーの可用性に依存します。 そのため、可用性が損なわれる可能性があるために、そのようなコンポーネントに依存できない場合は、`kubectl gadget` のデプロイ メカニズムは使わないことをお勧めします。 それについて行う必要があること、および他のユース ケースについては、[ig のドキュメント](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md)をご覧ください。

### kubectl プラグインのインストール: `gadget`

リリース ページから最新バージョンの kubectl プラグインをインストールし、`kubectl-gadget` 実行可能ファイルを圧縮解除して `$HOME/.local/bin` に移動します。

> [!NOTE]
> [`krew`](https://sigs.k8s.io/krew) を使ってインストールする場合、またはソースからコンパイルする場合は、[kubectl ガジェットのインストール](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget)に関する公式ドキュメントに従って行ってください。

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

次に、`version` コマンドを実行してインストールを検証します。

```bash
kubectl gadget version
```

`version` コマンドでは、クライアント (kubectl ガジェット プラグイン) のバージョンが表示され、それがサーバー (クラスター) にまだインストールされていないことが示されます。

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### クラスターへの Inspektor Gadget のインストール

次のコマンドを実行すると、DaemonSet がデプロイされます。

> [!NOTE]
> 特定のコンテナー イメージの使用や、特定のノードへのデプロイなど、いくつかのオプションを使ってデプロイをカスタマイズできます。 それらのすべてについては、[クラスターへのインストール](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster)に関する公式ドキュメントをご覧ください。

```bash
kubectl gadget deploy
```

次に、もう一度 `version` コマンドを実行してインストールを検証します。

```bash
kubectl gadget version
```

ここまで済むと、クライアントとサーバーが正しくインストールされています。

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

ガジェットの実行を開始できるようになりました。

```bash
kubectl gadget help
```

<!--
## Clean Up

### Undeploy Inspektor Gadget

```bash
kubectl gadget undeploy
```

### Clean up Azure resources

When no longer needed, you can use `az group delete` to remove the resource group, cluster, and all related resources as follows. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

```bash
az group delete --name $MY_RESOURCE_GROUP_NAME --no-wait --yes
```
-->