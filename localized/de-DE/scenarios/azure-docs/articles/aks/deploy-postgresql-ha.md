---
title: Bereitstellen einer hochverfügbaren PostgreSQL-Datenbank in AKS mithilfe der Azure CLI
description: In diesem Artikel werden Sie mithilfe des CloudNativePG-Operators eine hochverfügbare PostgreSQL-Datenbank in AKS bereitstellen.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Bereitstellen einer hoch verfügbaren PostgreSQL-Datenbank auf AKS

In diesem Artikel werden Sie eine hochverfügbare PostgreSQL-Datenbank auf AKS bereitstellen.

* Wenn Sie die erforderliche Infrastruktur für diesen Einsatz noch nicht erstellt haben, folgen Sie den Schritten unter [Erstellen der Infrastruktur für den Einsatz einer hochverfügbaren PostgreSQL-Datenbank auf AKS][create-infrastructure], um die Einrichtung vorzunehmen, und kehren Sie dann zu diesem Artikel zurück.

## Geheimschlüssel für benutzenden Personen der Bootstrap-App erstellen

1. Generieren Sie ein Geheimnis, um die PostgreSQL-Bereitstellung durch interaktives Login für eine benutzende Person mit dem [`kubectl create secret`][kubectl-create-secret]-Befehl zu validieren.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Überprüfen Sie, ob das Geheimnis mit dem [`kubectl get`][kubectl-get]-Befehl erfolgreich erstellt wurde.

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Umgebungsvariablen für den PostgreSQL-Cluster setzen

* Stellen Sie eine ConfigMap bereit, um Umgebungsvariablen für den PostgreSQL-Cluster zu setzen, indem Sie den folgenden [`kubectl apply`][kubectl-apply]-Befehl verwenden:

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

## Installieren Sie die Prometheus PodMonitors

Prometheus erstellt PodMonitors für die CNPG-Instanzen unter Verwendung eines Satzes von Standardaufzeichnungsregeln, die im CNPG GitHub Samples Repo gespeichert sind. In einer Produktionsumgebung würden diese Regeln nach Bedarf geändert werden.

1. Fügen Sie das Prometheus Community Helm-Repository mit dem [`helm repo add`][helm-repo-add]-Befehl hinzu.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Aktualisieren Sie das Prometheus Community Helm-Repository und installieren Sie es auf dem primären Cluster mit dem [`helm upgrade`][helm-upgrade]-Befehl mit dem `--install`-Flag.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Stellen Sie sicher, dass der PodMonitor erstellt wurde.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Erstellen einer Verbundanmeldeinformation

In diesem Abschnitt erstellen Sie eine Partneranmeldeinformation für PostgreSQL-Backups, damit CNPG die AKS-Workloadidentität zur Authentifizierung beim Speicherkontozel für Backups verwenden kann. Der CNPG-Operator erstellt ein Kubernetes-Dienstkonto mit demselben Namen wie der im CNPG-Clusterbereitstellungsmanifest verwendete Clustername.

1. Rufen Sie die OIDC-Aussteller-URL des Clusters mithilfe des [`az aks show`][az-aks-show]-Befehls ab.

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Erstellen Sie mithilfe des Befehls [`az identity federated-credential create`][az-identity-federated-credential-create] eine Anmeldeinformationen für die Verbundidentität.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Bereitstellen eines hoch verfügbaren PostgreSQL-Clusters

In diesem Abschnitt stellen Sie einen hochverfügbaren PostgreSQL-Cluster mit Hilfe der [CNPG Cluster Custom Resource Definition (CRD)][cluster-crd] bereit.

In der folgenden Tabelle sind die wichtigsten Eigenschaften aufgeführt, die im YAML-Bereitstellungsmanifest für das Cluster CRD festgelegt sind:

