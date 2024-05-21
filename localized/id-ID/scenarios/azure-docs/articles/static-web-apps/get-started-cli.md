---
title: 'Mulai Cepat: Membangun aplikasi web statis pertama Anda dengan Azure Static Web Apps menggunakan CLI'
description: Pelajari cara menyebarkan situs statis ke Azure Static Web Apps dengan Azure CLI.
services: static-web-apps
author: craigshoemaker
ms.service: static-web-apps
ms.topic: quickstart
ms.date: 03/21/2024
ms.author: cshoe
ms.custom: 'mode-api, devx-track-azurecli, innovation-engine, linux-related-content'
ms.devlang: azurecli
---

# Mulai cepat: Membangun situs statis pertama Anda menggunakan Azure CLI

[![Sebarkan ke Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262845)

Azure Static Web Apps menerbitkan situs web ke produksi dengan membangun aplikasi dari repositori kode.

Dalam mulai cepat ini, Anda akan menyebarkan aplikasi web ke Azure Static Web Apps menggunakan Azure CLI.

## Prasyarat

- [Akun GitHub](https://github.com) .
- [Akun Azure](https://portal.azure.com) .
  - Jika Anda tidak memiliki langganan Azure, Anda dapat [membuat akun](https://azure.microsoft.com/free) uji coba gratis.
- [Azure CLI](/cli/azure/install-azure-cli) terinstal (versi 2.29.0 atau lebih tinggi).
- [Penyiapan](https://www.git-scm.com/downloads) Git. 

## Menentukan variabel lingkungan

Langkah pertama dalam mulai cepat ini adalah menentukan variabel lingkungan.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myStaticWebAppResourceGroup$RANDOM_ID"
export REGION=EastUS2
export MY_STATIC_WEB_APP_NAME="myStaticWebApp$RANDOM_ID"
```

## Membuat repositori (opsional)

(Opsional) Artikel ini menggunakan repositori templat GitHub sebagai cara lain untuk memudahkan Anda memulai. Templat ini menampilkan aplikasi pemula untuk disebarkan ke Azure Static Web Apps.

1. Navigasi ke lokasi berikut untuk membuat repositori baru: https://github.com/staticwebdev/vanilla-basic/generate.
2. Beri nama repositori `my-first-static-web-app`Anda .

> [!NOTE]
> Azure Static Web Apps memerlukan setidaknya satu file HTML untuk membuat aplikasi web. Repositori yang Anda buat dalam langkah ini menyertakan satu `index.html` file.

3. Pilih **Buat repositori**.

## Menyebarkan Aplikasi Web Statis

Sebarkan aplikasi sebagai aplikasi web statis dari Azure CLI.

1. Buat grup sumber daya.

```bash
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Hasil:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/my-swa-group",
  "location": "eastus2",
  "managedBy": null,
  "name": "my-swa-group",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

2. Sebarkan aplikasi web statis baru dari repositori Anda.

```bash
az staticwebapp create \
    --name $MY_STATIC_WEB_APP_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION 
```

Ada dua aspek untuk menyebarkan aplikasi statik. Operasi pertama membuat sumber daya Azure yang mendasar yang membentuk aplikasi Anda. Yang kedua adalah alur kerja yang membangun dan menerbitkan aplikasi Anda.

Sebelum Anda dapat membuka situs statis baru Anda, build penyebaran harus terlebih dahulu selesai berjalan.

3. Kembali ke jendela konsol Anda dan jalankan perintah berikut untuk mencantumkan URL situs web.

```bash
export MY_STATIC_WEB_APP_URL=$(az staticwebapp show --name  $MY_STATIC_WEB_APP_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "defaultHostname" -o tsv)
```

```bash
runtime="1 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
    if curl -I -s $MY_STATIC_WEB_APP_URL > /dev/null ; then 
        curl -L -s $MY_STATIC_WEB_APP_URL 2> /dev/null | head -n 9
        break
    else 
        sleep 10
    fi;
done
```

Hasil:
<!-- expected_similarity=0.3 -->
```HTML
<!DOCTYPE html>
<html lang=en>
<head>
<meta charset=utf-8 />
<meta name=viewport content="width=device-width, initial-scale=1.0" />
<meta http-equiv=X-UA-Compatible content="IE=edge" />
<title>Azure Static Web Apps - Welcome</title>
<link rel="shortcut icon" href=https://appservice.azureedge.net/images/static-apps/v3/favicon.svg type=image/x-icon />
<link rel=stylesheet href=https://ajax.aspnetcdn.com/ajax/bootstrap/4.1.1/css/bootstrap.min.css crossorigin=anonymous />
```

```bash
echo "You can now visit your web server at https://$MY_STATIC_WEB_APP_URL"
```

## Menggunakan templat GitHub

Anda berhasil menyebarkan aplikasi web statis ke Azure Static Web Apps menggunakan Azure CLI. Sekarang setelah Anda memiliki pemahaman dasar tentang cara menyebarkan aplikasi web statis, Anda dapat menjelajahi fitur dan fungsionalitas Azure Static Web Apps yang lebih canggih.

Jika Anda ingin menggunakan repositori templat GitHub, ikuti langkah-langkah berikut:

https://github.com/login/device Buka dan masukkan kode yang Anda dapatkan dari GitHub untuk mengaktifkan dan mengambil token akses pribadi GitHub Anda.

1. Buka https://github.com/login/device.
2. Masukkan kode pengguna seperti yang ditampilkan pesan konsol Anda.
3. Pilih `Continue`.
4. Pilih `Authorize AzureAppServiceCLI`.

### Lihat Situs Web melalui Git

1. Saat Anda mendapatkan URL repositori saat menjalankan skrip, salin URL repositori dan tempelkan ke browser Anda.
2. Pilih tab `Actions`.

   Pada titik ini, Azure membuat sumber daya untuk mendukung aplikasi web statis Anda. Tunggu hingga ikon di samping alur kerja yang sedang berjalan berubah menjadi tanda centang dengan latar belakang hijau. Operasi ini mungkin perlu waktu beberapa menit untuk dijalankan.

3. Setelah ikon berhasil muncul, alur kerja selesai dan Anda dapat kembali ke jendela konsol Anda.
4. Jalankan perintah berikut untuk mengkueri URL situs web Anda.
```bash
   az staticwebapp show \
     --name $MY_STATIC_WEB_APP_NAME \
     --query "defaultHostname"
```
5. Salin URL ke browser Anda untuk membuka situs web Anda.

## Membersihkan sumber daya (opsional)

Jika Anda tidak akan terus menggunakan aplikasi ini, hapus grup sumber daya dan aplikasi web statis menggunakan [perintah az group delete](/cli/azure/group#az-group-delete) .

## Langkah berikutnya

> [!div class="nextstepaction"]
> [Menambahkan API](add-api.md)
