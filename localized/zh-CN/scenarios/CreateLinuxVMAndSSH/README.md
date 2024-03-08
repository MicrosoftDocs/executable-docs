---
title: 在 Azure 上创建 Linux VM 和 SSH
description: 本教程介绍如何在 Azure 上创建 Linux VM 和 SSH。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# 在 Azure 上创建 Linux VM 和 SSH

[![部署到 Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## 定义环境变量

本教程的第一步是定义环境变量。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# 使用 CLI 登录到 Azure

若要使用 CLI 对 Azure 运行命令，需要登录。 可通过 `az login` 命令非常简单地完成此操作：

# 创建资源组

资源组是相关资源的容器。 所有资源都必须在资源组中部署。 我们将为本教程创建一个资源组。 以下命令创建具有前面定义的 $MY_RESOURCE_GROUP_NAME 和 $REGION 参数的资源组。

```bash
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

若要在此资源组中创建 VM，我们需要运行一个简单的命令，此处我们提供了 `--generate-ssh-keys` 标志，这将导致 CLI 在 `~/.ssh` 中查找一个可用的 ssh 密钥，如果找到，则使用该密钥，否则会生成一个密钥并将其存储在 `~/.ssh` 中。 我们还提供 `--public-ip-sku Standard` 标志，以确保计算机可通过公共 IP 访问。 最后，我们将部署最新的 `Ubuntu 22.04` 映像。 

所有其他值都使用环境变量进行配置。

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

### 在 Azure 中为 Linux 虚拟机启用 Azure AD 登录

以下示例部署一个 Linux VM，然后安装该扩展以启用适用于 Linux VM 的 Azure AD 登录。 VM 扩展是小型应用程序，可在 Azure 虚拟机上提供部署后配置和自动化任务。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# 存储 VM 的 IP 地址，以便通过 SSH 进行连接
运行以下命令以获取 VM 的 IP 地址，并将其存储为环境变量

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# 通过 SSH 连接到 VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

现在，可以通过在所选 SSH 客户端中运行以下命令的输出来通过 SSH 连接到 VM

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# 后续步骤

* [VM 文档](https://learn.microsoft.com/azure/virtual-machines/)
* [首次启动时使用 Cloud-Init 初始化 Linux VM](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [创建自定义 VM 映像](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [对 VM 进行负载均衡](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
