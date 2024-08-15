---
title: Distribuera en PostgreSQL-databas med hög tillgänglighet på AKS med Azure CLI
description: I den här artikeln distribuerar du en PostgreSQL-databas med hög tillgänglighet på AKS med hjälp av CloudNativePG-operatorn.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Distribuera en PostgreSQL-databas med hög tillgänglighet på AKS

I den här artikeln distribuerar du en PostgreSQL-databas med hög tillgänglighet på AKS.

* Om du inte redan har skapat den infrastruktur som krävs för den här distributionen följer du stegen i [Skapa infrastruktur för att distribuera en PostgreSQL-databas med hög tillgänglighet i AKS][create-infrastructure] för att konfigurera och sedan kan du återgå till den här artikeln.

## Skapa hemlighet för bootstrap-appanvändare

1. Generera en hemlighet för att verifiera PostgreSQL-distributionen genom interaktiv inloggning för en bootstrap-appanvändare med hjälp av [`kubectl create secret`][kubectl-create-secret] kommandot .

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Kontrollera att hemligheten har skapats med kommandot [`kubectl get`][kubectl-get] .

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Ange miljövariabler för PostgreSQL-klustret

* Distribuera en ConfigMap för att ange miljövariabler för PostgreSQL-klustret med följande [`kubectl apply`][kubectl-apply] kommando:

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

## Installera Prometheus PodMonitors

Prometheus skapar PodMonitors för CNPG-instanserna med hjälp av en uppsättning standardinspelningsregler som lagras på CNPG GitHub-exempellagringsplatsen. I en produktionsmiljö ändras dessa regler efter behov.

1. Lägg till Prometheus Community Helm-lagringsplatsen med kommandot [`helm repo add`][helm-repo-add] .

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Uppgradera Prometheus Community Helm-lagringsplatsen och installera den på det primära klustret med kommandot [`helm upgrade`][helm-upgrade] med `--install` flaggan .

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Kontrollera att poddövervakaren har skapats.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Skapa en federerad autentiseringsuppgift

I det här avsnittet skapar du en federerad identitetsautentiseringsuppgift för PostgreSQL-säkerhetskopiering så att CNPG kan använda AKS-arbetsbelastningsidentitet för att autentisera till lagringskontots mål för säkerhetskopior. CNPG-operatorn skapar ett Kubernetes-tjänstkonto med samma namn som klustret med namnet som används i CNPG-klusterdistributionsmanifestet.

1. Hämta OIDC-utfärdarens URL för klustret med kommandot [`az aks show`][az-aks-show] .

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Skapa en federerad identitetsautentiseringsuppgift med kommandot [`az identity federated-credential create`][az-identity-federated-credential-create] .

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Distribuera ett PostgreSQL-kluster med hög tillgänglighet

I det här avsnittet distribuerar du ett PostgreSQL-kluster med hög tillgänglighet med hjälp av den anpassade resursdefinitionen [för CNPG-kluster (CRD).][cluster-crd]

I följande tabell beskrivs de nyckelegenskaper som anges i YAML-distributionsmanifestet för kluster-CRD:

| Property | Definition |
| --------- | ------------ |
| `inheritedMetadata` | Specifikt för CNPG-operatorn. Metadata ärvs av alla objekt som är relaterade till klustret. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | DNS-etikett för användning när skrivskyddade och skrivskyddade Postgres-klusterslutpunkter exponeras. |
| `labels: azure.workload.identity/use: "true"` | Anger att AKS ska mata in arbetsbelastningsidentitetsberoenden i poddarna som är värdar för PostgreSQL-klusterinstanserna. |
| `topologySpreadConstraints` | Kräv olika zoner och olika noder med etiketten `"workload=postgres"`. |
| `resources` | Konfigurerar en QoS-klass *(Quality of Service) för Guaranteed*. I en produktionsmiljö är dessa värden viktiga för att maximera användningen av den underliggande virtuella nodddatorn och varierar beroende på vilken Azure VM SKU som används. |
| `bootstrap` | Specifikt för CNPG-operatorn. Initieras med en tom appdatabas. |
| `storage` / `walStorage` | Specifikt för CNPG-operatorn. Definierar lagringsmallar för PersistentVolumeClaims (PVCs) för data och logglagring. Det går också att ange lagring för tablespaces som ska shardas ut för ökade IOP:er. |
| `replicationSlots` | Specifikt för CNPG-operatorn. Aktiverar replikeringsplatser för hög tillgänglighet. |
| `postgresql` | Specifikt för CNPG-operatorn. Maps-inställningar för `postgresql.conf`, `pg_hba.conf`och `pg_ident.conf config`. |
| `serviceAccountTemplate` | Innehåller mallen som behövs för att generera tjänstkontona och mappar AKS-federerade identitetsautentiseringsuppgifter till UAMI för att aktivera AKS-arbetsbelastningsidentitetsautentisering från poddarna som är värd för PostgreSQL-instanserna till externa Azure-resurser. |
| `barmanObjectStore` | Specifikt för CNPG-operatorn. Konfigurerar barman-cloud-verktygssviten med hjälp av AKS-arbetsbelastningsidentiteten för autentisering till Azure Blob Storage-objektarkivet. |

