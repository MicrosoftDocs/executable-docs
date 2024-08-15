---
title: 使用 Azure CLI 在 AKS 上部署高可用性 PostgreSQL 数据库
description: 在本文中，你将使用 CloudNativePG 运算符在 AKS 上部署高度可用的 PostgreSQL 数据库。
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# 在 AKS 上部署高度可用的 PostgreSQL 数据库

在本文中，你将在 AKS 上部署高度可用的 PostgreSQL 数据库。

* 如果尚未为此部署创建所需的基础结构，请按照[创建基础结构以在 AKS 上部署高度可用的 PostgreSQL 数据库][create-infrastructure]中的步骤进行设置，然后可返回到本文。

## 为启动应用用户创建机密

1. 使用 [`kubectl create secret`][kubectl-create-secret] 命令为启动应用用户生成一个机密，通过交互式登录来验证 PostgreSQL 部署。

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. 使用 [`kubectl get`][kubectl-get] 命令验证是否已成功创建机密。

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## 设置用于 PostgreSQL 群集的环境变量

* 部署 ConfigMap，使用以下 [`kubectl apply`][kubectl-apply] 命令为 PostgreSQL 群集设置环境变量：

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

## 安装 Prometheus PodMonitor

Prometheus 使用 CNPG GitHub 示例存储库中存储的一组默认记录规则为 CNPG 实例创建 PodMonitor。 在生产环境中，将根据需要修改这些规则。

1. 使用 [`helm repo add`][helm-repo-add] 命令添加 Prometheus 社区 Helm 存储库。

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. 升级 Prometheus 社区 Helm 存储库，并使用带有 `--install` 标志的 [`helm upgrade`][helm-upgrade] 命令在主群集上安装它。

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

验证是否已创建 Pod 监视器。

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## 创建联合凭据

在本部分，你将创建 PostgreSQL 备份的联合标识凭据，以允许 CNPG 使用 AKS 工作负载标识向存储帐户目标进行身份验证来进行备份。 CNPG 运算符会创建一个与 CNPG 群集部署清单中使用的群集同名的 Kubernetes 服务帐户。

1. 使用 [`az aks show`][az-aks-show] 命令获取群集 OIDC 颁发者 URL。

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. 使用 [`az identity federated-credential create`][az-identity-federated-credential-create] 命令创建联合标识凭据。

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## 部署高度可用的 PostgreSQL 群集

在本部分，你将使用 [CNPG 群集自定义资源定义 (CRD)][cluster-crd] 部署高度可用的 PostgreSQL 群集。

下表概述了在群集 CRD 的 YAML 部署清单中设置的关键属性：

| properties | 定义 |
| --------- | ------------ |
| `inheritedMetadata` | 特定于 CNPG 运算符。 元数据由与群集相关的所有对象继承。 |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | 公开读写和只读 Postgres 群集终结点时要使用的 DNS 标签。 |
| `labels: azure.workload.identity/use: "true"` | 指示 AKS 应将工作负载标识依赖项注入托管 PostgreSQL 群集实例的 Pod。 |
| `topologySpreadConstraints` | 需要不同的区域和具有 `"workload=postgres"` 标签的不同节点。 |
| `resources` | 配置服务质量 (QoS) 类 Guaranteed。** 在生产环境中，这些值是最大限度使用基础节点 VM 的关键，根据所使用的 Azure VM SKU 而有所不同。 |
| `bootstrap` | 特定于 CNPG 运算符。 使用空的应用数据库进行初始化。 |
| `storage` / `walStorage` | 特定于 CNPG 运算符。 为数据和日志存储的 PersistentVolumeClaim (PVC) 定义存储模板。 还可以为表空间指定存储来进行分片，以增加 IOPs。 |
| `replicationSlots` | 特定于 CNPG 运算符。 启用复制槽来实现高可用性。 |
| `postgresql` | 特定于 CNPG 运算符。 映射 `postgresql.conf`、`pg_hba.conf` 和 `pg_ident.conf config` 的设置。 |
| `serviceAccountTemplate` | 包含生成服务帐户所需的模板，并将 AKS 联合标识凭据映射到 UAMI，从而能够从托管 PostgreSQL 实例的 Pod 进行 AKS 工作负载标识身份验证来访问外部 Azure 资源。 |
| `barmanObjectStore` | 特定于 CNPG 运算符。 使用 AKS 工作负载标识配置 barman-cloud 工具套件，以便向 Azure Blob 存储对象存储进行身份验证。 |

1. 使用 [`kubectl apply`][kubectl-apply] 命令通过群集 CRD 部署 PostgreSQL 群集。

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

1. 使用 [`kubectl get`][kubectl-get] 命令验证是否已成功创建主要 PostgreSQL 群集。 CNPG 群集 CRD 指定了三个实例，可以在启动并加入每个实例进行复制后查看正在运行的 Pod 来验证。 请耐心等待，因为所有三个实例需要一些时间才能联机并加入群集。

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    示例输出

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### 验证 Prometheus PodMonitor 是否正在运行

