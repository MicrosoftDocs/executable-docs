---
title: 'クイック スタート: Azure CLI を使用して Linux 仮想マシンを作成する'
description: このクイック スタートでは、Azure CLI を使用して Linux 仮想マシンを作成する方法について説明します。
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# クイック スタート: Azure で Azure CLI を使用して Linux 仮想マシンを作成する

**適用対象:** :heavy_check_mark: Linux VM

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

このクイック スタートでは、Azure CLI を使用して、Linux 仮想マシン (VM) を Azure にデプロイする方法を示します。 Azure CLI は、コマンド ラインまたはスクリプトで Azure リソースを作成および管理するために使用します。

Azure サブスクリプションをお持ちでない場合は、開始する前に [無料アカウント](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) を作成してください。

## Azure Cloud Shell を起動する

Azure Cloud Shell は無料のインタラクティブ シェルです。この記事の手順は、Azure Cloud Shell を使って実行することができます。 一般的な Azure ツールが事前にインストールされており、アカウントで使用できるように構成されています。 

Cloud Shell を開くには、コード ブロックの右上隅にある **[使ってみる]** を選択します。 [https://shell.azure.com/bash](https://shell.azure.com/bash) に移動して、別のブラウザー タブで Cloud Shell を開くこともできます。 **[コピー]** を選択してコードのブロックをコピーし、Cloud Shell に貼り付けてから、 **[入力]** を選択して実行します。

CLI をローカルにインストールして使用する場合、このクイック スタートでは、Azure CLI バージョン 2.0.30 以降が必要です。 バージョンを確認するには、`az --version` を実行します。 インストールまたはアップグレードする必要がある場合は、[Azure CLI のインストール]( /cli/azure/install-azure-cli)に関するページを参照してください。

## 環境変数を定義する

最初のステップは、環境変数を定義することです。 Linux で環境変数は通常、構成データを一元化してシステムの一貫性と保守容易性を向上させるために使用します。 このチュートリアルで後ほど作成するリソースの名前を指定するための、次の環境変数を作成します。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## CLI を使用して Azure にログインする

CLI を使用して Azure でコマンドを実行するには、まず、ログインする必要があります。 `az login` コマンドを使ってログインします。

## リソース グループを作成する

リソース グループとは、関連リソース用のコンテナーです。 すべてのリソースをリソース グループに配置する必要があります。 [az group create](/cli/azure/group) コマンドは、前に定義した $MY_RESOURCE_GROUP_NAME と $REGION パラメーターを使ってリソース グループを作成します。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果:

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myVMResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## 仮想マシンの作成

このリソース グループに VM を作成するには、`vm create` コマンドを使います。 

次の例では、VM を作成し、ユーザー アカウントを追加します。 `--generate-ssh-keys` パラメーターを指定すると、CLI は `~/.ssh` で使用可能な SSH キーを検索します。 見つかった場合は、そのキーが使われます。 見つからない場合は、キーが生成され、`~/.ssh` に格納されます。 `--public-ip-sku Standard` パラメーターを指定すると、パブリック IP アドレスを介してマシンに確実にアクセスできます。 最後に、最新の `Ubuntu 22.04` イメージをデプロイします。

その他のすべての値は、環境変数を使用して構成されます。

```bash
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

VM とサポートするリソースを作成するには数分かかります。 次の出力例では、成功した VM 作成操作を示します。

結果:
<!-- expected_similarity=0.3 -->
```json
{
  "fqdns": "",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myVMResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
  "location": "eastus",
  "macAddress": "00-0D-3A-10-4F-70",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.147.208.85",
  "resourceGroup": "myVMResourceGroup",
  "zones": ""
}
```

## Azure 内の Linux 仮想マシンに対して Azure AD ログインを有効にする

次のコード例では、Linux VM をデプロイし、拡張機能をインストールして、Linux VM に対して Azure AD ログインを有効にします。 VM 拡張機能は、Azure 仮想マシンでのデプロイ後の構成と自動タスクを提供する小さなアプリケーションです。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## SSH を実行するために VM の IP アドレスを格納する

次のコマンドを実行し、VM の IP アドレスを環境変数として格納します。

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## VM に SSH 接続します

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

任意の SSH クライアントで次のコマンドの出力を実行して、VM に SSH 接続できるようになりました。

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## 次のステップ

* [仮想マシンについて](../index.yml)
* [最初の起動時に cloud-init を使用して Linux VM を初期化する](tutorial-automate-vm-deployment.md)
* [カスタム VM イメージを作成する](tutorial-custom-images.md)
* [VM の負荷分散](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)