1. Distribuera PostgreSQL-klustret med kluster-CRD med hjälp av [`kubectl apply`][kubectl-apply] kommandot .

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

1. Kontrollera att det primära PostgreSQL-klustret har skapats med kommandot [`kubectl get`][kubectl-get] . CNPG-kluster-CRD angav tre instanser, som kan verifieras genom att visa poddar som körs när varje instans har tagits upp och anslutits för replikering. Ha tålamod eftersom det kan ta lite tid för alla tre instanserna att komma online och ansluta till klustret.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Exempel på utdata

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Verifiera att Prometheus PodMonitor körs

CNPG-operatorn skapar automatiskt en PodMonitor för den primära instansen med hjälp av de inspelningsregler som skapades under Installationen av [Prometheus Community](#install-the-prometheus-podmonitors).

1. Verifiera att PodMonitor körs med kommandot [`kubectl get`][kubectl-get] .

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Exempel på utdata

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Om du använder Azure Monitor för Managed Prometheus måste du lägga till ytterligare en poddövervakare med det anpassade gruppnamnet. Managed Prometheus hämtar inte de anpassade resursdefinitionerna (CRD) från Prometheus-communityn. Förutom gruppnamnet är CRD:erna samma. På så sätt kan poddövervakare för Managed Prometheus finnas sida vid sida som använder community-poddövervakaren. Om du inte använder Managed Prometheus kan du hoppa över det här. Skapa en ny poddövervakare:

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

Kontrollera att poddövervakaren har skapats (observera skillnaden i gruppnamnet).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Alternativ A – Azure Monitor-arbetsyta

När du har distribuerat Postgres-klustret och poddövervakaren kan du visa måtten med hjälp av Azure-portalen på en Azure Monitor-arbetsyta.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Skärmbild som visar mått på en Azure Monitor-arbetsyta." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Alternativ B – Hanterad Grafana

När du har distribuerat Postgres-klustret och poddövervakarna kan du också skapa en instrumentpanel för mått på den Hanterade Grafana-instansen som skapats av distributionsskriptet för att visualisera de mått som exporteras till Azure Monitor-arbetsytan. Du kan komma åt Managed Grafana via Azure-portalen. Gå till den hanterade Grafana-instansen som skapats av distributionsskriptet och klicka på länken Slutpunkt enligt följande:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Skärmbild som visar en Azure Managed Grafana-instans." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Om du klickar på länken Slutpunkt öppnas ett nytt webbläsarfönster där du kan skapa instrumentpaneler på den hanterade Grafana-instansen. Genom att följa anvisningarna för att [konfigurera en Azure Monitor-datakälla](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) kan du sedan lägga till visualiseringar för att skapa en instrumentpanel med mått från Postgres-klustret. När du har konfigurerat datakällanslutningen klickar du på alternativet Datakällor på huvudmenyn och du bör se en uppsättning datakällalternativ för datakällanslutningen enligt följande:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Skärmbild som visar alternativ för datakälla." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

I alternativet Hanterad Prometheus klickar du på alternativet för att skapa en instrumentpanel för att öppna instrumentpanelsredigeraren. När redigeringsfönstret öppnas klickar du på alternativet Lägg till visualisering och klickar sedan på alternativet Hanterad Prometheus för att bläddra bland måtten från Postgres-klustret. När du har valt det mått som du vill visualisera klickar du på knappen Kör frågor för att hämta data för visualiseringen enligt följande:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Skärmbild som visar instrumentpanelen för konstruktion." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Klicka på knappen Spara för att lägga till panelen på instrumentpanelen. Du kan lägga till andra paneler genom att klicka på knappen Lägg till i instrumentpanelsredigeraren och upprepa den här processen för att visualisera andra mått. Om du lägger till måttvisualiseringarna bör du ha något som ser ut så här:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Skärmbild som visar spara instrumentpanelen." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Spara instrumentpanelen genom att klicka på ikonen Spara.

## Granska det distribuerade PostgreSQL-klustret

Kontrollera att PostgreSQL är utspritt i flera tillgänglighetszoner genom att hämta AKS-nodinformationen [`kubectl get`][kubectl-get] med hjälp av kommandot .

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Dina utdata bör likna följande exempelutdata med tillgänglighetszonen som visas för varje nod:

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

## Anslut till PostgreSQL och skapa en exempeldatauppsättning

I det här avsnittet skapar du en tabell och infogar data i appdatabasen som skapades i CNPG-kluster-CRD som du distribuerade tidigare. Du använder dessa data för att verifiera säkerhetskopierings- och återställningsåtgärderna för PostgreSQL-klustret.

* Skapa en tabell och infoga data i appdatabasen med hjälp av följande kommandon:

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

    Dina utdata bör likna följande exempelutdata:

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
## Ansluta till Skrivskyddade PostgreSQL-repliker

* Anslut till PostgreSQL-skrivskyddade repliker och verifiera exempeldatauppsättningen med hjälp av följande kommandon:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Exempel på utdata

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

    Exempel på utdata

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Konfigurera postgreSQL-säkerhetskopieringar på begäran och schemalagda med Barman

1. Kontrollera att PostgreSQL-klustret kan komma åt azure-lagringskontot som anges i CNPG-kluster-CRD och som rapporterar som `Working WAL archiving` `OK` med hjälp av följande kommando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Exempel på utdata

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Distribuera en säkerhetskopiering på begäran till Azure Storage, som använder identitetsintegrering för AKS-arbetsbelastning med hjälp av YAML-filen med [`kubectl apply`][kubectl-apply] kommandot .

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

1. Verifiera statusen för säkerhetskopieringen på begäran med hjälp av [`kubectl describe`][kubectl-describe] kommandot .

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Exempel på utdata

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Kontrollera att klustret har en första återställningspunkt med hjälp av följande kommando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Exempel på utdata

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Konfigurera en schemalagd säkerhetskopiering för *varje timme vid 15 minuter efter timmen* med hjälp av YAML-filen med [`kubectl apply`][kubectl-apply] kommandot .

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

1. Verifiera statusen för den schemalagda säkerhetskopieringen [`kubectl describe`][kubectl-describe] med kommandot .

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Visa säkerhetskopieringsfilerna som lagras i Azure Blob Storage för det primära klustret med hjälp av [`az storage blob list`][az-storage-blob-list] kommandot .

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Dina utdata bör likna följande exempelutdata och verifieringen av säkerhetskopian lyckades:

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

## Återställa säkerhetskopieringen på begäran till ett nytt PostgreSQL-kluster

I det här avsnittet återställer du säkerhetskopieringen på begäran som du skapade tidigare med CNPG-operatorn till en ny instans med hjälp av bootstrap-kluster-CRD. Ett kluster med en enda instans används för enkelhetens skull. Kom ihåg att AKS-arbetsbelastningsidentiteten (via CNPG ärverFromAzureAD) har åtkomst till säkerhetskopieringsfilerna och att namnet på återställningsklustret används för att generera ett nytt Kubernetes-tjänstkonto som är specifikt för återställningsklustret.

Du kan också skapa en andra federerad autentiseringsuppgift för att mappa det nya tjänstkontot för återställningskluster till den befintliga UAMI som har åtkomsten "Storage Blob Data Contributor" till säkerhetskopieringsfilerna i Blob Storage.

1. Skapa en andra federerad identitetsautentiseringsuppgift med kommandot [`az identity federated-credential create`][az-identity-federated-credential-create] .

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

1. Återställ säkerhetskopieringen på begäran med hjälp av kluster-CRD med [`kubectl apply`][kubectl-apply] kommandot .

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

1. Anslut till den återställda instansen och kontrollera sedan att den datauppsättning som skapades i det ursprungliga klustret där den fullständiga säkerhetskopieringen gjordes finns med följande kommando:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Exempel på utdata

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Ta bort det återställda klustret med följande kommando:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Ta bort den federerade identitetsautentiseringsuppgiften [`az identity federated-credential delete`][az-identity-federated-credential-delete] med kommandot .

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Exponera PostgreSQL-klustret med hjälp av en offentlig lastbalanserare

I det här avsnittet konfigurerar du nödvändig infrastruktur för att offentligt exponera PostgreSQL-slutpunkterna för skrivskyddad och skrivskyddad med IP-källbegränsningar för den offentliga IP-adressen för klientarbetsstationen.

Du kan också hämta följande slutpunkter från kluster-IP-tjänsten:

* *En* primär läs- och skrivslutpunkt som slutar med `*-rw`.
* *Noll till N* (beroende på antalet repliker) skrivskyddade slutpunkter som slutar med `*-ro`.
* *En* replikeringsslutpunkt som slutar med `*-r`.

1. Hämta information om kluster-IP-tjänsten med hjälp av [`kubectl get`][kubectl-get] kommandot .

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Exempel på utdata

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Det finns tre tjänster: `namespace/cluster-name-ro` mappade till port 5433 och `namespace/cluster-name-rw``namespace/cluster-name-r` mappade till port 5433. Det är viktigt att undvika att använda samma port som läs-/skrivnoden i PostgreSQL-databasklustret. Om du bara vill att program ska få åtkomst till den skrivskyddade repliken av PostgreSQL-databasklustret dirigerar du dem till port 5433. Den slutliga tjänsten används vanligtvis för datasäkerhetskopior men kan också fungera som en skrivskyddad nod.

1. Hämta tjänstinformationen med hjälp av [`kubectl get`][kubectl-get] kommandot .

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

1. Konfigurera lastbalanserarens tjänst med följande YAML-filer med hjälp av [`kubectl apply`][kubectl-apply] kommandot .

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

1. Hämta tjänstinformationen med hjälp av [`kubectl describe`][kubectl-describe] kommandot .

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

### Verifiera offentliga PostgreSQL-slutpunkter

I det här avsnittet kontrollerar du att Azure Load Balancer har konfigurerats korrekt med den statiska IP-adress som du skapade tidigare och dirigerar anslutningar till de primära skrivskyddade och skrivskyddade replikerna och använder psql CLI för att ansluta till båda.

Kom ihåg att den primära skrivskyddade slutpunkten mappar till TCP-port 5432 och den skrivskyddade replikslutpunkten mappas till port 5433 så att samma PostgreSQL DNS-namn kan användas för läsare och skrivare.

> [!NOTE]
> Du behöver värdet för appanvändarlösenordet för grundläggande PostgreSQL-autentisering som genererades tidigare och lagrades i `$PG_DATABASE_APPUSER_SECRET` miljövariabeln.

* Verifiera de offentliga PostgreSQL-slutpunkterna med hjälp av följande `psql` kommandon:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Exempel på utdata

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

    Exempel på utdata

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    När den är ansluten till den primära skrivskyddade slutpunkten returnerar `f` funktionen PostgreSQL falskt**, vilket anger att den aktuella anslutningen kan skrivas.

    När den är ansluten till en replik returnerar `t` funktionen true**, vilket indikerar att databasen är i återställning och skrivskyddad.

## Simulera en oplanerad redundans

I det här avsnittet utlöser du ett plötsligt fel genom att ta bort podden som kör den primära, vilket simulerar en plötslig krasch eller förlust av nätverksanslutning till noden som är värd för PostgreSQL-primärt.

1. Kontrollera statusen för de poddinstanser som körs med hjälp av följande kommando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Exempel på utdata

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Ta bort den primära podden med kommandot [`kubectl delete`][kubectl-delete] .

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Kontrollera att poddinstansen `pg-primary-cnpg-sryti1qf-2` nu är den primära med hjälp av följande kommando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Exempel på utdata

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. `pg-primary-cnpg-sryti1qf-1` Återställ poddinstansen som primär med hjälp av följande kommando:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Kontrollera att poddinstanserna har återgåt till sitt ursprungliga tillstånd före det oplanerade redundanstestet med hjälp av följande kommando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Exempel på utdata

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Rensa resurser

* När du har granskat distributionen tar du bort alla resurser som du skapade i den här guiden med hjälp av [`az group delete`][az-group-delete] kommandot .

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Nästa steg

I den här guiden har du lärt dig att:

* Använd Azure CLI för att skapa ett AKS-kluster med flera zoner.
* Distribuera ett PostgreSQL-kluster och en databas med hög tillgänglighet med hjälp av CNPG-operatorn.
* Konfigurera övervakning för PostgreSQL med Prometheus och Grafana.
* Distribuera en exempeldatauppsättning till PostgreSQL-databasen.
* Utför uppgraderingar av PostgreSQL- och AKS-kluster.
* Simulera ett klusteravbrott och PostgreSQL-replikredundans.
* Utför en säkerhetskopia och återställning av PostgreSQL-databasen.

Mer information om hur du kan använda AKS för dina arbetsbelastningar finns i [Vad är Azure Kubernetes Service (AKS)?][what-is-aks]

## Deltagare

*Den här artikeln underhålls av Microsoft. Den skrevs ursprungligen av följande deltagare*:

* Ken Kilty | Huvudnamn för TPM
* Russell de Pina | Huvudnamn för TPM
* Adrian Joian | Senior kundtekniker
* Jenny Hayes | Senior innehållsutvecklare
* Carol Smith | Senior innehållsutvecklare
* Erin Schaffer | Innehållsutvecklare 2
* Adam Sharif | Kundtekniker 2

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
