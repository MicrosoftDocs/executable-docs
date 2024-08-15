---
title: Azure CLI を使用して高可用性 PostgreSQL データベースを AKS にデプロイする
description: この記事では、CloudNativePG オペレーターを使用して、高可用性 PostgreSQL データベースを AKS にデプロイします。
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# 高可用性 PostgreSQL データベースを AKS にデプロイする

この記事では、高可用性 PostgreSQL データベースを AKS にデプロイします。

* このデプロイに必要なインフラストラクチャをまだ作成していない場合は、「[高可用性 PostgreSQL データベースを AKS にデプロイするためのインフラストラクチャを作成する][create-infrastructure]」の手順に従って設定し、この記事に戻ることができます。

## ブートストラップ アプリ ユーザーのシークレットを作成する

1. [`kubectl create secret`][kubectl-create-secret] コマンドを使用してブートストラップ アプリ ユーザーの対話型ログインによって PostgreSQL デプロイを検証するシークレットを生成します。

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. [`kubectl get`][kubectl-get] コマンドを使用して、シークレットが正常に作成されたことを検証します。

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## PostgreSQL クラスターの環境変数を設定する

* 次の [`kubectl apply`][kubectl-apply] コマンドを使用して、ConfigMap をデプロイして PostgreSQL クラスターの環境変数を設定します。

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

## Prometheus PodMonitors をインストールする

Prometheus は、CNPG GitHub サンプル リポジトリに格納されている既定の記録規則のセットを使用して、CNPG インスタンスの PodMonitors を作成します。 運用環境では、これらのルールは必要に応じて変更されます。

1. [`helm repo add`][helm-repo-add] コマンドを使用して、Prometheus Community Helm リポジトリを追加します。

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Prometheus Community Helm リポジトリをアップグレードし、`--install` フラグを持つ [`helm upgrade`][helm-upgrade] コマンドを使用してプライマリ クラスターにインストールします。

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

ポッド モニターが作成されていることを確認します。

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## フェデレーション資格情報を作成する

このセクションでは、PostgreSQL バックアップ用のフェデレーション ID 資格情報を作成して、CNPG が AKS ワークロード ID を使用してバックアップ用のストレージ アカウントの保存先に対して認証できるようにします。 CNPG オペレーターは、CNPG クラスター配置マニフェストで使用されるクラスター名と同じ名前の Kubernetes サービス アカウントを作成します。

1. [`az aks show`][az-aks-show] コマンドを使用して、クラスターの OIDC 発行者 URL を取得します。

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. [`az identity federated-credential create`][az-identity-federated-credential-create] コマンドを使用して、フェデレーション ID 資格情報を作成します。

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## 高可用性 PostgreSQL クラスターをデプロイする

このセクションでは、[CNPG クラスター カスタム リソース定義 (CRD)][cluster-crd] を使用して、高可用性 PostgreSQL クラスターをデプロイします。

次の表は、クラスター CRD の YAML 配置マニフェストで設定されたキー プロパティの概要を示しています。

| プロパティ | 定義 |
| --------- | ------------ |
| `inheritedMetadata` | CNPG 演算子に固有です。 メタデータは、クラスターに関連するすべてのオブジェクトによって継承されます。 |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | 読み取り/書き込みおよび読み取り専用 Postgres クラスター エンドポイントを公開するときに使用する DNS ラベル。 |
| `labels: azure.workload.identity/use: "true"` | AKS が PostgreSQL クラスター インスタンスをホストするポッドにワークロード ID の依存関係を挿入する必要があることを示します。 |
| `topologySpreadConstraints` | ラベル `"workload=postgres"` がある、異なるゾーンと異なるノードを必要とします。 |
| `resources` | *Guaranteed* のQoS クラスを構成します。 運用環境では、これらの値は基になるノード VM の使用を最大化するための鍵であり、使用される Azure VM SKU によって異なります。 |
| `bootstrap` | CNPG 演算子に固有です。 空のアプリ データベースを使用して初期化します。 |
| `storage` / `walStorage` | CNPG 演算子に固有です。 データおよびログ ストレージ用の PersistentVolumeClaims (PVC) のストレージ テンプレートを定義します。 また、IOPS の増加に対してテーブルスペースをシャード アウトするストレージを指定することもできます。 |
| `replicationSlots` | CNPG 演算子に固有です。 高可用性のためにレプリケーション スロットを有効にします。 |
| `postgresql` | CNPG 演算子に固有です。 `postgresql.conf`、`pg_hba.conf`、`pg_ident.conf config` 用のマップの設定。 |
| `serviceAccountTemplate` | サービス アカウントを生成し、AKS フェデレーション ID 資格情報を UAMI にマップして、PostgreSQL インスタンスをホストするポッドから外部 Azure リソースへの AKS ワークロードの ID 認証を有効にするために必要なテンプレートが含まれています。 |
| `barmanObjectStore` | CNPG 演算子に固有です。 Azure Blob Storage オブジェクト ストアへの認証に AKS ワークロード ID を使用して、barman-cloud ツール スイートを構成します。 |

1. [`kubectl apply`][kubectl-apply] コマンドを使用して、クラスター CRD で PostgreSQL クラスターをデプロイします。

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

1. [`kubectl get`][kubectl-get] コマンドを使用して、プライマリ PostgreSQL クラスターが正常に作成されたことを検証します。 CNPG クラスター CRD では 3 つのインスタンスが指定されています。これは、各インスタンスを起動して、レプリケーションに参加させた後、実行中のポッドを表示すると検証できます。 3 つのインスタンスすべてがオンラインになってクラスターに参加するまでに時間がかかる場合があるため、しばらくお待ちください。

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    出力例

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Prometheus PodMonitor が実行されていることを検証する

CNPG オペレーターにより、[Prometheus Community のインストール](#install-the-prometheus-podmonitors)中に作成された記録規則を使用して、プライマリ インスタンスの PodMonitor が自動的に作成されます。

1. [`kubectl get`][kubectl-get] コマンドを使用して、PodMonitor が実行されていることを検証します。

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    出力例

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Managed Prometheus 用の Azure Monitor を使用している場合は、カスタム グループ名を使用して別のポッド モニターを追加する必要があります。 Managed Prometheus は、Prometheus コミュニティからカスタム リソース定義 (CRD) を取得しません。 グループ名を除けば、CRD は同じです。 これにより、Managed Prometheus のポッド モニターが、コミュニティ ポッド モニターを使用するポッド モニターと並んで存在できるようになります。 Managed Prometheus を使用していない場合は、これをスキップできます。 新しいポッド モニターを作成します。

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

ポッド モニターが作成されていることを確認します (グループ名の違いに注目してください)。

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### オプション A - Azure Monitor ワークスペース

Postgres クラスターとポッド モニターをデプロイしたら、Azure Monitor ワークスペースで Azure portal を使用してメトリックを表示できます。

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Azure Monitor ワークスペースのメトリックを示すスクリーンショット。" lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### オプション B - Managed Grafana

あるいは、Postgres クラスターとポッド モニターをデプロイしたら、デプロイ スクリプトで作成された Managed Grafana インスタンスにメトリック ダッシュボードを作成して、Azure Monitor ワークスペースにエクスポートされたメトリックを視覚化できます。 Managed Grafana には、Azure portal からアクセスできます。 デプロイ スクリプトによって作成された Managed Grafana インスタンスに移動し、次のように [エンドポイント] リンクをクリックします。

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Azure Managed Grafana インスタンスを示すスクリーンショット。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

[エンドポイント] リンクをクリックすると、新しいブラウザー ウィンドウが開き、Managed Grafana インスタンスにダッシュボードを作成できます。 [Azure Monitor データ ソースを構成する](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in)手順に従って、視覚化を追加し、Postgres クラスターからメトリックのダッシュボードを作成できます。 データ ソース接続を設定した後、メイン メニューで [データ ソース] オプションをクリックすると、次に示すように、一連のデータ ソース接続のデータ ソース オプションが表示されます。

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="データ ソース オプションを示すスクリーンショット。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

[Managed Prometheus] オプションで、ダッシュボードをビルドするオプションをクリックしてダッシュボード エディターを開きます。 エディター ウィンドウが開いたら、[視覚化の追加] オプションをクリックし、[Managed Prometheus] オプションをクリックして Postgres クラスターからメトリックを参照します。 視覚化するメトリックを選択したら、[クエリの実行] ボタンをクリックして、次に示すように視覚化のデータをフェッチします。

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="コンストラクト ダッシュボードを示すスクリーンショット。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

[保存] ボタンをクリックして、パネルをダッシュボードに追加します。 他のパネルを追加するには、ダッシュボード エディターの [追加] ボタンをクリックし、このプロセスを繰り返して他のメトリックを視覚化します。 メトリックの視覚化を追加すると、次のようになります。

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="ダッシュボードの保存を示すスクリーンショット。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

[保存] をクリックして変更を保存します。

## デプロイされた PostgreSQL クラスターを調べる

[`kubectl get`][kubectl-get] コマンドを使用して AKS ノードの詳細を取得して、PostgreSQL が複数の可用性ゾーンに分散していることを検証します。

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

出力は、各ノードに対して可用性ゾーンが表示され、次の出力例のようになります。

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

## PostgreSQL に接続し、サンプル データセットを作成する

このセクションでは、テーブルを作成し、先ほどデプロイした CNPG クラスター CRD で作成されたアプリ データベースにいくつかのデータを挿入します。 このデータを使用して、PostgreSQL クラスターのバックアップと復元操作を検証します。

* 次のコマンドを使用して、テーブルを作成し、アプリ データベースにデータを挿入します。

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

    出力は、次の出力例のようになります。

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
## PostgreSQL 読み取り専用レプリカに接続する

* PostgreSQL の読み取り専用レプリカに接続し、次のコマンドを使用してサンプル データセットを検証します。

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    出力例

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

    出力例

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Barman を使用してオンデマンドおよびスケジュールされた PostgreSQL バックアップを設定する

1. 次のコマンドを使用して、PostgreSQL クラスターが CNPG クラスター CRD で指定された Azure ストレージ アカウントにアクセスできることと、`Working WAL archiving` が `OK` と報告されていることを確認します。

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    出力例

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. [`kubectl apply`][kubectl-apply] コマンドで YAML ファイルを使用して、AKS ワークロード ID 統合を使用するオンデマンド バックアップを Azure Storage にデプロイします。

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

1. [`kubectl describe`][kubectl-describe] コマンドを使用して、オンデマンド バックアップの状態を検証します。

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    出力例

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. 次のコマンドを使用して、クラスターに回復可能性の最初のポイントがあることを確認します。

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    出力例

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. [`kubectl apply`][kubectl-apply] コマンドで YAML ファイルを使用して" 毎時 15 分に" スケジュールされたバックアップを構成します。**

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

1. [`kubectl describe`][kubectl-describe] コマンドを使用して、スケジュールされたバックアップの状態を検証します。

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. [`az storage blob list`][az-storage-blob-list] コマンドを使用して、プライマリ クラスターの Azure Blob Storage に格納されているバックアップ ファイルを表示します。

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    出力は、バックアップが成功したことを検証する次の出力例のようになります。

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

## オンデマンド バックアップを新しい PostgreSQL クラスターに復元する

このセクションでは、CNPG オペレーターを使用して以前に作成したオンデマンド バックアップを、ブートストラップ クラスター CRD を使用して新しいインスタンスに復元します。 わかりやすくするために、1 つのインスタンス クラスターを使用します。 AKS ワークロード ID (CNPG inheritFromAzureAD 経由) は、バックアップ ファイルにアクセスし、リカバリ クラスター名を使用してリカバリ クラスターに固有の新しい Kubernetes サービス アカウントを生成することを忘れないでください。

また、2 つ目のフェデレーション資格情報を作成して、新しいリカバリ クラスター サービス アカウントを、Blob Storage 上のバックアップ ファイルへの "ストレージ BLOB データ共同作成者" アクセス権を持つ既存の UAMI にマップします。

1. [`az identity federated-credential create`][az-identity-federated-credential-create] コマンドを使用して、2 番目のフェデレーション ID 資格情報を作成します。

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

1. [`kubectl apply`][kubectl-apply] コマンドを使用して、クラスター CRD を使用してオンデマンド バックアップを復元します。

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

1. 復旧されたインスタンスに接続し、次のコマンドを使用して、完全バックアップが作成された元のクラスターに作成されたデータセットが存在することを検証します。

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    出力例

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. 次のコマンドを使用して、復旧したクラスターを削除します。

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. [`az identity federated-credential delete`][az-identity-federated-credential-delete] コマンドを使用して、フェデレーション ID 資格情報を作成します。

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## パブリック ロード バランサーを使用して PostgreSQL クラスターを公開する

このセクションでは、IP ソース制限のある PostgreSQL 読み取り/書き込みおよび読み取り専用エンドポイントをクライアント ワークステーションのパブリック IP にパブリックに公開するために必要なインフラストラクチャを構成します。

クラスター IP サービスから次のエンドポイントも取得します。

* `*-rw` で終わる "1 個" のプライマリ読み取り/書き込みエンドポイント。**
* `*-ro` で終わる "0 から N 個" (レプリカの数に応じる) の読み取り専用エンドポイント。**
* `*-r` で終わる "1 個" のレプリケーション エンドポイント。**

1. [`kubectl get`][kubectl-get] コマンドを使用して、クラスター IP サービスの詳細を取得します。

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    出力例

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > 3 つのサービスがあり、`namespace/cluster-name-ro` は、ポート 5433 にマップされ、`namespace/cluster-name-rw` と `namespace/cluster-name-r` はポート 5433 にマップされます。 PostgreSQL データベース クラスターの読み取り/書き込みノードと同じポートを使用しないようにすることが重要です。 アプリケーションが PostgreSQL データベース クラスターの読み取り専用レプリカにのみアクセスできるようにする場合は、それらをポート 5433 に転送します。 最終的なサービスは通常、データ バックアップに使用されますが、読み取り専用ノードとしても機能します。

1. [`kubectl get`][kubectl-get] コマンドを使用して、サービスの詳細を取得します。

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

1. [`kubectl apply`][kubectl-apply] コマンドを使用して、次の YAML ファイルでロード バランサー サービスを構成します。

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

1. [`kubectl describe`][kubectl-describe] コマンドを使用して、サービスの詳細を取得します。

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

### パブリック PostgreSQL エンドポイントを検証する

このセクションでは、先ほど作成した静的 IP を使用し、プライマリ読み取り/書き込み、および読み取り専用レプリカに接続をルーティングし、psql CLI を使用して両方に接続することにより、Azure Load Balancer が適切に設定されていることを検証します。

プライマリ読み取り/書き込みエンドポイントは TCP ポート 5432 にマップされ、読み取り専用レプリカ エンドポイントはポート 5433 にマップされるので、リーダーとライターに同じ PostgreSQL DNS 名を使用できます。

> [!NOTE]
> 先ほど生成した、`$PG_DATABASE_APPUSER_SECRET` 環境変数に格納されている PostgreSQL 基本認証のアプリ ユーザー パスワードの値が必要です。

* 次の `psql` コマンドを使用して、パブリック PostgreSQL エンドポイントを検証します。

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    出力例

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

    出力例

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    プライマリ読み取り/書き込みエンドポイントに正常に接続されると、PostgreSQL 関数は *false* を表す `f` を返し、現在の接続が書き込み可能であることを示します。

    レプリカに接続すると、この関数は *true * を表す `t` を返します。これは、データベースが復旧中で、読み取り専用であることを示します。

## 計画外のフェールオーバーをシミュレートする

このセクションでは、プライマリを実行しているポッドを削除して、突然の障害をトリガーします。これにより、PostgreSQL プライマリをホストしているノードへの突然のクラッシュまたはネットワーク接続の損失がシミュレートされます。

1. 次のコマンドを使用して、実行中のポッド インスタンスの状態を確認します。

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    出力例

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. [`kubectl delete`][kubectl-delete] コマンドを使用してプライマリ ポッドを削除します。

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. 次のコマンドを使用して、`pg-primary-cnpg-sryti1qf-2` ポッド インスタンスがプライマリになっていることを確認します。

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    出力例

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. 次のコマンドを使用して、`pg-primary-cnpg-sryti1qf-1` ポッド インスタンスをプライマリとしてリセットします。

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. 次のコマンドを使用して、計画外のフェールオーバー テストの前にポッド インスタンスが元の状態に戻ったことを確認します。

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    出力例

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## リソースをクリーンアップする

* デプロイの確認が終わったら、[`az group delete`][az-group-delete] コマンドを使用して、このガイドで作成したすべてのリソースを削除します。

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## 次のステップ

この攻略ガイドで学習した内容は次のとおりです。

* Azure CLI を使用して、マルチゾーン AKS クラスターを作成する。
* CNPG オペレーターを使用して高可用性 PostgreSQL クラスターとデータベースをデプロイする。
* Prometheus と Grafana を使用して PostgreSQL の監視を設定する。
* PostgreSQL データベースにサンプル データセットをデプロイする。
* PostgreSQL と AKS クラスターのアップグレードを実行する。
* クラスターの中断と PostgreSQL レプリカのフェールオーバーをシミュレートする。
* PostgreSQL データベースのバックアップと復元を実行する。

ワークロードに AKS を活用する方法の詳細については、「[Azure Kubernetes Service (AKS) とは」を参照してください。][what-is-aks]

## 共同作成者

*この記事は Microsoft によって管理されています。これはもともと次の共同作成者によって書かれました*:

* Ken Kilty | プリンシパル TPM
* Russell de Pina | プリンシパル TPM
* Adrian Joian | シニア カスタマー エンジニア
* Jenny Hayes | シニア コンテンツ開発者
* Carol Smith | シニア コンテンツ開発者
* Erin Schaffer |コンテンツ開発者 2
* Adam Sharif | カスタマー エンジニア 2

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
