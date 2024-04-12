---
title: 'Tutorial: Menyebarkan WordPress pada kluster AKS dengan menggunakan Azure CLI'
description: Pelajari cara cepat membangun dan menyebarkan WordPress di AKS dengan Azure Database for MySQL - Server Fleksibel.
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Tutorial: Terapkan aplikasi WordPress di AKS dengan Azure Database for MySQL - Flexible Server

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Sebarkan ke Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Dalam tutorial ini, Anda menyebarkan aplikasi WordPress yang dapat diskalakan yang diamankan melalui HTTPS pada kluster Azure Kubernetes Service (AKS) dengan server fleksibel Azure Database for MySQL menggunakan Azure CLI.
**[AKS](../../aks/intro-kubernetes.md)** adalah layanan Kubernetes terkelola yang memungkinkan Anda menyebarkan dan mengelola kluster dengan cepat. **[Server](overview.md)** fleksibel Azure Database for MySQL adalah layanan database terkelola penuh yang dirancang untuk memberikan kontrol dan fleksibilitas yang lebih terperinci atas fungsi manajemen database dan pengaturan konfigurasi.

> [!NOTE]
> Tutorial ini mengasumsikan pemahaman dasar tentang konsep Kubernetes, WordPress, dan MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Prasyarat 

Sebelum memulai, pastikan Anda masuk ke Azure CLI dan telah memilih langganan untuk digunakan dengan CLI. Pastikan Anda telah [menginstal](https://helm.sh/docs/intro/install/) Helm.

> [!NOTE]
> Jika Anda menjalankan perintah dalam tutorial ini secara lokal alih-alih Azure Cloud Shell, jalankan perintah sebagai administrator.

## Tentukan Variabel Lingkungan

Langkah pertama dalam tutorial ini adalah menentukan variabel lingkungan.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Buat grup sumber daya

Grup sumber daya Azure adalah grup logis tempat sumber daya Azure disebarkan dan dikelola. Semua sumber daya harus ditempatkan dalam grup sumber daya. Perintah berikut membuat grup sumber daya dengan parameter dan `$REGION` yang ditentukan `$MY_RESOURCE_GROUP_NAME` sebelumnya.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Hasil:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
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

> [!NOTE]
> Lokasi untuk grup sumber daya adalah tempat metadata grup sumber daya disimpan. Ini juga tempat sumber daya Anda berjalan di Azure jika Anda tidak menentukan wilayah lain selama pembuatan sumber daya.

## Membuat jaringan virtual dan subnet

Jaringan virtual adalah blok penyusun dasar untuk jaringan privat di Azure. Azure Virtual Network memungkinkan sumber daya Azure seperti VM untuk berkomunikasi satu sama lain dengan aman dan internet.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Hasil:
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Membuat instans server fleksibel Azure Database for MySQL

Server fleksibel Azure Database for MySQL adalah layanan terkelola yang dapat Anda gunakan untuk menjalankan, mengelola, dan menskalakan server MySQL yang sangat tersedia di cloud. Buat instans server fleksibel Azure Database for MySQL dengan [perintah az mysql flexible-server create](/cli/azure/mysql/flexible-server) . Server bisa berisi beberapa database. Perintah berikut membuat server menggunakan default layanan dan nilai variabel dari konteks lokal Azure CLI Anda:

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

Hasil:
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

Server yang dibuat memiliki atribut berikut:

- Database kosong baru dibuat saat server pertama kali disediakan.
- Nama server, nama pengguna admin, kata sandi admin, nama grup sumber daya, dan lokasi sudah ditentukan di lingkungan konteks lokal shell cloud dan berada di lokasi yang sama dengan grup sumber daya Anda dan komponen Azure lainnya.
- Default layanan untuk konfigurasi server yang tersisa adalah tingkat komputasi (Burstable), ukuran komputasi/SKU (Standard_B2s), periode retensi cadangan (tujuh hari), dan versi MySQL (8.0.21).
- Metode konektivitas default adalah Akses privat (integrasi jaringan virtual) dengan jaringan virtual tertaut dan subnet yang dihasilkan secara otomatis.

> [!NOTE]
> Metode konektivitas tidak dapat diubah setelah membuat server. Misalnya, jika Anda memilih `Private access (VNet Integration)` selama pembuatan, maka Anda tidak dapat berubah menjadi `Public access (allowed IP addresses)` setelah pembuatan. Kami sangat menyarankan untuk membuat server dengan akses Pribadi untuk mengakses server Anda dengan aman menggunakan Integrasi VNet. Pelajari selengkapnya tentang akses Pribadi [di artikel konsep](./concepts-networking-vnet.md).

Jika Anda ingin mengubah default apa pun, lihat dokumentasi[ referensi Azure CLI ](/cli/azure//mysql/flexible-server)untuk daftar lengkap parameter CLI yang dapat dikonfigurasi.

## Periksa Status Azure Database for MySQL - Server Fleksibel

Dibutuhkan beberapa menit untuk membuat Azure Database for MySQL - Server Fleksibel dan sumber daya pendukung.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Mengonfigurasi parameter server di Azure Database for MySQL - Server Fleksibel

Anda dapat mengelola Konfigurasi Azure Database for MySQL - Server Fleksibel menggunakan parameter server. Parameter server dikonfigurasi dengan nilai default dan direkomendasikan saat Anda membuat server.

Untuk menampilkan rincian parameter tertentu untuk server, jalankan perintah [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter).

### Nonaktifkan Azure Database for MySQL - Parameter koneksi SSL Server Fleksibel untuk integrasi WordPress

Anda juga dapat memodifikasi nilai parameter server tertentu untuk memperbarui nilai konfigurasi yang mendasar untuk mesin server MySQL. Untuk memperbarui parameter server, gunakan perintah [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Hasil:
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## Membuat kluster AKS

Untuk membuat kluster AKS dengan Container Insights, gunakan [perintah az aks create](/cli/azure/aks#az-aks-create) dengan **parameter pemantauan --enable-addons** . Contoh berikut membuat kluster berkemampuan zona ketersediaan otomatis bernama **myAKSCluster**:

Tindakan ini membutuhkan waktu beberapa menit.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> Saat membuat kluster AKS, grup sumber daya kedua secara otomatis dibuat untuk menyimpan sumber daya AKS. Lihat [Mengapa dua grup sumber daya dibuat dengan AKS?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Menyambungkan ke kluster

Untuk mengelola kluster Kubernetes, gunakan [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), klien baris-perintah Kubernetes. Jika Anda menggunakan Azure Cloud Shell, `kubectl` sudah terpasang. Contoh berikut menginstal `kubectl` secara lokal menggunakan [perintah az aks install-cli](/cli/azure/aks#az-aks-install-cli) . 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Selanjutnya, konfigurasikan `kubectl` untuk terhubung ke kluster Kubernetes menggunakan [perintah az aks get-credentials](/cli/azure/aks#az-aks-get-credentials) . Perintah ini mengunduh informasi masuk dan mengonfigurasi CLI Kube untuk menggunakannya. Perintah menggunakan `~/.kube/config`, lokasi default untuk [file](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) konfigurasi Kubernetes. Anda dapat menentukan lokasi yang berbeda untuk file konfigurasi Kubernetes menggunakan **argumen --file** .

> [!WARNING]
> Perintah ini akan menimpa kredensial yang ada dengan entri yang sama.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Untuk memverifikasi sambungan ke kluster Anda, gunakan perintah [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) untuk mengembalikan daftar node kluster.

```bash
kubectl get nodes
```

## Memasang pengontrol ingress NGINX

Anda dapat mengonfigurasi pengontrol ingress Anda dengan alamat IP publik statis. Alamat IP publik statis tetap ada jika Anda menghapus pengontrol ingress Anda. Alamat IP tidak tetap jika Anda menghapus kluster AKS Anda.
Saat meningkatkan pengontrol ingress, Anda harus meneruskan parameter ke rilis Helm untuk memastikan layanan pengontrol ingress dibuat mengetahui load balancer yang akan dialokasikan untuk itu. Agar sertifikat HTTPS berfungsi dengan benar, gunakan label DNS untuk mengonfigurasi nama domain yang sepenuhnya memenuhi syarat (FQDN) untuk alamat IP pengontrol ingress. FQDN Anda harus mengikuti formulir ini: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Selanjutnya, Anda menambahkan repositori Helm ingress-nginx, memperbarui cache repositori Bagan Helm lokal, dan menginstal addon ingress-nginx melalui Helm. Anda dapat mengatur label DNS dengan **--set controller.service.annotations." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** parameter baik ketika Anda pertama kali menyebarkan pengontrol ingress atau yang lebih baru. Dalam contoh ini, Anda menentukan alamat IP publik Anda sendiri yang Anda buat di langkah sebelumnya dengan **parameter --set controller.service.loadBalancerIP="<STATIC_IP>"**.

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## Menambahkan penghentian HTTPS ke domain kustom

Pada titik ini dalam tutorial, Anda memiliki aplikasi web AKS dengan NGINX sebagai pengontrol ingress dan domain kustom yang dapat Anda gunakan untuk mengakses aplikasi Anda. Langkah selanjutnya adalah menambahkan sertifikat SSL ke domain sehingga pengguna dapat menjangkau aplikasi Anda dengan aman melalui https.

### Menyiapkan Cert Manager

Untuk menambahkan HTTPS, kita akan menggunakan Cert Manager. Cert Manager adalah alat sumber terbuka untuk mendapatkan dan mengelola sertifikat SSL untuk penyebaran Kubernetes. Cert Manager mendapatkan sertifikat dari penerbit publik dan penerbit privat populer, memastikan sertifikat valid dan terbaru, dan mencoba memperbarui sertifikat pada waktu yang dikonfigurasi sebelum kedaluwarsa.

1. Untuk menginstal cert-manager, kita harus terlebih dahulu membuat namespace layanan untuk menjalankannya. Tutorial ini menginstal cert-manager ke dalam namespace layanan cert-manager. Anda dapat menjalankan cert-manager di namespace layanan yang berbeda, tetapi Anda harus membuat modifikasi pada manifes penyebaran.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Kita sekarang dapat menginstal cert-manager. Semua sumber daya disertakan dalam satu file manifes YAML. Instal file manifes dengan perintah berikut:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. `certmanager.k8s.io/disable-validation: "true"` Tambahkan label ke namespace layanan cert-manager dengan menjalankan yang berikut ini. Ini memungkinkan sumber daya sistem yang diperlukan cert-manager untuk bootstrap TLS untuk dibuat di namespacenya sendiri.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Mendapatkan sertifikat melalui Bagan Helm

Helm adalah alat penyebaran Kubernetes untuk mengotomatiskan pembuatan, pengemasan, konfigurasi, dan penyebaran aplikasi dan layanan ke kluster Kubernetes.

Cert-manager menyediakan bagan Helm sebagai metode penginstalan kelas satu di Kubernetes.

1. Tambahkan repositori Jetstack Helm. Repositori ini adalah satu-satunya sumber bagan cert-manager yang didukung. Ada cermin dan salinan lain di internet, tetapi itu tidak resmi dan dapat menghadirkan risiko keamanan.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Perbarui cache repositori Bagan Helm lokal.

    ```bash
    helm repo update
    ```

3. Instal addon Cert-Manager melalui Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Terapkan file YAML penerbit sertifikat. ClusterIssuers adalah sumber daya Kubernetes yang mewakili otoritas sertifikat (CA) yang dapat menghasilkan sertifikat yang ditandatangani dengan mematuhi permintaan penandatanganan sertifikat. Semua sertifikat cert-manager memerlukan pengeluar sertifikat yang direferensikan dalam kondisi siap untuk mencoba memenuhi permintaan. Anda dapat menemukan pengeluar sertifikat tempat kami berada di `cluster-issuer-prod.yaml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Membuat kelas penyimpanan kustom

Kelas penyimpanan default sesuai dengan skenario yang paling umum, tetapi tidak semua. Untuk beberapa kasus, Anda mungkin ingin memiliki kelas penyimpanan yang disesuaikan dengan parameter Anda sendiri. Misalnya, gunakan manifes berikut untuk mengonfigurasi **mountOptions** dari berbagi file.
Nilai default untuk **fileMode** dan **dirMode** adalah **0755** untuk berbagi file yang dipasang Kubernetes. Anda dapat menentukan opsi pemasangan yang berbeda pada objek kelas penyimpanan.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Menyebarkan WordPress ke kluster AKS

Untuk tutorial ini, kami menggunakan bagan Helm yang ada untuk WordPress yang dibangun oleh Bitnami. Bagan Bitnami Helm menggunakan MariaDB lokal sebagai database, jadi kita perlu mengambil alih nilai-nilai ini untuk menggunakan aplikasi dengan Azure Database for MySQL. Anda dapat mengambil alih nilai dan pengaturan `helm-wp-aks-values.yaml` kustom file.

1. Tambahkan repositori Wordpress Bitnami Helm.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Perbarui cache repositori bagan Helm lokal.

    ```bash
    helm repo update
    ```

3. Instal beban kerja Wordpress melalui Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

Hasil:
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## Telusuri penyebaran AKS Anda yang diamankan melalui HTTPS

Jalankan perintah berikut untuk mendapatkan titik akhir HTTPS untuk aplikasi Anda:

> [!NOTE]
> Sering kali dibutuhkan 2-3 menit agar sertifikat SSL menyebar dan sekitar 5 menit agar semua replika POD WordPress siap dan situs dapat dijangkau sepenuhnya melalui https.

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

Periksa apakah konten WordPress dikirimkan dengan benar menggunakan perintah berikut:

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Hasil:
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

Kunjungi situs web melalui URL berikut:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Membersihkan sumber daya (opsional)

Untuk menghindari biaya Azure, Anda harus membersihkan sumber daya yang tidak diperlukan. Saat Anda tidak lagi memerlukan kluster, gunakan [perintah az group delete](/cli/azure/group#az-group-delete) untuk menghapus grup sumber daya, layanan kontainer, dan semua sumber daya terkait. 

> [!NOTE]
> Saat Anda menghapus kluster, perwakilan layanan Microsoft Entra yang digunakan oleh kluster AKS tidak dihapus. Untuk langkah tentang cara menghapus perwakilan layanan, lihat [Pertimbangan dan penghapusan perwakilan layanan AKS](../../aks/kubernetes-service-principal.md#other-considerations). Jika Anda menggunakan identitas terkelola, identitas dikelola oleh platform dan tidak memerlukan penghapusan.

## Langkah berikutnya

- Pelajari cara [mengakses dasbor web Kubernetes](../../aks/kubernetes-dashboard.md) untuk kluster AKS Anda
- Pelajari cara [menskalakan kluster Anda](../../aks/tutorial-kubernetes-scale.md)
- Pelajari cara mengelola instans server fleksibel Azure Database for MySQL Anda [](./quickstart-create-server-cli.md)
- Pelajari cara [mengonfigurasi parameter](./how-to-configure-server-parameters-cli.md) server untuk server database Anda