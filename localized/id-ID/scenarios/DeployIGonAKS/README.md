---
title: Menyebarkan Inspektor Gadget di kluster Azure Kubernetes Service
description: Tutorial ini menunjukkan cara menyebarkan Inspektor Gadget dalam kluster AKS
author: josebl
ms.author: josebl
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Mulai Cepat: Menyebarkan Inspektor Gadget di kluster Azure Kubernetes Service

Selamat datang di tutorial ini di mana kami akan membawa Anda selangkah demi selangkah dalam menyebarkan [Inspektor Gadget](https://www.inspektor-gadget.io/) di kluster Azure Kubernetes Service (AKS) dengan plugin kubectl: `gadget`. Tutorial ini mengasumsikan Anda sudah masuk ke Azure CLI dan telah memilih langganan untuk digunakan dengan CLI.

## Tentukan Variabel Lingkungan

Langkah pertama dalam tutorial ini adalah menentukan variabel lingkungan:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
```

## Buat grup sumber daya

Grup sumber daya adalah kontainer untuk sumber daya terkait. Semua sumber daya harus ditempatkan dalam grup sumber daya. Kami akan membuatnya untuk tutorial ini. Perintah berikut membuat grup sumber daya dengan parameter $MY_RESOURCE_GROUP_NAME dan $REGION yang ditentukan sebelumnya.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Hasil:

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

## Buat Kluster AKS

Buat kluster AKS menggunakan perintahaz.aks.create.

Ini akan memakan waktu beberapa menit untuk menyelesaikannya.

```bash
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --location $REGION \
  --no-ssh-key
```

## Menyambungkan ke kluster

Untuk mengelola kluster Kube, gunakan klien baris perintah Kube, kubectl. kubectl sudah diinstal jika Anda menggunakan Azure Cloud Shell.

1. Instal az aks CLI secara lokal menggunakan perintah az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Konfigurasikan kubectl untuk terhubung ke kluster Kubernetes Anda menggunakan perintah az aks get-credentials. Jalankan perintah berikut:
    - Unduh informasi masuk dan konfigurasikan Kube CLI untuk menggunakannya.
    - Menggunakan ~/.kube/config, lokasi default untuk file konfigurasi Kubernetes. Tentukan lokasi berbeda untuk file konfigurasi Kubernetes Anda menggunakan argumen --file.

    > [!WARNING]
    > Ini akan menimpa kredensial yang ada dengan entri yang sama

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Verifikasi koneksi ke kluster menggunakan perintah kubectl get. Perintah ini menampilkan daftar node kluster.

    ```bash
    kubectl get nodes
    ```

## Pasang Gadget Inspektor

Penginstalan Inspektor Gadget terdiri dari dua langkah:

1. Menginstal plugin kubectl di sistem pengguna.
2. Menginstal Inspektor Gadget di kluster.

    > [!NOTE]
    > Ada mekanisme tambahan untuk menyebarkan dan menggunakan Inspektor Gadget, masing-masing disesuaikan dengan kasus dan persyaratan penggunaan tertentu. `kubectl gadget` Menggunakan plugin mencakup banyak dari mereka, tetapi tidak semua. Misalnya, menyebarkan Inspektor Gadget dengan `kubectl gadget` plugin tergantung pada ketersediaan server API Kubernetes. Jadi, jika Anda tidak dapat bergantung pada komponen seperti itu karena ketersediaannya kadang-kadang dapat disusupi, maka disarankan untuk tidak menggunakan `kubectl gadget`mekanisme penyebaran. Silakan periksa [dokumentasi](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/ig.md) ig untuk mengetahui apa yang harus dilakukan dalam hal itu, dan kasus penggunaan lainnya.

### Menginstal plugin kubectl: `gadget`

Instal versi terbaru plugin kubectl dari halaman rilis, uncompress dan pindahkan `kubectl-gadget` executable ke `$HOME/.local/bin`:

> [!NOTE]
> Jika Anda ingin menginstalnya menggunakan [`krew`](https://sigs.k8s.io/krew) atau mengkompilasinya dari sumber, ikuti dokumentasi resmi: [menginstal gadget](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-kubectl-gadget) kubectl.

```bash
IG_VERSION=$(curl -s https://api.github.com/repos/inspektor-gadget/inspektor-gadget/releases/latest | jq -r .tag_name)
IG_ARCH=amd64
mkdir -p $HOME/.local/bin
export PATH=$PATH:$HOME/.local/bin
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/download/${IG_VERSION}/kubectl-gadget-linux-${IG_ARCH}-${IG_VERSION}.tar.gz  | tar -C $HOME/.local/bin -xzf - kubectl-gadget
```

Sekarang, mari kita verifikasi penginstalan dengan menjalankan `version` perintah:

```bash
kubectl gadget version
```

Perintah `version` akan menampilkan versi klien (plugin gadget kubectl) dan menunjukkan bahwa itu belum diinstal di server (kluster):

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: not installed$"-->
```text
Client version: vX.Y.Z
Server version: not installed
```

### Menginstal Inspektor Gadget di kluster

Perintah berikut akan menyebarkan DaemonSet:

> [!NOTE]
> Beberapa opsi tersedia untuk menyesuaikan penyebaran: gunakan gambar kontainer tertentu, sebarkan ke simpul tertentu, dan banyak lainnya. Untuk mengetahui semuanya, silakan periksa dokumentasi resmi: [menginstal di kluster](https://github.com/inspektor-gadget/inspektor-gadget/blob/main/docs/install.md#installing-in-the-cluster).

```bash
kubectl gadget deploy
```

Sekarang, mari kita verifikasi penginstalan dengan menjalankan `version` perintah lagi:

```bash
kubectl gadget version
```

Kali ini, klien dan server akan diinstal dengan benar:

<!--expected_similarity="(?m)^Client version: v\d+\.\d+\.\d+$\n^Server version: v\d+\.\d+\.\d+$"-->
```text
Client version: vX.Y.Z
Server version: vX.Y.Z
```

Anda sekarang dapat mulai menjalankan gadget:

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