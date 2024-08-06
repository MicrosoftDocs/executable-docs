---
title: 快速入门：使用 Azure CLI 创建 Linux 虚拟机
description: 本文快速入门介绍了如何使用 Azure CLI 创建 Linux 虚拟机
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# 快速入门：在 Azure 上使用 Azure CLI 创建 Linux 虚拟机

适用于：:heavy_check_mark: Linux VM****

[![部署到 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

本快速入门介绍了如何使用 Azure CLI 在 Azure 中部署 Linux 虚拟机 (VM)。 Azure CLI 用于从命令行或脚本创建和管理 Azure 资源。

如果没有 Azure 订阅，请在开始之前创建一个[免费帐户](https://azure.microsoft.com/free/?WT.mc_id=A261C142F)。

## 启动 Azure Cloud Shell

Azure Cloud Shell 是免费的交互式 shell，可以使用它运行本文中的步骤。 它预安装有常用 Azure 工具并将其配置与帐户一起使用。 

若要打开 Cloud Shell，只需要从代码块的右上角选择“试一试”。 也可以在单独的浏览器标签页中通过转到 [https://shell.azure.com/bash](https://shell.azure.com/bash) 打开 Cloud Shell。 选择“复制”以复制代码块，将其粘贴到 Cloud Shell 中，然后选择 Enter 来运行它。

如果希望在本地安装并使用 CLI，则本快速入门需要 Azure CLI version 2.0.30 或更高版本。 运行 `az --version` 即可查找版本。 如果需要进行安装或升级，请参阅[安装 Azure CLI]( /cli/azure/install-azure-cli)。

## 使用 CLI 登录到 Azure

要使用 CLI 在 Azure 中运行命令，首先需要登录。 使用 `az login` 命令登录。

## 创建资源组

资源组是相关资源的容器。 所有资源都必须在资源组中部署。 [az group create](/cli/azure/group) 命令创建具有前面定义的 $MY_RESOURCE_GROUP_NAME 和 $REGION 参数的资源组。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

结果：

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

## 创建虚拟机

要在此资源组中创建 VM，请使用 `vm create` 命令。 

以下示例将创建 VM 并添加用户帐户。 `--generate-ssh-keys` 参数会导致 CLI 在 `~/.ssh` 中查找可用的 ssh 密钥。 如果找到一个，则使用此密钥。 否则，将会生成一个密钥并存储在 `~/.ssh` 中。 `--public-ip-sku Standard` 参数可确保能够通过公共 IP 地址访问该计算机。 最后，我们将部署最新的 `Ubuntu 22.04` 映像。

所有其他值都使用环境变量进行配置。

```bash
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image $MY_VM_IMAGE \
    --admin-username $MY_USERNAME \
    --assign-identity \
    --generate-ssh-keys \
    --public-ip-sku Standard
```

创建 VM 和支持资源需要几分钟时间。 以下示例输出表明 VM 创建操作已成功。

结果：
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

## 在 Azure 中为 Linux 虚拟机启用 Azure AD 登录

以下代码示例部署了一台 Linux VM，然后安装扩展以启用适用于 Linux VM 的 Azure AD 登录。 VM 扩展是小型应用程序，可在 Azure 虚拟机上提供部署后配置和自动化任务。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## 存储 VM 的 IP 地址，以通过 SSH 进行连接

运行以下命令以将 VM 的 IP 地址存储为环境变量：

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## 通过 SSH 登录到 VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

现在，可以在所选 SSH 客户端中运行以下命令的输出来通过 SSH 连接到 VM：

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## 后续步骤

* [了解虚拟机](../index.yml)
* [首次启动时使用 Cloud-Init 初始化 Linux VM](tutorial-automate-vm-deployment.md)
* [创建自定义 VM 映像](tutorial-custom-images.md)
* [对 VM 进行负载均衡](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)