CNPG 运算符使用在 [Prometheus 社区安装](#install-the-prometheus-podmonitors)期间创建的记录规则自动为主实例创建 PodMonitor。

1. 使用 [`kubectl get`][kubectl-get] 命令验证 PodMonitor 是否正在运行。

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    示例输出

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

如果使用适用于托管 Prometheus 的 Azure Monitor，需要使用自定义组名再添加一个 Pod 监视器。 托管 Prometheus 不会从 Prometheus 社区获取自定义资源定义 (CRD)。 除了组名外，CRD 是相同的。 这使得托管 Prometheus 的 Pod 监视器能够与使用社区 Pod 监视器的项并排存在。 如果没有使用托管 Prometheus，可跳过此操作。 创建新的 Pod 监视器：

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

验证是否已创建 Pod 监视器（请注意组名的差异）。

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### 选项 A - Azure Monitor 工作区

部署 Postgres 群集和 Pod 监视器后，可以在 Azure Monitor 工作区中使用 Azure 门户查看指标。

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="显示 Azure Monitor 工作区中的指标的屏幕截图。" lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### 选项 B - 托管 Grafana

或者，部署 Postgres 群集和 Pod 监视器后，可以在部署脚本创建的托管 Grafana 实例上创建指标仪表板，可视化导出到 Azure Monitor 工作区的指标。 可以通过 Azure 门户访问托管 Grafana。 导航到部署脚本创建的托管 Grafana 实例，然后单击“终结点”链接，如下所示：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="显示 Azure 托管 Grafana 实例的屏幕截图。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

单击“终结点”链接会打开新的浏览器窗口，可在这里创建关于托管 Grafana 实例的仪表板。 按照说明[配置 Azure Monitor 数据源](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in)，然后就可添加可视化效果，创建 Postgres 群集指标仪表板。 设置数据源连接后，在主菜单中单击“数据源”选项，你应该会看到一组用于数据源连接的数据源选项，如下所示：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="显示数据源选项的屏幕截图。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

在“托管 Prometheus”选项上，单击生成仪表板的选项以打开仪表板编辑器。 编辑器窗口打开后，单击“添加可视化效果”选项，然后单击“托管 Prometheus”选项，浏览来自 Postgres 群集的指标。 选择要可视化的指标后，单击“运行查询”按钮来提取数据进行可视化，如下所示：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="显示构造仪表板的屏幕截图。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

单击“保存”按钮，将面板添加到仪表板。 可以单击仪表板编辑器中的“添加”按钮来添加其他面板，并重复此过程来可视化其他指标。 添加指标可视化效果后，应会显示如下所示的内容：

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="显示保存仪表板的屏幕截图。" lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

单击“保存”图标以保存仪表板。

## 检查已部署的 PostgreSQL 群集

使用 [`kubectl get`][kubectl-get] 命令检索 AKS 节点详细信息，验证 PostgreSQL 是否跨多个可用性区域分布。

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

输出应与下面的示例输出类似，其中显示了每个节点的可用性区域：

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

## 连接到 PostgreSQL 并创建示例数据集

在本部分，你将创建一个表，并在前面部署的 CNPG 群集 CRD 中创建的应用数据库中插入一些数据。 使用此数据来验证 PostgreSQL 群集的备份和还原操作。

* 使用以下命令创建表并在应用数据库中插入数据：

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

    输出应与下面的示例输出类似：

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
## 连接到 PostgreSQL 只读副本

* 使用以下命令连接到 PostgreSQL 只读副本并验证示例数据集：

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    示例输出

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

    示例输出

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## 使用 Barman 设置按需和计划的 PostgreSQL 备份

1. 使用以下命令验证 PostgreSQL 群集是否可访问 CNPG 群集 CRD 中指定的 Azure 存储帐户，以及 `Working WAL archiving` 是否报告为 `OK`：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    示例输出

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. 使用 [`kubectl apply`][kubectl-apply] 命令和 YAML 文件将按需备份部署到 Azure 存储，该备份使用 AKS 工作负载标识集成。

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

1. 使用 [`kubectl describe`][kubectl-describe] 命令验证按需备份的状态。

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    示例输出

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. 使用以下命令验证群集是否具有第一个可恢复性点：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    示例输出

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. 使用 [`kubectl apply`][kubectl-apply] 命令和 YAML 文件，配置每小时每 15 分钟一次的计划备份。**

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

1. 使用 [`kubectl describe`][kubectl-describe] 命令验证计划备份的状态。

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. 使用 [`az storage blob list`][az-storage-blob-list] 命令查看存储在主群集的 Azure Blob 存储上的备份文件。

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    输出应与下面的示例输出类似，验证备份是否成功：

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

## 将按需备份还原到新的 PostgreSQL 群集

在本部分，使用启动群集 CRD 将之前使用 CNPG 运算符创建的按需备份还原到新实例中。 为了简单起见，使用单个实例群集。 请记住，AKS 工作负载标识（通过 CNPG inheritFromAzureAD）访问备份文件，并且恢复群集名称用于生成特定于恢复群集的新 Kubernetes 服务帐户。

还需要另外创建一个联合凭据，将新的恢复群集服务帐户映射到对 Blob 存储上的备份文件具有“存储 Blob 数据参与者”访问权限的现有 UAMI。

1. 使用 [`az identity federated-credential create`][az-identity-federated-credential-create] 命令另外创建一个联合标识凭据。

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

1. 使用群集 CRD 和 [`kubectl apply`][kubectl-apply] 命令还原按需备份。

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

1. 连接到恢复的实例，然后使用以下命令验证在进行完整备份的原始群集上创建的数据集是否存在：

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    示例输出

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. 使用以下命令删除恢复的群集：

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. 使用 [`az identity federated-credential delete`][az-identity-federated-credential-delete] 命令删除联合标识凭据。

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## 使用公共负载均衡器公开 PostgreSQL 群集

在本部分，你将配置必要的基础结构，以向客户端工作站的公共 IP 地址公开具有 IP 源限制的 PostgreSQL 读写和只读终结点。

你还需要从群集 IP 服务检索以下终结点：

* 一个以 `*-rw` 结尾的主要读写终结点。**
* 以 `*-ro` 结尾的零到 N 个只读终结点（数量由副本数量决定）。**
* 一个以 `*-r` 结尾的复制终结点。**

1. 使用 [`kubectl get`][kubectl-get] 命令获取群集 IP 服务详细信息。

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    示例输出

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > 有三个服务：`namespace/cluster-name-ro`（映射到端口 5433）、`namespace/cluster-name-rw` 和 `namespace/cluster-name-r`（映射到端口 5433）。 请务必避免使用与 PostgreSQL 数据库群集的读/写节点相同的端口。 如果希望应用程序仅访问 PostgreSQL 数据库群集的只读副本，请将其定向到端口 5433。 最终服务通常用于数据备份，但也可用作只读节点。

1. 使用 [`kubectl get`][kubectl-get] 命令获取服务详细信息。

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

1. 使用 [`kubectl apply`][kubectl-apply] 命令和以下 YAML 文件配置负载均衡器服务。

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

1. 使用 [`kubectl describe`][kubectl-describe] 命令获取服务详细信息。

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

### 验证公共 PostgreSQL 终结点

在本部分，你将使用你之前创建的静态 IP 并将连接路由到主要的读写和只读副本，验证 Azure 负载均衡器是否正确设置。你还将使用 psql CLI 连接到这两种副本。

请记住，主要读写终结点映射到 TCP 端口 5432，只读副本终结点映射到端口 5433，以允许读取器和编写器使用相同的 PostgreSQL DNS 名称。

> [!NOTE]
> 需要之前生成的 PostgreSQL 基本身份验证的应用用户密码的值，并将其存储在 `$PG_DATABASE_APPUSER_SECRET` 环境变量中。

* 使用以下 `psql` 命令验证公共 PostgreSQL 终结点：

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    示例输出

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

    示例输出

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    成功连接到主要读写终结点时，PostgreSQL 函数会返回 `f` 表示 false，指出当前连接是可写的。**

    连接到副本时，该函数返回 `t` 表示 true，指出数据库处于恢复状态且只读。**

## 模拟计划外故障转移

在本部分，通过删除运行主终结点的 Pod 来触发突然失败，这模拟了与托管 PostgreSQL 主终结点的节点的网络连接突然崩溃或断开的情况。

1. 使用以下命令检查正在运行的 Pod 实例的状态：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    示例输出

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. 使用 [`kubectl delete`][kubectl-delete] 命令删除主要 Pod。

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. 使用以下命令验证 `pg-primary-cnpg-sryti1qf-2` Pod 实例现在是否是主要 Pod：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    示例输出

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. 使用以下命令将 `pg-primary-cnpg-sryti1qf-1` Pod 实例重置为主要 Pod：

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. 使用以下命令验证 Pod 实例在计划外故障转移测试之前是否已返回到其原始状态：

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    示例输出

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## 清理资源

* 完成部署评审后，使用 [`az group delete`][az-group-delete] 命令删除本指南中创建的所有资源。

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## 后续步骤

通过本操作指南，我们已学会了：

* 使用 Azure CLI 创建多区域 AKS 群集。
* 使用 CNPG operator 部署高可用性 PostgreSQL 群集和数据库。
* 使用 Prometheus 和 Grafana 设置 PostgreSQL 的监视。
* 将示例数据集部署到 PostgreSQL 数据库。
* 执行 PostgreSQL 和 AKS 群集升级。
* 模拟群集中断和 PostgreSQL 副本故障转移。
* 执行 PostgreSQL 数据库的备份和还原。

若要详细了解如何对工作负载使用 AKS，请参阅[什么是 Azure Kubernetes 服务 (AKS)？][what-is-aks]

## 供稿人

*本文由Microsoft维护。它最初由以下参与者*编写：

* Ken Kilty | 首席 TPM
* Russell de Pina | 首席 TPM
* Adrian Joian | 高级客户工程师
* Jenny Hayes | 高级内容开发人员
* Carol Smith | 高级内容开发人员
* Erin Schaffer | 内容开发人员 2
* Adam Sharif | 客户工程师 2

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
