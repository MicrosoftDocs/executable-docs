---
title: Menyebarkan database PostgreSQL yang sangat tersedia di AKS dengan Azure CLI
description: 'Dalam artikel ini, Anda menyebarkan database PostgreSQL yang sangat tersedia di AKS menggunakan operator CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Menyebarkan database PostgreSQL yang sangat tersedia di AKS

Dalam artikel ini, Anda menyebarkan database PostgreSQL yang sangat tersedia di AKS.

* Jika Anda belum membuat infrastruktur yang diperlukan untuk penyebaran ini, ikuti langkah-langkah dalam [Membuat infrastruktur untuk menyebarkan database PostgreSQL yang sangat tersedia di AKS][create-infrastructure] untuk disiapkan, lalu Anda dapat kembali ke artikel ini.

## Membuat rahasia untuk pengguna aplikasi bootstrap

1. Buat rahasia untuk memvalidasi penyebaran PostgreSQL dengan masuk interaktif untuk pengguna aplikasi bootstrap menggunakan [`kubectl create secret`][kubectl-create-secret] perintah .

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Validasi bahwa rahasia berhasil dibuat menggunakan [`kubectl get`][kubectl-get] perintah .

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Mengatur variabel lingkungan untuk kluster PostgreSQL

* Sebarkan ConfigMap untuk mengatur variabel lingkungan untuk kluster PostgreSQL menggunakan perintah berikut [`kubectl apply`][kubectl-apply] :

    ```bash
    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME -n $PG_NAMESPACE -f -
    apiVersion: v1
    kind: ConfigMap
    metadata:
        name: cnpg-controller-manager-config
    data:
        ENABLE_AZURE_PVC_UPDATES: 'true'
    EOF
    ```

## Menginstal Prometheus PodMonitors

Prometheus membuat PodMonitors untuk instans CNPG menggunakan sekumpulan aturan perekaman default yang disimpan pada repositori sampel GitHub CNPG. Dalam lingkungan produksi, aturan ini akan dimodifikasi sesuai kebutuhan.

1. Tambahkan repositori Prometheus Community Helm menggunakan [`helm repo add`][helm-repo-add] perintah .

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Tingkatkan repositori Prometheus Community Helm dan instal pada kluster utama menggunakan [`helm upgrade`][helm-upgrade] perintah dengan `--install` bendera .

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Verifikasi bahwa monitor pod dibuat.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Buat info masuk terfederasi

Di bagian ini, Anda membuat kredensial identitas federasi untuk cadangan PostgreSQL untuk memungkinkan CNPG menggunakan identitas beban kerja AKS untuk mengautentikasi ke tujuan akun penyimpanan untuk cadangan. Operator CNPG membuat akun layanan Kubernetes dengan nama yang sama dengan kluster bernama yang digunakan dalam manifes penyebaran Kluster CNPG.

1. Dapatkan URL pengeluar sertifikat OIDC dari kluster menggunakan [`az aks show`][az-aks-show] perintah .

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Buat kredensial identitas federasi menggunakan [`az identity federated-credential create`][az-identity-federated-credential-create] perintah .

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Menyebarkan kluster PostgreSQL yang sangat tersedia

Di bagian ini, Anda menyebarkan kluster PostgreSQL yang sangat tersedia menggunakan [definisi sumber daya kustom Kluster CNPG (CRD)][cluster-crd].

Tabel berikut menguraikan properti utama yang ditetapkan dalam manifes penyebaran YAML untuk Kluster CRD:

| Properti | Definisi |
| --------- | ------------ |
| `inheritedMetadata` | Khusus untuk operator CNPG. Metadata diwariskan oleh semua objek yang terkait dengan kluster. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Label DNS untuk digunakan saat mengekspos titik akhir kluster Postgres baca-tulis dan baca-saja. |
| `labels: azure.workload.identity/use: "true"` | Menunjukkan bahwa AKS harus menyuntikkan dependensi identitas beban kerja ke dalam pod yang menghosting instans kluster PostgreSQL. |
| `topologySpreadConstraints` | Memerlukan zona yang berbeda dan node yang berbeda dengan label `"workload=postgres"`. |
| `resources` | Mengonfigurasi kelas Quality of Service (QoS) dari *Guaranteed*. Dalam lingkungan produksi, nilai-nilai ini adalah kunci untuk memaksimalkan penggunaan VM simpul yang mendasar dan bervariasi berdasarkan Azure VM SKU yang digunakan. |
| `bootstrap` | Khusus untuk operator CNPG. Menginisialisasi dengan database aplikasi kosong. |
| `storage` / `walStorage` | Khusus untuk operator CNPG. Menentukan templat penyimpanan untuk PersistentVolumeClaims (PVC) untuk penyimpanan data dan log. Dimungkinkan juga untuk menentukan penyimpanan untuk ruang tabel untuk memecah untuk peningkatan IOP. |
| `replicationSlots` | Khusus untuk operator CNPG. Mengaktifkan slot replikasi untuk ketersediaan tinggi. |
| `postgresql` | Khusus untuk operator CNPG. Pengaturan peta untuk `postgresql.conf`, `pg_hba.conf`, dan `pg_ident.conf config`. |
| `serviceAccountTemplate` | Berisi templat yang diperlukan untuk menghasilkan akun layanan dan memetakan kredensial identitas federasi AKS ke UAMI untuk mengaktifkan autentikasi identitas beban kerja AKS dari pod yang menghosting instans PostgreSQL ke sumber daya Azure eksternal. |
| `barmanObjectStore` | Khusus untuk operator CNPG. Mengonfigurasi rangkaian alat barman-cloud menggunakan identitas beban kerja AKS untuk autentikasi ke penyimpanan objek Azure Blob Storage. |

1. Sebarkan kluster PostgreSQL dengan Cluster CRD menggunakan [`kubectl apply`][kubectl-apply] perintah .

    ```bash
    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME -n $PG_NAMESPACE -v 9 -f -
    apiVersion: postgresql.cnpg.io/v1
    kind: Cluster
    metadata:
      name: $PG_PRIMARY_CLUSTER_NAME
    spec:
      inheritedMetadata:
        annotations:
          service.beta.kubernetes.io/azure-dns-label-name: $AKS_PRIMARY_CLUSTER_PG_DNSPREFIX
        labels:
          azure.workload.identity/use: "true"
      
      instances: 3
      startDelay: 30
      stopDelay: 30
      minSyncReplicas: 1
      maxSyncReplicas: 1
      replicationSlots:
        highAvailability:
          enabled: true
        updateInterval: 30
      
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            cnpg.io/cluster: $PG_PRIMARY_CLUSTER_NAME
      
      affinity:
        nodeSelector:
          workload: postgres
      
      resources:
        requests:
          memory: '8Gi'
          cpu: 2
        limits:
          memory: '8Gi'
          cpu: 2
      
      bootstrap:
        initdb:
          database: appdb
          owner: app
          secret:
            name: db-user-pass
          dataChecksums: true
      
      storage:
        size: 2Gi
        pvcTemplate:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 2Gi
          storageClassName: managed-csi-premium
      
      walStorage:
        size: 2Gi
        pvcTemplate:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 2Gi
          storageClassName: managed-csi-premium
      
      monitoring:
        enablePodMonitor: true
      
      postgresql:
        parameters:
          archive_timeout: '5min'
          auto_explain.log_min_duration: '10s'
          checkpoint_completion_target: '0.9'
          checkpoint_timeout: '15min'
          shared_buffers: '256MB'
          effective_cache_size: '512MB'
          pg_stat_statements.max: '1000'
          pg_stat_statements.track: 'all'
          max_connections: '400'
          max_prepared_transactions: '400'
          max_parallel_workers: '32'
          max_parallel_maintenance_workers: '8'
          max_parallel_workers_per_gather: '8'
          max_replication_slots: '32'
          max_worker_processes: '32'
          wal_keep_size: '512MB'
          max_wal_size: '1GB'
        pg_hba:
          - host all all all scram-sha-256
      
      serviceAccountTemplate:
        metadata:
          annotations:
            azure.workload.identity/client-id: "$AKS_UAMI_WORKLOAD_CLIENTID"  
          labels:
            azure.workload.identity/use: "true"
      
      backup:
        barmanObjectStore:
          destinationPath: "https://${PG_PRIMARY_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/backups"
          azureCredentials:
            inheritFromAzureAD: true
        
        retentionPolicy: '7d'
    EOF
    ```

