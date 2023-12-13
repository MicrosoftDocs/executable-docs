---
title: Membuat VM Linux dan SSH Di Azure
description: Tutorial ini menunjukkan cara membuat VM Linux dan SSH Di Azure.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Membuat VM Linux dan SSH Di Azure

[![Sebarkan ke Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateLinuxVMAndSSH)


## Tentukan Variabel Lingkungan

Langkah pertama dalam tutorial ini adalah menentukan variabel lingkungan.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

# Masuk ke Azure menggunakan CLI

Untuk menjalankan perintah terhadap Azure menggunakan CLI, Anda perlu masuk. Ini dilakukan, sangat sederhana, meskipun `az login` perintah:

# Buat grup sumber daya

Grup sumber daya adalah kontainer untuk sumber daya terkait. Semua sumber daya harus ditempatkan dalam grup sumber daya. Kami akan membuatnya untuk tutorial ini. Perintah berikut membuat grup sumber daya dengan parameter $MY_RESOURCE_GROUP_NAME dan $REGION yang ditentukan sebelumnya.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Hasil:

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

## Membuat Komputer Virtual

Untuk membuat VM dalam grup sumber daya ini, kita perlu menjalankan perintah sederhana, di sini kita telah menyediakan `--generate-ssh-keys` bendera, ini akan menyebabkan CLI mencari kunci ssh yang dapat divialkan di `~/.ssh`, jika ditemukan, itu akan digunakan, jika tidak, satu akan dihasilkan dan disimpan di `~/.ssh`. Kami juga menyediakan `--public-ip-sku Standard` bendera untuk memastikan bahwa mesin dapat diakses melalui IP publik. Akhirnya, kami menyebarkan gambar terbaru `Ubuntu 22.04` . 

Semua nilai lain dikonfigurasi menggunakan variabel lingkungan.

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

Hasil:

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

### Mengaktifkan login Azure ACTIVE Directory untuk Komputer Virtual Linux di Azure

Contoh berikut telah menyebarkan VM Linux lalu menginstal ekstensi untuk mengaktifkan login Azure AD untuk VM Linux. Ekstensi VM Azure adalah aplikasi kecil yang menyediakan konfigurasi pasca-penyebaran dan tugas otomatisasi pada komputer virtual Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

# Simpan Alamat IP VM untuk SSH
jalankan perintah berikut untuk mendapatkan Alamat IP VM dan menyimpannya sebagai variabel lingkungan

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

# SSH Ke VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Login to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Anda sekarang dapat SSH ke VM dengan menjalankan output perintah berikut di klien ssh pilihan Anda

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

# Langkah berikutnya

* [Dokumentasi VM](https://learn.microsoft.com/azure/virtual-machines/)
* [Menggunakan Cloud-Init untuk menginisialisasi VM Linux pada boot pertama](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-automate-vm-deployment)
* [Membuat gambar VM kustom](https://learn.microsoft.com/azure/virtual-machines/linux/tutorial-custom-images)
* [Load Balance VM](https://learn.microsoft.com/azure/load-balancer/quickstart-load-balancer-standard-public-cli)
