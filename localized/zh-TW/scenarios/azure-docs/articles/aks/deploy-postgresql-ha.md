---
title: 使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 資料庫
description: 在本文中，您會使用 CloudNativePG 運算子，在 AKS 上部署高可用性 PostgreSQL 資料庫。
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# 在 AKS 上部署高可用性 PostgreSQL 資料庫

在本文中，您會在 AKS 上部署高可用性 PostgreSQL 資料庫。

* 如果您尚未為此部署建立必要的基礎結構，請遵循[在 AKS 上建立高可用性 PostgreSQL 資料庫以部署高可用性基礎結構中][create-infrastructure]的步驟，然後返回本文。

## 建立啟動程序應用程式使用者的秘密

1. 使用 [`kubectl create secret`][kubectl-create-secret] 命令，產生秘密，以透過啟動程序應用程式使用者的互動式登入來驗證 PostgreSQL 部署。

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. 使用 [`kubectl get`][kubectl-get] 命令驗證密碼已成功建立。

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## 設定 PostgreSQL 叢集的環境變數

* 使用下列 [`kubectl apply`][kubectl-apply] 命令，部署 ConfigMap 以設定 PostgreSQL 叢集的環境變數：

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

## 安裝 Prometheus PodMonitors

Prometheus 會使用儲存在 CNPG GitHub 範例存放庫中的一組預設錄製規則，為 CNPG 執行個體建立 PodMonitors。 在生產環境中，這些規則會視需要修改。

1. 使用 [`helm repo add`][helm-repo-add] 命令新增 Prometheus Community Helm 存放庫。

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. 升級 Prometheus Community Helm 存放庫，並使用具有 `--install` 旗標的 [`helm upgrade`][helm-upgrade] 命令，將它安裝在主要叢集上。

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

確認已建立 Pod 監視器。

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## 編輯同盟認證

在本節中，您會建立 PostgreSQL 備份的同盟身分識別認證，以允許 CNPG 使用 AKS 工作負載身分識別向儲存體帳戶目的地進行驗證以進行備份。 CNPG 操作員會建立 Kubernetes 服務帳戶，其名稱與 CNPG 叢集部署指令清單中使用的叢集名稱相同。

1. 使用 [`az aks show`][az-aks-show] 命令取得叢集的 OIDC 簽發者 URL。

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. 使用 [`az identity federated-credential create`][az-identity-federated-credential-create] 命令，建立同盟身分識別認證。

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## 部署高可用性 PostgreSQL 叢集

在本節中，您會使用 [CNPG 叢集自訂資源定義 (CRD)][cluster-crd] 部署高可用性 PostgreSQL 叢集。

下表概述叢集 CRD 之 YAML 部署指令清單中設定的主要屬性：

| 屬性 | 定義 |
| --------- | ------------ |
| `inheritedMetadata` | 特定於 CNPG 運算子。 中繼資料是由與叢集相關的所有物件繼承。 |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | 公開讀寫和唯讀 Postgres 叢集端點時要使用的 DNS 標籤。 |
| `labels: azure.workload.identity/use: "true"` | 指出 AKS 應該將工作負載身分識別相依性插入裝載 PostgreSQL 叢集執行個體的 Pod 中。 |
| `topologySpreadConstraints` | 需要具有標籤 `"workload=postgres"` 的不同區域和不同節點。 |
| `resources` | 將服務品質 (QoS) 類別設定為*有保證*。 在生產環境中，這些值是最大化基礎節點 VM 使用量的關鍵，而且會根據所使用的 Azure VM SKU 而有所不同。 |
| `bootstrap` | 特定於 CNPG 運算子。 使用空的應用程式資料庫初始化。 |
| `storage` / `walStorage` | 特定於 CNPG 運算子。 針對資料和記錄儲存體定義 PersistentVolumeClaims (PVC) 的儲存體範本。 您也可以指定資料表空間的儲存體，以針對增加的 IOP 進行分區化。 |
| `replicationSlots` | 特定於 CNPG 運算子。 啟用高可用性的複寫位置。 |
| `postgresql` | 特定於 CNPG 運算子。 對應 `postgresql.conf`、`pg_hba.conf` 和 `pg_ident.conf config` 的設定。 |
| `serviceAccountTemplate` | 包含產生服務帳戶並將 AKS 同盟身分識別認證對應至 UAMI 所需的範本，以啟用從裝載 PostgreSQL 執行個體的 Pod 到外部 Azure 資源的 AKS 工作負載身分識別驗證。 |
| `barmanObjectStore` | 特定於 CNPG 運算子。 使用 AKS 工作負載身分識別來設定 barman-cloud 工具套件，以向 Azure Blob 儲存體物件存放區進行驗證。 |