1. Validasi bahwa kluster PostgreSQL utama berhasil dibuat menggunakan [`kubectl get`][kubectl-get] perintah . CRD Kluster CNPG menentukan tiga instans, yang dapat divalidasi dengan melihat pod yang berjalan setelah setiap instans dibesarkan dan bergabung untuk replikasi. Bersabarlah karena dapat memakan waktu bagi ketiga instans untuk online dan bergabung dengan kluster.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Contoh output

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Memvalidasi Prometheus PodMonitor sedang berjalan

Operator CNPG secara otomatis membuat PodMonitor untuk instans utama menggunakan aturan perekaman yang dibuat selama [penginstalan](#install-the-prometheus-podmonitors) Prometheus Community.

1. Validasi PodMonitor yang berjalan menggunakan [`kubectl get`][kubectl-get] perintah .

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Contoh output

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Jika Anda menggunakan Azure Monitor untuk Prometheus Terkelola, Anda harus menambahkan monitor pod lain menggunakan nama grup kustom. Prometheus terkelola tidak mengambil definisi sumber daya kustom (CRD) dari komunitas Prometheus. Selain dari nama grup, CRDnya sama. Hal ini memungkinkan monitor pod untuk Prometheus Terkelola ada secara berdampingan yang menggunakan monitor pod komunitas. Jika Anda tidak menggunakan Prometheus Terkelola, Anda dapat melewati ini. Buat monitor pod baru:

```bash
cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -f -
apiVersion: azmonitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: cnpg-cluster-metrics-managed-prometheus
  namespace: ${PG_NAMESPACE}
  labels:
    azure.workload.identity/use: "true"
    cnpg.io/cluster: ${PG_PRIMARY_CLUSTER_NAME}
spec:
  selector:
    matchLabels:
      azure.workload.identity/use: "true"
      cnpg.io/cluster: ${PG_PRIMARY_CLUSTER_NAME}
  podMetricsEndpoints:
    - port: metrics
EOF
```

Verifikasi bahwa monitor pod dibuat (perhatikan perbedaan nama grup).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Opsi A - Ruang Kerja Azure Monitor

Setelah menyebarkan kluster Postgres dan monitor pod, Anda dapat melihat metrik menggunakan portal Azure di ruang kerja Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Cuplikan layar memperlihatkan metrik di ruang kerja Azure Monitor." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Opsi B - Grafana Terkelola

Atau, Setelah Anda menyebarkan kluster Postgres dan monitor pod, Anda dapat membuat dasbor metrik pada instans Grafana Terkelola yang dibuat oleh skrip penyebaran untuk memvisualisasikan metrik yang diekspor ke ruang kerja Azure Monitor. Anda dapat mengakses Managed Grafana melalui portal Azure. Navigasikan ke instans Grafana Terkelola yang dibuat oleh skrip penyebaran dan klik tautan Titik Akhir seperti yang ditunjukkan di sini:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Cuplikan layar memperlihatkan instans Azure Managed Grafana." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Mengklik tautan Titik Akhir akan menyebabkan jendela browser baru terbuka di mana Anda dapat membuat dasbor pada instans Grafana Terkelola. Mengikuti instruksi untuk [mengonfigurasi sumber](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) data Azure Monitor, Anda kemudian dapat menambahkan visualisasi untuk membuat dasbor metrik dari kluster Postgres. Setelah menyiapkan koneksi sumber data, dari menu utama, klik opsi Sumber data dan Anda akan melihat sekumpulan opsi sumber data untuk koneksi sumber data seperti yang ditunjukkan di sini:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Cuplikan layar memperlihatkan opsi sumber data." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Pada opsi Prometheus Terkelola, klik opsi untuk membangun dasbor untuk membuka editor dasbor. Setelah jendela editor terbuka, klik opsi Tambahkan visualisasi lalu klik opsi Prometheus Terkelola untuk menelusuri metrik dari kluster Postgres. Setelah Anda memilih metrik yang ingin Anda visualisasikan, klik tombol Jalankan kueri untuk mengambil data untuk visualisasi seperti yang diperlihatkan di sini:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Cuplikan layar memperlihatkan dasbor konstruksi." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Klik tombol Simpan untuk menambahkan panel ke dasbor Anda. Anda dapat menambahkan panel lain dengan mengklik tombol Tambahkan di editor dasbor dan mengulangi proses ini untuk memvisualisasikan metrik lain. Menambahkan visualisasi metrik, Anda harus memiliki sesuatu yang terlihat seperti ini:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Cuplikan layar memperlihatkan dasbor penyimpanan." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Klik ikon Simpan untuk menyimpan dasbor Anda.

## Memeriksa kluster PostgreSQL yang disebarkan

Validasi bahwa PostgreSQL tersebar di beberapa zona ketersediaan dengan mengambil detail simpul AKS menggunakan [`kubectl get`][kubectl-get] perintah .

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Output Anda harus menyerupai contoh output berikut dengan zona ketersediaan yang ditampilkan untuk setiap simpul:

```output
{
    "node": "aks-postgres-15810965-vmss000000",
    "zone": "westus3-1"
}
{
    "node": "aks-postgres-15810965-vmss000001",
    "zone": "westus3-2"
}
{
    "node": "aks-postgres-15810965-vmss000002",
    "zone": "westus3-3"
}
{
    "node": "aks-systempool-26112968-vmss000000",
    "zone": "westus3-1"
}
{
    "node": "aks-systempool-26112968-vmss000001",
    "zone": "westus3-2"
}
```

## Menyambungkan ke PostgreSQL dan membuat himpunan data sampel

Di bagian ini, Anda membuat tabel dan menyisipkan beberapa data ke dalam database aplikasi yang dibuat di CRD Kluster CNPG yang Anda sebarkan sebelumnya. Anda menggunakan data ini untuk memvalidasi operasi pencadangan dan pemulihan untuk kluster PostgreSQL.

* Buat tabel dan sisipkan data ke database aplikasi menggunakan perintah berikut:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    # Run the following PSQL commands to create a small dataset
    # postgres=#

    CREATE TABLE datasample (id INTEGER,name VARCHAR(255));
    INSERT INTO datasample (id, name) VALUES (1, 'John');
    INSERT INTO datasample (id, name) VALUES (2, 'Jane');
    INSERT INTO datasample (id, name) VALUES (3, 'Alice');
    SELECT COUNT(*) FROM datasample;
    
    # Type \q to exit psql
    ```

    Output Anda harus menyerupai contoh output berikut:

    ```output
    CREATE TABLE
    INSERT 0 1
    INSERT 0 1
    INSERT 0 1
    count
    -------
        3
    (1 row)
    ```
## Menyambungkan ke replika baca-saja PostgreSQL

* Sambungkan ke replika baca-saja PostgreSQL dan validasi himpunan data sampel menggunakan perintah berikut:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Contoh output

    ```output
    # pg_is_in_recovery
    #-------------------
    # t
    #(1 row)
    ```

    ```sql
    #postgres=# 
    SELECT COUNT(*) FROM datasample;
    ```

    Contoh output

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Menyiapkan cadangan PostgreSQL sesuai permintaan dan terjadwal menggunakan Barman

1. Validasi bahwa kluster PostgreSQL dapat mengakses akun penyimpanan Azure yang ditentukan dalam CRD Kluster CNPG dan yang `Working WAL archiving` melaporkan sebagai `OK` menggunakan perintah berikut:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Contoh output

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Sebarkan cadangan sesuai permintaan ke Azure Storage, yang menggunakan integrasi identitas beban kerja AKS, menggunakan file YAML dengan [`kubectl apply`][kubectl-apply] perintah .

    ```bash
    export BACKUP_ONDEMAND_NAME="on-demand-backup-1"

    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -v 9 -f -
    apiVersion: postgresql.cnpg.io/v1
    kind: Backup
    metadata:
      name: $BACKUP_ONDEMAND_NAME
    spec:
      method: barmanObjectStore
      cluster:
        name: $PG_PRIMARY_CLUSTER_NAME
    EOF
    ```

1. Validasi status cadangan sesuai permintaan menggunakan [`kubectl describe`][kubectl-describe] perintah .

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Contoh output

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Validasi bahwa kluster memiliki titik pemulihan pertama menggunakan perintah berikut:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Contoh output

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Konfigurasikan cadangan terjadwal untuk *setiap jam pada 15 menit melewati jam* menggunakan file YAML dengan [`kubectl apply`][kubectl-apply] perintah .

    ```bash
    export BACKUP_SCHEDULED_NAME="scheduled-backup-1"

    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -v 9 -f -
    apiVersion: postgresql.cnpg.io/v1
    kind: ScheduledBackup
    metadata:
      name: $BACKUP_SCHEDULED_NAME
    spec:
      # Backup once per hour
      schedule: "0 15 * ? * *"
      backupOwnerReference: self
      cluster:
        name: $PG_PRIMARY_CLUSTER_NAME
    EOF
    ```

1. Validasi status pencadangan terjadwal menggunakan [`kubectl describe`][kubectl-describe] perintah .

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Lihat file cadangan yang disimpan di penyimpanan blob Azure untuk kluster utama menggunakan [`az storage blob list`][az-storage-blob-list] perintah .

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Output Anda harus menyerupai contoh output berikut, memvalidasi cadangan berhasil:

    ```output
    [
      "pg-primary-cnpg-r8c7unrw/base/20240605T134715/backup.info",
      "pg-primary-cnpg-r8c7unrw/base/20240605T134715/data.tar",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000001",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000002",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000003",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000003.00000028.backup",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000004",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000005",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000005.00000028.backup",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000006",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000007",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000008",
      "pg-primary-cnpg-r8c7unrw/wals/0000000100000000/000000010000000000000009"
    ]
    ```

## Memulihkan cadangan sesuai permintaan ke kluster PostgreSQL baru

Di bagian ini, Anda memulihkan cadangan sesuai permintaan yang Anda buat sebelumnya menggunakan operator CNPG ke instans baru menggunakan Bootstrap Cluster CRD. Kluster instans tunggal digunakan untuk kesederhanaan. Ingatlah bahwa identitas beban kerja AKS (melalui CNPG inheritFromAzureAD) mengakses file cadangan, dan bahwa nama kluster pemulihan digunakan untuk menghasilkan akun layanan Kubernetes baru khusus untuk kluster pemulihan.

Anda juga membuat kredensial federasi kedua untuk memetakan akun layanan kluster pemulihan baru ke UAMI yang ada yang memiliki akses "Kontributor Data Blob Penyimpanan" ke file cadangan pada penyimpanan blob.

1. Buat kredensial identitas federasi kedua menggunakan [`az identity federated-credential create`][az-identity-federated-credential-create] perintah .

    ```bash
    export PG_PRIMARY_CLUSTER_NAME_RECOVERED="$PG_PRIMARY_CLUSTER_NAME-recovered-db"

    az identity federated-credential create \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME_RECOVERED}" \
        --audience api://AzureADTokenExchange
    ```

1. Pulihkan cadangan sesuai permintaan menggunakan Cluster CRD dengan [`kubectl apply`][kubectl-apply] perintah .

    ```bash
    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -v 9 -f -
    apiVersion: postgresql.cnpg.io/v1
    kind: Cluster
    metadata:
      name: $PG_PRIMARY_CLUSTER_NAME_RECOVERED
    spec:
    
      inheritedMetadata:
        annotations:
          service.beta.kubernetes.io/azure-dns-label-name: $AKS_PRIMARY_CLUSTER_PG_DNSPREFIX
        labels:
          azure.workload.identity/use: "true"
    
      instances: 1
    
      affinity:
        nodeSelector:
          workload: postgres
    
      # Point to cluster backup created earlier and stored on Azure Blob Storage
      bootstrap:
        recovery:
          source: clusterBackup
    
      storage:
        size: 2Gi
        pvcTemplate:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 2Gi
          storageClassName: managed-csi-premium
          volumeMode: Filesystem
    
      walStorage:
        size: 2Gi
        pvcTemplate:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 2Gi
          storageClassName: managed-csi-premium
          volumeMode: Filesystem
      
      serviceAccountTemplate:
        metadata:
          annotations:
            azure.workload.identity/client-id: "$AKS_UAMI_WORKLOAD_CLIENTID"  
          labels:
            azure.workload.identity/use: "true"
    
      externalClusters:
        - name: clusterBackup
          barmanObjectStore:
            destinationPath: https://${PG_PRIMARY_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/backups
            serverName: $PG_PRIMARY_CLUSTER_NAME
            azureCredentials:
              inheritFromAzureAD: true
            wal:
              maxParallel: 8
    EOF
    ```

1. Sambungkan ke instans yang dipulihkan, lalu validasi bahwa himpunan data yang dibuat pada kluster asli tempat pencadangan penuh diambil ada menggunakan perintah berikut:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Contoh output

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Hapus kluster yang dipulihkan menggunakan perintah berikut:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Hapus kredensial identitas federasi menggunakan [`az identity federated-credential delete`][az-identity-federated-credential-delete] perintah .

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Mengekspos kluster PostgreSQL menggunakan load balancer publik

Di bagian ini, Anda mengonfigurasi infrastruktur yang diperlukan untuk mengekspos titik akhir baca-tulis dan baca-saja PostgreSQL dengan pembatasan sumber IP ke alamat IP publik stasiun kerja klien Anda.

Anda juga mengambil titik akhir berikut dari layanan IP Kluster:

* *Satu* titik akhir baca-tulis utama yang berakhir dengan `*-rw`.
* *Nol hingga N* (tergantung pada jumlah replika) titik akhir baca-saja yang diakhir dengan `*-ro`.
* *Satu* titik akhir replikasi yang diakhiri dengan `*-r`.

1. Dapatkan detail layanan IP Kluster menggunakan [`kubectl get`][kubectl-get] perintah .

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Contoh output

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Ada tiga layanan: `namespace/cluster-name-ro` dipetakan ke port 5433, `namespace/cluster-name-rw`, dan `namespace/cluster-name-r` dipetakan ke port 5433. Penting untuk menghindari penggunaan port yang sama dengan node baca/tulis kluster database PostgreSQL. Jika Anda ingin aplikasi hanya mengakses replika baca-saja dari kluster database PostgreSQL, arahkan ke port 5433. Layanan akhir biasanya digunakan untuk pencadangan data tetapi juga dapat berfungsi sebagai simpul baca-saja.

1. Dapatkan detail layanan menggunakan [`kubectl get`][kubectl-get] perintah .

    ```bash
    export PG_PRIMARY_CLUSTER_RW_SERVICE=$(kubectl get services \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        -l "cnpg.io/cluster" \
        --output json | jq -r '.items[] | select(.metadata.name | endswith("-rw")) | .metadata.name')

    echo $PG_PRIMARY_CLUSTER_RW_SERVICE

    export PG_PRIMARY_CLUSTER_RO_SERVICE=$(kubectl get services \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        -l "cnpg.io/cluster" \
        --output json | jq -r '.items[] | select(.metadata.name | endswith("-ro")) | .metadata.name')

    echo $PG_PRIMARY_CLUSTER_RO_SERVICE
    ```

1. Konfigurasikan layanan load balancer dengan file YAML berikut menggunakan [`kubectl apply`][kubectl-apply] perintah .

    ```bash
    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME -f -
    apiVersion: v1
    kind: Service
    metadata:
      annotations:
        service.beta.kubernetes.io/azure-load-balancer-resource-group: $AKS_PRIMARY_CLUSTER_NODERG_NAME
        service.beta.kubernetes.io/azure-pip-name: $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME
        service.beta.kubernetes.io/azure-dns-label-name: $AKS_PRIMARY_CLUSTER_PG_DNSPREFIX
      name: cnpg-cluster-load-balancer-rw
      namespace: "${PG_NAMESPACE}"
    spec:
      type: LoadBalancer
      ports: 
      - protocol: TCP
        port: 5432
        targetPort: 5432
      selector:
        cnpg.io/instanceRole: primary
        cnpg.io/podRole: instance
      loadBalancerSourceRanges:
      - "$MY_PUBLIC_CLIENT_IP/32"
    EOF
    
    cat <<EOF | kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME -f -
    apiVersion: v1
    kind: Service
    metadata:
      annotations:
        service.beta.kubernetes.io/azure-load-balancer-resource-group: $AKS_PRIMARY_CLUSTER_NODERG_NAME
        service.beta.kubernetes.io/azure-pip-name: $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME
        service.beta.kubernetes.io/azure-dns-label-name: $AKS_PRIMARY_CLUSTER_PG_DNSPREFIX
      name: cnpg-cluster-load-balancer-ro
      namespace: "${PG_NAMESPACE}"
    spec:
      type: LoadBalancer
      ports: 
      - protocol: TCP
        port: 5433
        targetPort: 5432
      selector:
        cnpg.io/instanceRole: replica
        cnpg.io/podRole: instance
      loadBalancerSourceRanges:
      - "$MY_PUBLIC_CLIENT_IP/32"
    EOF
    ```

1. Dapatkan detail layanan menggunakan [`kubectl describe`][kubectl-describe] perintah .

    ```bash
    kubectl describe service cnpg-cluster-load-balancer-rw \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE

    kubectl describe service cnpg-cluster-load-balancer-ro \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE

    export AKS_PRIMARY_CLUSTER_ALB_DNSNAME="$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query "dnsSettings.fqdn" --output tsv)"

    echo $AKS_PRIMARY_CLUSTER_ALB_DNSNAME
    ```

### Memvalidasi titik akhir PostgreSQL publik

Di bagian ini, Anda memvalidasi bahwa Azure Load Balancer disiapkan dengan benar menggunakan IP statis yang Anda buat sebelumnya dan koneksi perutean ke replika baca-tulis dan baca-saja utama dan gunakan CLI psql untuk menyambungkan ke keduanya.

Ingatlah bahwa titik akhir baca-tulis utama memetakan ke port TCP 5432 dan titik akhir replika baca-saja memetakan ke port 5433 untuk memungkinkan nama DNS PostgreSQL yang sama digunakan untuk pembaca dan penulis.

> [!NOTE]
> Anda memerlukan nilai kata sandi pengguna aplikasi untuk autentikasi dasar PostgreSQL yang dihasilkan sebelumnya dan disimpan dalam `$PG_DATABASE_APPUSER_SECRET` variabel lingkungan.

* Validasi titik akhir PostgreSQL publik menggunakan perintah berikut `psql` :

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Contoh output

    ```output
    pg_is_in_recovery
    -------------------
     f
    (1 row)
    ```

    ```bash
    echo "Query a replica, pg_is_in_recovery = true"
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5433 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Contoh output

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Ketika berhasil tersambung ke titik akhir baca-tulis utama, fungsi PostgreSQL mengembalikan `f` untuk *false*, yang menunjukkan bahwa koneksi saat ini dapat ditulis.

    Saat tersambung ke replika, fungsi mengembalikan `t` true**, menunjukkan database dalam pemulihan dan baca-saja.

## Mensimulasikan failover yang tidak direncanakan

Di bagian ini, Anda memicu kegagalan mendadak dengan menghapus pod yang menjalankan primer, yang mensimulasikan crash mendadak atau hilangnya konektivitas jaringan ke node yang menghosting primer PostgreSQL.

1. Periksa status instans pod yang sedang berjalan menggunakan perintah berikut:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Contoh output

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Hapus pod utama menggunakan [`kubectl delete`][kubectl-delete] perintah .

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Validasi bahwa `pg-primary-cnpg-sryti1qf-2` instans pod sekarang menjadi yang utama menggunakan perintah berikut:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Contoh output

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Reset `pg-primary-cnpg-sryti1qf-1` instans pod sebagai primer menggunakan perintah berikut:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Validasi bahwa instans pod telah kembali ke status aslinya sebelum pengujian failover yang tidak direncanakan menggunakan perintah berikut:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Contoh output

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Membersihkan sumber daya

* Setelah selesai meninjau penyebaran, hapus semua sumber daya yang Anda buat dalam panduan ini menggunakan [`az group delete`][az-group-delete] perintah .

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Langkah berikutnya

Dalam panduan ini, Anda mempelajari cara:

* Gunakan Azure CLI untuk membuat kluster AKS multi-zona.
* Sebarkan kluster dan database PostgreSQL yang sangat tersedia menggunakan operator CNPG.
* Siapkan pemantauan untuk PostgreSQL menggunakan Prometheus dan Grafana.
* Sebarkan himpunan data sampel ke database PostgreSQL.
* Lakukan peningkatan kluster PostgreSQL dan AKS.
* Simulasikan gangguan kluster dan failover replika PostgreSQL.
* Lakukan pencadangan dan pemulihan database PostgreSQL.

Untuk mempelajari selengkapnya tentang bagaimana Anda dapat memanfaatkan AKS untuk beban kerja Anda, lihat [Apa itu Azure Kubernetes Service (AKS)?][what-is-aks]

## Kontributor

*Artikel ini dikelola oleh Microsoft. Awalnya ditulis oleh kontributor* berikut:

* Ken Kilty | TPM Utama
* Russell de Pina | TPM Utama
* Adrian Joian | Insinyur Pelanggan Senior
* Jenny Hayes | Pengembang Konten Senior
* Carol Smith | Pengembang Konten Senior
* Erin Schaffer | Pengembang Konten 2
* Adam Sharif | Teknisi Pelanggan 2

<!-- LINKS -->
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[create-infrastructure]: ./create-postgresql-ha.md
[kubectl-create-secret]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_secret/
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az_identity_federated_credential_create
[cluster-crd]: https://cloudnative-pg.io/documentation/1.23/cloudnative-pg.v1/#postgresql-cnpg-io-v1-ClusterSpec
[kubectl-describe]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_describe/
[az-storage-blob-list]: /cli/azure/storage/blob/#az_storage_blob_list
[az-identity-federated-credential-delete]: /cli/azure/identity/federated-credential#az_identity_federated_credential_delete
[kubectl-delete]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_delete/
[az-group-delete]: /cli/azure/group#az_group_delete
[what-is-aks]: ./what-is-aks.md
