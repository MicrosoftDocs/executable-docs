---
title: Membuat infrastruktur untuk menyebarkan database PostgreSQL yang sangat tersedia di AKS
description: Buat infrastruktur yang diperlukan untuk menyebarkan database PostgreSQL yang sangat tersedia di AKS menggunakan operator CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Membuat infrastruktur untuk menyebarkan database PostgreSQL yang sangat tersedia di AKS

Dalam artikel ini, Anda membuat infrastruktur yang diperlukan untuk menyebarkan database PostgreSQL yang sangat tersedia di AKS menggunakan [operator CloudNativePG (CNPG).](https://cloudnative-pg.io/)

## Sebelum Anda mulai

* Tinjau gambaran umum penyebaran dan pastikan Anda memenuhi semua prasyarat dalam [Cara menyebarkan database PostgreSQL yang sangat tersedia di AKS dengan Azure CLI][postgresql-ha-deployment-overview].
* [Atur variabel](#set-environment-variables) lingkungan untuk digunakan di seluruh panduan ini.
* [Instal ekstensi yang](#install-required-extensions) diperlukan.

## Atur variabel lingkungan

Atur variabel lingkungan berikut untuk digunakan di seluruh panduan ini:

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export LOCAL_NAME="cnpg"
export TAGS="owner=user"
export RESOURCE_GROUP_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export PRIMARY_CLUSTER_REGION="westus3"
export AKS_PRIMARY_CLUSTER_NAME="aks-primary-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_MANAGED_RG_NAME="rg-${LOCAL_NAME}-primary-aksmanaged-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME="pg-primary-fedcred1-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_PG_DNSPREFIX=$(echo $(echo "a$(openssl rand -hex 5 | cut -c1-11)"))
export AKS_UAMI_CLUSTER_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_VERSION="1.29"
export PG_NAMESPACE="cnpg-database"
export PG_SYSTEM_NAMESPACE="cnpg-system"
export PG_PRIMARY_CLUSTER_NAME="pg-primary-${LOCAL_NAME}-${SUFFIX}"
export PG_PRIMARY_STORAGE_ACCOUNT_NAME="hacnpgpsa${SUFFIX}"
export PG_STORAGE_BACKUP_CONTAINER_NAME="backups"
export ENABLE_AZURE_PVC_UPDATES="true"
export MY_PUBLIC_CLIENT_IP=$(dig +short myip.opendns.com @resolver3.opendns.com)
```

## Menginstal ekstensi yang diperlukan

Ekstensi `aks-preview`, `k8s-extension` dan `amg` menyediakan lebih banyak fungsionalitas untuk mengelola kluster Kubernetes dan mengkueri sumber daya Azure. Instal ekstensi ini menggunakan perintah berikut [`az extension add`][az-extension-add] :

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

Sebagai prasyarat untuk menggunakan kubectl, penting untuk terlebih dahulu menginstal [Krew][install-krew], diikuti dengan penginstalan [plugin][cnpg-plugin] CNPG. Ini akan memungkinkan manajemen operator PostgreSQL menggunakan perintah berikutnya.

```bash
(
  set -x; cd "$(mktemp -d)" &&
  OS="$(uname | tr '[:upper:]' '[:lower:]')" &&
  ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/\(arm\)\(64\)\?.*/\1\2/' -e 's/aarch64$/arm64/')" &&
  KREW="krew-${OS}_${ARCH}" &&
  curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" &&
  tar zxvf "${KREW}.tar.gz" &&
  ./"${KREW}" install krew
)

export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"

kubectl krew install cnpg
```

## Buat grup sumber daya

Buat grup sumber daya untuk menyimpan sumber daya yang Anda buat dalam panduan ini menggunakan [`az group create`][az-group-create] perintah .

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Membuat identitas terkelola yang ditetapkan pengguna

Di bagian ini, Anda membuat identitas terkelola yang ditetapkan pengguna (UAMI) untuk memungkinkan CNPG PostgreSQL menggunakan identitas beban kerja AKS untuk mengakses Azure Blob Storage. Konfigurasi ini memungkinkan kluster PostgreSQL di AKS untuk terhubung ke Azure Blob Storage tanpa rahasia.

1. Buat identitas terkelola yang ditetapkan pengguna menggunakan [`az identity create`][az-identity-create] perintah .

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Aktifkan identitas beban kerja AKS dan buat akun layanan untuk digunakan nanti dalam panduan ini menggunakan perintah berikut:

    ```bash
    export AKS_UAMI_WORKLOAD_OBJECTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.principalId')
    export AKS_UAMI_WORKLOAD_RESOURCEID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.id')
    export AKS_UAMI_WORKLOAD_CLIENTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.clientId')

    echo "ObjectId: $AKS_UAMI_WORKLOAD_OBJECTID"
    echo "ResourceId: $AKS_UAMI_WORKLOAD_RESOURCEID"
    echo "ClientId: $AKS_UAMI_WORKLOAD_CLIENTID"
    ```

ID objek adalah pengidentifikasi unik untuk ID klien (juga dikenal sebagai ID aplikasi) yang secara unik mengidentifikasi prinsip keamanan jenis *Aplikasi* dalam penyewa ID Entra. ID sumber daya adalah pengidentifikasi unik untuk mengelola dan menemukan sumber daya di Azure. Nilai-nilai ini diperlukan untuk mengaktifkan identitas beban kerja AKS.

Operator CNPG secara otomatis menghasilkan akun layanan yang disebut *postgres* yang Anda gunakan nanti dalam panduan untuk membuat kredensial federasi yang memungkinkan akses OAuth dari PostgreSQL ke Azure Storage.

## Membuat akun penyimpanan di wilayah utama

1. Buat akun penyimpanan objek untuk menyimpan cadangan PostgreSQL di wilayah utama menggunakan [`az storage account create`][az-storage-account-create] perintah .

    ```bash
    az storage account create \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard_ZRS \
        --kind StorageV2 \
        --query 'provisioningState' \
        --output tsv
    ```

1. Buat kontainer penyimpanan untuk menyimpan Write Ahead Logs (WAL) dan PostgreSQL reguler sesuai permintaan dan pencadangan terjadwal menggunakan [`az storage container create`][az-storage-container-create] perintah .

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Contoh output:

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Jika Anda menemukan pesan kesalahan: `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Harap verifikasi izin pengguna untuk Azure Blob Storage dan, jika **perlu, tingkatkan peran Anda untuk `Storage Blob Data Owner` menggunakan perintah yang disediakan di bawah ini dan setelah mencoba [`az storage container create`][az-storage-container-create] kembali perintah.**

    ```bash
    az role assignment list --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID --output table

    export USER_ID=$(az ad signed-in-user show --query id --output tsv)

    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    az role assignment create \
        --assignee-object-id $USER_ID \
        --assignee-principal-type User \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --role "Storage Blob Data Owner" \
        --output tsv
    ```

## Menetapkan RBAC ke akun penyimpanan

Untuk mengaktifkan cadangan, kluster PostgreSQL perlu membaca dan menulis ke penyimpanan objek. Kluster PostgreSQL yang berjalan di AKS menggunakan identitas beban kerja untuk mengakses akun penyimpanan melalui parameter [`inheritFromAzureAD`][inherit-from-azuread]konfigurasi operator CNPG .

1. Dapatkan ID sumber daya utama untuk akun penyimpanan menggunakan [`az storage account show`][az-storage-account-show] perintah .

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Tetapkan peran bawaan Azure "Storage Blob Data Contributor" ke ID objek dengan cakupan ID sumber daya akun penyimpanan untuk UAMI yang terkait dengan identitas terkelola untuk setiap kluster AKS menggunakan [`az role assignment create`][az-role-assignment-create] perintah .

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Menyiapkan infrastruktur pemantauan

Di bagian ini, Anda menyebarkan instans Azure Managed Grafana, ruang kerja Azure Monitor, dan ruang kerja Azure Monitor Log Analytics untuk mengaktifkan pemantauan kluster PostgreSQL. Anda juga menyimpan referensi ke infrastruktur pemantauan yang dibuat untuk digunakan sebagai input selama proses pembuatan kluster AKS nanti dalam panduan. Bagian ini mungkin perlu waktu untuk menyelesaikannya.

> [!NOTE]
> Instans Azure Managed Grafana dan kluster AKS ditagih secara independen. Untuk informasi harga selengkapnya, lihat [Harga][azure-managed-grafana-pricing] Azure Managed Grafana.

1. Buat instans Azure Managed Grafana menggunakan [`az grafana create`][az-grafana-create] perintah .

    ```bash
    export GRAFANA_PRIMARY="grafana-${LOCAL_NAME}-${SUFFIX}"

    export GRAFANA_RESOURCE_ID=$(az grafana create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $GRAFANA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --zone-redundancy Enabled \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $GRAFANA_RESOURCE_ID
    ```

1. Buat ruang kerja Azure Monitor menggunakan [`az monitor account create`][az-monitor-account-create] perintah .

    ```bash
    export AMW_PRIMARY="amw-${LOCAL_NAME}-${SUFFIX}"

    export AMW_RESOURCE_ID=$(az monitor account create \
        --name $AMW_PRIMARY \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $AMW_RESOURCE_ID
    ```

1. Buat ruang kerja Analitik Log Azure Monitor menggunakan [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create] perintah .

    ```bash
    export ALA_PRIMARY="ala-${LOCAL_NAME}-${SUFFIX}"

    export ALA_RESOURCE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-name $ALA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --query "id" \
        --output tsv)

    echo $ALA_RESOURCE_ID
    ```

## Membuat kluster AKS untuk menghosting kluster PostgreSQL

Di bagian ini, Anda membuat kluster AKS multizone dengan kumpulan simpul sistem. Kluster AKS menghosting replika utama kluster PostgreSQL dan dua replika siaga, masing-masing selaras dengan zona ketersediaan yang berbeda untuk mengaktifkan redundansi zona.

Anda juga menambahkan kumpulan simpul pengguna ke kluster AKS untuk menghosting kluster PostgreSQL. Menggunakan kumpulan simpul terpisah memungkinkan kontrol atas SKU Azure VM yang digunakan untuk PostgreSQL dan memungkinkan kumpulan sistem AKS untuk mengoptimalkan performa dan biaya. Anda menerapkan label ke kumpulan simpul pengguna yang dapat Anda referensikan untuk pilihan simpul saat menyebarkan operator CNPG nanti dalam panduan ini. Bagian ini mungkin perlu waktu untuk menyelesaikannya.

1. Buat kluster AKS menggunakan [`az aks create`][az-aks-create] perintah .

    ```bash
    export SYSTEM_NODE_POOL_VMSKU="standard_d2s_v3"
    export USER_NODE_POOL_NAME="postgres"
    export USER_NODE_POOL_VMSKU="standard_d4s_v3"
    
    az aks create \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --tags $TAGS \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --generate-ssh-keys \
        --node-resource-group $AKS_PRIMARY_MANAGED_RG_NAME \
        --enable-managed-identity \
        --assign-identity $AKS_UAMI_WORKLOAD_RESOURCEID \
        --network-plugin azure \
        --network-plugin-mode overlay \
        --network-dataplane cilium \
        --nodepool-name systempool \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 3 \
        --node-vm-size $SYSTEM_NODE_POOL_VMSKU \
        --enable-azure-monitor-metrics \
        --azure-monitor-workspace-resource-id $AMW_RESOURCE_ID \
        --grafana-resource-id $GRAFANA_RESOURCE_ID \
        --api-server-authorized-ip-ranges $MY_PUBLIC_CLIENT_IP \
        --tier standard \
        --kubernetes-version $AKS_CLUSTER_VERSION \
        --zones 1 2 3 \
        --output table
    ```

2. Tambahkan kumpulan simpul pengguna ke kluster AKS menggunakan [`az aks nodepool add`][az-aks-node-pool-add] perintah .

    ```bash
    az aks nodepool add \
        --resource-group $RESOURCE_GROUP_NAME \
        --cluster-name $AKS_PRIMARY_CLUSTER_NAME \
        --name $USER_NODE_POOL_NAME \
        --enable-cluster-autoscaler \
        --min-count 3 \
        --max-count 6 \
        --node-vm-size $USER_NODE_POOL_VMSKU \
        --zones 1 2 3 \
        --labels workload=postgres \
        --output table
    ```

> [!NOTE]
> Jika Anda menerima pesan `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` kesalahan saat menambahkan kumpulan simpul AKS, harap tunggu beberapa menit hingga operasi kluster AKS selesai lalu jalankan `az aks nodepool add` perintah.

## Menyambungkan ke kluster AKS dan membuat namespace layanan

Di bagian ini, Anda mendapatkan kredensial kluster AKS, yang berfungsi sebagai kunci yang memungkinkan Anda mengautentikasi dan berinteraksi dengan kluster. Setelah tersambung, Anda membuat dua namespace: satu untuk layanan manajer pengontrol CNPG dan satu untuk kluster PostgreSQL dan layanan terkait.

1. Dapatkan kredensial kluster AKS menggunakan [`az aks get-credentials`][az-aks-get-credentials] perintah .

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Buat namespace layanan untuk layanan manajer pengontrol CNPG, kluster PostgreSQL, dan layanan terkait dengan menggunakan [`kubectl create namespace`][kubectl-create-namespace] perintah .

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Memperbarui infrastruktur pemantauan

Ruang kerja Azure Monitor untuk Prometheus Terkelola dan Azure Managed Grafana secara otomatis ditautkan ke kluster AKS untuk metrik dan visualisasi selama proses pembuatan kluster. Di bagian ini, Anda mengaktifkan pengumpulan log dengan wawasan Kontainer AKS dan memvalidasi bahwa Prometheus Terkelola mengekstrak metrik dan wawasan Kontainer menyerap log.

1. Aktifkan pemantauan wawasan Kontainer pada kluster AKS menggunakan [`az aks enable-addons`][az-aks-enable-addons] perintah .

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Validasi bahwa Prometheus Terkelola mengekstrak metrik dan wawasan Kontainer menyerap log dari kluster AKS dengan memeriksa DaemonSet menggunakan [`kubectl get`][kubectl-get] perintah dan [`az aks show`][az-aks-show] perintah .

    ```bash
    kubectl get ds ama-metrics-node \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    kubectl get ds ama-logs \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    az aks show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --query addonProfiles
    ```

    Output Anda harus menyerupai contoh output berikut, dengan *total enam* simpul (tiga untuk kumpulan simpul sistem dan tiga untuk kumpulan simpul PostgreSQL) dan wawasan Kontainer yang `"enabled": true`menunjukkan :

    ```output
    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-metrics-node   6         6         6       6            6           <none>       

    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-logs           6         6         6       6            6           <none>       

    {
      "omsagent": {
        "config": {
          "logAnalyticsWorkspaceResourceID": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-cnpg-9vbin3p8/providers/Microsoft.OperationalInsights/workspaces/ala-cnpg-9vbin3p8",
          "useAADAuth": "true"
        },
        "enabled": true,
        "identity": null
      }
    }
    ```

## Membuat IP statis publik untuk ingress kluster PostgreSQL

Untuk memvalidasi penyebaran kluster PostgreSQL dan menggunakan alat PostgreSQL klien, seperti *psql* dan *PgAdmin*, Anda perlu mengekspos replika utama dan baca-saja untuk masuk. Di bagian ini, Anda membuat sumber daya IP publik Azure yang nantinya Anda berikan ke load balancer Azure untuk mengekspos titik akhir PostgreSQL untuk kueri.

1. Dapatkan nama grup sumber daya simpul kluster AKS menggunakan [`az aks show`][az-aks-show] perintah .

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Buat alamat IP publik menggunakan [`az network public-ip create`][az-network-public-ip-create] perintah .

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_NAME="$AKS_PRIMARY_CLUSTER_NAME-pip"

    az network public-ip create \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard \
        --zone 1 2 3 \
        --allocation-method static \
        --output table
    ```

3. Dapatkan alamat IP publik yang baru dibuat menggunakan [`az network public-ip show`][az-network-public-ip-show] perintah .

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Dapatkan ID sumber daya grup sumber daya simpul menggunakan [`az group show`][az-group-show] perintah .

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Tetapkan peran "Kontributor Jaringan" ke ID objek UAMI menggunakan cakupan grup sumber daya simpul menggunakan [`az role assignment create`][az-role-assignment-create] perintah .

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Menginstal operator CNPG di kluster AKS

Di bagian ini, Anda menginstal operator CNPG di kluster AKS menggunakan Helm atau manifes YAML.

### [Helm](#tab/helm)

1. Tambahkan repositori CNPG Helm menggunakan [`helm repo add`][helm-repo-add] perintah .

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Tingkatkan repositori CNPG Helm dan instal pada kluster AKS menggunakan [`helm upgrade`][helm-upgrade] perintah dengan `--install` bendera .

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Verifikasi penginstalan operator pada kluster AKS menggunakan [`kubectl get`][kubectl-get] perintah .

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Instal operator CNPG pada kluster AKS menggunakan [`kubectl apply`][kubectl-apply] perintah .

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Verifikasi penginstalan operator pada kluster AKS menggunakan [`kubectl get`][kubectl-get] perintah .

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Langkah berikutnya

> [!div class="nextstepaction"]
> [Menyebarkan database PostgreSQL yang sangat tersedia pada kluster AKS][deploy-postgresql]

## Kontributor

*Artikel ini dikelola oleh Microsoft. Awalnya ditulis oleh kontributor* berikut:

* Ken Kilty | TPM Utama
* Russell de Pina | TPM Utama
* Adrian Joian | Insinyur Pelanggan Senior
* Jenny Hayes | Pengembang Konten Senior
* Carol Smith | Pengembang Konten Senior
* Erin Schaffer | Pengembang Konten 2

<!-- LINKS -->
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-grafana-create]: /cli/azure/grafana#az-grafana-create
[postgresql-ha-deployment-overview]: ./postgresql-ha-overview.md
[az-extension-add]: /cli/azure/extension#az_extension_add
[az-group-create]: /cli/azure/group#az_group_create
[az-storage-account-create]: /cli/azure/storage/account#az_storage_account_create
[az-storage-container-create]: /cli/azure/storage/container#az_storage_container_create
[inherit-from-azuread]: https://cloudnative-pg.io/documentation/1.23/appendixes/object_stores/#azure-blob-storage
[az-storage-account-show]: /cli/azure/storage/account#az_storage_account_show
[az-role-assignment-create]: /cli/azure/role/assignment#az_role_assignment_create
[az-monitor-account-create]: /cli/azure/monitor/account#az_monitor_account_create
[az-monitor-log-analytics-workspace-create]: /cli/azure/monitor/log-analytics/workspace#az_monitor_log_analytics_workspace_create
[azure-managed-grafana-pricing]: https://azure.microsoft.com/pricing/details/managed-grafana/
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-node-pool-add]: /cli/azure/aks/nodepool#az_aks_nodepool_add
[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[az-aks-enable-addons]: /cli/azure/aks#az_aks_enable_addons
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-show]: /cli/azure/network/public-ip#az_network_public_ip_show
[az-group-show]: /cli/azure/group#az_group_show
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[deploy-postgresql]: ./deploy-postgresql-ha.md
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
