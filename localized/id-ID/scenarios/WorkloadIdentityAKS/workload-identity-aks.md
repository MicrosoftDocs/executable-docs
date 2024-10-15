---
title: Menyebarkan dan mengonfigurasi kluster AKS dengan identitas beban kerja
description: 'Dalam artikel Azure Kubernetes Service (AKS) ini, Anda menyebarkan kluster Azure Kubernetes Service dan mengonfigurasinya dengan ID Beban Kerja Microsoft Entra.'
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Menyebarkan dan mengonfigurasi identitas beban kerja pada kluster Azure Kubernetes Service (AKS)

Azure Kubernetes Service (AKS) adalah layanan Kubernetes terkelola yang memungkinkan Anda dengan cepat menyebarkan dan mengelola kluster Kubernetes. Artikel ini menunjukkan cara:

* Sebarkan kluster AKS menggunakan Azure CLI dengan penerbit OpenID Connect dan ID Beban Kerja Microsoft Entra.
* Buat ID Beban Kerja Microsoft Entra dan akun layanan Kubernetes.
* Konfigurasikan identitas terkelola untuk federasi token.
* Sebarkan beban kerja dan verifikasi autentikasi dengan identitas beban kerja.
* Secara opsional memberikan pod dalam akses kluster ke rahasia di brankas kunci Azure.

Artikel ini mengasumsikan Anda memiliki pemahaman dasar tentang konsep Kubernetes. Untuk informasi lebih, lihat [konsep inti Kubernetes untuk Azure Kubernetes Service (AKS)][kubernetes-concepts]. Jika Anda tidak terbiasa dengan ID Beban Kerja Microsoft Entra, lihat artikel Gambaran Umum[ berikut ini][workload-identity-overview].

## Prasyarat

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Artikel ini memerlukan Azure CLI versi 2.47.0 atau yang lebih baru. Jika menggunakan Azure Cloud Shell, versi terbaru sudah terinstal.
* Pastikan bahwa identitas yang Anda gunakan untuk membuat kluster Anda memiliki izin minimum yang sesuai. Untuk informasi selengkapnya tentang akses dan identitas untuk AKS, lihat [Opsi akses dan identitas untuk Azure Kubernetes Service (AKS)][aks-identity-concepts].
* Jika Anda memiliki beberapa langganan Azure, pilih ID langganan yang sesuai tempat sumber daya harus ditagih menggunakan [perintah az account set][az-account-set] .

> [!NOTE]
> Anda dapat menggunakan _Konektor_ Layanan untuk membantu Mengonfigurasi beberapa langkah secara otomatis. Lihat juga: [Tutorial: Menyambungkan ke akun penyimpanan Azure di Azure Kubernetes Service (AKS) dengan Konektor Layanan menggunakan identitas][tutorial-python-aks-storage-workload-identity] beban kerja.

## Buat grup sumber daya

[Grup sumber daya Azure][azure-resource-group] adalah grup logis tempat sumber daya Azure disebarkan dan dikelola. Saat membuat grup sumber daya, Anda diminta untuk menentukan lokasi. Lokasi ini adalah lokasi penyimpanan metadata grup sumber daya Anda dan tempat sumber daya Anda berjalan di Azure jika Anda tidak menentukan wilayah lain selama pembuatan sumber daya.

