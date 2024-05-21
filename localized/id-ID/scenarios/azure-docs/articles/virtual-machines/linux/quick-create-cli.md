---
title: 'Mulai cepat: Menggunakan Azure CLI untuk membuat Komputer Virtual Linux'
description: 'Dalam mulai cepat ini, Anda mempelajari cara menggunakan Azure CLI untuk membuat komputer virtual Linux'
author: ju-shim
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 03/11/2024
ms.author: jushiman
ms.custom: 'mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Mulai cepat: Membuat komputer virtual Linux dengan Azure CLI di Azure

**Berlaku untuk:** :heavy_check_mark: VM Linux

[![Sebarkan ke Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262692)

Mulai cepat ini menunjukkan kepada Anda cara menggunakan modul Azure PowerShell untuk menyebarkan komputer virtual Linux (VM) di Azure. Azure CLI digunakan untuk membuat dan mengelola sumber daya Azure melalui baris perintah atau skrip.

Jika Anda tidak memiliki langganan Azure, buat [akun gratis ](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) sebelum Anda memulai.

## Meluncurkan Azure Cloud Shell

Azure Cloud Shell adalah shell interaktif gratis yang dapat Anda gunakan untuk menjalankan langkah-langkah dalam artikel ini. Shell ini memiliki alat Azure umum yang telah dipasang sebelumnya dan dikonfigurasi untuk digunakan dengan akun Anda. 

Untuk membuka Cloud Shell, cukup pilih **Cobalah** dari sudut kanan atas blok kode. Anda juga dapat membuka Cloud Shell di tab browser terpisah dengan membuka [https://shell.azure.com/bash](https://shell.azure.com/bash). Pilih **Salin** untuk menyalin blok kode, tempelkan ke Cloud Shell, lalu pilih **Masukkan** untuk menjalankannya.

Jika Anda lebih suka menginstal dan menggunakan CLI secara lokal, mulai cepat ini memerlukan Azure CLI versi 2.0.30 atau yang lebih baru. Jalankan `az --version` untuk menemukan versinya. Jika Anda perlu memasang atau meningkatkan, lihat [Memasang Azure CLI]( /cli/azure/install-azure-cli).

## Menentukan variabel lingkungan

Langkah pertama adalah menentukan variabel lingkungan. Variabel lingkungan umumnya digunakan di Linux untuk memusatkan data konfigurasi untuk meningkatkan konsistensi dan pemeliharaan sistem. Buat variabel lingkungan berikut untuk menentukan nama sumber daya yang Anda buat nanti dalam tutorial ini:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myVMResourceGroup$RANDOM_ID"
export REGION=EastUS
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_USERNAME=azureuser
export MY_VM_IMAGE="Canonical:0001-com-ubuntu-minimal-jammy:minimal-22_04-lts-gen2:latest"
```

## Masuk ke Azure menggunakan CLI

Untuk menjalankan perintah di Azure menggunakan CLI, Anda perlu masuk terlebih dahulu. Masuk menggunakan `az login` perintah .

## Buat grup sumber daya

Grup sumber daya adalah kontainer untuk sumber daya terkait. Semua sumber daya harus ditempatkan dalam grup sumber daya. [Perintah az group create](/cli/azure/group) membuat grup sumber daya dengan parameter $MY_RESOURCE_GROUP_NAME dan $REGION yang ditentukan sebelumnya.

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

## Membuat komputer virtual

Untuk membuat VM di grup sumber daya ini, gunakan `vm create` perintah . 

Contoh berikut membuat VM dan menambahkan akun pengguna. Parameter `--generate-ssh-keys` menyebabkan CLI mencari kunci ssh yang tersedia di `~/.ssh`. Jika ditemukan, kunci tersebut akan digunakan. Jika tidak, satu dibuat dan disimpan di `~/.ssh`. Parameter `--public-ip-sku Standard` memastikan bahwa komputer dapat diakses melalui alamat IP publik. Terakhir, kami menyebarkan gambar terbaru `Ubuntu 22.04` .

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

Dibutuhkan beberapa menit untuk membuat komputer virtual dan sumber daya pendukung. Contoh output berikut menunjukkan operasi pembuatan komputer virtual berhasil.

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

## Mengaktifkan Masuk Azure AD untuk komputer virtual Linux di Azure

Contoh kode berikut menyebarkan VM Linux lalu menginstal ekstensi untuk mengaktifkan Login Azure AD untuk VM Linux. Ekstensi VM Azure adalah aplikasi kecil yang menyediakan konfigurasi pasca-penyebaran dan tugas otomatisasi pada komputer virtual Azure.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME
```

## Menyimpan alamat IP VM untuk SSH

Jalankan perintah berikut untuk menyimpan alamat IP VM sebagai variabel lingkungan:

```bash
export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)
```

## SSH ke VM

<!--## Export the SSH configuration for use with SSH clients that support OpenSSH & SSH into the VM.
Log in to Azure Linux VMs with Azure AD supports exporting the OpenSSH certificate and configuration. That means you can use any SSH clients that support OpenSSH-based certificates to sign in through Azure AD. The following example exports the configuration for all IP addresses assigned to the VM:-->

<!--
```bash
yes | az ssh config --file ~/.ssh/config --name $MY_VM_NAME --resource-group $MY_RESOURCE_GROUP_NAME
```
-->

Anda sekarang dapat SSH ke VM dengan menjalankan output perintah berikut di klien ssh pilihan Anda:

```bash
ssh -o StrictHostKeyChecking=no $MY_USERNAME@$IP_ADDRESS
```

## Langkah berikutnya

* [Pelajari tentang komputer virtual](../index.yml)
* [Menggunakan Cloud-Init untuk menginisialisasi VM Linux pada boot pertama](tutorial-automate-vm-deployment.md)
* [Membuat gambar VM kustom](tutorial-custom-images.md)
* [Load Balance VM](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
