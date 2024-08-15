---
title: Implementación de una base de datos PostgreSQL de alta disponibilidad en AKS con la CLI de Azure
description: 'En este artículo, implementará una base de datos PostgreSQL de alta disponibilidad en AKS mediante el operador CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Implementación de una base de datos PostgreSQL de alta disponibilidad en AKS

En este artículo, implementará una base de datos PostgreSQL de alta disponibilidad en AKS.

* Si aún no ha creado la infraestructura necesaria para esta implementación, siga los pasos descritos en [Creación de una infraestructura para implementar una base de datos PostgreSQL de alta disponibilidad en AKS][create-infrastructure] para configurarla y, a continuación, puede volver a este artículo.

## Creación de un secreto para el usuario de la aplicación de arranque

1. Genere un secreto para validar la implementación de PostgreSQL mediante el inicio de sesión interactivo de un usuario de aplicación de arranque mediante el comando [`kubectl create secret`][kubectl-create-secret].

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Compruebe que el secreto se creó correctamente mediante el comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Establecimiento de variables de entorno para el clúster de PostgreSQL

* Implemente un objeto ConfigMap para establecer variables de entorno para el clúster de PostgreSQL mediante el siguiente comando [`kubectl apply`][kubectl-apply]:

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

## Instalación de PodMonitors de Prometheus

Prometheus crea PodMonitors para las instancias de CNPG mediante un conjunto de reglas de grabación predeterminadas almacenadas en el repositorio de ejemplos de CNPG de GitHub. En un entorno de producción, estas reglas se modificarían según sea necesario.

