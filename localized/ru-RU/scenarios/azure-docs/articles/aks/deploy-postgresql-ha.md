---
title: Развертывание высокодоступной базы данных PostgreSQL в AKS с помощью Azure CLI
description: 'В этой статье описано, как развернуть высокодоступную базу данных PostgreSQL в AKS с помощью оператора CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Развертывание высокодоступной базы данных PostgreSQL в AKS

В этой статье описано, как развернуть высокодоступную базу данных PostgreSQL в AKS.

* Если вы еще не создали необходимую инфраструктуру для этого развертывания, выполните действия, описанные в [статье "Создание инфраструктуры" для развертывания базы данных PostgreSQL с высоким уровнем доступности в AKS][create-infrastructure] , чтобы настроить ее, а затем вернуться к этой статье.

## Создание секрета для пользователя приложения начальной загрузки

1. Создайте секрет для проверки развертывания PostgreSQL с помощью интерактивного входа для пользователя начального приложения с помощью [`kubectl create secret`][kubectl-create-secret] команды.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Убедитесь, что секрет был успешно создан с помощью [`kubectl get`][kubectl-get] команды.

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Задание переменных среды для кластера PostgreSQL

* Разверните ConfigMap, чтобы задать переменные среды для кластера PostgreSQL с помощью следующей [`kubectl apply`][kubectl-apply] команды:

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

## Установка podMonitors Prometheus

Prometheus создает PodMonitors для экземпляров CNPG с помощью набора правил записи по умолчанию, хранящихся в репозитории примеров GitHub CNPG. В рабочей среде эти правила будут изменены по мере необходимости.

1. Добавьте репозиторий Prometheus Community Helm с помощью [`helm repo add`][helm-repo-add] команды.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Обновите репозиторий Prometheus Community Helm и установите его в основном кластере с помощью [`helm upgrade`][helm-upgrade] команды с флагом `--install` .

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Убедитесь, что монитор pod создан.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Создание федеративных учетных данных

В этом разделе описано, как создать федеративные учетные данные удостоверения для резервного копирования PostgreSQL, чтобы разрешить CNPG использовать удостоверение рабочей нагрузки AKS для проверки подлинности в целевой учетной записи хранения для резервного копирования. Оператор CNPG создает учетную запись службы Kubernetes с тем же именем, что и кластер, который называется в манифесте развертывания кластера CNPG.

1. Получите URL-адрес издателя OIDC кластера с помощью [`az aks show`][az-aks-show] команды.

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Создайте учетные данные федеративного [`az identity federated-credential create`][az-identity-federated-credential-create] удостоверения с помощью команды.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Развертывание кластера PostgreSQL с высоким уровнем доступности

В этом разделе описано, как развернуть высокодоступный кластер PostgreSQL с помощью настраиваемого [определения ресурсов кластера CNPG (CRD).][cluster-crd]

В следующей таблице описаны ключевые свойства, заданные в манифесте развертывания YAML для кластера CRD:

| Свойство | Определение |
| --------- | ------------ |
| `inheritedMetadata` | Зависит от оператора CNPG. Метаданные наследуются всеми объектами, связанными с кластером. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Метка DNS для использования при предоставлении конечных точек кластера Postgres только для чтения и чтения. |
| `labels: azure.workload.identity/use: "true"` | Указывает, что AKS должен внедрять зависимости удостоверений рабочей нагрузки в модули pod, в которые размещаются экземпляры кластера PostgreSQL. |
| `topologySpreadConstraints` | Требовать разные зоны и разные узлы с меткой `"workload=postgres"`. |
| `resources` | Настраивает класс Quality of Service (QoS) гарантированного**. В рабочей среде эти значения являются ключевыми для максимизации использования базовой виртуальной машины узла и зависят от используемого SKU виртуальной машины Azure. |
| `bootstrap` | Зависит от оператора CNPG. Инициализируется с пустой базой данных приложения. |
| `storage` / `walStorage` | Зависит от оператора CNPG. Определяет шаблоны хранилища для службы PersistentVolumeClaims (PVCs) для хранения данных и журналов. Кроме того, можно указать хранилище для табличных пространств для сегментирования для увеличения операций ввода-вывода в секунду. |
| `replicationSlots` | Зависит от оператора CNPG. Включает слоты репликации для обеспечения высокой доступности. |
| `postgresql` | Зависит от оператора CNPG. Сопоставляет параметры для `postgresql.conf`, `pg_hba.conf`и `pg_ident.conf config`. |
| `serviceAccountTemplate` | Содержит шаблон, необходимый для создания учетных записей службы и сопоставляет учетные данные федеративного удостоверения AKS с UAMI, чтобы включить проверку подлинности удостоверения рабочей нагрузки AKS из модулей pod, на которых размещены экземпляры PostgreSQL, с внешними ресурсами Azure. |
| `barmanObjectStore` | Зависит от оператора CNPG. Настраивает набор инструментов barman-cloud с помощью удостоверения рабочей нагрузки AKS для проверки подлинности в хранилище объектов Хранилище BLOB-объектов Azure. |

1. Разверните кластер PostgreSQL с помощью crD кластера с помощью [`kubectl apply`][kubectl-apply] команды.

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

1. Убедитесь, что основной кластер PostgreSQL успешно создан с помощью [`kubectl get`][kubectl-get] команды. CrD кластера CNPG указал три экземпляра, которые можно проверить, просматривая модули pod после создания и объединения каждого экземпляра для репликации. Будьте терпеливы, так как это может занять некоторое время для всех трех экземпляров, чтобы прийти в сеть и присоединиться к кластеру.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Пример результата

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Проверка запущенного модуля PodMonitor Prometheus

Оператор CNPG автоматически создает podMonitor для основного экземпляра с помощью правил записи, созданных во время [установки](#install-the-prometheus-podmonitors) Сообщества Prometheus.

1. Убедитесь, что podMonitor выполняется с помощью [`kubectl get`][kubectl-get] команды.

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Пример результата

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Если вы используете Azure Monitor для Managed Prometheus, необходимо добавить другой монитор pod с помощью имени настраиваемой группы. Управляемый Prometheus не выбирает пользовательские определения ресурсов (CRD) из сообщества Prometheus. Помимо имени группы, crD совпадают. Это позволяет мониторам pod для управляемого Prometheus существовать параллельно с монитором pod сообщества. Если вы не используете Управляемый prometheus, можно пропустить это. Создайте монитор pod:

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

Убедитесь, что монитор pod создан (обратите внимание на разницу в имени группы).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Вариант A. Рабочая область Azure Monitor

После развертывания кластера Postgres и монитора pod можно просмотреть метрики с помощью портал Azure в рабочей области Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Снимок экрана: метрики в рабочей области Azure Monitor." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Вариант B — Управляемый Grafana

Кроме того, после развертывания кластера Postgres и мониторов pod можно создать панель мониторинга метрик на экземпляре Управляемой Grafana, созданном скриптом развертывания, чтобы визуализировать метрики, экспортированные в рабочую область Azure Monitor. Вы можете получить доступ к Управляемой Grafana с помощью портал Azure. Перейдите к управляемому экземпляру Grafana, созданному скриптом развертывания, и щелкните ссылку "Конечная точка", как показано ниже:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Снимок экрана: экземпляр Управляемой Grafana Azure." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Щелкнув ссылку "Конечная точка", откроется новое окно браузера, в котором можно создать панели мониторинга в управляемом экземпляре Grafana. Следуя инструкциям по [настройке источника](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) данных Azure Monitor, вы можете добавить визуализации для создания панели мониторинга метрик из кластера Postgres. После настройки подключения к источнику данных в главном меню выберите параметр "Источники данных", и вы увидите набор параметров источника данных для подключения к источнику данных, как показано здесь:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Снимок экрана: параметры источника данных." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

В параметре Managed Prometheus щелкните параметр, чтобы создать панель мониторинга, чтобы открыть редактор панели мониторинга. Когда откроется окно редактора, щелкните параметр "Добавить визуализацию", а затем выберите параметр Managed Prometheus, чтобы просмотреть метрики из кластера Postgres. После выбора метрики, которую вы хотите визуализировать, нажмите кнопку "Выполнить запросы", чтобы получить данные для визуализации, как показано ниже:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Снимок экрана: панель мониторинга конструктора." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Нажмите кнопку "Сохранить", чтобы добавить панель на панель мониторинга. Вы можете добавить другие панели, нажав кнопку "Добавить" в редакторе панели мониторинга и повторив этот процесс, чтобы визуализировать другие метрики. Добавление визуализаций метрик должно выглядеть следующим образом:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Снимок экрана: панель мониторинга сохранения." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Щелкните значок "Сохранить", чтобы сохранить панель мониторинга.

## Проверка развернутого кластера PostgreSQL

Убедитесь, что PostgreSQL распространяется по нескольким зонам доступности, извлекая сведения о узле AKS с помощью [`kubectl get`][kubectl-get] команды.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Выходные данные должны выглядеть примерно в следующем примере с зоной доступности, показанной для каждого узла:

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

## Подключение к PostgreSQL и создание примера набора данных

В этом разделе описано, как создать таблицу и вставить некоторые данные в базу данных приложения, созданную в кластере CNPG, развернутой ранее. Эти данные используются для проверки операций резервного копирования и восстановления для кластера PostgreSQL.

* Создайте таблицу и вставьте данные в базу данных приложения с помощью следующих команд:

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

    Выходные данные должны выглядеть примерно так:

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
## Подключение к репликам postgreSQL только для чтения

* Подключитесь к репликам postgreSQL только для чтения и проверьте пример набора данных с помощью следующих команд:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Пример результата

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

    Пример результата

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Настройка резервных копий PostgreSQL по запросу и запланированных резервных копий PostgreSQL с помощью Barman

1. Убедитесь, что кластер PostgreSQL может получить доступ к учетной записи хранения Azure, указанной в CRD кластера CNPG, и `Working WAL archiving` отчеты, как `OK` с помощью следующей команды:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Пример результата

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Разверните резервную копию по запросу в служба хранилища Azure, которая использует интеграцию удостоверений рабочей нагрузки AKS с помощью файла YAML с командой[`kubectl apply`][kubectl-apply].

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

1. Проверьте состояние резервной копии по запросу [`kubectl describe`][kubectl-describe] с помощью команды.

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Пример результата

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Убедитесь, что кластер имеет первую точку восстановления с помощью следующей команды:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Пример результата

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Настройте запланированное резервное копирование каждые *15 минут за* час с помощью файла YAML с [`kubectl apply`][kubectl-apply] помощью команды.

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

1. Проверьте состояние запланированной резервной копии с помощью [`kubectl describe`][kubectl-describe] команды.

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Просмотрите файлы резервной копии, хранящиеся в хранилище BLOB-объектов Azure, для основного кластера с помощью [`az storage blob list`][az-storage-blob-list] команды.

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Выходные данные должны выглядеть следующим образом: проверка резервного копирования выполнена успешно.

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

## Восстановление резервного копирования по запросу в новый кластер PostgreSQL

В этом разделе описано, как восстановить резервную копию по запросу, созданную ранее с помощью оператора CNPG в новом экземпляре с помощью crD кластера начальной загрузки. Для простоты используется один кластер экземпляров. Помните, что удостоверение рабочей нагрузки AKS (через CNPG наследуетFromAzureAD) обращается к файлам резервной копии и что имя кластера восстановления используется для создания новой учетной записи службы Kubernetes, относящуюся к кластеру восстановления.

Вы также создадите второй федеративные учетные данные для сопоставления новой учетной записи службы кластера восстановления с существующим UAMI с доступом "Участник данных BLOB-объектов хранилища" к файлам резервной копии в хранилище BLOB-объектов.

1. Создайте второе федеративное удостоверение с помощью [`az identity federated-credential create`][az-identity-federated-credential-create] команды.

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

1. Восстановите резервную копию по запросу с помощью crD кластера с [`kubectl apply`][kubectl-apply] помощью команды.

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

1. Подключитесь к восстановленным экземплярам, а затем убедитесь, что набор данных, созданный в исходном кластере, где выполнена полная резервная копия, используется следующая команда:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Пример результата

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Удалите восстановленный кластер с помощью следующей команды:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Удалите учетные данные федеративного [`az identity federated-credential delete`][az-identity-federated-credential-delete] удостоверения с помощью команды.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Предоставление кластера PostgreSQL с помощью общедоступной подсистемы балансировки нагрузки

В этом разделе описана настройка необходимой инфраструктуры для общедоступного предоставления конечных точек PostgreSQL для чтения и записи и чтения с ограничениями на общедоступный IP-адрес клиентской рабочей станции.

Вы также получите следующие конечные точки из службы IP-адресов кластера:

* *Одна* основная конечная точка чтения и записи, которая заканчивается `*-rw`.
* *Ноль до N* (в зависимости от количества реплик) конечных точек только для чтения, которые заканчиваются `*-ro`.
* *Одна конечная* точка репликации, которая заканчивается `*-r`.

1. Получение сведений о службе IP-адресов кластера с помощью [`kubectl get`][kubectl-get] команды.

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Пример результата

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Существует три службы: `namespace/cluster-name-ro` сопоставлены с портом 5433 и `namespace/cluster-name-rw``namespace/cluster-name-r` сопоставлены с портом 5433. Важно избегать использования того же порта, что и узел чтения и записи кластера базы данных PostgreSQL. Если вы хотите, чтобы приложения получают доступ только к реплике базы данных PostgreSQL только для чтения, перенаправьте их на порт 5433. Окончательная служба обычно используется для резервного копирования данных, но также может функционировать как узел только для чтения.

1. Получение сведений [`kubectl get`][kubectl-get] о службе с помощью команды.

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

1. Настройте службу подсистемы балансировки нагрузки со следующими файлами YAML с помощью [`kubectl apply`][kubectl-apply] команды.

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

1. Получение сведений [`kubectl describe`][kubectl-describe] о службе с помощью команды.

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

### Проверка общедоступных конечных точек PostgreSQL

В этом разделе описано, как правильно настроить Azure Load Balancer с помощью статического IP-адреса, созданного ранее, и маршрутизации подключений к основным репликам только для чтения и чтения, а также использовать интерфейс командной строки psql для подключения к обоим.

Помните, что основная конечная точка чтения и записи сопоставляется с TCP-портом 5432, а конечные точки реплики только для чтения сопоставляются с портом 54333, чтобы разрешить использовать одно и то же DNS-имя PostgreSQL для чтения и записи.

> [!NOTE]
> Вам потребуется значение пароля пользователя приложения для базовой проверки подлинности PostgreSQL, созданной ранее и хранящейся в переменной `$PG_DATABASE_APPUSER_SECRET` среды.

* Проверьте общедоступные конечные точки PostgreSQL с помощью следующих `psql` команд:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Пример результата

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

    Пример результата

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    При успешном подключении к основной конечной точке чтения и записи функция PostgreSQL возвращает значение `f` *false*, указывающее, что текущее подключение доступно для записи.

    При подключении к реплике функция возвращает `t` *значение true*, указывающее, что база данных находится в восстановлении и доступна только для чтения.

## Имитация un плановая отработка отказа

В этом разделе вы активируете внезапный сбой, удалив модуль pod, на котором выполняется основной модуль, который имитирует внезапный сбой или потерю сетевого подключения к узлу, на котором размещен основной сервер PostgreSQL.

1. Проверьте состояние запущенных экземпляров pod с помощью следующей команды:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Пример результата

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Удалите основной модуль pod с помощью [`kubectl delete`][kubectl-delete] команды.

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Убедитесь, что `pg-primary-cnpg-sryti1qf-2` экземпляр pod теперь является основным, используя следующую команду:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Пример результата

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. `pg-primary-cnpg-sryti1qf-1` Сбросите экземпляр pod в качестве основного с помощью следующей команды:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Убедитесь, что экземпляры pod вернулись в исходное состояние перед тестом un плановая отработка отказа с помощью следующей команды:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Пример результата

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Очистка ресурсов

* После завершения проверки развертывания удалите все ресурсы, созданные в этом руководстве [`az group delete`][az-group-delete] , с помощью команды.

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Следующие шаги

В этом руководстве вы узнали следующее:

* Используйте Azure CLI для создания кластера AKS с несколькими зонами.
* Разверните высокодоступный кластер PostgreSQL и базу данных с помощью оператора CNPG.
* Настройте мониторинг для PostgreSQL с помощью Prometheus и Grafana.
* Разверните пример набора данных в базе данных PostgreSQL.
* Выполните обновление кластера PostgreSQL и AKS.
* Имитация прерывания кластера и отработка отказа реплики PostgreSQL.
* Выполните резервное копирование и восстановление базы данных PostgreSQL.

Дополнительные сведения о том, как использовать AKS для рабочих нагрузок, см. в статье ["Что такое Служба Azure Kubernetes (AKS)?][what-is-aks]

## Соавторы

*Эта статья поддерживается корпорацией Майкрософт. Первоначально он был написан следующими участниками*:

* Кен Килти | Основной TPM
* Рассел де Пина | Основной TPM
* Адриан Джоан | Старший инженер клиента
* Дженни Хейс | Старший разработчик содержимого
* Кэрол Смит | Старший разработчик содержимого
* Эрин Шаффер | Разработчик содержимого 2
* Адам Шариф | Инженер клиента 2

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
