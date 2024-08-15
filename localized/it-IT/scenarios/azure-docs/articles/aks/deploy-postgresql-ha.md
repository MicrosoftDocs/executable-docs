---
title: Distribuire un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes con l'interfaccia della riga di comando di Azure
description: 'In questo articolo, si distribuirà un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes usando l''operatore CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Distribuire un database PostgreSQL a disponibilità elevata sul servizio Azure Kubernetes

In questo articolo viene distribuito un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes.

* Se non è già stata creata l'infrastruttura necessaria per questa distribuzione, seguire la procedura descritta in [Creare un'infrastruttura per la distribuzione di un database PostgreSQL a disponibilità elevata nel servizio Azure Kubernetes][create-infrastructure] per configurarla, poi tornare a questo articolo.

## Creare un segreto per l'utente dell'app bootstrap

1. Generare un segreto per convalidare la distribuzione di PostgreSQL tramite l'accesso interattivo per un utente dell'app bootstrap usando il comando [`kubectl create secret`][kubectl-create-secret].

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Verificare che il segreto sia stato creato correttamente usando il comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Impostare le variabili di ambiente per il cluster PostgreSQL

* Distribuire un oggetto ConfigMap per impostare le variabili di ambiente per il cluster PostgreSQL usando il comando [`kubectl apply`][kubectl-apply] seguente:

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

## Installare PodMonitors Prometheus

Prometheus crea PodMonitors per le istanze CNPG usando un set di regole di registrazione predefinite, archiviate nel repository di esempi GitHub CNPG. In un ambiente di produzione queste regole verranno modificate in base alle esigenze.