Buat grup sumber daya dengan memanggil [perintah az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

Contoh output berikut menunjukkan keberhasilan pembuatan grup sumber daya:

Hasil:
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Membuat kluster AKS

Buat kluster AKS menggunakan [perintah az aks create][az-aks-create] dengan `--enable-oidc-issuer` parameter untuk mengaktifkan pengeluar sertifikat OIDC. Contoh berikut membuat kluster dengan satu simpul:

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Setelah beberapa menit, perintah selesai dan kembalikan informasi berformat JSON tentang kluster.

> [!NOTE]
> Saat Anda membuat kluster AKS, grup sumber daya kedua secara otomatis dibuat untuk menyimpan sumber daya AKS. Untuk informasi selengkapnya, lihat [Mengapa dua grup sumber daya dibuat dengan AKS?][aks-two-resource-groups].

## Memperbarui kluster AKS yang ada

Anda dapat memperbarui kluster AKS untuk menggunakan pengeluar sertifikat OIDC dan mengaktifkan identitas beban kerja dengan memanggil [perintah az aks update][az aks update] dengan `--enable-oidc-issuer` parameter dan `--enable-workload-identity` . Contoh berikut memperbarui kluster yang ada:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Mengambil URL penerbit OIDC

Untuk mendapatkan URL penerbit OIDC dan menyimpannya ke variabel lingkungan, jalankan perintah berikut:

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

Variabel lingkungan harus berisi URL penerbit, mirip dengan contoh berikut:

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Secara default, penerbit diatur untuk menggunakan URL `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`dasar , di mana nilai untuk `{region}` mencocokkan lokasi tempat kluster AKS disebarkan. Nilai `{uuid}` mewakili kunci OIDC, yang merupakan guid yang dihasilkan secara acak untuk setiap kluster yang tidak dapat diubah.

## Buat identitas terkelola

[Panggil perintah az identity create][az-identity-create] untuk membuat identitas terkelola.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

Contoh output berikut menunjukkan keberhasilan pembuatan identitas terkelola:

Hasil:
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

Selanjutnya, buat variabel untuk ID klien identitas terkelola.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Membuat akun layanan Kubernetes

Buat akun layanan Kubernetes dan anotasi dengan ID klien identitas terkelola yang dibuat pada langkah sebelumnya. [Gunakan perintah az aks get-credentials][az-aks-get-credentials] dan ganti nilai untuk nama kluster dan nama grup sumber daya.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Salin dan tempel input multibaris berikut di Azure CLI.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

Output berikut menunjukkan keberhasilan pembuatan identitas beban kerja:

```output
serviceaccount/workload-identity-sa created
```

## Membuat kredensial identitas federasi

[Panggil perintah az identity federated-credential create][az-identity-federated-credential-create] untuk membuat kredensial identitas federasi antara identitas terkelola, penerbit akun layanan, dan subjek. Untuk informasi selengkapnya tentang kredensial identitas gabungan di Microsoft Entra, lihat [Gambaran Umum kredensial identitas federasi di ID][federated-identity-credential] Microsoft Entra.

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> Dibutuhkan beberapa detik agar kredensial identitas federasi disebarluaskan setelah ditambahkan. Jika permintaan token dibuat segera setelah menambahkan kredensial identitas federasi, permintaan mungkin gagal sampai cache di-refresh. Untuk menghindari masalah ini, Anda dapat menambahkan sedikit penundaan setelah menambahkan kredensial identitas federasi.

## Menyebarkan aplikasi Anda

Saat Anda menyebarkan pod aplikasi, manifes harus mereferensikan akun layanan yang dibuat di **langkah Buat akun** layanan Kubernetes. Manifes berikut menunjukkan cara mereferensikan akun, khususnya _properti metadata\namespace_ dan _spec\serviceAccountName_ . Pastikan untuk menentukan gambar untuk `<image>` dan nama kontainer untuk `<containerName>`:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
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
EOF
```

> [!IMPORTANT]
> Pastikan pod aplikasi yang menggunakan identitas beban kerja menyertakan label `azure.workload.identity/use: "true"` dalam spesifikasi pod. Jika tidak, pod akan gagal setelah di-restart.

## Memberikan izin untuk mengakses Azure Key Vault

Instruksi dalam langkah ini menunjukkan cara mengakses rahasia, kunci, atau sertifikat dalam brankas kunci Azure dari pod. Contoh di bagian ini mengonfigurasi akses ke rahasia di brankas kunci untuk identitas beban kerja, tetapi Anda dapat melakukan langkah serupa untuk mengonfigurasi akses ke kunci atau sertifikat.

Contoh berikut menunjukkan cara menggunakan model izin kontrol akses berbasis peran Azure (Azure RBAC) untuk memberikan akses pod ke brankas kunci. Untuk informasi selengkapnya tentang model izin Azure RBAC untuk Azure Key Vault, lihat [Memberikan izin ke aplikasi untuk mengakses brankas kunci Azure menggunakan Azure RBAC](/azure/key-vault/general/rbac-guide).

1. Buat brankas kunci dengan perlindungan penghapusan menyeluruh dan otorisasi RBAC diaktifkan. Anda juga dapat menggunakan brankas kunci yang ada jika dikonfigurasi untuk perlindungan penghapusan menyeluruh dan otorisasi RBAC:

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. Tetapkan diri Anda peran Petugas[ Rahasia RBAC ](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer)Key Vault sehingga Anda dapat membuat rahasia di brankas kunci baru:

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. Buat rahasia di brankas kunci:

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Tetapkan [peran Pengguna](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) Rahasia Key Vault ke identitas terkelola yang ditetapkan pengguna yang Anda buat sebelumnya. Langkah ini memberikan izin identitas terkelola untuk membaca rahasia dari brankas kunci:

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. Buat variabel lingkungan untuk URL brankas kunci:

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Sebarkan pod yang mereferensikan akun layanan dan URL brankas kunci:

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

Untuk memeriksa apakah semua properti disuntikkan dengan benar oleh webhook, gunakan [perintah kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Jika berhasil, output harus mirip dengan yang berikut ini:

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Untuk memverifikasi bahwa pod mampu mendapatkan token dan mengakses sumber daya, gunakan perintah log kubectl:

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Jika berhasil, output harus mirip dengan yang berikut ini:

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Penetapan peran Azure RBAC dapat memakan waktu hingga sepuluh menit untuk disebarluaskan. Jika pod tidak dapat mengakses rahasia, Anda mungkin perlu menunggu penetapan peran disebarluaskan. Untuk informasi selengkapnya, lihat [Memecahkan Masalah Azure RBAC](/azure/role-based-access-control/troubleshooting#).

## Menonaktifkan identitas beban kerja

Untuk menonaktifkan ID Beban Kerja Microsoft Entra pada kluster AKS tempat id tersebut diaktifkan dan dikonfigurasi, Anda dapat menjalankan perintah berikut:

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Langkah berikutnya

Dalam artikel ini, Anda menyebarkan kluster Kubernetes dan mengonfigurasinya untuk menggunakan identitas beban kerja sebagai persiapan beban kerja aplikasi untuk mengautentikasi dengan kredensial tersebut. Sekarang Anda siap untuk menyebarkan aplikasi Anda dan mengonfigurasinya untuk menggunakan identitas beban kerja dengan versi [terbaru pustaka klien Azure Identity][azure-identity-libraries] . Jika Anda tidak dapat menulis ulang aplikasi untuk menggunakan versi pustaka klien terbaru, Anda dapat [menyiapkan pod][workload-identity-migration] aplikasi untuk mengautentikasi menggunakan identitas terkelola dengan identitas beban kerja sebagai solusi migrasi jangka pendek.

Integrasi [Konektor](/azure/service-connector/overview) Layanan membantu menyederhanakan konfigurasi koneksi untuk beban kerja AKS dan layanan dukungan Azure. Ini dengan aman menangani konfigurasi autentikasi dan jaringan dan mengikuti praktik terbaik untuk menyambungkan ke layanan Azure. Untuk informasi selengkapnya, lihat [Menyambungkan ke Layanan Azure OpenAI di AKS menggunakan Identitas](/azure/service-connector/tutorial-python-aks-openai-workload-identity) Beban Kerja dan [pengenalan](https://azure.github.io/AKS/2024/05/23/service-connector-intro) Konektor Layanan.

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries