---
title: Een maximaal beschikbare PostgreSQL-database implementeren in AKS met Azure CLI
description: In dit artikel implementeert u een maximaal beschikbare PostgreSQL-database op AKS met behulp van de CloudNativePG-operator.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Een maximaal beschikbare PostgreSQL-database implementeren in AKS

In dit artikel implementeert u een maximaal beschikbare PostgreSQL-database op AKS.

* Als u de vereiste infrastructuur voor deze implementatie nog niet hebt gemaakt, volgt u de stappen in [Infrastructuur maken voor het implementeren van een maximaal beschikbare PostgreSQL-database op AKS][create-infrastructure] om deze in te stellen. Vervolgens kunt u terugkeren naar dit artikel.

## Geheim maken voor bootstrap-app-gebruiker

1. Genereer een geheim om de PostgreSQL-implementatie te valideren door interactieve aanmelding voor een bootstrap-app-gebruiker met behulp van de [`kubectl create secret`][kubectl-create-secret] opdracht.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Controleer of het geheim is gemaakt met behulp van de [`kubectl get`][kubectl-get] opdracht.

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Omgevingsvariabelen instellen voor het PostgreSQL-cluster

* Implementeer een ConfigMap om omgevingsvariabelen in te stellen voor het PostgreSQL-cluster met behulp van de volgende [`kubectl apply`][kubectl-apply] opdracht:

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

## De Prometheus PodMonitors installeren

Prometheus maakt PodMonitors voor de CNPG-exemplaren met behulp van een set standaardopnameregels die zijn opgeslagen in de opslagplaats voor CNPG GitHub-voorbeelden. In een productieomgeving worden deze regels zo nodig gewijzigd.

1. Voeg de Prometheus Community Helm-opslagplaats toe met behulp van de [`helm repo add`][helm-repo-add] opdracht.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Werk de Prometheus Community Helm-opslagplaats bij en installeer deze op het primaire cluster met behulp van de [`helm upgrade`][helm-upgrade] opdracht met de `--install` vlag.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Controleer of de podmonitor is gemaakt.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Een federatieve referentie maken

In deze sectie maakt u een federatieve identiteitsreferentie voor PostgreSQL-back-up, zodat CNPG AKS-workloadidentiteit kan gebruiken om te verifiëren bij de bestemming van het opslagaccount voor back-ups. De CNPG-operator maakt een Kubernetes-serviceaccount met dezelfde naam als het cluster dat wordt gebruikt in het CNPG-clusterimplementatiemanifest.

1. Haal de URL van de OIDC-verlener van het cluster op met behulp van de [`az aks show`][az-aks-show] opdracht.

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Maak een federatieve identiteitsreferentie met behulp van de [`az identity federated-credential create`][az-identity-federated-credential-create] opdracht.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Een postgreSQL-cluster met hoge beschikbaarheid implementeren

In deze sectie implementeert u een maximaal beschikbare PostgreSQL-cluster met behulp van de [aangepaste CRD -definitie (CNPG-cluster).][cluster-crd]

De volgende tabel bevat een overzicht van de belangrijkste eigenschappen die zijn ingesteld in het YAML-implementatiemanifest voor de CLUSTER CRD:

| Eigenschap | Definitie |
| --------- | ------------ |
| `inheritedMetadata` | Specifiek voor de CNPG-operator. Metagegevens worden overgenomen door alle objecten die betrekking hebben op het cluster. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | DNS-label voor gebruik bij het weergeven van de postgres-eindpunten voor lezen/schrijven en alleen-lezen. |
| `labels: azure.workload.identity/use: "true"` | Geeft aan dat AKS workloadidentiteitsafhankelijkheden moet injecteren in de pods die als host fungeren voor de PostgreSQL-clusterexemplaren. |
| `topologySpreadConstraints` | Verschillende zones en verschillende knooppunten met label `"workload=postgres"`vereisen. |
| `resources` | Hiermee configureert u een QoS-klasse (Quality of Service) van *Gegarandeerd*. In een productieomgeving zijn deze waarden essentieel voor het maximaliseren van het gebruik van de onderliggende knooppunt-VM en variëren op basis van de gebruikte Azure VM-SKU. |
| `bootstrap` | Specifiek voor de CNPG-operator. Initialiseert met een lege app-database. |
| `storage` / `walStorage` | Specifiek voor de CNPG-operator. Definieert opslagsjablonen voor de PersistentVolumeClaims (PVC's) voor gegevens- en logboekopslag. Het is ook mogelijk om opslag op te geven voor tablespaces om uit te sharden voor verhoogde IOPS. |
| `replicationSlots` | Specifiek voor de CNPG-operator. Hiermee schakelt u replicatiesites in voor hoge beschikbaarheid. |
| `postgresql` | Specifiek voor de CNPG-operator. Kaartinstellingen voor `postgresql.conf`, `pg_hba.conf`en `pg_ident.conf config`. |
| `serviceAccountTemplate` | Bevat de sjabloon die nodig is voor het genereren van de serviceaccounts en wijst de federatieve AKS-identiteitsreferenties toe aan de UAMI om AKS-workloadidentiteitsverificatie in te schakelen van de pods die als host fungeren voor de PostgreSQL-exemplaren naar externe Azure-resources. |
| `barmanObjectStore` | Specifiek voor de CNPG-operator. Hiermee configureert u de barman-cloud tool suite met behulp van AKS-workloadidentiteit voor verificatie bij het Azure Blob Storage-objectarchief. |

1. Implementeer het PostgreSQL-cluster met cluster CRD met behulp van de [`kubectl apply`][kubectl-apply] opdracht.

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

1. Controleer of het primaire PostgreSQL-cluster is gemaakt met behulp van de [`kubectl get`][kubectl-get] opdracht. Het CNPG-cluster CRD heeft drie exemplaren opgegeven, die kunnen worden gevalideerd door actieve pods weer te geven zodra elk exemplaar wordt opgehaald en toegevoegd voor replicatie. Wees geduldig omdat het enige tijd kan duren voordat alle drie de exemplaren online zijn en deelnemen aan het cluster.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Voorbeelduitvoer

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Valideren dat Prometheus PodMonitor wordt uitgevoerd

De CNPG-operator maakt automatisch een PodMonitor voor het primaire exemplaar met behulp van de opnameregels die zijn gemaakt tijdens de installatie van[ de ](#install-the-prometheus-podmonitors)Prometheus Community.

1. Controleer of PodMonitor wordt uitgevoerd met behulp van de [`kubectl get`][kubectl-get] opdracht.

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Voorbeelduitvoer

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Als u Azure Monitor voor Beheerde Prometheus gebruikt, moet u een andere podmonitor toevoegen met behulp van de aangepaste groepsnaam. Beheerde Prometheus haalt de aangepaste resourcedefinities (CRD's) niet op uit de Prometheus-community. Afgezien van de groepsnaam zijn de CRD's hetzelfde. Hierdoor kunnen podmonitors voor Beheerde Prometheus naast elkaar bestaan die gebruikmaken van de communitypodmonitor. Als u Beheerde Prometheus niet gebruikt, kunt u dit overslaan. Maak een nieuwe podmonitor:

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

Controleer of de podmonitor is gemaakt (let op het verschil in de groepsnaam).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Optie A - Azure Monitor-werkruimte

Zodra u het Postgres-cluster en de podmonitor hebt geïmplementeerd, kunt u de metrische gegevens bekijken met behulp van Azure Portal in een Azure Monitor-werkruimte.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Schermopname van metrische gegevens in een Azure Monitor-werkruimte." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Optie B - Beheerd Grafana

Als u het Postgres-cluster en de podmonitoren hebt geïmplementeerd, kunt u ook een dashboard met metrische gegevens maken op het beheerde Grafana-exemplaar dat door het implementatiescript is gemaakt om de metrische gegevens te visualiseren die zijn geëxporteerd naar de Azure Monitor-werkruimte. U hebt toegang tot managed Grafana via Azure Portal. Navigeer naar het beheerde Grafana-exemplaar dat is gemaakt met het implementatiescript en klik op de koppeling Eindpunt, zoals hier wordt weergegeven:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Schermopname van een azure Managed Grafana-exemplaar." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Als u op de koppeling Eindpunt klikt, wordt er een nieuw browservenster geopend waar u dashboards kunt maken op het beheerde Grafana-exemplaar. Volg de instructies voor [het configureren van een Azure Monitor-gegevensbron](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in). Vervolgens kunt u visualisaties toevoegen om een dashboard met metrische gegevens te maken vanuit het Postgres-cluster. Nadat u de verbinding met de gegevensbron hebt ingesteld, klikt u in het hoofdmenu op de optie Gegevensbronnen en ziet u een set opties voor de gegevensbronverbinding, zoals hier wordt weergegeven:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Schermopname met opties voor gegevensbronnen." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Klik in de optie Managed Prometheus op de optie om een dashboard te maken om de dashboardeditor te openen. Zodra het editorvenster wordt geopend, klikt u op de optie Visualisatie toevoegen en klikt u vervolgens op de optie Beheerde Prometheus om door de metrische gegevens van het Postgres-cluster te bladeren. Nadat u de metrische gegevens hebt geselecteerd die u wilt visualiseren, klikt u op de knop Query's uitvoeren om de gegevens voor de visualisatie op te halen, zoals hier wordt weergegeven:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Schermopname van het constructdashboard." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Klik op de knop Opslaan om het deelvenster toe te voegen aan uw dashboard. U kunt andere panelen toevoegen door te klikken op de knop Toevoegen in de dashboardeditor en dit proces te herhalen om andere metrische gegevens te visualiseren. Als u de visualisaties voor metrische gegevens toevoegt, moet u iets hebben dat er als volgt uitziet:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Schermopname van het dashboard opslaan." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Klik op het pictogram Opslaan om uw dashboard op te slaan.

## Het geïmplementeerde PostgreSQL-cluster controleren

Controleer of PostgreSQL is verdeeld over meerdere beschikbaarheidszones door de details van het AKS-knooppunt op te halen met behulp van de [`kubectl get`][kubectl-get] opdracht.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Uw uitvoer moet er ongeveer uitzien als in de volgende voorbeelduitvoer met de beschikbaarheidszone die voor elk knooppunt wordt weergegeven:

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

## Verbinding maken met PostgreSQL en een voorbeeldgegevensset maken

In deze sectie maakt u een tabel en voegt u enkele gegevens in de app-database in die is gemaakt in de CNPG-cluster-CRD die u eerder hebt geïmplementeerd. U gebruikt deze gegevens om de back-up- en herstelbewerkingen voor het PostgreSQL-cluster te valideren.

* Maak een tabel en voeg gegevens in de app-database in met behulp van de volgende opdrachten:

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

    De uitvoer moet er ongeveer uitzien als in de volgende voorbeelduitvoer:

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
## Verbinding maken met Alleen-lezen Replica's van PostgreSQL

* Maak verbinding met de alleen-lezen Replica's van PostgreSQL en valideer de voorbeeldgegevensset met behulp van de volgende opdrachten:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Voorbeelduitvoer

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

    Voorbeelduitvoer

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## PostgreSQL-back-ups op aanvraag en gepland instellen met Behulp van Barman

1. Controleer of het PostgreSQL-cluster toegang heeft tot het Azure-opslagaccount dat is opgegeven in het CNPG-cluster CRD en dat `Working WAL archiving` rapporteert met `OK` behulp van de volgende opdracht:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Voorbeelduitvoer

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Implementeer een back-up op aanvraag in Azure Storage, die gebruikmaakt van de integratie van de AKS-workloadidentiteit met behulp van het YAML-bestand met de [`kubectl apply`][kubectl-apply] opdracht.

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

1. Valideer de status van de back-up op aanvraag met behulp van de [`kubectl describe`][kubectl-describe] opdracht.

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Voorbeelduitvoer

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Controleer of het cluster een eerste herstelpunt heeft met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Voorbeelduitvoer

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Configureer een geplande back-up voor *elk uur om 15 minuten na het uur* met behulp van het YAML-bestand met de [`kubectl apply`][kubectl-apply] opdracht.

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

1. Valideer de status van de geplande back-up met behulp van de [`kubectl describe`][kubectl-describe] opdracht.

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Bekijk de back-upbestanden die zijn opgeslagen in Azure Blob Storage voor het primaire cluster met behulp van de [`az storage blob list`][az-storage-blob-list] opdracht.

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    De uitvoer moet lijken op de volgende voorbeelduitvoer, waarbij de back-up is gevalideerd:

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

## De back-up op aanvraag herstellen naar een nieuw PostgreSQL-cluster

In deze sectie herstelt u de back-up op aanvraag die u eerder hebt gemaakt met behulp van de CNPG-operator in een nieuw exemplaar met behulp van de bootstrapcluster-CRD. Een cluster met één exemplaar wordt gebruikt om het eenvoudig te maken. Houd er rekening mee dat de AKS-workloadidentiteit (via CNPG inheritFromAzureAD) toegang heeft tot de back-upbestanden en dat de naam van het herstelcluster wordt gebruikt om een nieuw Kubernetes-serviceaccount te genereren dat specifiek is voor het herstelcluster.

U maakt ook een tweede federatieve referentie om het nieuwe serviceaccount voor het herstelcluster toe te wijzen aan de bestaande UAMI met 'Inzender voor opslagblobgegevens' tot de back-upbestanden in blobopslag.

1. Maak een tweede federatieve identiteitsreferentie met behulp van de [`az identity federated-credential create`][az-identity-federated-credential-create] opdracht.

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

1. Herstel de back-up op aanvraag met behulp van cluster CRD met de [`kubectl apply`][kubectl-apply] opdracht.

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

1. Maak verbinding met het herstelde exemplaar en valideer vervolgens of de gegevensset die is gemaakt op het oorspronkelijke cluster waarop de volledige back-up is gemaakt aanwezig is met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Voorbeelduitvoer

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Verwijder het herstelde cluster met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Verwijder de federatieve identiteitsreferentie met behulp van de [`az identity federated-credential delete`][az-identity-federated-credential-delete] opdracht.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Het PostgreSQL-cluster beschikbaar maken met behulp van een openbare load balancer

In deze sectie configureert u de benodigde infrastructuur om de PostgreSQL-eindpunten voor lezen/schrijven en alleen-lezen beschikbaar te maken met IP-bronbeperkingen voor het openbare IP-adres van uw clientwerkstation.

U haalt ook de volgende eindpunten op uit de CLUSTER-IP-service:

* *Eén* primair eindpunt voor lezen/schrijven dat eindigt op `*-rw`.
* *Nul tot N* (afhankelijk van het aantal replica's) alleen-lezen eindpunten die eindigen op `*-ro`.
* *Eén* replicatie-eindpunt dat eindigt op `*-r`.

1. Haal de details van de Cluster IP-service op met behulp van de [`kubectl get`][kubectl-get] opdracht.

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Voorbeelduitvoer

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Er zijn drie services: `namespace/cluster-name-ro` toegewezen aan poort 5433 en `namespace/cluster-name-rw``namespace/cluster-name-r` toegewezen aan poort 5433. Het is belangrijk om te voorkomen dat u dezelfde poort gebruikt als het lees-/schrijfknooppunt van het PostgreSQL-databasecluster. Als u wilt dat toepassingen alleen toegang hebben tot de alleen-lezen replica van het PostgreSQL-databasecluster, stuurt u deze naar poort 5433. De laatste service wordt doorgaans gebruikt voor gegevensback-ups, maar kan ook fungeren als een alleen-lezen knooppunt.

1. Haal de servicedetails op met behulp van de [`kubectl get`][kubectl-get] opdracht.

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

1. Configureer de load balancer-service met de volgende YAML-bestanden met behulp van de [`kubectl apply`][kubectl-apply] opdracht.

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

1. Haal de servicedetails op met behulp van de [`kubectl describe`][kubectl-describe] opdracht.

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

### Openbare PostgreSQL-eindpunten valideren

In deze sectie controleert u of de Azure Load Balancer juist is ingesteld met behulp van het statische IP-adres dat u eerder hebt gemaakt en verbindingen omleiden naar de primaire replica's met het kenmerk Alleen-lezen en alleen-lezen en de psql CLI gebruiken om verbinding te maken met beide.

Houd er rekening mee dat het primaire eindpunt voor lezen/schrijven is toegewezen aan TCP-poort 5432 en de alleen-lezen replica-eindpunten worden toegewezen aan poort 5433, zodat dezelfde PostgreSQL DNS-naam kan worden gebruikt voor lezers en schrijvers.

> [!NOTE]
> U hebt de waarde nodig van het app-gebruikerswachtwoord voor postgreSQL-basisverificatie die eerder is gegenereerd en die is opgeslagen in de `$PG_DATABASE_APPUSER_SECRET` omgevingsvariabele.

* Valideer de openbare PostgreSQL-eindpunten met behulp van de volgende `psql` opdrachten:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Voorbeelduitvoer

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

    Voorbeelduitvoer

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Wanneer de PostgreSQL-functie is verbonden met het primaire eindpunt voor lezen/schrijven, retourneert `f` *de functie Onwaar*, waarmee wordt aangegeven dat de huidige verbinding beschrijfbaar is.

    Wanneer u verbinding maakt met een replica, retourneert `t` *de functie waar*, waarmee wordt aangegeven dat de database zich in herstel bevindt en alleen-lezen is.

## Een niet-geplande failover simuleren

In deze sectie activeert u een plotselinge fout door de pod waarop de primaire pod wordt uitgevoerd, te verwijderen. Dit simuleert een plotselinge crash of verlies van netwerkconnectiviteit met het knooppunt dat als host fungeert voor de PostgreSQL-primaire.

1. Controleer de status van de actieve pod-exemplaren met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Voorbeelduitvoer

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Verwijder de primaire pod met behulp van de [`kubectl delete`][kubectl-delete] opdracht.

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Controleer of het `pg-primary-cnpg-sryti1qf-2` pod-exemplaar nu de primaire is met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Voorbeelduitvoer

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Stel het `pg-primary-cnpg-sryti1qf-1` pod-exemplaar opnieuw in als de primaire instantie met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Controleer of de pod-exemplaren zijn teruggekomen naar de oorspronkelijke status vóór de ongeplande failovertest met behulp van de volgende opdracht:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Voorbeelduitvoer

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Resources opschonen

* Wanneer u klaar bent met het controleren van uw implementatie, verwijdert u alle resources die u in deze handleiding hebt gemaakt met behulp van de [`az group delete`][az-group-delete] opdracht.

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Volgende stappen

In deze handleiding hebt u geleerd hoe u het volgende kunt doen:

* Gebruik Azure CLI om een AKS-cluster met meerdere zones te maken.
* Implementeer een postgreSQL-cluster en -database met hoge beschikbaarheid met behulp van de CNPG-operator.
* Bewaking voor PostgreSQL instellen met Prometheus en Grafana.
* Implementeer een voorbeeldgegevensset in de PostgreSQL-database.
* PostgreSQL- en AKS-clusterupgrades uitvoeren.
* Simuleer een onderbreking van een cluster en een PostgreSQL-replicafailover.
* Voer een back-up en herstel uit van de PostgreSQL-database.

Zie [Wat is Azure Kubernetes Service (AKS)?][what-is-aks]

## Medewerkers

*Dit artikel wordt onderhouden door Microsoft. Het is oorspronkelijk geschreven door de volgende inzenders*:

* Ken Kilty | Principal TPM
* Russell de Tina | Principal TPM
* Adrian Joian | Senior klanttechnicus
* Jenny Hayes | Senior Content Developer
* Carol Smith | Senior Content Developer
* Erin Schaffer | Inhoudsontwikkelaar 2
* Adam Sharif | Klanttechnicus 2

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
