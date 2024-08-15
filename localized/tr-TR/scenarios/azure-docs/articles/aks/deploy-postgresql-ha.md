---
title: Azure CLI ile AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtma
description: Bu makalede CloudNativePG işlecini kullanarak AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtacaksınız.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# AKS'de yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtma

Bu makalede AKS üzerinde yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtacaksınız.

* Bu dağıtım için gerekli altyapıyı henüz oluşturmadıysanız, ayarlamak üzere AKS'de [][create-infrastructure] yüksek oranda kullanılabilir bir PostgreSQL veritabanı dağıtmak için altyapı oluşturma başlığındaki adımları izleyin ve sonra bu makaleye dönebilirsiniz.

## Bootstrap uygulaması kullanıcısı için gizli dizi oluşturma

1. Komutunu kullanarak bir bootstrap uygulaması kullanıcısı için etkileşimli oturum açarak PostgreSQL dağıtımını [`kubectl create secret`][kubectl-create-secret] doğrulamak için bir gizli dizi oluşturun.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. komutunu kullanarak gizli dizinin başarıyla oluşturulduğunu [`kubectl get`][kubectl-get] doğrulayın.

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## PostgreSQL kümesi için ortam değişkenlerini ayarlama

* Aşağıdaki [`kubectl apply`][kubectl-apply] komutu kullanarak PostgreSQL kümesi için ortam değişkenlerini ayarlamak üzere bir ConfigMap dağıtın:

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

## Prometheus PodMonitors'ı yükleme

Prometheus, CNPG GitHub örnek deposunda depolanan bir dizi varsayılan kayıt kuralı kullanarak CNPG örnekleri için PodMonitors oluşturur. Bir üretim ortamında bu kurallar gerektiğinde değiştirilebilir.

1. komutunu kullanarak Prometheus Community Helm deposunu [`helm repo add`][helm-repo-add] ekleyin.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Prometheus Community Helm deposunu yükseltin ve bayrağını kullanarak birincil kümeye [`helm upgrade`][helm-upgrade] `--install` yükleyin.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Pod izleyicisinin oluşturulduğunu doğrulayın.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Federasyon kimlik bilgisi oluşturma

Bu bölümde, CNPG'nin yedeklemeler için depolama hesabı hedefinde kimlik doğrulaması yapmak üzere AKS iş yükü kimliğini kullanmasına izin vermek üzere PostgreSQL yedeklemesi için federasyon kimlik bilgileri oluşturacaksınız. CNPG işleci, CNPG Kümesi dağıtım bildiriminde kullanılan adlı kümeyle aynı ada sahip bir Kubernetes hizmet hesabı oluşturur.

1. komutunu kullanarak kümenin OIDC veren URL'sini [`az aks show`][az-aks-show] alın.

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. komutunu kullanarak [`az identity federated-credential create`][az-identity-federated-credential-create] bir federasyon kimliği kimlik bilgisi oluşturun.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Yüksek oranda kullanılabilir bir PostgreSQL kümesi dağıtma

Bu bölümde, CNPG Kümesi özel kaynak tanımını (CRD)[ kullanarak ][cluster-crd]yüksek oranda kullanılabilir bir PostgreSQL kümesi dağıtacaksınız.

Aşağıdaki tabloda, Küme CRD'sinin YAML dağıtım bildiriminde ayarlanan temel özellikler özetlenmiştir:

| Özellik | Açıklama |
| --------- | ------------ |
| `inheritedMetadata` | CNPG işlecine özgüdür. Meta veriler kümeyle ilgili tüm nesneler tarafından devralınır. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Salt okunur ve salt okunur Postgres kümesi uç noktaları kullanıma sunulurken kullanılacak DNS etiketi. |
| `labels: azure.workload.identity/use: "true"` | AKS'nin PostgreSQL küme örneklerini barındıran podlara iş yükü kimlik bağımlılıkları eklemesi gerektiğini gösterir. |
| `topologySpreadConstraints` | etiketine `"workload=postgres"`sahip farklı bölgeler ve farklı düğümler gerektir. |
| `resources` | Garantili Hizmet Kalitesi (QoS) sınıfını *yapılandırıyor*. Üretim ortamında bu değerler, temel düğüm VM'sinin kullanımını en üst düzeye çıkarmak için önemlidir ve kullanılan Azure VM SKU'su temelinde farklılık gösterir. |
| `bootstrap` | CNPG işlecine özgüdür. Boş bir uygulama veritabanıyla başlatılır. |
| `storage` / `walStorage` | CNPG işlecine özgüdür. Veriler ve günlük depolama için PersistentVolumeClaims (PVC) için depolama şablonlarını tanımlar. Artan IOP'ler için parçalanan tablo alanları için depolama alanı da belirtebilirsiniz. |
| `replicationSlots` | CNPG işlecine özgüdür. Yüksek kullanılabilirlik için çoğaltma yuvalarını etkinleştirir. |
| `postgresql` | CNPG işlecine özgüdür. , `pg_hba.conf`ve `pg_ident.conf config`için ayarları `postgresql.conf`eşler. |
| `serviceAccountTemplate` | Hizmet hesaplarını oluşturmak için gereken şablonu içerir ve PostgreSQL örneklerini barındıran podlardan AKS iş yükü kimliği kimlik doğrulamasını etkinleştirmek için AKS federasyon kimliği kimlik bilgilerini UAMI ile eşler. |
| `barmanObjectStore` | CNPG işlecine özgüdür. Azure Blob Depolama nesne deposunda kimlik doğrulaması için AKS iş yükü kimliğini kullanarak barman-cloud araç paketini yapılandırılır. |

1. Komutunu kullanarak PostgreSQL kümesini Küme CRD'siyle dağıtın [`kubectl apply`][kubectl-apply] .

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

1. birincil PostgreSQL kümesinin komutunu kullanarak başarıyla oluşturulduğunu [`kubectl get`][kubectl-get] doğrulayın. CNPG Kümesi CRD'si üç örnek belirtmiştir. Bu örnek çoğaltma için bir kez getirilip birleştirildikten sonra çalışan podlar görüntülenerek doğrulanabilir. Üç örneğin de çevrimiçi olması ve kümeye katılması biraz zaman alabildiği için sabırlı olun.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Örnek çıkış

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Prometheus PodMonitor'ın çalıştığını doğrulama