1. Aggiungere il repository Helm della community Prometheus usando il comando [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Aggiornare il repository Helm della community Prometheus e installarlo nel cluster primario usando il comando [`helm upgrade`][helm-upgrade] con il flag `--install`.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Verificare che il monitoraggio pod sia stato creato.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Creare credenziali federate

In questa sezione viene creata una credenziale di identità federata per PostgreSQL per consentire a CNPG di usare l'identità del carico di lavoro del servizio Azure Kubernetes per l'autenticazione nella destinazione dell'account di archiviazione per i backup. L'operatore CNPG crea un account del servizio Kubernetes con lo stesso nome del cluster denominato usato nel manifesto della distribuzione del cluster CNPG.

1. Ottenere l'URL dell'autorità di certificazione OIDC del cluster usando il comando [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Creare una credenziale di identità federata tramite il comando [`az identity federated-credential create`][az-identity-federated-credential-create].

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Distribuire un cluster PostgreSQL a disponibilità elevata

In questa sezione viene distribuito un cluster PostgreSQL a disponibilità elevata usando la [definizione di risorsa personalizzata (CRD) del cluster CNPG][cluster-crd].

Nella tabella seguente vengono descritte le proprietà chiave impostate nel manifesto della distribuzione YAML per la definizione di risorsa personalizzata del cluster:

| Proprietà | Definizione |
| --------- | ------------ |
| `inheritedMetadata` | Specifico dell'operatore CNPG. I metadati vengono ereditati da tutti gli oggetti correlati al cluster. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Etichetta DNS da usare quando si espongono gli endpoint del cluster Postgres di lettura/scrittura e di sola lettura. |
| `labels: azure.workload.identity/use: "true"` | Indica che il servizio Azure Kubernetes deve inserire le dipendenze dell'identità del carico di lavoro nei pod che ospitano le istanze del cluster PostgreSQL. |
| `topologySpreadConstraints` | Richiedere zone e nodi diversi con etichetta `"workload=postgres"`. |
| `resources` | Configura una classe QoS (Quality of Service) *Garantita*. In un ambiente di produzione, questi valori sono fondamentali per ottimizzare l'utilizzo della macchina virtuale del nodo sottostante e variare in base allo SKU della macchina virtuale di Azure usato. |
| `bootstrap` | Specifico dell'operatore CNPG. Inizializza con un database app vuoto. |
| `storage` / `walStorage` | Specifico dell'operatore CNPG. Definisce i modelli di archiviazione per i PVC (PersistentVolumeClaims) per l'archiviazione di dati e log. È inoltre possibile specificare lo spazio di archiviazione per gli spazi di tabella da partizionare per aumentare le operazioni di I/O. |
| `replicationSlots` | Specifico dell'operatore CNPG. Abilita gli slot di replica per la disponibilità elevata. |
| `postgresql` | Specifico dell'operatore CNPG. Esegue il mapping delle impostazioni per `postgresql.conf`, `pg_hba.conf` e `pg_ident.conf config`. |
| `serviceAccountTemplate` | Contiene il modello necessario per generare gli account del servizio ed eseguire il mapping delle credenziali dell'identità federata del servizio Azure Kubernetes all'UAMI per abilitare l'autenticazione dell'identità del carico di lavoro del servizio Azure Kubernetes dai pod che ospitano le istanze di PostgreSQL per le risorse di Azure esterne. |
| `barmanObjectStore` | Specifico dell'operatore CNPG. Configura la suite di strumenti barman-cloud usando l'identità del carico di lavoro del servizio Azure Kubernetes per l'autenticazione nell'archivio oggetti di Archiviazione BLOB di Azure. |

1. Distribuire il cluster PostgreSQL con definizione di risorsa personalizzata del cluster usando il comando [`kubectl apply`][kubectl-apply].

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

1. Verificare che il cluster PostgreSQL primario sia stato creato correttamente usando il comando [`kubectl get`][kubectl-get]. la definizione di risorsa personalizzata del cluster CNPG ha specificato tre istanze, che possono essere convalidate visualizzando i pod in esecuzione una volta che ogni istanza viene aperta e unita per la replica. Attendere un po' di tempo affinché tutte e tre le istanze siano online e unite al cluster.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Output di esempio

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Verificare che PodMonitor Prometheus sia in esecuzione

L'operatore CNPG crea automaticamente un PodMonitor per l'istanza primaria usando le regole di registrazione create durante l'[installazione della community Prometheus](#install-the-prometheus-podmonitors).

1. Verificare che PodMonitor sia in esecuzione usando il comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Output di esempio

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Se si usa Monitoraggio di Azure per Prometheus gestito, sarà necessario aggiungere un altro monitoraggio pod usando il nome del gruppo personalizzato. Prometheus gestito non preleva le definizioni di risorse personalizzate (CRD) dalla community Prometheus. A parte il nome del gruppo, le definizioni di risorse personalizzate sono le stesse. In questo modo, i monitoraggi dei pod per Prometheus gestito possono essere affiancati a quelli che usano il monitoraggio dei pod della community. Se non si usa Prometheus gestito, si possono ignorare queste indicazioni. Creare un nuovo monitoraggio pod:

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

Verificare che il monitoraggio pod sia stato creato (si noti la differenza nel nome del gruppo).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Opzione A - Area di lavoro di Monitoraggio di Azure

Dopo aver distribuito il cluster Postgres e il monitoraggio dei pod, è possibile visualizzare le metriche usando il portale di Azure in un'area di lavoro di Monitoraggio di Azure.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Screenshot che mostra le metriche in un'area di lavoro di Monitoraggio di Azure." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Opzione B - Grafana gestito

In alternativa, dopo aver distribuito il cluster Postgres e i monitoraggi dei pod, è possibile creare un dashboard delle metriche nell'istanza di Grafana gestita creata dallo script di distribuzione per visualizzare le metriche esportate nell'area di lavoro di Monitoraggio di Azure. È possibile accedere a Grafana gestito tramite il portale di Azure. Passare all'istanza di Grafana gestito creata dallo script di distribuzione e fare clic sul collegamento Endpoint come illustrato di seguito:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Screenshot che mostra un'istanza di Grafana gestita di Azure." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Facendo clic sul collegamento Endpoint verrà aperta una nuova finestra del browser in cui è possibile creare dashboard nell'istanza di Grafana gestito. Seguendo le istruzioni per [configurare un'origine dati di Monitoraggio di Azure](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in), è possibile aggiungere visualizzazioni per creare un dashboard di metriche dal cluster Postgres. Dopo aver configurato la connessione all'origine dati, dal menu principale cliccare sull'opzione Origini dati e verrà visualizzato un set di opzioni per l'origine dati per la connessione all'origine dati, come illustrato di seguito:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Screenshot che mostra le opzioni dell'origine dati." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Nell'opzione Prometheus gestito cliccare sull'opzione di creazione di un dashboard per aprire l'editor del dashboard. Dopo aver aperto la finestra dell'editor, fare clic sull'opzione Aggiungi visualizzazione, quindi fare clic sull'opzione Prometheus gestito per esplorare le metriche dal cluster Postgres. Dopo aver selezionato la metrica da visualizzare, fare clic sul pulsante Esegui query per recuperare i dati per la visualizzazione, come illustrato di seguito:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Screenshot che mostra il dashboard del costrutto." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Cliccare sul pulsante Salva per aggiungere il pannello al dashboard. È possibile aggiungere altri pannelli facendo clic sul pulsante Aggiungi nell'editor del dashboard e ripetendo questo processo per visualizzare altre metriche. L'aggiunta delle visualizzazioni delle metriche dovrebbe avere un aspetto simile al seguente:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Screenshot che mostra il dashboard di salvataggio." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Cliccare sull'icona Salva per salvare il dashboard.

## Esaminare il cluster PostgreSQL distribuito

Verificare che PostgreSQL sia distribuito in più zone di disponibilità recuperando i dettagli del nodo del servizio Azure Kubernetes tramite il comando [`kubectl get`][kubectl-get].

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

L'output dovrebbe essere simile all'output di esempio seguente, con la zona di disponibilità mostrata per ogni nodo:

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

## Connettersi a PostgreSQL e creare un set di dati di esempio

In questa sezione si crea una tabella e si inseriscono alcuni dati nel database dell'app creato nella definizione di risorsa personalizzata CNPG distribuita in precedenza. Questi dati vengono usati per convalidare le operazioni di backup e ripristino per il cluster PostgreSQL.

* Creare una tabella e inserire i dati nel database dell'app usando i comandi seguenti:

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

    L'output dovrebbe essere simile all'output di esempio seguente:

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
## Connettersi alle repliche di sola lettura di PostgreSQL

* Connettersi alle repliche di sola lettura di PostgreSQL e convalidare il set di dati di esempio usando i comandi seguenti:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Output di esempio

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

    Output di esempio

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Configurare backup PostgreSQL su richiesta e pianificati con Barman

1. Verificare che il cluster PostgreSQL possa accedere all'account di archiviazione di Azure specificato nella definizione di risorsa personalizzata del cluster CNPG e che `Working WAL archiving` riporti `OK` usando il comando seguente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Output di esempio

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Distribuire un backup su richiesta in Archiviazione di Azure, che usa l'integrazione dell'identità del carico di lavoro del servizio Azure Kubernetes usando il file YAML con il comando [`kubectl apply`][kubectl-apply].

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

1. Convalidare lo stato del backup su richiesta usando il comando [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Output di esempio

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Verificare che il cluster abbia un primo punto di recuperabilità usando il comando seguente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Output di esempio

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Configurare un backup pianificato *ogni ora a 15 minuti dall'ora* usando il file YAML con il comando [`kubectl apply`][kubectl-apply].

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

1. Convalidare lo stato del backup pianificato usando il comando [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Visualizzare i file di backup archiviati nell'archivio BLOB di Azure per il cluster primario usando il comando [`az storage blob list`][az-storage-blob-list].

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    L'output dovrebbe essere simile all'output di esempio seguente, verificando che il backup sia stato eseguito correttamente:

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

## Ripristinare il backup su richiesta in un nuovo cluster PostgreSQL

In questa sezione viene ripristinato il backup su richiesta creato in precedenza usando l'operatore CNPG in una nuova istanza tramite la definizione di risorsa personalizzata del cluster bootstrap. Per semplificare, viene usato un cluster a istanza singola. Tenere presente che l'identità del carico di lavoro del servizio Azure Kubernetes (tramite CNPG inheritFromAzureAD) accede ai file di backup, e che il nome del cluster di ripristino viene usato per generare un nuovo account del servizio Kubernetes specifico del cluster di ripristino.

È inoltre possibile creare una seconda credenziale federata per eseguire il mapping del nuovo account del servizio cluster di ripristino all'UAMI esistente con accesso "Collaboratore ai dati dei BLOB di archiviazione" nei file di backup dell'archiviazione BLOB.

1. Creare una seconda credenziale di identità federata tramite il comando [`az identity federated-credential create`][az-identity-federated-credential-create].

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

1. Ripristinare il backup su richiesta usando la definizione di risorse personalizzate del cluster con il comando [`kubectl apply`][kubectl-apply].

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

1. Connettersi all'istanza ripristinata, quindi verificare che sia presente il set di dati creato nel cluster originale in cui è stato eseguito il backup completo usando il comando seguente:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Output di esempio

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Eliminare il cluster ripristinato con il comando seguente:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Eliminare la credenziale di identità federata tramite il comando [`az identity federated-credential delete`][az-identity-federated-credential-delete].

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Esporre il cluster PostgreSQL usando un servizio di bilanciamento del carico pubblico

In questa sezione viene configurata l'infrastruttura necessaria per esporre pubblicamente gli endpoint di lettura/scrittura e di sola lettura PostgreSQL limitando l’origine IP all'indirizzo IP pubblico della workstation client.

È inoltre possibile recuperare gli endpoint seguenti dal servizio IP del cluster:

* *Un* endpoint primario di lettura/scrittura che termina con `*-rw`.
* *Da zero a N* (a seconda del numero di repliche) endpoint di sola lettura che terminano con `*-ro`.
* *Un* endpoint di replica che termina con `*-r`.

1. Ottenere i dettagli del servizio IP del cluster usando il comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Output di esempio

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Sono disponibili tre servizi: `namespace/cluster-name-ro` mappato alla porta 5433, `namespace/cluster-name-rw` e `namespace/cluster-name-r` mappati alla porta 5433. È importante evitare di usare la stessa porta del nodo di lettura/scrittura del cluster di database PostgreSQL. Per consentire alle applicazioni di accedere solo alla replica di sola lettura del cluster di database PostgreSQL, indirizzarle alla porta 5433. Il servizio finale viene in genere usato per i backup dei dati, ma può anche funzionare come nodo di sola lettura.

1. Ottenere i dettagli del servizio usando il comando [`kubectl get`][kubectl-get].

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

1. Configurare il servizio di bilanciamento del carico con i file YAML seguenti usando il comando [`kubectl apply`][kubectl-apply].

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

1. Ottenere i dettagli del servizio usando il comando [`kubectl describe`][kubectl-describe].

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

### Convalidare gli endpoint PostgreSQL pubblici

In questa sezione viene verificato che Azure Load Balancer sia configurato correttamente usando l'indirizzo IP statico creato in precedenza e le connessioni di routing alle repliche primarie di lettura/scrittura e di sola lettura, e viene usata l'interfaccia della riga di comando psql per connettersi a entrambe.

Tenere presente che l'endpoint primario di lettura/scrittura esegue il mapping alla porta TCP 5432 e che gli endpoint di replica di sola lettura eseguono il mapping alla porta 5433 per consentire l'uso dello stesso nome DNS PostgreSQL per lettori e scrittori.

> [!NOTE]
> È necessario il valore della password utente dell'app per PostgreSQL di base generata in precedenza e archiviata nella variabile di ambiente `$PG_DATABASE_APPUSER_SECRET`.

* Convalidare gli endpoint PostgreSQL pubblici usando i comandi `psql` seguenti:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Output di esempio

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

    Output di esempio

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Una volta stabilita la connessione all'endpoint di lettura/scrittura primario, la funzione PostgreSQL restituisce `f` per *false*, a indicare che la connessione corrente è scrivibile.

    Quando si è connessi a una replica, la funzione restituisce `t` per *true*, a indicare che il database è in fase di recupero e di sola lettura.

## Simulare un failover non pianificato

In questa sezione viene attivato un errore improvviso eliminando il pod che esegue il database primario, il che simula un arresto anomalo improvviso o una perdita di connettività di rete al nodo che ospita il database primario PostgreSQL.

1. Controllare lo stato delle istanze del pod in esecuzione usando il comando seguente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Output di esempio

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Eliminare il pod primario usando il comando [`kubectl delete`][kubectl-delete].

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Verificare che l'istanza del pod `pg-primary-cnpg-sryti1qf-2` ora sia la replica primaria usando il comando seguente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Output di esempio

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Reimpostare l'istanza del pod `pg-primary-cnpg-sryti1qf-1` come primaria usando il comando seguente:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Verificare che le istanze del pod siano tornate allo stato originale precedente al test di failover non pianificato usando il comando seguente:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Output di esempio

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Pulire le risorse

* Dopo aver esaminato la distribuzione, eliminare tutte le risorse create in questa guida usando il comando [`az group delete`][az-group-delete].

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Passaggi successivi

In questa guida procedurale si è appreso come:

* Usare l'interfaccia della riga di comando di Azure per creare un cluster del servizio Azure Kubernetes a più zone.
* Distribuire un cluster e un database PostgreSQL a disponibilità elevata usando l'operatore CNPG.
* Configurare il monitoraggio per PostgreSQL usando Prometheus e Grafana.
* Distribuire un set di dati di esempio nel database PostgreSQL.
* Eseguire gli aggiornamenti del cluster PostgreSQL e del servizio Azure Kubernetes.
* Simulare un'interruzione del cluster e il failover della replica PostgreSQL.
* Eseguire un backup e ripristino del database PostgreSQL.

Per altre informazioni su come sfruttare il servizio Azure Kubernetes per i carichi di lavoro, vedere [Che cos'è il servizio Azure Kubernetes?][what-is-aks]

## Collaboratori

*Questo articolo viene gestito da Microsoft. Originariamente è stato scritto dai collaboratori* seguenti:

* Ken Kilty | Responsabile TPM
* Russell de Pina | Responsabile TPM
* Adrian Joian | Senior Customer Engineer
* Jenny Hayes | Sviluppatore di contenuti senior
* Carol Smith | Sviluppatore di contenuti senior
* Erin Schaffer | Sviluppatore di contenuti 2
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
