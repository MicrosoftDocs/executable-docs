---
title: Nasazení vysoce dostupné databáze PostgreSQL v AKS pomocí Azure CLI
description: V tomto článku nasadíte vysoce dostupnou databázi PostgreSQL do AKS pomocí operátoru CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Nasazení vysoce dostupné databáze PostgreSQL v AKS

V tomto článku nasadíte vysoce dostupnou databázi PostgreSQL v AKS.

* Pokud jste ještě nevytvořili požadovanou infrastrukturu pro toto nasazení, postupujte podle kroků v [tématu Vytvoření infrastruktury pro nasazení vysoce dostupné databáze PostgreSQL v AKS][create-infrastructure] , abyste mohli nastavit a pak se můžete vrátit k tomuto článku.

## Vytvoření tajného kódu pro uživatele aplikace bootstrap

1. Vygenerujte tajný kód pro ověření nasazení PostgreSQL interaktivním přihlášením uživatele aplikace bootstrap pomocí [`kubectl create secret`][kubectl-create-secret] příkazu.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Pomocí příkazu ověřte, že se tajný kód úspěšně vytvořil [`kubectl get`][kubectl-get] .

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Nastavení proměnných prostředí pro cluster PostgreSQL

* Pomocí následujícího [`kubectl apply`][kubectl-apply] příkazu nasaďte objekt ConfigMap pro nastavení proměnných prostředí pro cluster PostgreSQL:

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

## Instalace monitorů PodMonitors prometheus

Prometheus vytvoří PodMonitory pro instance CNPG pomocí sady výchozích pravidel nahrávání uložených v úložišti ukázek GitHubu CNPG. V produkčním prostředí by se tato pravidla podle potřeby upravila.

1. Přidejte úložiště Prometheus Community Helm pomocí [`helm repo add`][helm-repo-add] příkazu.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Upgradujte úložiště Prometheus Community Helm a nainstalujte ho do primárního clusteru pomocí [`helm upgrade`][helm-upgrade] příkazu s příznakem `--install` .

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Ověřte, že je vytvořený monitor podu.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Vytvoření federovaných přihlašovacích údajů

V této části vytvoříte přihlašovací údaje federované identity pro zálohování PostgreSQL, které cnPG povolí použití identity úloh AKS k ověření v cíli účtu úložiště pro zálohy. Operátor CNPG vytvoří účet služby Kubernetes se stejným názvem jako cluster použitý v manifestu nasazení clusteru CNPG.

1. Pomocí příkazu získejte adresu URL vystavitele OIDC clusteru [`az aks show`][az-aks-show] .

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Pomocí příkazu vytvořte přihlašovací údaje [`az identity federated-credential create`][az-identity-federated-credential-create] federované identity.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Nasazení clusteru PostgreSQL s vysokou dostupností

V této části nasadíte vysoce dostupný cluster PostgreSQL pomocí [vlastní definice prostředků clusteru CNPG (CRD).][cluster-crd]

Následující tabulka popisuje klíčové vlastnosti nastavené v manifestu nasazení YAML pro CRD clusteru:

| Vlastnost | definice |
| --------- | ------------ |
| `inheritedMetadata` | Specifické pro operátor CNPG. Metadata dědí všechny objekty související s clusterem. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Popisek DNS pro použití při zveřejnění koncových bodů clusteru Postgres jen pro čtení a pro čtení. |
| `labels: azure.workload.identity/use: "true"` | Označuje, že služba AKS by měla do podů hostující instance clusteru PostgreSQL vkládat závislosti identit úloh. |
| `topologySpreadConstraints` | Vyžadovat různé zóny a různé uzly s popiskem `"workload=postgres"`. |
| `resources` | Nakonfiguruje třídu QoS (Quality of Service) zaručené**. V produkčním prostředí jsou tyto hodnoty klíčem k maximalizaci využití základního virtuálního počítače uzlu a liší se podle použité skladové položky virtuálního počítače Azure. |
| `bootstrap` | Specifické pro operátor CNPG. Inicializuje prázdnou databázi aplikace. |
| `storage` / `walStorage` | Specifické pro operátor CNPG. Definuje šablony úložiště pro PersistentVolumeClaims (PVCs) pro úložiště dat a protokolů. Je také možné zadat úložiště pro tabulkové prostory, které se mají horizontálně navýšit pro vstupně-výstupní operace za sekundu. |
| `replicationSlots` | Specifické pro operátor CNPG. Umožňuje sloty replikace pro zajištění vysoké dostupnosti. |
| `postgresql` | Specifické pro operátor CNPG. Nastavení mapy pro `postgresql.conf`, `pg_hba.conf`a `pg_ident.conf config`. |
| `serviceAccountTemplate` | Obsahuje šablonu potřebnou k vygenerování účtů služeb a mapuje přihlašovací údaje federované identity AKS na UAMI, aby se z podů hostovaných instancí PostgreSQL povolilo ověřování identit úloh AKS na externí prostředky Azure. |
| `barmanObjectStore` | Specifické pro operátor CNPG. Nakonfiguruje sadu nástrojů barman-cloud pomocí identity úlohy AKS pro ověřování v úložišti objektů Azure Blob Storage. |