1. 使用 [`kubectl apply`][kubectl-apply] 命令，使用叢集 CRD 部署 PostgreSQL 叢集。

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

1. 使用 [`kubectl get`][kubectl-get] 命令驗證已成功建立主要 PostgreSQL 叢集。 CNPG 叢集 CRD 指定三個執行個體，只要每個執行個體啟動並聯結複寫，即可檢視執行中的 Pod 來進行驗證。 請耐心等候，因為這三個執行個體上線並加入叢集可能需要一些時間。

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    範例輸出

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### 驗證 Prometheus PodMonitor 正在執行

CNPG 運算子使用 [Prometheus Community 安裝](#install-the-prometheus-podmonitors)期間建立的錄製規則，自動為主要執行個體建立 PodMonitor。

1. 使用 [`kubectl get`][kubectl-get] 命令驗證 PodMonitor 正在執行。

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    範例輸出

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

如果您使用適用於受控 Prometheus 的 Azure 監視器，則必須使用自訂群組名稱，以利新增另一個 Pod 監視器。 Managed Prometheus 不會從 Prometheus 社群挑選自訂資源定義 (CRD)。 除了群組名稱之外，CRD 都是相同的。 這可讓受控 Prometheus 的 Pod 監視器與使用社群 Pod 監視器的監視器並存。 如果您未使用受控 Prometheus，您可以跳過此動作。 建立新的 Pod 監控器：

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

確認已建立 Pod 監視器 (請注意群組名稱的差異)。

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### 選項 A - Azure 監視器工作區

部署 Postgres 叢集和 Pod 監視器之後，您就可以在 Azure 監視器工作區中使用 Azure 入口網站來檢視計量。

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="顯示 Azure 監視器工作區中計量的螢幕快照。" lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### 選項 B - 受控 Grafana

或者，部署 Postgres 叢集和 Pod 監視器之後，您可以在部署指令碼所建立的受控 Grafana 執行個體上建立計量儀表板，以將匯出至 Azure 監視器工作區的計量視覺化。 您可以透過 Azure 入口網站存取受控 Grafana。 瀏覽至部署指令碼所建立的受控 Grafana 執行個體，然後按一下 [端點] 連結，如下所示：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="顯示 Azure 受控 Grafana 實例的螢幕快照。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

按一下 [端點] 連結會導致開啟新的瀏覽器視窗，您可以在受控 Grafana 執行個體上建立儀表板。 依照指示[設定 Azure 監視器資料來源](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in)，然後您可以新增視覺效果，以利從 Postgres 叢集建立計量的儀表板。 設定資料源連線之後，從主功能表中按一下 [資料來源] 選項，您應該會看到資料來源連線的一組資料來源選項，如下所示：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="顯示數據源選項的螢幕快照。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

在 [受控 Prometheus] 選項上，按一下選項來建置儀表板以利開啟儀表板編輯器。 編輯器視窗開啟后，按一下 [新增視覺效果] 選項，然後按一下 [受控 Prometheus] 選項，以利從 Postgres 叢集瀏覽計量。 選取您想要視覺化的計量之後，請按一下 [執行查詢] 按鈕，以利擷取視覺效果的資料，如下所示：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="顯示建構儀錶板的螢幕快照。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

按一下 [儲存] 按鈕，將面板新增至儀表板。 您可以按下儀表板編輯器中的 [新增] 按鈕來新增其他面板，並重複此流程以利將其他計量視覺化。 新增計量視覺效果時，您應該會有如下所示的內容：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="顯示儲存儀錶板的螢幕快照。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

按一下儲存圖示以儲存儀表板。

## 檢查已部署的 PostgreSQL 叢集

使用 [`kubectl get`][kubectl-get] 命令來擷取 AKS 節點詳細資料，以驗證 PostgreSQL 是否分散到多個可用性區域。

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

您的輸出應該類似下列範例輸出，並顯示每個節點的可用性區域：

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

## 連線至 PostgreSQL 並建立範例資料集

在本節中，您會建立資料表，並將一些資料插入您稍早部署之 CNPG 叢集 CRD 中建立的應用程式資料庫中。 您可以使用此資料來驗證 PostgreSQL 叢集的備份和還原作業。

* 使用下列命令，建立資料表並將資料插入應用程式資料庫中：

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

    您的輸出應該類似下列範例輸出：

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
## 連線到 PostgreSQL 唯讀複本

* 連線到 PostgreSQL 唯讀複本，並使用下列命令驗證範例資料集：

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    範例輸出

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

    範例輸出

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## 使用 Barman 設定隨選和排程的 PostgreSQL 備份

1. 使用下列命令驗證 PostgreSQL 叢集是否可以存取 CNPG 叢集 CRD 中指定的 Azure 儲存體帳戶，以及 `Working WAL archiving` 是否報告為 `OK`：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    範例輸出

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. 使用 YAML 檔案搭配 [`kubectl apply`][kubectl-apply] 命令，將隨選備份部署至使用 AKS 工作負載身分識別整合的 Azure 儲存體。

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

1. 使用 [`kubectl describe`][kubectl-describe] 命令驗證隨選備份的狀態。

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    範例輸出

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. 使用下列命令驗證叢集具有第一個可復原性點：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    範例輸出

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. 使用 YAML 檔案搭配 [`kubectl apply`][kubectl-apply] 命令，設定*每小時 15 分鐘*的排程備份。

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

1. 使用 [`kubectl describe`][kubectl-describe] 命令驗證排程備份的狀態。

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. 使用 [`az storage blob list`][az-storage-blob-list] 命令，檢視主要叢集儲存在 Azure Blob 儲存體上的備份檔案。

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    您的輸出應該類似下列範例輸出，驗證備份成功：

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

## 將隨選備份還原至新的 PostgreSQL 叢集

在本節中，您會使用 CNPG 運算子將稍早使用 CNPG 運算子建立的隨選備份還原到使用啟動程序叢集 CRD 的新執行個體。 單一執行個體叢集是為了簡單起見而使用。 請記住，AKS 工作負載身分識別 (透過 CNPG inheritFromAzureAD) 會存取備份檔案，並使用復原叢集名稱來產生復原叢集專屬的新 Kubernetes 服務帳戶。

您也會建立第二個同盟認證，將新的復原叢集服務帳戶對應至具有 Blob 儲存體上備份檔案之「儲存體 Blob 資料參與者」存取權的現有 UAMI。

1. 使用 [`az identity federated-credential create`][az-identity-federated-credential-create] 命令，建立第二個同盟身分識別認證。

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

1. 使用叢集 CRD 搭配 [`kubectl apply`][kubectl-apply] 命令還原隨選備份。

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

1. 連接到已復原的執行個體，然後使用下列命令，驗證在建立完整備份的原始叢集上建立的資料集是否存在：

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    範例輸出

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. 使用下列命令刪除復原的叢集：

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. 使用 [`az identity federated-credential delete`][az-identity-federated-credential-delete] 命令，刪除同盟身分識別認證。

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## 使用公用負載平衡器公開 PostgreSQL 叢集

在本節中，您會設定必要的基礎結構，以公開 PostgreSQL 讀寫和唯讀端點，並將 IP 來源限制公開至用戶端工作站的公用 IP 位址。

您也會從叢集 IP 服務擷取下列端點：

* 以 `*-rw` 結尾的*一個*主要讀寫端點。
* *零到 N* (視複本數目而定) 以 `*-ro` 結尾的唯讀端點。
* 以 `*-r` 結尾的*一個*複寫端點。

1. 使用 [`kubectl get`][kubectl-get] 命令取得叢集 IP 服務詳細資料。

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    範例輸出

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > 有三個服務：`namespace/cluster-name-ro` 對應至連接埠 5433、`namespace/cluster-name-rw` 以及對應至連結埠 5433 的 `namespace/cluster-name-r`。 請務必避免使用與 PostgreSQL 資料庫叢集讀取/寫入節點相同的連接埠。 如果您想要讓應用程式只存取 PostgreSQL 資料庫叢集的唯讀複本，請將它們導向連接埠 5433。 最終服務通常用於資料備份，但也可作為唯讀節點。

1. 使用 [`kubectl get`][kubectl-get] 命令取得服務詳細資料。

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

1. 使用 [`kubectl apply`][kubectl-apply] 命令，以下列 YAML 檔案設定負載平衡器服務。

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

1. 使用 [`kubectl describe`][kubectl-describe] 命令取得服務詳細資料。

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

### 驗證公用 PostgreSQL 端點

在本節中，您會使用您稍早建立的靜態 IP，以及將連線路由傳送至主要讀寫和唯讀複本，並使用 psql CLI 連線至這兩者，來驗證 Azure Load Balancer 是否已正確設定。

請記住，主要讀寫端點會對應至 TCP 連接埠 5432，而唯讀複本端點會對應至連接埠 5433，以允許讀取器和寫入器使用相同的 PostgreSQL DNS 名稱。

> [!NOTE]
> 您需要稍早產生並儲存在 `$PG_DATABASE_APPUSER_SECRET` 環境變數中 PostgreSQL 基本身分驗證的應用程式使用者密碼值。

* 使用下列 `psql` 命令來驗證公用 PostgreSQL 端點：

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    範例輸出

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

    範例輸出

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    成功連線到主要讀寫端點時，PostgreSQL 函式會傳回 `f` (如果為 *false*)，指出目前的連線是可寫入的。

    連接到複本時，函式會針對 *true* 傳回 `t`，表示資料庫處於復原狀態且唯讀。

## 模擬非計劃性容錯移轉

在本節中，您會刪除執行主要複本的 Pod 來觸發突然失敗，以模擬裝載 PostgreSQL 主要節點的突然當機或網路連線中斷。

1. 使用下列命令檢查執行中 Pod 執行個體的狀態：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    範例輸出

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. 使用 [`kubectl delete`][kubectl-delete] 命令刪除主要 Pod。

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. 使用下列命令驗證 `pg-primary-cnpg-sryti1qf-2` Pod 執行個體現在是主要執行個體：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    範例輸出

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. 使用下列命令，將 `pg-primary-cnpg-sryti1qf-1` Pod 執行個體重設為主要執行個體：

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. 使用下列命令，驗證 Pod 執行個體在非計劃性容錯移轉測試之前已回到其原始狀態：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    範例輸出

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## 清除資源

* 完成部署檢閱之後，請使用 [`az group delete`][az-group-delete] 命令，刪除本指南中建立的所有資源。

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## 下一步

在此操作指南中，您已了解如何：

* 使用 Azure CLI 建立多區域 AKS 叢集。
* 使用 CNPG 運算子 部署高可用性 PostgreSQL 叢集和資料庫。
* 使用 Prometheus 和 Grafana 設定 PostgreSQL 的監視。
* 將範例資料集部署至 PostgreSQL 資料庫。
* 執行 PostgreSQL 和 AKS 叢集升級。
* 模擬叢集中斷和 PostgreSQL 複本容錯移轉。
* 執行 PostgreSQL 資料庫的備份和還原。

若要深入瞭解如何為您的工作負載運用 AKS，請參閱 [什麼是 Azure Kubernetes Service (AKS)？][what-is-aks]

## 參與者

*本文由 Microsoft 維護。它最初是由下列參與者*所撰寫：

* Ken Kilty | 首席 TPM
* Russell de Pina | 首席 TPM
* Adrian Joian |資深客戶工程師
* Jenny Hayes | 資深內容開發人員
* Carol Smith | 資深內容開發人員
* Erin Schaffer |內容開發人員 2
* Adam Sharif |客戶工程師 2

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
