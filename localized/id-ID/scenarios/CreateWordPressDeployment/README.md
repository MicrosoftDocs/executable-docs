---
title: Menyebarkan instans WordPress yang Dapat Diskalakan & Aman di AKS
description: Tutorial ini menunjukkan cara menyebarkan instans WordPress yang Dapat Diskalakan & Aman pada AKS melalui CLI
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Mulai Cepat: Menyebarkan instans WordPress yang Dapat Diskalakan & Aman di AKS

Selamat datang di tutorial ini di mana kami akan membawa Anda langkah demi langkah dalam membuat Aplikasi Web Azure Kubernetes yang diamankan melalui https. Tutorial ini mengasumsikan Anda sudah masuk ke Azure CLI dan telah memilih langganan untuk digunakan dengan CLI. Ini juga mengasumsikan bahwa Anda telah menginstal Helm ([Instruksi dapat ditemukan di sini](https://helm.sh/docs/intro/install/)).

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

Grup sumber daya adalah kontainer untuk sumber daya terkait. Semua sumber daya harus ditempatkan dalam grup sumber daya. Kami akan membuatnya untuk tutorial ini. Perintah berikut membuat grup sumber daya dengan parameter $MY_RESOURCE_GROUP_NAME dan $REGION yang ditentukan sebelumnya.

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

## Membuat Server Fleksibel Azure Database for MySQL

Azure Database for MySQL - Server Fleksibel adalah layanan terkelola yang dapat Anda gunakan untuk menjalankan, mengelola, dan menskalakan server MySQL yang sangat tersedia di cloud. Membuat server fleksibel dengan perintah [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create). Server bisa berisi beberapa database. Perintah berikut membuat server menggunakan default layanan dan nilai variabel dari lingkungan lokal Azure CLI Anda:

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

Server yang dibuat memiliki atribut di bawah ini:

- Nama server, nama pengguna admin, kata sandi admin, nama grup sumber daya, lokasi sudah ditentukan di lingkungan konteks lokal shell cloud, dan akan dibuat di lokasi yang sama dengan Anda adalah grup sumber daya dan komponen Azure lainnya.
- Default layanan untuk konfigurasi server yang tersisa: tingkat komputasi (Burstable), ukuran komputasi/SKU (Standard_B2s), periode retensi cadangan (7 hari), dan versi MySQL (8.0.21)
- Metode konektivitas default adalah Akses privat (Integrasi VNet) dengan jaringan virtual tertaut dan subnet yang dihasilkan secara otomatis.

> [!NOTE]
> Metode konektivitas tidak dapat diubah setelah membuat server. Misalnya, jika Anda memilih `Private access (VNet Integration)` selama pembuatan, Maka Anda tidak dapat mengubahnya `Public access (allowed IP addresses)` setelah membuat. Kami sangat menyarankan untuk membuat server dengan akses Pribadi untuk mengakses server Anda dengan aman menggunakan Integrasi VNet. Pelajari selengkapnya tentang akses Pribadi [di artikel konsep](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Jika Anda ingin mengubah default apa pun, silakan lihat dokumentasi [referensi](https://learn.microsoft.com/cli/azure//mysql/flexible-server) Azure CLI untuk daftar lengkap parameter CLI yang dapat dikonfigurasi.

## Periksa Status Azure Database for MySQL - Server Fleksibel

Dibutuhkan beberapa menit untuk membuat Azure Database for MySQL - Server Fleksibel dan sumber daya pendukung.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Mengonfigurasi parameter server di Azure Database for MySQL - Server Fleksibel

Anda dapat mengelola Konfigurasi Azure Database for MySQL - Server Fleksibel menggunakan parameter server. Parameter server dikonfigurasi dengan nilai default dan direkomendasikan saat Anda membuat server.

Tampilkan detail parameter server Untuk menampilkan detail tentang parameter tertentu untuk server, jalankan [perintah az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) .

### Nonaktifkan Azure Database for MySQL - Parameter koneksi SSL Server Fleksibel untuk integrasi WordPress

Anda juga dapat memodifikasi nilai parameter server tertentu, yang memperbarui nilai konfigurasi yang mendasar untuk mesin server MySQL. Untuk memperbarui parameter server, gunakan perintah [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

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

## Buat Kluster AKS

Membuat kluster AKS menggunakan perintah az aks create dengan parameter --enable-addons monitoring untuk mengaktifkan insight Kontainer. Contoh berikut membuat kluster berkemampuan zona ketersediaan otomatis bernama myAKSCluster:

Ini akan memakan waktu beberapa menit

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

## Memasang Pengontrol Ingress NGINX

Anda dapat mengonfigurasi pengontrol ingress Anda dengan alamat IP publik statis. Alamat IP publik statis tetap ada jika Anda menghapus pengontrol ingress Anda. Alamat IP tidak tetap jika Anda menghapus kluster AKS Anda.
Saat meningkatkan pengontrol ingress, Anda harus meneruskan parameter ke rilis Helm untuk memastikan layanan pengontrol ingress dibuat mengetahui load balancer yang akan dialokasikan untuk itu. Agar sertifikat HTTPS berfungsi dengan benar, Anda menggunakan label DNS untuk mengonfigurasi FQDN untuk alamat IP pengontrol ingress.
FQDN Anda harus mengikuti formulir ini: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Tambahkan --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" parameter. Label DNS dapat diatur, baik saat pengontrol ingress pertama kali disebarkan atau dapat dikonfigurasi nanti. Tambahkan parameter --set controller.service.loadBalancerIP="<STATIC_IP>". Tentukan alamat IP publik Anda yang dibuat di langkah sebelumnya.

1. Tambahkan repositori ingress-nginx Helm

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Memperbarui cache repositori Bagan Helm lokal

    ```bash
    helm repo update
    ```

3. Instal addon ingress-nginx melalui Helm dengan menjalankan yang berikut:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## Menambahkan penghentian HTTPS ke domain kustom

Pada titik ini dalam tutorial, Anda memiliki aplikasi web AKS dengan NGINX sebagai pengontrol Ingress dan domain kustom yang dapat Anda gunakan untuk mengakses aplikasi Anda. Langkah selanjutnya adalah menambahkan sertifikat SSL ke domain sehingga pengguna dapat menjangkau aplikasi Anda dengan aman melalui https.

## Menyiapkan Cert Manager

Untuk menambahkan HTTPS, kami akan menggunakan Cert Manager. Cert Manager adalah alat sumber terbuka yang digunakan untuk mendapatkan dan mengelola sertifikat SSL untuk penyebaran Kubernetes. Cert Manager akan mendapatkan sertifikat dari berbagai Penerbit, penerbit publik populer maupun Penerbit privat, dan memastikan sertifikat valid dan terbaru, dan akan mencoba memperbarui sertifikat pada waktu yang dikonfigurasi sebelum kedaluwarsa.

1. Untuk menginstal cert-manager, kita harus terlebih dahulu membuat namespace layanan untuk menjalankannya. Tutorial ini akan menginstal cert-manager ke dalam namespace layanan cert-manager. Dimungkinkan untuk menjalankan cert-manager di namespace layanan yang berbeda, meskipun Anda harus membuat modifikasi pada manifes penyebaran.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Kita sekarang dapat menginstal cert-manager. Semua sumber daya disertakan dalam satu file manifes YAML. Ini dapat diinstal dengan menjalankan hal berikut:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Tambahkan label certmanager.k8s.io/disable-validation: "true" ke namespace layanan cert-manager dengan menjalankan yang berikut ini. Ini akan memungkinkan sumber daya sistem yang diperlukan cert-manager untuk bootstrap TLS untuk dibuat di namespacenya sendiri.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Mendapatkan sertifikat melalui Bagan Helm

Helm adalah alat penyebaran Kubernetes untuk mengotomatiskan pembuatan, pengemasan, konfigurasi, dan penyebaran aplikasi dan layanan ke kluster Kubernetes.

Cert-manager menyediakan bagan Helm sebagai metode penginstalan kelas satu di Kubernetes.

1. Menambahkan repositori Jetstack Helm

    Repositori ini adalah satu-satunya sumber bagan cert-manager yang didukung. Ada beberapa cermin dan salinan lain di internet, tetapi itu sepenuhnya tidak resmi dan dapat menghadirkan risiko keamanan.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Memperbarui cache repositori Bagan Helm lokal

    ```bash
    helm repo update
    ```

3. Instal addon Cert-Manager melalui Helm dengan menjalankan hal berikut:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Terapkan File YAML Penerbit Sertifikat

    ClusterIssuers adalah sumber daya Kubernetes yang mewakili otoritas sertifikat (CA) yang dapat menghasilkan sertifikat yang ditandatangani dengan mematuhi permintaan penandatanganan sertifikat. Semua sertifikat cert-manager memerlukan pengeluar sertifikat yang direferensikan dalam kondisi siap untuk mencoba memenuhi permintaan.
    Penerbit yang kami gunakan dapat ditemukan di `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Membuat kelas penyimpanan kustom

Kelas penyimpanan default sesuai dengan skenario yang paling umum, tetapi tidak semua. Untuk beberapa kasus, Anda mungkin ingin memiliki kelas penyimpanan yang disesuaikan dengan parameter Anda sendiri. Misalnya, gunakan manifes berikut untuk mengonfigurasi mountOptions dari berbagi file.
Nilai default untuk fileMode dan dirMode adalah 0755 untuk berbagi file yang dipasang Kubernetes. Anda dapat menentukan opsi pemasangan yang berbeda pada objek kelas penyimpanan.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Menyebarkan WordPress ke kluster AKS

Untuk dokumen ini, kami menggunakan Bagan Helm yang ada untuk WordPress yang dibangun oleh Bitnami. Misalnya bagan Bitnami Helm menggunakan MariaDB lokal sebagai database dan kita perlu mengambil alih nilai-nilai ini untuk menggunakan aplikasi dengan Azure Database for MySQL. Semua nilai penimpaan Anda dapat mengambil alih nilai dan pengaturan kustom dapat ditemukan dalam file `helm-wp-aks-values.yaml`

1. Menambahkan repositori Wordpress Bitnami Helm

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Memperbarui cache repositori Bagan Helm lokal

    ```bash
    helm repo update
    ```

3. Instal beban kerja Wordpress melalui Helm dengan menjalankan hal berikut:

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

## Telusuri Penyebaran AKS Anda Diamankan melalui HTTPS

Jalankan perintah berikut untuk mendapatkan titik akhir HTTPS untuk aplikasi Anda:

> [!NOTE]
> Sering kali diperlukan waktu 2-3 menit agar sertifikat SSL menyebar dan sekitar 5 menit agar semua replika POD WordPress siap dan situs dapat dijangkau sepenuhnya melalui https.

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

Memeriksa apakah konten WordPress sedang dikirimkan dengan benar.

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

Situs web dapat dikunjungi dengan mengikuti URL di bawah ini:

```bash
echo "You can now visit your web server at https://$FQDN"
```