| Eigenschaft | Definition |
| --------- | ------------ |
| `inheritedMetadata` | Spezifisch für den CNPG-Operator. Die Metadaten werden an alle mit dem Cluster verbundenen Objekte vererbt. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | DNS-Bezeichnung zur Verwendung bei der Freigabe der Postgres-Clusterendpunkte mit Lese- und Schreibzugriff. |
| `labels: azure.workload.identity/use: "true"` | Zeigt an, dass AKS Workloadidentitätsabhängigkeiten in die Pods einfügen soll, die die PostgreSQL-Clusterinstanzen hosten. |
| `topologySpreadConstraints` | Sie benötigen unterschiedliche Zonen und verschiedene Knoten mit der Bezeichnung `"workload=postgres"`. |
| `resources` | Konfiguriert die Quality of Service (QoS)-Klasse *Garantiert*. In einer Produktionsumgebung sind diese Werte entscheidend für die maximale Nutzung der zugrunde liegenden Knoten-VM und variieren je nach der verwendeten Azure-VM-SKU. |
| `bootstrap` | Spezifisch für den CNPG-Operator. Initialisiert mit einer leeren App-Datenbank. |
| `storage` / `walStorage` | Spezifisch für den CNPG-Operator. Definiert Speichervorlagen für die PersistentVolumeClaims (PVCs) für Daten- und Protokollspeicher. Es ist auch möglich, Speicher für Tablespaces zu spezifizieren, die für höhere IOPs aufgeteilt werden. |
| `replicationSlots` | Spezifisch für den CNPG-Operator. Aktiviert Replikationsplätze für hohe Verfügbarkeit. |
| `postgresql` | Spezifisch für den CNPG-Operator. Karteneinstellungen für `postgresql.conf`, `pg_hba.conf` und `pg_ident.conf config`. |
| `serviceAccountTemplate` | Enthält die Vorlage, die für die Erstellung der Dienstkonten benötigt wird, und ordnet die Partneranmeldeinformationen für die AKS-Verbundidentität der UAMI zu, um die Authentifizierung der AKS-Workloadidentität von den Pods, die die PostgreSQL-Instanzen hosten, zu externen Azure-Ressourcen zu ermöglichen. |
| `barmanObjectStore` | Spezifisch für den CNPG-Operator. Konfiguriert die barman-cloud-Toolsuite unter Verwendung der AKS-Workloadidentität für die Authentifizierung beim Azure Blob Storage-Objektspeicher. |

1. Stellen Sie den PostgreSQL-Cluster mit der Cluster-CRD mithilfe des [`kubectl apply`][kubectl-apply]-Befehls bereit.

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

1. Überprüfen Sie, ob der primäre PostgreSQL-Cluster mithilfe des [`kubectl get`][kubectl-get]-Befehls erfolgreich erstellt wurde. In der CNPG-Cluster-CRD wurden drei Instanzen angegeben, die durch Anzeige der laufenden Pods überprüft werden können, sobald jede Instanz hochgefahren und für die Replikation verbunden wurde. Haben Sie etwas Geduld, da es einige Zeit dauern kann, bis alle drei Instanzen online sind und dem Cluster beitreten.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Beispielausgabe

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Überprüfen, ob der Prometheus PodMonitor läuft

Der CNPG-Operator erstellt automatisch einen PodMonitor für die primäre Instanz unter Verwendung der bei der [Prometheus Community-Installation](#install-the-prometheus-podmonitors) erstellten Aufzeichnungsregeln.

1. Überprüfen Sie, ob der PodMonitor läuft, indem Sie den [`kubectl get`][kubectl-get]-Befehl verwenden.

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Beispielausgabe

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Wenn Sie Azure Monitor für Managed Prometheus verwenden, müssen Sie einen weiteren PodMonitor unter Verwendung des benutzerdefinierten Gruppennamens hinzufügen. Die kundenspezifischen Ressourcendefinitionen (CRDs) der Prometheus-Community werden von Prometheus nicht übernommen. Neben dem Gruppennamen sind die CRDs identisch. Dadurch können PodMonitors für Managed Prometheus neben denen existieren, die den Community-PodMonitor verwenden. Wenn Sie nicht mit Managed Prometheus arbeiten, können Sie dies überspringen. Erstellen eines neuen PodMonitors:

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

Überprüfen Sie, ob der PodMonitor erstellt wurde (beachten Sie den Unterschied im Gruppennamen).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Option A – Azure Monitor Workspace

Sobald Sie den Postgres-Cluster und den PodMonitor bereitgestellt haben, können Sie die Metriken über das Azure-Portal in einem Azure Monitor-Arbeitsbereich anzeigen.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Screenshot mit Metriken in einem Azure Monitor-Arbeitsbereich." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Option B – Verwaltete Grafana

Alternativ können Sie, nachdem Sie die Postgres-Cluster- und PodMonitore bereitgestellt haben, ein Metrikdashboard auf der vom Bereitstellungsskript erstellten Managed-Grafana-Instanz erstellen, um die in den Azure Monitor-Arbeitsbereich exportierten Metriken zu visualisieren. Sie können über das Azure-Portal auf das Managed Grafana zugreifen. Navigieren Sie zu der verwalteten Grafana-Instanz, die vom Bereitstellungsskript erstellt wurde, und klicken Sie wie hier gezeigt auf den Endpunktlink:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Screenshot einer Azure Managed Grafana-Instanz." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Wenn Sie auf den Endpunktlink klicken, wird ein neues Browserfenster geöffnet, in dem Sie Dashboards auf der verwalteten Grafana-Instanz erstellen können. Wenn Sie den Anweisungen zum [Konfigurieren einer Azure Monitor-Datenquelle](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) folgen, können Sie anschließend Visualisierungen hinzufügen, um ein Dashboard mit Metriken aus dem Postgres-Cluster zu erstellen. Nachdem Sie die Datenquellenverbindung eingerichtet haben, klicken Sie im Hauptmenü auf die Option „Datenquellen“ und Sie sollten eine Reihe von Datenquellenoptionen für die Datenquellenverbindung sehen, wie hier gezeigt:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Screenshot mit Datenquellenoptionen." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Klicken Sie in der Option „Managed Prometheus“ auf die Option zum Erstellen eines Dashboards, um den Dashboardeditor zu öffnen. Sobald sich das Editorfenster öffnet, klicken Sie auf die Option „Visualisierung hinzufügen“ und dann auf die Option „Managed Prometheus“, um die Metriken des Postgres-Clusters zu durchsuchen. Sobald Sie die Metrik ausgewählt haben, die Sie visualisieren möchten, klicken Sie auf die Schaltfläche „Abfragen ausführen“, um die Daten für die Visualisierung abzurufen, wie hier gezeigt:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Screenshot des Konstruktdashboards." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Klicken Sie auf die Schaltfläche „Speichern“, um dem Dashboard den Bereich hinzuzufügen. Sie können weitere Panels hinzufügen, indem Sie im Dashboardeditor auf die Schaltfläche „Hinzufügen“ klicken und diesen Vorgang wiederholen, um weitere Metriken zu visualisieren. Wenn Sie die Metrikvisualisierungen hinzufügen, sollten Sie ein Ergebnis erhalten, das wie folgt aussieht:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Screenshot des Speicherdashboards." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Klicken Sie auf das Symbol zum Speichern, um Ihr Dashboard zu speichern.

## Überprüfen des bereitgestellten PostgreSQL-Clusters

Überprüfen Sie, ob PostgreSQL über mehrere Verfügbarkeitszonen verteilt ist, indem Sie die AKS-Knotendetails mithilfe des [`kubectl get`][kubectl-get]-Befehls abrufen.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Die Ausgabe sollte der folgenden Beispielausgabe ähneln, wobei die Verfügbarkeitszone für jeden Knoten angezeigt wird:

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

## Herstellen einer Verbindung mit PostgreSQL und Erstellen eines Beispieldatensatzes

In diesem Abschnitt erstellen Sie eine Tabelle und fügen einige Daten in die App-Datenbank ein, die in den zuvor bereitgestellten CNPG-Cluster-CRD erstellt wurde. Sie verwenden diese Daten, um die Sicherungs- und Wiederherstellungsoperationen für den PostgreSQL-Cluster zu validieren.

* Erstellen Sie eine Tabelle und fügen Sie mit den folgenden Befehlen Daten in die App-Datenbank ein:

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

    Ihre Ausgabe sollte in etwa wie die folgende Beispielausgabe aussehen:

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
## Verbindung zu PostgreSQL-Replikaten mit Lesezugriff

* Stellen Sie eine Verbindung zu den PostgreSQL-Replikaten mit Lesezugriff her und validieren Sie das Beispieldataset mit den folgenden Befehlen:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Beispielausgabe

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

    Beispielausgabe

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Einrichten von bedarfsgesteuerten und geplanten PostgreSQL-Backups mit Barman

1. Überprüfen Sie mit dem folgenden Befehl, ob der PostgreSQL-Cluster auf das in den CNPG-Cluster-CRD angegebene Azure-Speicherkonto zugreifen kann und ob `Working WAL archiving` als `OK` berichtet:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Beispielausgabe

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Stellen Sie ein On-Demand-Backup auf Azure Storage bereit, das die AKS Workloadidentitätsintegration verwendet, indem Sie die YAML-Datei mit dem Befehl [`kubectl apply`][kubectl-apply] verwenden.

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

1. Überprüfen Sie den Status der bedarfsgesteuerten Sicherung mit dem Befehl [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Beispielausgabe

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Überprüfen Sie mit dem folgenden Befehl, ob der Cluster einen ersten Wiederherstellungspunkt hat:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Beispielausgabe

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Konfigurieren Sie ein geplantes Backup für *jede Stunde um 15 Minuten nach der vollen Stunde*, indem Sie die YAML-Datei mit dem [`kubectl apply`][kubectl-apply]-Befehl.

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

1. Überprüfen Sie den Status der geplanten Sicherung mithilfe des [`kubectl describe`][kubectl-describe]-Befehls.

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Zeigen Sie die Sicherungsdateien an, die im Azure Blob Storage für den primären Cluster gespeichert sind, mithilfe des [`az storage blob list`][az-storage-blob-list]-Befehls.

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Ihre Ausgabe sollte der folgenden Beispielausgabe entsprechen, die bestätigt, dass die Sicherung erfolgreich war:

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

## Wiederherstellen der bedarfsgesteuerten Sicherung in einem neuen PostgreSQL-Cluster

In diesem Abschnitt stellen Sie die zuvor erstellte bedarfsgesteuerte Sicherung mithilfe des CNPG-Operators in einer neuen Instanz mithilfe der Bootstrap-Cluster-CRD wieder her. Der Einfachheit halber wird ein einzelner Instanzcluster verwendet. Denken Sie daran, dass die AKS-Workloadidentität (über CNPG inheritFromAzureAD) auf die Sicherungsdateien zugreift und dass der Name des Wiederherstellungsclusters verwendet wird, um ein neues Kubernetes-Dienstkonto zu generieren, das für den Wiederherstellungscluster spezifisch ist.

Außerdem erstellen Sie einen zweiten Satz Partneranmeldeinformationen, um das neue Wiederherstellungsclusterdienstkonto dem vorhandenen UAMI zuzuordnen, das Zugriff auf die Sicherungsdateien im BLOB-Speicher hat.

1. Erstellen Sie mithilfe des Befehls [`az identity federated-credential create`][az-identity-federated-credential-create] einen zweiten Satz Anmeldeinformationen für die Partneridentität.

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

1. Stellen Sie die bedarfsgesteuerte Sicherung mithilfe der Cluster-CRD mit dem [`kubectl apply`][kubectl-apply]-Befehl wieder her.

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

1. Stellen Sie eine Verbindung zur wiederhergestellten Instanz her und überprüfen Sie mit dem folgenden Befehl, ob das Dataset, das auf dem ursprünglichen Cluster erstellt wurde, in dem die Vollsicherung durchgeführt wurde, vorhanden ist:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Beispielausgabe

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Löschen Sie den wiederhergestellten Cluster mithilfe des folgenden Befehls:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Löschen Sie mithilfe des Befehls [`az identity federated-credential delete`][az-identity-federated-credential-delete] die Anmeldeinformationen für die Partneridentität.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Den PostgreSQL-Cluster über einen öffentlichen Lastenausgleich zugänglich machen

In diesem Abschnitt konfigurieren Sie die nötige Infrastruktur, um die PostgreSQL-Endpunkte für Lese- und Schreibzugriff mit IP-Quellenbeschränkungen für die öffentliche IP-Adresse Ihrer Clientworkstation freizugeben.

Sie rufen auch die folgenden Endpunkte vom Cluster-IP-Dienst ab:

* *Ein* primärer Lese-/Schreibzugriffsendpunkt, der auf `*-rw` endet.
* *Null bis N* (abhängig von der Anzahl der Replikate) schreibgeschützte Endpunkte, die auf `*-ro` enden.
* *Ein* Replikationsendpunkt, der auf `*-r` endet.

1. Rufen Sie die Cluster-IP-Dienstdetails mithilfe des [`kubectl get`][kubectl-get]-Befehls ab.

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Beispielausgabe

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Es gibt drei Dienste: `namespace/cluster-name-ro` ist dem Anschluss 5433 zugeordnet, `namespace/cluster-name-rw`, und `namespace/cluster-name-r` dem Anschluss 5433. Es ist wichtig, denselben Port wie den Lese-/Schreibknoten des PostgreSQL-Datenbankclusters zu vermeiden. Wenn Sie möchten, dass Anwendungen nur auf das schreibgeschützte Replikat des PostgreSQL-Datenbankclusters zugreifen, leiten Sie sie zu Port 5433. Der letzte Dienst wird normalerweise für Datensicherungen verwendet, kann aber auch als reiner Leseknoten fungieren.

1. Rufen Sie die Dienstdetails mithilfe des Befehls [`kubectl get`][kubectl-get] ab.

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

1. Konfigurieren Sie den Lastenausgleichsdienst mit den folgenden YAML-Dateien mithilfe des [`kubectl apply`][kubectl-apply]-Befehls.

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

1. Rufen Sie die Dienstdetails mithilfe des Befehls [`kubectl describe`][kubectl-describe] ab.

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

### Überprüfen öffentlicher PostgreSQL-Endpunkte

In diesem Abschnitt überprüfen Sie, ob der Azure Load Balancer ordnungsgemäß eingerichtet ist, indem Sie die zuvor erstellte statische IP-Adresse verwenden und Verbindungen zu den primären schreibgeschützten und schreibgeschützten Replikaten weiterleiten, und Sie verwenden die Befehlszeilenschnittstelle PSQL, um sich mit beiden zu verbinden.

Denken Sie daran, dass der primäre Schreib-/Leseendpunkt dem TCP-Port 5432 und die schreibgeschützten Replikationsendpunkte dem Port 5433 zugeordnet sind, damit der gleiche PostgreSQL-DNS-Name für Leser und Schreiber verwendet werden kann.

> [!NOTE]
> Sie benötigen den Wert des Kennworts der benutzenden Person für PostgreSQL „basic auth“, das zuvor generiert und in der Umgebungsvariablen `$PG_DATABASE_APPUSER_SECRET` gespeichert wurde.

* Überprüfen Sie die öffentlichen PostgreSQL-Endpunkte mithilfe der folgenden `psql`-Befehle:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Beispielausgabe

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

    Beispielausgabe

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Bei erfolgreicher Verbindung mit dem primären Schreib-/Leseendpunkt gibt die PostgreSQL-Funktion `f` für *FALSE* zurück, was anzeigt, dass die aktuelle Verbindung beschreibbar ist.

    Wenn eine Verbindung zu einem Replikat besteht, gibt die Funktion `t` *TRUE* zurück und zeigt damit an, dass die Datenbank wiederhergestellt und schreibgeschützt ist.

## Simulieren eines ungeplanten Failovers

In diesem Abschnitt lösen Sie einen plötzlichen Ausfall aus, indem Sie den Pod, auf dem der primäre Server läuft, löschen. Dies simuliert einen plötzlichen Absturz oder den Verlust der Netzwerkverbindung zu dem Knoten, auf dem der primäre PostgreSQL-Server läuft.

1. Überprüfen Sie den Status der laufenden Podinstanzen mit dem folgenden Befehl:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Beispielausgabe

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Löschen Sie den primären Pod mithilfe des [`kubectl delete`][kubectl-delete]-Befehls.

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Überprüfen Sie, ob die Podinstanz `pg-primary-cnpg-sryti1qf-2` jetzt der primäre Befehl ist, indem Sie den folgenden Befehl verwenden:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Beispielausgabe

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Setzen Sie die Podinstanz `pg-primary-cnpg-sryti1qf-1` als primäre Instanz mithilfe des folgenden Befehls zurück:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Überprüfen Sie mit folgendem Befehl, ob die Podinstanzen in ihren ursprünglichen Zustand vor dem ungeplanten Failovertest zurückgekehrt sind:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Beispielausgabe

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Bereinigen von Ressourcen

* Nachdem Sie die Überprüfung Der Bereitstellung abgeschlossen haben, löschen Sie alle Ressourcen, die Sie in dieser Anleitung erstellt haben, mithilfe des [`az group delete`][az-group-delete]-Befehls.

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Nächste Schritte

In dieser Schrittanleitung wurde Folgendes vermittelt:

* Verwenden Sie Azure CLI zum Erstellen eines AKS-Clusters mit mehreren Zonen.
* Bereitstellen eines hochverfügbaren PostgreSQL-Clusters und einer Datenbank mithilfe des CNPG-Operators.
* Richten Sie die Überwachung für PostgreSQL mithilfe von Prometheus und Grafana ein.
* Stellen Sie einen Beispieldataset für die PostgreSQL-Datenbank bereit.
* Führen Sie die PostgreSQL- und AKS-Clusterupgrades durch.
* Simulieren Sie eine Clusterunterbrechung und einen PostgreSQL-Replikatfailover.
* Führen Sie eine Sicherung und Wiederherstellung der PostgreSQL-Datenbank durch.

Weitere Informationen dazu, wie Sie AKS für Ihre Workloads nutzen können, finden Sie unter [Was ist Azure Kubernetes Service (AKS)?][what-is-aks]

## Beitragende

*Dieser Artikel wird von Microsoft verwaltet. Sie wurde ursprünglich von den folgenden Mitwirkenden* verfasst:

* Ken Kilty | Principal TPM
* Russell de Pina | Principal TPM
* Adrian Joian | Senior Customer Engineer
* Jenny Hayes | Senior Content Developer
* Carol Smith | Senior Content Developer
* Erin Schaffer | Content Developer 2
* Adam Sharif | Customer Engineer 2

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