CNPG işleci, Prometheus Community yüklemesi[ sırasında ](#install-the-prometheus-podmonitors)oluşturulan kayıt kurallarını kullanarak birincil örnek için otomatik olarak bir PodMonitor oluşturur.

1. Komutunu kullanarak PodMonitor'ın [`kubectl get`][kubectl-get] çalıştığını doğrulayın.

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Örnek çıkış

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Yönetilen Prometheus için Azure İzleyici kullanıyorsanız, özel grup adını kullanarak başka bir pod izleyicisi eklemeniz gerekir. Yönetilen Prometheus, Prometheus topluluğundan özel kaynak tanımlarını (CRD) almaz. Grup adının yanı sıra CRD'ler de aynıdır. Bu, Yönetilen Prometheus için pod izleyicilerinin topluluk pod izleyicisini kullananların yan yana var olmasını sağlar. Managed Prometheus kullanmıyorsanız, bunu atlayabilirsiniz. Yeni bir pod izleyicisi oluşturun:

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

Pod izleyicisinin oluşturulduğunu doğrulayın (grup adındaki farkı not edin).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### A Seçeneği - Azure İzleyici Çalışma Alanı

Postgres kümesini ve pod izleyicisini dağıttıktan sonra Azure İzleyici çalışma alanında Azure portalını kullanarak ölçümleri görüntüleyebilirsiniz.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Azure İzleyici çalışma alanında ölçümleri gösteren ekran görüntüsü." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Seçenek B - Yönetilen Grafana

Alternatif olarak, Postgres kümesini ve pod izleyicilerini dağıttıktan sonra, Azure İzleyici çalışma alanına aktarılan ölçümleri görselleştirmek için dağıtım betiği tarafından oluşturulan Yönetilen Grafana örneğinde bir ölçüm panosu oluşturabilirsiniz. Yönetilen Grafana'ya Azure portalı üzerinden erişebilirsiniz. Dağıtım betiği tarafından oluşturulan Yönetilen Grafana örneğine gidin ve burada gösterildiği gibi Uç Nokta bağlantısına tıklayın:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Azure Yönetilen Grafana örneğini gösteren ekran görüntüsü." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Uç Nokta bağlantısına tıklanması, Yönetilen Grafana örneğinde pano oluşturabileceğiniz yeni bir tarayıcı penceresinin açılmasına neden olur. Azure İzleyici veri kaynağını[ yapılandırma yönergelerini ](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in)izleyerek görselleştirmeler ekleyerek Postgres kümesinden bir ölçüm panosu oluşturabilirsiniz. Veri kaynağı bağlantısını ayarladıktan sonra, ana menüden Veri kaynakları seçeneğine tıklayın ve burada gösterildiği gibi veri kaynağı bağlantısı için bir veri kaynağı seçenekleri kümesi görmeniz gerekir:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Veri kaynağı seçeneklerini gösteren ekran görüntüsü." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Yönetilen Prometheus seçeneğinde, pano düzenleyicisini açmak için pano oluşturma seçeneğine tıklayın. Düzenleyici penceresi açıldıktan sonra Görselleştirme ekle seçeneğine ve ardından Yönetilen Prometheus seçeneğine tıklayarak Postgres kümesindeki ölçümlere göz atın. Görselleştirmek istediğiniz ölçümü seçtikten sonra, burada gösterildiği gibi görselleştirme verilerini getirmek için Sorguları çalıştır düğmesine tıklayın:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Yapı panosunu gösteren ekran görüntüsü." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Paneli panonuza eklemek için Kaydet düğmesine tıklayın. Pano düzenleyicisinde Ekle düğmesine tıklayarak ve diğer ölçümleri görselleştirmek için bu işlemi yineleyerek başka paneller ekleyebilirsiniz. Ölçüm görselleştirmelerini eklerken aşağıdakine benzer bir öğeye sahip olmanız gerekir:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Panoyu kaydetmeyi gösteren ekran görüntüsü." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Panonuzu kaydetmek için Kaydet simgesine tıklayın.

## Dağıtılan PostgreSQL kümesini inceleme

komutunu kullanarak [`kubectl get`][kubectl-get] AKS düğümü ayrıntılarını alarak PostgreSQL'in birden çok kullanılabilirlik alanına yayıldığını doğrulayın.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Çıkışınız, her düğüm için gösterilen kullanılabilirlik alanıyla aşağıdaki örnek çıkışa benzemelidir:

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

## PostgreSQL'e bağlanma ve örnek veri kümesi oluşturma

Bu bölümde bir tablo oluşturacak ve daha önce dağıttığınız CNPG Kümesi CRD'sinde oluşturulan uygulama veritabanına bazı veriler ekleyebilirsiniz. PostgreSQL kümesinin yedekleme ve geri yükleme işlemlerini doğrulamak için bu verileri kullanırsınız.

* Aşağıdaki komutları kullanarak bir tablo oluşturun ve uygulama veritabanına veri ekleyin:

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

    Çıkışınız aşağıdaki örnek çıkışa benzemelidir:

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
## PostgreSQL salt okunur çoğaltmalarına bağlanma

* PostgreSQL salt okunur çoğaltmalarına bağlanın ve aşağıdaki komutları kullanarak örnek veri kümesini doğrulayın:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Örnek çıkış

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

    Örnek çıkış

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Barman kullanarak isteğe bağlı ve zamanlanmış PostgreSQL yedeklemeleri ayarlama

1. PostgreSQL kümesinin CNPG Kümesi CRD'sinde belirtilen Azure depolama hesabına erişebildiğini ve aşağıdaki komutu kullanarak raporlandığını `Working WAL archiving` `OK` doğrulayın:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Örnek çıkış

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. KOMUTUyla YAML dosyasını kullanarak AKS iş yükü kimlik tümleştirmesini kullanan Azure Depolama'ya isteğe bağlı yedekleme dağıtın [`kubectl apply`][kubectl-apply] .

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

1. komutunu kullanarak [`kubectl describe`][kubectl-describe] isteğe bağlı yedeklemenin durumunu doğrulayın.

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Örnek çıkış

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Aşağıdaki komutu kullanarak kümenin ilk kurtarılabilirlik noktasına sahip olduğunu doğrulayın:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Örnek çıkış

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. komutuyla YAML dosyasını kullanarak saati 15 dakika geçe her saat için *zamanlanmış yedekleme yapılandırın[][kubectl-apply]`kubectl apply`.*

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

1. komutunu kullanarak [`kubectl describe`][kubectl-describe] zamanlanmış yedeklemenin durumunu doğrulayın.

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. komutunu kullanarak [`az storage blob list`][az-storage-blob-list] birincil küme için Azure blob depolamada depolanan yedekleme dosyalarını görüntüleyin.

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Çıktınız aşağıdaki örnek çıkışa benzemelidir ve yedeklemenin başarılı olduğunu doğrular:

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

## İsteğe bağlı yedeklemeyi yeni bir PostgreSQL kümesine geri yükleme

Bu bölümde, daha önce CNPG işlecini kullanarak oluşturduğunuz isteğe bağlı yedeklemeyi bootstrap Kümesi CRD'sini kullanarak yeni bir örneğe geri yüklersiniz. Basitlik için tek bir örnek kümesi kullanılır. AKS iş yükü kimliğinin (CNPG aracılığıyla inheritFromAzureAD aracılığıyla) yedekleme dosyalarına eriştiği ve kurtarma kümesi adının kurtarma kümesine özgü yeni bir Kubernetes hizmet hesabı oluşturmak için kullanıldığını unutmayın.

Ayrıca yeni kurtarma kümesi hizmet hesabını blob depolamadaki yedekleme dosyalarına "Depolama Blob Verileri Katkıda Bulunanı" erişimi olan mevcut UAMI ile eşlemek için ikinci bir federasyon kimlik bilgisi oluşturursunuz.

1. komutunu kullanarak [`az identity federated-credential create`][az-identity-federated-credential-create] ikinci bir federasyon kimliği kimlik bilgisi oluşturun.

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

1. komutuyla Küme CRD'sini kullanarak isteğe bağlı yedeklemeyi [`kubectl apply`][kubectl-apply] geri yükleyin.

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

1. Kurtarılan örneğe bağlanın, ardından aşağıdaki komutu kullanarak tam yedeklemenin alındığı özgün kümede oluşturulan veri kümesinin mevcut olduğunu doğrulayın:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Örnek çıkış

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Aşağıdaki komutu kullanarak kurtarılan kümeyi silin:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. komutunu kullanarak [`az identity federated-credential delete`][az-identity-federated-credential-delete] federasyon kimliği kimlik bilgilerini silin.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Genel yük dengeleyici kullanarak PostgreSQL kümesini kullanıma sunma

Bu bölümde, IP kaynağı kısıtlamaları olan PostgreSQL okuma-yazma ve salt okunur uç noktalarını istemci iş istasyonunuzun genel IP adresine genel olarak göstermek için gerekli altyapıyı yapılandıracaksınız.

Küme IP hizmetinden de aşağıdaki uç noktaları alırsınız:

* ** ile `*-rw`biten bir birincil okuma-yazma uç noktası.
* *Sıfırdan N'ye* (çoğaltma sayısına bağlı olarak) ile `*-ro`biten salt okunur uç noktalar.
* ** ile `*-r`biten bir çoğaltma uç noktası.

1. komutunu kullanarak [`kubectl get`][kubectl-get] Küme IP hizmeti ayrıntılarını alın.

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Örnek çıkış

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Üç hizmet vardır: `namespace/cluster-name-ro` 5433 `namespace/cluster-name-rw`numaralı bağlantı noktasına eşlenir ve `namespace/cluster-name-r` 5433 numaralı bağlantı noktasına eşlenir. PostgreSQL veritabanı kümesinin okuma/yazma düğümüyle aynı bağlantı noktasını kullanmaktan kaçınmak önemlidir. Uygulamaların PostgreSQL veritabanı kümesinin salt okunur çoğaltmasına erişmesini istiyorsanız, bunları 5433 numaralı bağlantı noktasına yönlendirin. Son hizmet genellikle veri yedeklemeleri için kullanılır, ancak salt okunur düğüm olarak da işlev görebilir.

1. komutunu kullanarak [`kubectl get`][kubectl-get] hizmet ayrıntılarını alın.

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

1. komutunu kullanarak yük dengeleyici hizmetini aşağıdaki YAML dosyalarıyla [`kubectl apply`][kubectl-apply] yapılandırın.

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

1. komutunu kullanarak [`kubectl describe`][kubectl-describe] hizmet ayrıntılarını alın.

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

### Genel PostgreSQL uç noktalarını doğrulama

Bu bölümde, Azure Load Balancer'ın daha önce oluşturduğunuz statik IP'yi kullanarak ve bağlantıları birincil okuma-yazma ve salt okunur çoğaltmalara yönlendirerek düzgün şekilde ayarlandığını doğrular ve psql CLI'yi kullanarak her ikisine de bağlanırsınız.

Birincil okuma-yazma uç noktasının TCP bağlantı noktası 5432 ile eşlendiğini ve salt okunur çoğaltma uç noktalarının aynı PostgreSQL DNS adının okuyucular ve yazarlar için kullanılmasına izin vermek için 5433 numaralı bağlantı noktasına eşlendiğini unutmayın.

> [!NOTE]
> Daha önce oluşturulan ve ortam değişkeninde depolanan PostgreSQL temel kimlik doğrulaması için uygulama kullanıcı parolasının `$PG_DATABASE_APPUSER_SECRET` değerine ihtiyacınız vardır.

* Aşağıdaki `psql` komutları kullanarak genel PostgreSQL uç noktalarını doğrulayın:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Örnek çıkış

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

    Örnek çıkış

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Birincil okuma-yazma uç noktasına başarıyla bağlandığında PostgreSQL işlevi false* değerini *döndürür `f` ve geçerli bağlantının yazılabilir olduğunu gösterir.

    Bir çoğaltmaya bağlanıldığında işlev true* değerini *döndürür `t` ve veritabanının kurtarma ve salt okunur durumda olduğunu gösterir.

## Planlanmamış yük devretme simülasyonu

Bu bölümde, postgreSQL birincilini barındıran düğüme ani bir kilitlenme veya ağ bağlantısı kaybı simülasyonu yapan birincil podu silerek ani bir hata tetiklersiniz.

1. Aşağıdaki komutu kullanarak çalışan pod örneklerinin durumunu denetleyin:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Örnek çıkış

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. komutunu kullanarak birincil podu [`kubectl delete`][kubectl-delete] silin.

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. `pg-primary-cnpg-sryti1qf-2` Aşağıdaki komutu kullanarak pod örneğinin artık birincil olduğunu doğrulayın:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Örnek çıkış

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. `pg-primary-cnpg-sryti1qf-1` Aşağıdaki komutu kullanarak pod örneğini birincil olarak sıfırlayın:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Aşağıdaki komutu kullanarak pod örneklerinin planlanmamış yük devretme testi öncesinde özgün durumlarına geri döndüğünü doğrulayın:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Örnek çıkış

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Kaynakları temizleme

* Dağıtımınızı gözden geçirmeyi bitirdikten sonra komutunu kullanarak [`az group delete`][az-group-delete] bu kılavuzda oluşturduğunuz tüm kaynakları silin.

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Sonraki adımlar

Bu nasıl yapılır kılavuzunda şunların nasıl yapılacağını öğrendiniz:

* Çok bölgeli aks kümesi oluşturmak için Azure CLI'yi kullanın.
* CNPG işlecini kullanarak yüksek oranda kullanılabilir bir PostgreSQL kümesi ve veritabanı dağıtın.
* Prometheus ve Grafana kullanarak PostgreSQL için izlemeyi ayarlayın.
* PostgreSQL veritabanına örnek bir veri kümesi dağıtın.
* PostgreSQL ve AKS kümesi yükseltmeleri gerçekleştirin.
* Küme kesintisi ve PostgreSQL çoğaltma yük devretme benzetimi.
* PostgreSQL veritabanının yedeğini ve geri yüklemesini gerçekleştirin.

İş yükleriniz için AKS'den nasıl yararlanabileceğiniz hakkında daha fazla bilgi edinmek için bkz [. Azure Kubernetes Service (AKS) nedir?][what-is-aks]

## Katkıda Bulunanlar

*Bu makale Microsoft tarafından yönetilir. Başlangıçta aşağıdaki katkıda bulunanlar* tarafından yazılmıştır:

* Ken Kilty | Asıl TPM
* Russell de Pina | Asıl TPM
* Adrian Joian | Kıdemli Müşteri Mühendisi
* Jenny Hayes | Kıdemli İçerik Geliştirici
* Carol Smith | Kıdemli İçerik Geliştirici
* Erin Schaffer | İçerik Geliştirici 2
* Adem Şerif | Müşteri Mühendisi 2

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