1. Agregue el repositorio de Helm de la comunidad de Prometheus mediante el comando [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Actualice el repositorio de Helm de la comunidad de Prometheus e instálelo en el clúster principal mediante el comando [`helm upgrade`][helm-upgrade] con la marca `--install`.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Compruebe que se crea el monitor de pod.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Creación de una credencial federada

En esta sección, creará una credencial de identidad federada para la copia de seguridad de PostgreSQL para permitir que CNPG use la identidad de carga de trabajo de AKS para autenticarse en el destino de la cuenta de almacenamiento para las copias de seguridad. El operador CNPG crea una cuenta de servicio de Kubernetes con el mismo nombre que el clúster denominado usado en el manifiesto de implementación del clúster CNPG.

1. Obtenga la dirección URL del emisor de OIDC del clúster mediante el comando [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Cree una credencial de identidad federada mediante el comando [`az identity federated-credential create`][az-identity-federated-credential-create].

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Implementación de un clúster de PostgreSQL de alta disponibilidad

En esta sección, implementará un clúster de PostgreSQL de alta disponibilidad mediante la [definición de recursos personalizados (CRD) del clúster CNPG][cluster-crd].

En la tabla siguiente se describen las propiedades clave establecidas en el manifiesto de implementación de YAML para el CRD de clúster:

| Propiedad | Definición |
| --------- | ------------ |
| `inheritedMetadata` | Específico del operador CNPG. Todos los objetos relacionados con el clúster heredan los metadatos. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Etiqueta DNS para su uso al exponer los puntos de conexión de clúster de Postgres de solo lectura y escritura. |
| `labels: azure.workload.identity/use: "true"` | Indica que AKS debe insertar dependencias de identidad de carga de trabajo en los pods que hospedan las instancias del clúster de PostgreSQL. |
| `topologySpreadConstraints` | Requerir zonas diferentes y nodos diferentes con la etiqueta `"workload=postgres"`. |
| `resources` | Configura una clase de calidad de servicio (QoS) de *Garantizado*. En un entorno de producción, estos valores son clave para maximizar el uso de la máquina virtual del nodo subyacente y variar en función de la SKU de máquina virtual de Azure usada. |
| `bootstrap` | Específico del operador CNPG. Inicializa con una base de datos de aplicación vacía. |
| `storage` / `walStorage` | Específico del operador CNPG. Define plantillas de almacenamiento para PersistentVolumeClaims (PVC) para el almacenamiento de datos y registros. También es posible especificar el almacenamiento para que los espacios de tablas se particionen para aumentar las E/S por segundo. |
| `replicationSlots` | Específico del operador CNPG. Habilita ranuras de replicación para alta disponibilidad. |
| `postgresql` | Específico del operador CNPG. Asigna la configuración de `postgresql.conf`, `pg_hba.conf` y `pg_ident.conf config`. |
| `serviceAccountTemplate` | Contiene la plantilla necesaria para generar las cuentas de servicio y asignar la credencial de identidad federada de AKS a la UAMI para habilitar la autenticación de identidad de carga de trabajo de AKS desde los pods que hospedan las instancias de PostgreSQL a recursos externos de Azure. |
| `barmanObjectStore` | Específico del operador CNPG. Configura el conjunto de herramientas barman-cloud mediante la identidad de carga de trabajo de AKS para la autenticación en el almacén de objetos de Azure Blob Storage. |

1. Implemente el clúster de PostgreSQL con el CRD de clúster mediante el comando [`kubectl apply`][kubectl-apply].

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

1. Compruebe que el clúster de PostgreSQL principal se creó correctamente mediante el comando [`kubectl get`][kubectl-get]. La CRD del clúster CNPG especificó tres instancias, que se pueden validar mediante la visualización de pods en ejecución una vez que cada instancia se abre y se une para la replicación. Tenga paciencia, ya que puede tardar algún tiempo en conectarse a las tres instancias y unirse al clúster.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Salida de ejemplo

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Validar que Prometheus PodMonitor se está ejecutando

El operador CNPG crea automáticamente un PodMonitor para la instancia principal mediante las reglas de grabación creadas durante la [instalación de Prometheus Community](#install-the-prometheus-podmonitors).

1. Valide que PodMonitor se está ejecutando con el comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Salida de ejemplo

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Si usa Azure Monitor para Prometheus administrado, deberá agregar otro monitor de pod mediante el nombre del grupo personalizado. Prometheus administrado no recoge las definiciones de recursos personalizados (CRD) de la comunidad de Prometheus. Aparte del nombre del grupo, los CRD son los mismos. Esto permite que los monitores de pod para Prometheus administrado existan en paralelo con aquellos que usan el monitor de pods de la comunidad. Si no usa Prometheus administrado, puede omitirlo. Cree un nuevo monitor de pod:

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

Compruebe que se crea el monitor de pods (tenga en cuenta la diferencia en el nombre del grupo).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Opción A: área de trabajo de Azure Monitor

Una vez implementado el clúster de Postgres y el monitor de pods, puede ver las métricas mediante Azure Portal en un área de trabajo de Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Captura de pantalla que muestra las métricas en un área de trabajo de Azure Monitor." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Opción B: Grafana administrada

Como alternativa, una vez implementados los monitores de pod y clúster de Postgres, puede crear un panel de métricas en la instancia de Grafana administrada creada por el script de implementación para visualizar las métricas exportadas al área de trabajo de Azure Monitor. Puede acceder a Grafana administrada a través de Azure Portal. Vaya a la instancia de Grafana administrada creada por el script de implementación y haga clic en el vínculo Punto de conexión, como se muestra aquí:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Captura de pantalla que muestra una instancia de Grafana administrada de Azure." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Al hacer clic en el vínculo Punto de conexión, se abrirá una nueva ventana del explorador donde puede crear paneles en la instancia de Grafana administrada. Siguiendo las instrucciones para [configurar un origen de datos de Azure Monitor](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in), puede agregar visualizaciones para crear un panel de métricas desde el clúster de Postgres. Después de configurar la conexión de origen de datos, en el menú principal, haga clic en la opción Orígenes de datos y debería ver un conjunto de opciones de origen de datos para la conexión del origen de datos, como se muestra aquí:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Captura de pantalla que muestra las opciones del origen de datos." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

En la opción Prometheus administrado, haga clic en la opción para crear un panel para abrir el editor del panel. Una vez que se abra la ventana del editor, haga clic en la opción Agregar visualización y, a continuación, haga clic en la opción Prometheus administrado para examinar las métricas desde el clúster de Postgres. Una vez que haya seleccionado la métrica que desea visualizar, haga clic en el botón Ejecutar consultas para capturar los datos de la visualización, como se muestra aquí:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Captura de pantalla que muestra el panel de construcción." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Haga clic en el botón Guardar para agregar el panel al panel. Puede agregar otros paneles haciendo clic en el botón Agregar en el editor del panel y repitiendo este proceso para visualizar otras métricas. Al agregar las visualizaciones de métricas, debe tener algo similar al siguiente:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Captura de pantalla que muestra el panel de guardado." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Haga clic en el icono Guardar para guardar el panel.

## Inspección del clúster de PostgreSQL implementado

Compruebe que PostgreSQL se distribuye entre varias zonas de disponibilidad mediante la recuperación de los detalles del nodo de AKS mediante el comando [`kubectl get`][kubectl-get].

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

La salida debe ser similar a la siguiente salida de ejemplo con la zona de disponibilidad que se muestra para cada nodo:

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

## Conexión a PostgreSQL y creación de un conjunto de datos de ejemplo

En esta sección, creará una tabla e insertará algunos datos en la base de datos de la aplicación que se creó en el CRD del clúster CNPG que implementó anteriormente. Use estos datos para validar las operaciones de copia de seguridad y restauración del clúster de PostgreSQL.

* Cree una tabla e inserte datos en la base de datos de la aplicación mediante los siguientes comandos:

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

    La salida debería ser similar a la salida de ejemplo siguiente:

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
## Conexión a réplicas de solo lectura de PostgreSQL

* Conéctese a las réplicas de solo lectura de PostgreSQL y valide el conjunto de datos de ejemplo mediante los siguientes comandos:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Salida de ejemplo

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

    Salida de ejemplo

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Configuración de copias de seguridad de PostgreSQL a petición y programadas mediante Barman

1. Compruebe que el clúster de PostgreSQL puede acceder a la cuenta de almacenamiento de Azure especificada en el CRD del clúster CNPG y que `Working WAL archiving` notifica como `OK` mediante el comando siguiente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Salida de ejemplo

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Implemente una copia de seguridad a petición en Azure Storage, que usa la integración de identidades de carga de trabajo de AKS mediante el archivo YAML con el comando [`kubectl apply`][kubectl-apply].

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

1. Valide el estado de la copia de seguridad a petición mediante el comando [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Salida de ejemplo

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Compruebe que el clúster tiene un primer punto de capacidad de recuperación mediante el siguiente comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Salida de ejemplo

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Configure una copia de seguridad programada para *cada hora a 15 minutos después de la hora* mediante el archivo YAML con el comando [`kubectl apply`][kubectl-apply].

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

1. Valide el estado de la copia de seguridad programada mediante el comando [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Vea los archivos de copia de seguridad almacenados en Azure Blob Storage para el clúster principal mediante el comando [`az storage blob list`][az-storage-blob-list].

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    La salida debe ser similar a la siguiente salida de ejemplo, lo que valida que la copia de seguridad se realizó correctamente:

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

## Restauración de la copia de seguridad a petición en un nuevo clúster de PostgreSQL

En esta sección, restaurará la copia de seguridad a petición que creó anteriormente mediante el operador CNPG en una nueva instancia mediante el CRD de clúster de arranque. Se usa un único clúster de instancia para simplificar. Recuerde que la identidad de carga de trabajo de AKS (a través de inheritFromAzureAD de CNPG) tiene acceso a los archivos de copia de seguridad y que el nombre del clúster de recuperación se usa para generar una nueva cuenta de servicio de Kubernetes específica del clúster de recuperación.

También se crea una segunda credencial federada para asignar la nueva cuenta de servicio de clúster de recuperación a la UAMI existente que tiene acceso de "Colaborador de datos de blobs de almacenamiento" a los archivos de copia de seguridad en Blob Storage.

1. Cree una segunda credencial de identidad federada mediante el comando [`az identity federated-credential create`][az-identity-federated-credential-create].

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

1. Restaure la copia de seguridad a petición mediante el CRD de clúster con el comando [`kubectl apply`][kubectl-apply].

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

1. Conéctese a la instancia recuperada y, a continuación, compruebe que el conjunto de datos creado en el clúster original donde se realizó la copia de seguridad completa está presente mediante el siguiente comando:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Salida de ejemplo

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Elimine el clúster recuperado mediante el comando siguiente:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Elimine la credencial de identidad federada mediante el comando [`az identity federated-credential delete`][az-identity-federated-credential-delete].

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Exposición del clúster de PostgreSQL mediante un equilibrador de carga público

En esta sección, configurará la infraestructura necesaria para exponer públicamente los puntos de conexión de lectura y escritura de PostgreSQL y de solo lectura con restricciones de origen de IP a la dirección IP pública de la estación de trabajo cliente.

También se recuperan los siguientes puntos de conexión del servicio IP del clúster:

* *Un* punto de conexión de lectura y escritura principal que termina con `*-rw`.
* *Cero a N* (dependiendo del número de réplicas) puntos de conexión de solo lectura que terminan con `*-ro`.
* *Un* punto de conexión de replicación que termina con `*-r`.

1. Obtenga los detalles del servicio IP del clúster mediante el comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Salida de ejemplo

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Hay tres servicios: `namespace/cluster-name-ro` asignados al puerto 5433, `namespace/cluster-name-rw` y `namespace/cluster-name-r` asignados al puerto 5433. Es importante evitar el uso del mismo puerto que el nodo de lectura y escritura del clúster de base de datos PostgreSQL. Si desea que las aplicaciones accedan solo a la réplica de solo lectura del clúster de base de datos de PostgreSQL, apúntelas al puerto 5433. El servicio final se usa normalmente para las copias de seguridad de datos, pero también puede funcionar como un nodo de solo lectura.

1. Obtenga los detalles del servicio mediante el comando [`kubectl get`][kubectl-get].

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

1. Configure el servicio de equilibrador de carga con los siguientes archivos YAML mediante el comando [`kubectl apply`][kubectl-apply].

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

1. Obtenga los detalles del servicio mediante el comando [`kubectl describe`][kubectl-describe].

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

### Validación de puntos de conexión públicos de PostgreSQL

En esta sección, validará que Azure Load Balancer está configurado correctamente mediante la dirección IP estática que creó anteriormente y enrutar conexiones a las réplicas principales de lectura y escritura y de solo lectura y usar la CLI de psql para conectarse a ambas.

Recuerde que el punto de conexión principal de lectura y escritura se asigna al puerto TCP 5432 y los puntos de conexión de réplica de solo lectura se asignan al puerto 5433 para permitir que se use el mismo nombre DNS de PostgreSQL para lectores y escritores.

> [!NOTE]
> Necesita el valor de la contraseña de usuario de la aplicación para la autenticación básica de PostgreSQL que se generó anteriormente y se almacenó en la variable de entorno `$PG_DATABASE_APPUSER_SECRET`.

* Valide los puntos de conexión públicos de PostgreSQL mediante los siguientes comandos `psql`:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Salida de ejemplo

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

    Salida de ejemplo

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Cuando se conecta correctamente al punto de conexión de lectura y escritura principal, la función PostgreSQL devuelve `f` para *false*, lo que indica que la conexión actual se puede escribir.

    Cuando se conecta a una réplica, la función devuelve `t` para *true*, lo que indica que la base de datos está en recuperación y de solo lectura.

## Simular una conmutación por error no planeada

En esta sección, desencadenará un error repentino eliminando el pod que ejecuta la principal, lo que simula un bloqueo repentino o una pérdida de conectividad de red al nodo que hospeda la base de datos principal de PostgreSQL.

1. Compruebe el estado de las instancias de pod en ejecución mediante el comando siguiente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Salida de ejemplo

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Elimine el pod principal mediante el comando [`kubectl delete`][kubectl-delete].

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Compruebe que la instancia de pod `pg-primary-cnpg-sryti1qf-2` es ahora la principal mediante el siguiente comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Salida de ejemplo

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Restablezca la instancia de pod `pg-primary-cnpg-sryti1qf-1` como principal mediante el comando siguiente:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Compruebe que las instancias de pod se han devuelto a su estado original antes de la prueba de conmutación por error no planeada mediante el siguiente comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Salida de ejemplo

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Limpieza de recursos

* Una vez que haya terminado de revisar la implementación, elimine todos los recursos que creó en esta guía mediante el comando [`az group delete`][az-group-delete].

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Pasos siguientes

En esta guía paso a paso, ha aprendido lo siguiente:

* Use la CLI de Azure para crear un clúster de AKS de varias zonas.
* Implemente un clúster y una base de datos de PostgreSQL de alta disponibilidad mediante el operador CNPG.
* Configure la supervisión de PostgreSQL mediante Prometheus y Grafana.
* Implemente un conjunto de datos de ejemplo en la base de datos PostgreSQL.
* Realice actualizaciones de clúster de PostgreSQL y AKS.
* Simulación de una interrupción del clúster y conmutación por error de réplica de PostgreSQL.
* Realice una copia de seguridad y restauración de la base de datos PostgreSQL.

Para más información sobre cómo puede aprovechar AKS para las cargas de trabajo, consulte [¿Qué es Azure Kubernetes Service (AKS)?][what-is-aks]

## Colaboradores

*Microsoft mantiene este artículo. Originalmente fue escrito por los siguientes colaboradores*:

* Ken Kilty | TPM de entidad de seguridad
* Russell de Pina | TPM de entidad de seguridad
* Adrian Joian | Ingeniero de clientes sénior
* Jenny Hayes | Desarrollador de contenido sénior
* Carol Smith | Desarrollador de contenido sénior
* Erin Schaffer | Desarrollador de contenido 2
* Adam Fabric | Ingeniero de clientes 2

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
