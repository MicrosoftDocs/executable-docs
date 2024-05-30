---
title: 'Mulai cepat: Menyebarkan kluster Azure Kubernetes Service (AKS) menggunakan Azure CLI'
description: Pelajari cara menyebarkan kluster Kubernetes dengan cepat dan menyebarkan aplikasi di Azure Kubernetes Service (AKS) menggunakan Azure CLI.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Mulai cepat: Menyebarkan kluster Azure Kubernetes Service (AKS) menggunakan Azure CLI

[![Sebarkan ke Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) merupakan layanan Kube terkelola yang memungkinkan Anda menyebarkan dan mengelola kluster dengan cepat. Dalam panduan mulai cepat ini, Anda belajar cara:

- Menyebarkan kluster AKS menggunakan Azure CLI.
- Jalankan contoh aplikasi multi-kontainer dengan sekelompok layanan mikro dan ujung depan web yang mensimulasikan skenario ritel.

> [!NOTE]
> Untuk memulai provisi kluster AKS dengan cepat, artikel ini menyertakan langkah-langkah untuk menyebarkan kluster dengan pengaturan default hanya untuk tujuan evaluasi. Sebelum menyebarkan kluster siap produksi, kami sarankan Anda membiasakan diri dengan arsitektur[ referensi dasar kami ][baseline-reference-architecture]untuk mempertimbangkan bagaimana kluster tersebut selaras dengan kebutuhan bisnis Anda.

## Sebelum Anda mulai

Mulai cepat ini mengasumsikan pemahaman dasar tentang konsep Kube. Untuk informasi lebih, lihat [konsep inti Kubernetes untuk Azure Kubernetes Service (AKS)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Artikel ini memerlukan versi 2.0.64 atau yang lebih baru dari Azure CLI. Jika Anda menggunakan Azure Cloud Shell, versi terbaru sudah diinstal di sana.
- Pastikan identitas yang Anda gunakan untuk membuat kluster Anda memiliki izin minimum yang sesuai. Untuk informasi selengkapnya tentang akses dan identitas AKS, lihat [Opsi akses dan identitas untuk Azure Kubernetes Service (AKS)](../concepts-identity.md).
- Jika Anda memiliki beberapa langganan Azure, pilih ID langganan yang sesuai tempat sumber daya harus ditagih menggunakan [perintah az account set](/cli/azure/account#az-account-set) .

## Menentukan variabel lingkungan

Tentukan variabel lingkungan berikut untuk digunakan di seluruh mulai cepat ini:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Buat grup sumber daya

[Grup sumber daya Azure][azure-resource-group] adalah grup logis tempat sumber daya Azure disebarkan dan dikelola. Saat membuat grup sumber daya, Anda diminta untuk menentukan lokasi. Lokasi ini adalah lokasi penyimpanan metadata grup sumber daya Anda dan tempat sumber daya Anda berjalan di Azure jika Anda tidak menentukan wilayah lain selama pembuatan sumber daya.

Buat grup sumber daya menggunakan [`az group create`][az-group-create] perintah .

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Hasil:
<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
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

## Membuat kluster AKS

Buat kluster AKS menggunakan [`az aks create`][az-aks-create] perintah . Contoh berikut membuat kluster dengan satu simpul dan mengaktifkan identitas terkelola yang ditetapkan sistem.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> Saat Anda membuat kluster baru, AKS secara otomatis membuat grup sumber daya kedua untuk menyimpan sumber daya AKS. Untuk informasi selengkapnya, lihat [Mengapa ada dua grup sumber daya yang dibuat dengan AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Menyambungkan ke kluster

Untuk mengelola kluster Kube, gunakan klien baris perintah Kube, [kubectl][kubectl]. `kubectl` sudah diinstal jika Anda menggunakan Azure Cloud Shell. Untuk menginstal `kubectl` secara lokal, gunakan [`az aks install-cli`][az-aks-install-cli] perintah .

1. Konfigurasikan `kubectl` untuk terhubung ke kluster Kubernetes menggunakan perintah [az aks get-credentials][az-aks-get-credentials]. Perintah ini mengunduh informasi masuk dan mengonfigurasi CLI Kube untuk menggunakannya.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Verifikasi koneksi ke kluster menggunakan perintah [kubectl get][kubectl-get]. Perintah ini menampilkan daftar node kluster.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Menyebarkan aplikasi

Untuk menyebarkan aplikasi, Anda menggunakan file manifes untuk membuat semua objek yang diperlukan untuk menjalankan [aplikasi](https://github.com/Azure-Samples/aks-store-demo) AKS Store. [File manifes Kube][kubernetes-deployment] menentukan status kluster yang diinginkan, seperti gambar kontainer mana yang akan dijalankan. Manifes mencakup penyebaran dan layanan Kubernetes berikut:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Cuplikan layar arsitektur sampel Azure Store." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Simpan depan**: Aplikasi web bagi pelanggan untuk melihat produk dan melakukan pemesanan.
- **Layanan produk**: Menampilkan informasi produk.
- **Layanan** pesanan: Menempatkan pesanan.
- **Rabbit MQ**: Antrean pesan untuk antrean pesanan.

> [!NOTE]
> Kami tidak menyarankan untuk menjalankan kontainer stateful, seperti Rabbit MQ, tanpa penyimpanan persisten untuk produksi. Ini digunakan di sini untuk kesederhanaan, tetapi sebaiknya gunakan layanan terkelola, seperti Azure CosmosDB atau Azure Bus Layanan.

1. Buat file bernama `aks-store-quickstart.yaml` dan salin dalam manifes berikut:

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: rabbitmq
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: rabbitmq
      template:
        metadata:
          labels:
            app: rabbitmq
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: rabbitmq
            image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine
            ports:
            - containerPort: 5672
              name: rabbitmq-amqp
            - containerPort: 15672
              name: rabbitmq-http
            env:
            - name: RABBITMQ_DEFAULT_USER
              value: "username"
            - name: RABBITMQ_DEFAULT_PASS
              value: "password"
            resources:
              requests:
                cpu: 10m
                memory: 128Mi
              limits:
                cpu: 250m
                memory: 256Mi
            volumeMounts:
            - name: rabbitmq-enabled-plugins
              mountPath: /etc/rabbitmq/enabled_plugins
              subPath: enabled_plugins
          volumes:
          - name: rabbitmq-enabled-plugins
            configMap:
              name: rabbitmq-enabled-plugins
              items:
              - key: rabbitmq_enabled_plugins
                path: enabled_plugins
    ---
    apiVersion: v1
    data:
      rabbitmq_enabled_plugins: |
        [rabbitmq_management,rabbitmq_prometheus,rabbitmq_amqp1_0].
    kind: ConfigMap
    metadata:
      name: rabbitmq-enabled-plugins
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: rabbitmq
    spec:
      selector:
        app: rabbitmq
      ports:
        - name: rabbitmq-amqp
          port: 5672
          targetPort: 5672
        - name: rabbitmq-http
          port: 15672
          targetPort: 15672
      type: ClusterIP
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: order-service
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: order-service
      template:
        metadata:
          labels:
            app: order-service
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: order-service
            image: ghcr.io/azure-samples/aks-store-demo/order-service:latest
            ports:
            - containerPort: 3000
            env:
            - name: ORDER_QUEUE_HOSTNAME
              value: "rabbitmq"
            - name: ORDER_QUEUE_PORT
              value: "5672"
            - name: ORDER_QUEUE_USERNAME
              value: "username"
            - name: ORDER_QUEUE_PASSWORD
              value: "password"
            - name: ORDER_QUEUE_NAME
              value: "orders"
            - name: FASTIFY_ADDRESS
              value: "0.0.0.0"
            resources:
              requests:
                cpu: 1m
                memory: 50Mi
              limits:
                cpu: 75m
                memory: 128Mi
          initContainers:
          - name: wait-for-rabbitmq
            image: busybox
            command: ['sh', '-c', 'until nc -zv rabbitmq 5672; do echo waiting for rabbitmq; sleep 2; done;']
            resources:
              requests:
                cpu: 1m
                memory: 50Mi
              limits:
                cpu: 75m
                memory: 128Mi
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: order-service
    spec:
      type: ClusterIP
      ports:
      - name: http
        port: 3000
        targetPort: 3000
      selector:
        app: order-service
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: product-service
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: product-service
      template:
        metadata:
          labels:
            app: product-service
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: product-service
            image: ghcr.io/azure-samples/aks-store-demo/product-service:latest
            ports:
            - containerPort: 3002
            resources:
              requests:
                cpu: 1m
                memory: 1Mi
              limits:
                cpu: 1m
                memory: 7Mi
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: product-service
    spec:
      type: ClusterIP
      ports:
      - name: http
        port: 3002
        targetPort: 3002
      selector:
        app: product-service
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: store-front
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: store-front
      template:
        metadata:
          labels:
            app: store-front
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: store-front
            image: ghcr.io/azure-samples/aks-store-demo/store-front:latest
            ports:
            - containerPort: 8080
              name: store-front
            env:
            - name: VUE_APP_ORDER_SERVICE_URL
              value: "http://order-service:3000/"
            - name: VUE_APP_PRODUCT_SERVICE_URL
              value: "http://product-service:3002/"
            resources:
              requests:
                cpu: 1m
                memory: 200Mi
              limits:
                cpu: 1000m
                memory: 512Mi
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: store-front
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: store-front
      type: LoadBalancer
    ```

    Untuk perincian file manifes YAML, lihat [Manifes](../concepts-clusters-workloads.md#deployments-and-yaml-manifests) Penyebaran dan YAML.

    Jika Anda membuat dan menyimpan file YAML secara lokal, maka Anda dapat mengunggah file manifes ke direktori default Anda di CloudShell dengan memilih **tombol Unggah/Unduh file** dan memilih file dari sistem file lokal Anda.

1. Sebarkan aplikasi menggunakan [`kubectl apply`][kubectl-apply] perintah dan tentukan nama manifes YAML Anda.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Uji aplikasi

Anda dapat memvalidasi bahwa aplikasi berjalan dengan mengunjungi alamat IP publik atau URL aplikasi.

Dapatkan URL aplikasi menggunakan perintah berikut:

```azurecli-interactive
runtime="5 minutes"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]
do
   STATUS=$(kubectl get pods -l app=store-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')
   echo $STATUS
   if [ "$STATUS" == 'True' ]
   then
      export IP_ADDRESS=$(kubectl get service store-front --output 'jsonpath={..status.loadBalancer.ingress[0].ip}')
      echo "Service IP Address: $IP_ADDRESS"
      break
   else
      sleep 10
   fi
done
```

```azurecli-interactive
curl $IP_ADDRESS
```

Hasil:
<!-- expected_similarity=0.3 -->
```HTML
<!doctype html>
<html lang="">
   <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <link rel="icon" href="/favicon.ico">
      <title>store-front</title>
      <script defer="defer" src="/js/chunk-vendors.df69ae47.js"></script>
      <script defer="defer" src="/js/app.7e8cfbb2.js"></script>
      <link href="/css/app.a5dc49f6.css" rel="stylesheet">
   </head>
   <body>
      <div id="app"></div>
   </body>
</html>
```

```output
echo "You can now visit your web server at $IP_ADDRESS"
```

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Cuplikan layar aplikasi sampel AKS Store." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Menghapus kluster

Jika Anda tidak berencana untuk melalui [tutorial][aks-tutorial] AKS, bersihkan sumber daya yang tidak perlu untuk menghindari biaya Azure. Anda dapat menghapus grup sumber daya, layanan kontainer, dan semua sumber daya terkait menggunakan [`az group delete`][az-group-delete] perintah .

> [!NOTE]
> Kluster AKS dibuat dengan identitas terkelola yang ditetapkan sistem, yang merupakan opsi identitas default yang digunakan dalam mulai cepat ini. Platform mengelola identitas ini sehingga Anda tidak perlu menghapusnya secara manual.

## Langkah berikutnya

Dalam panduan mulai cepat ini, Anda menerapkan kluster Kubernetes dan kemudian menerapkan aplikasi multi-kontainer sederhana ke dalamnya. Aplikasi sampel ini hanya untuk tujuan demo dan tidak mewakili semua praktik terbaik untuk aplikasi Kubernetes. Untuk panduan tentang membuat solusi lengkap dengan AKS untuk produksi, lihat [panduan][aks-solution-guidance] solusi AKS.

Untuk mempelajari lebih lanjut tentang AKS dan menelusuri contoh kode-ke-penyebaran lengkap, lanjutkan ke tutorial kluster Kubernetes.

> [!div class="nextstepaction"]
> [Tutorial AKS][aks-tutorial]

<!-- LINKS - external -->
[kubectl]: https://kubernetes.io/docs/reference/kubectl/
[kubectl-apply]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
[kubectl-get]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get

<!-- LINKS - internal -->
[kubernetes-concepts]: ../concepts-clusters-workloads.md
[aks-tutorial]: ../tutorial-kubernetes-prepare-app.md
[azure-resource-group]: ../../azure-resource-manager/management/overview.md
[az-aks-create]: /cli/azure/aks#az-aks-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-aks-install-cli]: /cli/azure/aks#az-aks-install-cli
[az-group-create]: /cli/azure/group#az-group-create
[az-group-delete]: /cli/azure/group#az-group-delete
[kubernetes-deployment]: ../concepts-clusters-workloads.md#deployments-and-yaml-manifests
[aks-solution-guidance]: /azure/architecture/reference-architectures/containers/aks-start-here?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json
[baseline-reference-architecture]: /azure/architecture/reference-architectures/containers/aks/baseline-aks?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json
