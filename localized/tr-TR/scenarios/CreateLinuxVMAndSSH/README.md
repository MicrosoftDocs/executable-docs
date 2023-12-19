---
title: Azure'da Linux VM ve SSH oluşturma
description: 'Bu öğreticide, Azure''da Linux VM ve SSH oluşturma adımları gösterilmektedir.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Azure'da Linux VM ve SSH oluşturma

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Ortam Değişkenlerini Tanımlama

Bu öğreticinin ilk adımı ortam değişkenlerini tanımlamaktır.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# CLI kullanarak Azure'da oturum açma

CLI kullanarak Azure'da komut çalıştırmak için oturum açmanız gerekir. Bu çok basit bir şekilde yapılır, ancak `az login` komut:

# Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Bu öğretici için bir tane oluşturacağız. Aşağıdaki komut, önceden tanımlanmış $MY_RESOURCE_GROUP_NAME ve $REGION parametreleriyle bir kaynak grubu oluşturur.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Sonuçlar:

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

## Sanal Makine Oluşturma

Bu kaynak grubunda bir VM oluşturmak için basit bir komut çalıştırmamız gerekiyor, burada bayrağını `--generate-ssh-keys` sağladık, bu, CLI'nın içinde bir avialable ssh anahtarı `~/.ssh`aramasına neden olur, eğer biri bulunursa kullanılır, aksi takdirde biri oluşturulur ve içinde `~/.ssh`depolanır. Ayrıca, makinenin genel IP üzerinden erişilebilir olduğundan emin olmak için bayrağını da sağlarız `--public-ip-sku Standard` . Son olarak en son `Ubuntu 22.04` görüntüyü dağıtıyoruz. 

Diğer tüm değerler ortam değişkenleri kullanılarak yapılandırılır.

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

Sonuçlar:

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

### Azure'da Linux Sanal Makinesi için Azure AD oturum açma özelliğini etkinleştirme

Aşağıdaki örnekte bir Linux VM dağıtılır ve ardından Bir Linux VM için Azure AD oturum açma özelliğini etkinleştirmek üzere uzantı yüklenir. VM uzantıları, Azure sanal makinelerinde dağıtım sonrası yapılandırma ve otomasyon görevleri sağlayan küçük uygulamalardır.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# SSH için VM'nin IP Adresini depolama
VM'nin IP Adresini almak ve bir ortam değişkeni olarak depolamak için aşağıdaki komutu çalıştırın

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# VM'ye SSH

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Artık SSH istemcinizde aşağıdaki komutun çıkışını çalıştırarak VM'de SSH yapabilirsiniz

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Sonraki Adımlar

* [VM Belgeleri](https://learn.microsoft.com/azure/virtual-machines/)
* [Cloud-Init kullanarak ilk önyüklemede Bir Linux VM başlatma](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Özel VM görüntüleri oluşturma](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Vm'lerde Yük Dengeleme](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
