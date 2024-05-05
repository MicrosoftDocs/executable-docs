---
title: 'Hızlı Başlangıç: Red Hat Enterprise Linux Sanal Makinesi oluşturmak için Azure CLI kullanma'
description: Bu hızlı başlangıçta Azure CLI kullanarak Red Hat Enterprise Linux sanal makinesi oluşturmayı öğreneceksiniz
author: namanparikh
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 05/03/2024
ms.author: namanparikh
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Hızlı Başlangıç: Azure'da Azure CLI ile Red Hat Enterprise Linux sanal makinesi oluşturma

**Şunlar için geçerlidir:** :heavy_check_mark: Linux VM'leri

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Bu hızlı başlangıçta, Azure CLI kullanarak Azure'da Red Hat Enterprise Linux sanal makinesi (VM) dağıtma işlemi gösterilmektedir. Azure CLI, komut satırı veya betikler aracılığıyla Azure kaynakları oluşturmak ve yönetmek için kullanılır.

Azure aboneliğiniz yoksa başlamadan önce [ücretsiz bir hesap](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) oluşturun.

## Azure Cloud Shell'i başlatma

Azure Cloud Shell, bu makaledeki adımları çalıştırmak için kullanabileceğiniz ücretsiz bir etkileşimli kabuktur. Yaygın Azure araçları, kabuğa önceden yüklenmiştir ve kabuk, hesabınızla birlikte kullanılacak şekilde yapılandırılmıştır. 

Cloud Shell'i açmak için kod bloğunun sağ üst köşesinden **Deneyin**'i seçmeniz yeterlidir. Cloud Shell'i adresine giderek [https://shell.azure.com/bash](https://shell.azure.com/bash)ayrı bir tarayıcı sekmesinde de açabilirsiniz. Kod bloklarını kopyalamak için Kopyala'yı** seçin**, Cloud Shell'e yapıştırın ve çalıştırmak için Enter tuşuna** basın**.

CLI'yi yerel olarak yükleyip kullanmayı tercih ediyorsanız bu hızlı başlangıç için Azure CLI 2.0.30 veya sonraki bir sürümü gerekir. Sürümü bulmak için `az --version` komutunu çalıştırın. Yüklemeniz veya yükseltmeniz gerekirse, bkz. [Azure CLI yükleme]( /cli/azure/install-azure-cli).

## Ortam değişkenlerini tanımlama

İlk adım, ortam değişkenlerini tanımlamaktır. Ortam değişkenleri, sistemin tutarlılığını ve sürdürülebilirliğini geliştirmek üzere yapılandırma verilerini merkezileştirmek için Linux'ta yaygın olarak kullanılır. Bu öğreticinin ilerleyen bölümlerinde oluşturduğunuz kaynakların adlarını belirtmek için aşağıdaki ortam değişkenlerini oluşturun:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="RedHat:RHEL:8-LVM:latest"
```

## CLI kullanarak Azure'da oturum açma

CLI kullanarak Azure'da komutları çalıştırmak için önce oturum açmanız gerekir. komutunu kullanarak `az login` oturum açın.

## Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. [az group create](/cli/azure/group) komutu, önceden tanımlanmış $MY_RESOURCE_GROUP_NAME ve $REGION parametreleriyle bir kaynak grubu oluşturur.

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

## Sanal makineyi oluşturma

Bu kaynak grubunda vm oluşturmak için komutunu kullanın `vm create` . 

Aşağıdaki örnek bir VM oluşturur ve bir kullanıcı hesabı ekler. parametresi, `--generate-ssh-keys` CLI'nın içinde `~/.ssh`kullanılabilir bir ssh anahtarı aramasına neden olur. Bir anahtar bulunursa, bu anahtar kullanılır. Değilse, bir tane oluşturulur ve içinde `~/.ssh`depolanır. parametresi, `--public-ip-sku Standard` makinenin genel IP adresi üzerinden erişilebilir olmasını sağlar. Son olarak en son `Ubuntu 22.04` görüntüyü dağıtacağız.

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

VM’yi ve destekleyici kaynakları oluşturmak birkaç dakika sürer. Aşağıdaki örnekte VM oluşturma işleminin başarılı olduğu gösterilmektedir.

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

## Azure'da Linux sanal makinesi için Azure AD Oturum Açma özelliğini etkinleştirme

Aşağıdaki kod örneği bir Linux VM dağıtır ve ardından bir Linux VM için Azure AD Oturum Açma özelliğini etkinleştirmek üzere uzantıyı yükler. VM uzantıları, Azure sanal makinelerinde dağıtım sonrası yapılandırma ve otomasyon görevleri sağlayan küçük uygulamalardır.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## SSH için VM'nin IP adresini depolama

VM'nin IP adresini ortam değişkeni olarak depolamak için aşağıdaki komutu çalıştırın:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## VM'de SSH

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Artık SSH istemcinizde aşağıdaki komutun çıkışını çalıştırarak VM'de SSH yapabilirsiniz:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Sonraki Adımlar

* [Sanal makineler hakkında bilgi edinin](../index.yml)
* [Cloud-Init kullanarak ilk önyüklemede Bir Linux VM başlatma](tutorial-automate-vm-deployment.md)
* [Özel VM görüntüleri oluşturma](tutorial-custom-images.md)
* [Vm'lerde Yük Dengeleme](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
