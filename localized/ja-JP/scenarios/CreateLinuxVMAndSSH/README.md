---
title: Azure で Linux VM と SSH を作成する
description: このチュートリアルでは、Azure で Linux VM と SSH を作成する方法を示します。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Azure で Linux VM と SSH を作成する

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## 環境変数を定義する

このチュートリアルの最初の手順は、環境変数を定義することです。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# CLI を使用して Azure にログインします

CLI を使用して Azure に対してコマンドを実行するには、ログインする必要があります。 これを実行するには、`az login` コマンドを使用するだけです。

# リソース グループの作成

リソース グループとは、関連リソース用のコンテナーです。 すべてのリソースをリソース グループに配置する必要があります。 このチュートリアルに必要なものを作成します。 次のコマンドは、事前定義済みの $MY_RESOURCE_GROUP_NAME パラメーターと $REGION パラメーターを使用してリソース グループを作成します。

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

このリソース グループに VM を作成するために、単純なコマンドを実行する必要があります。ここでは、`--generate-ssh-keys` フラグを指定しています。これにより、CLI は `~/.ssh` で使用可能な ssh キーを検索します。見つかった場合は、それが生成され、見つからない場合は、キーが生成され、`~/.ssh` に格納されます。 また、`--public-ip-sku Standard` フラグを指定して、マシンにパブリック IP 経由でアクセスできるようにします。 最後に、最新の `Ubuntu 22.04` イメージをデプロイします。 

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

### Azure 内の Linux 仮想マシンに対して Azure AD ログインを有効にする

次の例では、Linux VM をデプロイし、拡張機能をインストールして、Linux VM に対して Azure AD ログインを有効にします。 VM 拡張機能は、Azure 仮想マシンでのデプロイ後の構成と自動タスクを提供する小さなアプリケーションです。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# SSH を実行するために VM の IP アドレスを格納する
次のコマンドを実行して VM の IP アドレスを取得し、環境変数として保存します

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# VM に SSH 接続する

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

任意の SSH クライアントで次のコマンドの出力を実行して、VM に SSH 接続できるようになりました。

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# 次のステップ

* [VM のドキュメント](https://learn.microsoft.com/azure/virtual-machines/)
* [最初の起動時に cloud-init を使用して Linux VM を初期化する](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [カスタム VM イメージを作成する](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [VM の負荷分散](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