1. Pomocí příkazu nasaďte cluster PostgreSQL s CRD clusteru [`kubectl apply`][kubectl-apply] .

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

1. Pomocí příkazu ověřte, že se primární cluster PostgreSQL úspěšně vytvořil [`kubectl get`][kubectl-get] . Cluster CNPG CRD zadal tři instance, které lze ověřit zobrazením spuštěných podů po spuštění každé instance a připojení k replikaci. Buďte trpěliví, protože může nějakou dobu trvat, než se všechny tři instance dostanou do režimu online a připojí se ke clusteru.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Příklad výstupu

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Ověřte, že je spuštěný monitor PodMonitoru Prometheus.

Operátor CNPG automaticky vytvoří PodMonitor pro primární instanci pomocí pravidel záznamu vytvořených během [instalace](#install-the-prometheus-podmonitors) Prometheus Community.

1. Pomocí příkazu ověřte, že podMonitor běží [`kubectl get`][kubectl-get] .

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Příklad výstupu

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Pokud používáte Azure Monitor pro spravovaný prometheus, budete muset přidat další monitorování podů pomocí názvu vlastní skupiny. Spravovaná služba Prometheus nezvedne vlastní definice prostředků (CRD) z komunity Prometheus. Kromě názvu skupiny jsou identifikátory CRD stejné. To umožňuje monitorování podů spravovaných prometheus existovat vedle těch, které používají monitorování podů komunity. Pokud nepoužíváte Managed Prometheus, můžete to přeskočit. Vytvoření nového monitoru podu:

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

Ověřte, že je vytvořený monitor podů (všimněte si rozdílu v názvu skupiny).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Možnost A – Pracovní prostor služby Azure Monitor

Po nasazení clusteru Postgres a monitorování podů můžete metriky zobrazit pomocí webu Azure Portal v pracovním prostoru služby Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Snímek obrazovky znázorňující metriky v pracovním prostoru služby Azure Monitor" lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Možnost B – Spravovaná grafana

Alternativně můžete po nasazení clusteru Postgres a monitorování podů vytvořit řídicí panel metrik na spravované instanci Grafana vytvořené skriptem nasazení a vizualizovat metriky exportované do pracovního prostoru služby Azure Monitor. Ke spravované grafaně se dostanete přes Azure Portal. Přejděte na spravovanou instanci Grafana vytvořenou skriptem nasazení a klikněte na odkaz koncový bod, jak je znázorněno tady:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Snímek obrazovky znázorňující instanci Azure Managed Grafana" lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Kliknutím na odkaz Koncový bod se otevře nové okno prohlížeče, kde můžete vytvářet řídicí panely ve spravované instanci Grafana. Podle pokynů ke [konfiguraci zdroje](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) dat azure Monitoru pak můžete přidat vizualizace pro vytvoření řídicího panelu metrik z clusteru Postgres. Po nastavení připojení ke zdroji dat v hlavní nabídce klikněte na možnost Zdroje dat a měli byste vidět sadu možností zdroje dat pro připojení ke zdroji dat, jak je znázorněno tady:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Snímek obrazovky s možnostmi zdroje dat" lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

V možnosti Managed Prometheus klikněte na možnost pro vytvoření řídicího panelu, aby se otevřel editor řídicího panelu. Jakmile se otevře okno editoru, klikněte na možnost Přidat vizualizaci a potom klikněte na možnost Managed Prometheus a procházejte metriky z clusteru Postgres. Jakmile vyberete metriku, kterou chcete vizualizovat, kliknutím na tlačítko Spustit dotazy načtěte data pro vizualizaci, jak je znázorněno tady:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Snímek obrazovky znázorňující řídicí panel konstruktoru" lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Kliknutím na tlačítko Uložit přidáte panel na řídicí panel. Další panely můžete přidat kliknutím na tlačítko Přidat v editoru řídicích panelů a opakováním tohoto procesu vizualizovat další metriky. Přidáním vizualizací metrik byste měli mít něco, co vypadá takto:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Snímek obrazovky s řídicím panelem pro uložení" lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Kliknutím na ikonu Uložit uložíte řídicí panel.

## Kontrola nasazeného clusteru PostgreSQL

Ověřte, že je PostgreSQL rozložený do více zón dostupnosti, a to načtením podrobností o uzlu AKS pomocí [`kubectl get`][kubectl-get] příkazu.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Výstup by měl vypadat podobně jako v následujícím příkladu výstupu se zónou dostupnosti zobrazenou pro každý uzel:

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

## Připojení k PostgreSQL a vytvoření ukázkové datové sady

V této části vytvoříte tabulku a vložíte některá data do databáze aplikace, která byla vytvořena v clusteru CNPG, který jste nasadili dříve. Tato data použijete k ověření operací zálohování a obnovení clusteru PostgreSQL.

* Vytvořte tabulku a vložte data do databáze aplikace pomocí následujících příkazů:

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

    Výstup by měl vypadat podobně jako v následujícím příkladu výstupu:

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
## Připojení k replikám jen pro čtení PostgreSQL

* Připojte se k replikám jen pro čtení PostgreSQL a pomocí následujících příkazů ověřte ukázkovou datovou sadu:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Příklad výstupu

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

    Příklad výstupu

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Nastavení zálohování PostgreSQL na vyžádání a plánované pomocí Barmanu

1. Ověřte, že cluster PostgreSQL má přístup k účtu úložiště Azure zadanému v CRD clusteru CNPG a že `Working WAL archiving` hlásí následující `OK` příkaz:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Příklad výstupu

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Nasaďte zálohu na vyžádání do služby Azure Storage, která používá integraci identity úloh AKS pomocí souboru YAML s příkazem [`kubectl apply`][kubectl-apply] .

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

1. Pomocí příkazu ověřte stav zálohování [`kubectl describe`][kubectl-describe] na vyžádání.

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Příklad výstupu

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Pomocí následujícího příkazu ověřte, že cluster má první bod obnovení:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Příklad výstupu

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Pomocí souboru YAML pomocí příkazu`kubectl apply`[][kubectl-apply] nakonfigurujte naplánované zálohování za *každou hodinu v 15 minutách za hodinu.*

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

1. Pomocí příkazu ověřte stav plánovaného zálohování [`kubectl describe`][kubectl-describe] .

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Pomocí příkazu zobrazte záložní soubory uložené v úložišti objektů blob v Azure pro primární cluster [`az storage blob list`][az-storage-blob-list] .

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Výstup by měl vypadat podobně jako v následujícím příkladu výstupu a ověření zálohování proběhlo úspěšně:

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

## Obnovení zálohy na vyžádání do nového clusteru PostgreSQL

V této části obnovíte zálohu na vyžádání, kterou jste vytvořili dříve, pomocí operátoru CNPG do nové instance pomocí CRD clusteru bootstrap. Pro zjednodušení se používá jeden cluster instancí. Nezapomeňte, že identita úlohy AKS (prostřednictvím CNPG dědíFromAzureAD) přistupuje k záložním souborům a že se název clusteru pro obnovení používá k vygenerování nového účtu služby Kubernetes specifického pro cluster pro obnovení.

Vytvoříte také druhé federované přihlašovací údaje, které mapují nový účet služby clusteru obnovení na existující UAMI, který má přístup Přispěvatel dat objektů blob úložiště k záložním souborům v úložišti objektů blob.

1. Pomocí příkazu vytvořte druhé přihlašovací údaje [`az identity federated-credential create`][az-identity-federated-credential-create] federované identity.

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

1. Obnovte zálohu na vyžádání pomocí CRD clusteru [`kubectl apply`][kubectl-apply] pomocí příkazu.

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

1. Připojte se k obnovené instanci a pak pomocí následujícího příkazu ověřte, že datová sada vytvořená v původním clusteru, kde byla provedena úplná záloha:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Příklad výstupu

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Pomocí následujícího příkazu odstraňte obnovený cluster:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Pomocí příkazu odstraňte přihlašovací údaje [`az identity federated-credential delete`][az-identity-federated-credential-delete] federované identity.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Zveřejnění clusteru PostgreSQL pomocí veřejného nástroje pro vyrovnávání zatížení

V této části nakonfigurujete potřebnou infrastrukturu tak, aby veřejně zpřístupnil koncové body PostgreSQL pro čtení a zápis a jen pro čtení s omezeními zdroje IP adres na veřejnou IP adresu vaší klientské pracovní stanice.

Ze služby IP clusteru také načtete následující koncové body:

* *Jeden* primární koncový bod pro čtení i zápis, který končí `*-rw`na .
* *Nula až N* (v závislosti na počtu replik) koncových bodů jen pro čtení, které končí `*-ro`.
* *Jeden* koncový bod replikace, který končí na `*-r`.

1. Pomocí příkazu získejte podrobnosti o službě IP clusteru [`kubectl get`][kubectl-get] .

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Příklad výstupu

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Existují tři služby: `namespace/cluster-name-ro` namapované na port 5433 `namespace/cluster-name-rw`a `namespace/cluster-name-r` mapované na port 5433. Je důležité se vyhnout použití stejného portu jako uzel pro čtení a zápis databázového clusteru PostgreSQL. Pokud chcete, aby aplikace přistupovaly pouze k replice databáze PostgreSQL jen pro čtení, nasměrujte je na port 5433. Konečná služba se obvykle používá pro zálohy dat, ale může také fungovat jako uzel jen pro čtení.

1. Pomocí příkazu získejte podrobnosti o službě [`kubectl get`][kubectl-get] .

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

1. Pomocí příkazu nakonfigurujte službu nástroje pro vyrovnávání zatížení s následujícími soubory [`kubectl apply`][kubectl-apply] YAML.

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

1. Pomocí příkazu získejte podrobnosti o službě [`kubectl describe`][kubectl-describe] .

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

### Ověření veřejných koncových bodů PostgreSQL

V této části ověříte, že je Azure Load Balancer správně nastavený pomocí statické IP adresy, kterou jste vytvořili dříve, a směrování připojení k primárním replikám pro čtení i zápis a jen pro čtení, a pomocí rozhraní příkazového řádku psql se připojte k oběma.

Nezapomeňte, že primární koncový bod pro čtení i zápis se mapuje na port TCP 5432 a koncové body repliky jen pro čtení na port 5433, aby se pro čtenáře a zapisovače používal stejný název DNS PostgreSQL.

> [!NOTE]
> Potřebujete hodnotu uživatelského hesla aplikace pro základní ověřování PostgreSQL, která byla vygenerována dříve a uložena v `$PG_DATABASE_APPUSER_SECRET` proměnné prostředí.

* Pomocí následujících `psql` příkazů ověřte veřejné koncové body PostgreSQL:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Příklad výstupu

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

    Příklad výstupu

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Po úspěšném připojení k primárnímu koncovému bodu pro čtení a zápis se funkce PostgreSQL vrátí `f` jako *nepravda*, což znamená, že aktuální připojení je zapisovatelné.

    Když je funkce připojená k replice, vrátí `t` *hodnotu true*, což znamená, že databáze je v obnovení a jen pro čtení.

## Simulace neplánovaného převzetí služeb při selhání

V této části aktivujete náhlé selhání odstraněním podu spuštěného primárního, který simuluje náhlé selhání nebo ztrátu síťového připojení k uzlu, který je hostitelem primárního serveru PostgreSQL.

1. Pomocí následujícího příkazu zkontrolujte stav spuštěných instancí podů:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Příklad výstupu

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Pomocí příkazu odstraňte primární pod [`kubectl delete`][kubectl-delete] .

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Pomocí následujícího příkazu ověřte, že `pg-primary-cnpg-sryti1qf-2` je instance podu primární:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Příklad výstupu

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Pomocí následujícího příkazu obnovte instanci podu `pg-primary-cnpg-sryti1qf-1` jako primární:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Pomocí následujícího příkazu ověřte, že se instance podů vrátily do původního stavu před neplánovaným testem převzetí služeb při selhání:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Příklad výstupu

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Vyčištění prostředků

* Jakmile dokončíte kontrolu nasazení, pomocí příkazu odstraňte všechny prostředky, které jste vytvořili v této příručce [`az group delete`][az-group-delete] .

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Další kroky

V tomto průvodci postupy jste se naučili:

* Pomocí Azure CLI vytvořte cluster AKS s více zónami.
* Nasaďte vysoce dostupný cluster a databázi PostgreSQL pomocí operátoru CNPG.
* Nastavení monitorování pro PostgreSQL pomocí Prometheus a Grafany
* Nasaďte ukázkovou datovou sadu do databáze PostgreSQL.
* Proveďte upgrady clusteru PostgreSQL a AKS.
* Simulace přerušení clusteru a převzetí služeb při selhání repliky PostgreSQL
* Proveďte zálohování a obnovení databáze PostgreSQL.

Další informace o využití AKS pro vaše úlohy najdete v tématu [Co je Azure Kubernetes Service (AKS)?][what-is-aks]

## Přispěvatelé

*Tento článek spravuje Microsoft. Původně byla napsána následujícími přispěvateli*:

* Ken Kilty | Hlavní čip TPM
* Russell de Pina | Hlavní čip TPM
* Adrian Joian | Vedoucí zákaznický inženýr
* Jenny Hayes | Vedoucí vývojář obsahu
* Carol Smith | Vedoucí vývojář obsahu
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
