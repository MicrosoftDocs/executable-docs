---
title: 在 Azure 上建立 Linux VM 和 SSH
description: 本教學課程示範如何在 Azure 上建立 Linux VM 和 SSH。
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# 在 Azure 上建立 Linux VM 和 SSH

[![部署至 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)


## 定義環境變數

本教學課程的第一個步驟是定義環境變數。

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# 使用 CLI 登入 Azure

若要使用 CLI 對 Azure 執行命令，您需要登入。 這樣做很簡單，但 `az login` 命令如下：

# 建立資源群組

資源群組是相關資源的容器。 所有資源都必須放在資源群組中。 我們將為此教學課程建立一個。 下列命令會使用先前定義的 $MY_RESOURCE_GROUP_NAME 和 $REGION 參數來建立資源群組。

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果：

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

## 建立虛擬機

若要在此資源群組中建立 VM，我們需要執行簡單的命令，我們在這裡提供了 `--generate-ssh-keys` 旗標，這會導致 CLI 在 中尋找可取得的 SSH 金鑰，如果找到該密鑰，則會使用其中一個，否則會產生一個並 `~/.ssh`儲存在 中 `~/.ssh`。 我們也提供 `--public-ip-sku Standard` 旗標，以確保計算機可透過公用IP存取。 最後，我們會部署最新的 `Ubuntu 22.04` 映像。 

所有其他值都是使用環境變數來設定。

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

結果：

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

### 在 Azure 中啟用 Linux 虛擬機的 Azure AD 登入

下列範例會部署Linux VM，然後安裝擴充功能以啟用Linux VM的 Azure AD 登入。 VM 擴充功能是小型應用程式，可在 Azure 虛擬機上提供部署後設定和自動化工作。

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# 將 VM 的 IP 位址儲存至 SSH
執行下列命令以取得 VM 的 IP 位址，並將其儲存為環境變數

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# 透過 SSH 連線到 VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

您現在可以在您選擇的 SSH 用戶端中執行下列命令的輸出，以 SSH 連線到 VM

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# 後續步驟

* [VM 檔](https://learn.microsoft.com/azure/virtual-machines/)
* [使用 Cloud-Init 在第一次開機時初始化 Linux VM](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [建立自訂的 VM 映像](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [負載平衡 VM](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
