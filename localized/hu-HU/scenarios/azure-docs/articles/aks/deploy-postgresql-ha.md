---
title: Magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezése az AKS-ben az Azure CLI-vel
description: Ebben a cikkben egy magas rendelkezésre állású PostgreSQL-adatbázist helyez üzembe az AKS-en a CloudNativePG operátor használatával.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Magas rendelkezésre állású PostgreSQL-adatbázis üzembe helyezése az AKS-en

Ebben a cikkben egy magas rendelkezésre állású PostgreSQL-adatbázist helyez üzembe az AKS-en.

* Ha még nem hozta létre a szükséges infrastruktúrát ehhez az üzembe helyezéshez, kövesse a Magas rendelkezésre állású PostgreSQL-adatbázis AKS-en[ való üzembe helyezéséhez szükséges infrastruktúra létrehozása című szakasz lépéseit][create-infrastructure], és visszatérhet ehhez a cikkhez.

## Titkos kód létrehozása a bootstrap-alkalmazás felhasználójának

1. Hozzon létre egy titkos kulcsot a PostgreSQL üzembe helyezésének ellenőrzéséhez interaktív bejelentkezéssel egy bootstrap-alkalmazás felhasználója számára a [`kubectl create secret`][kubectl-create-secret] parancs használatával.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Ellenőrizze, hogy a titkos kód sikeresen létrejött-e a [`kubectl get`][kubectl-get] paranccsal.

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Környezeti változók beállítása a PostgreSQL-fürthöz

* ConfigMap üzembe helyezése a PostgreSQL-fürt környezeti változóinak beállításához az alábbi [`kubectl apply`][kubectl-apply] paranccsal:

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

## A Prometheus PodMonitors telepítése

A Prometheus podMonitorokat hoz létre a CNPG-példányokhoz a CNPG GitHub-minták adattárában tárolt alapértelmezett rögzítési szabályok készletével. Éles környezetben ezek a szabályok szükség szerint módosulnak.

1. Adja hozzá a Prometheus Community Helm-adattárat a [`helm repo add`][helm-repo-add] paranccsal.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Frissítse a Prometheus Community Helm-adattárat, és telepítse az elsődleges fürtre a [`helm upgrade`][helm-upgrade] jelölővel ellátott `--install` paranccsal.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Ellenőrizze, hogy létrejött-e a podmonitor.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Összevont hitelesítő adatok létrehozása

Ebben a szakaszban egy összevont identitás-hitelesítő adatokat hoz létre a PostgreSQL biztonsági mentéséhez, amely lehetővé teszi a CNPG számára, hogy AKS számítási feladatok identitásával hitelesítse magát a tárfiók célhelyére a biztonsági mentésekhez. A CNPG-operátor létrehoz egy Kubernetes-szolgáltatásfiókot ugyanazzal a névvel, mint a CNPG-fürt üzembehelyezési jegyzékében használt fürt.

1. Kérje le a fürt OIDC-kiállítójának URL-címét a [`az aks show`][az-aks-show] paranccsal.

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Hozzon létre egy összevont identitás hitelesítő adatokat a [`az identity federated-credential create`][az-identity-federated-credential-create] paranccsal.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Magas rendelkezésre állású PostgreSQL-fürt üzembe helyezése

Ebben a szakaszban egy magas rendelkezésre állású PostgreSQL-fürtöt helyez üzembe a [CNPG-fürt egyéni erőforrásdefiníciója (CRD)][cluster-crd] használatával.

Az alábbi táblázat a fürt CRD-jének YAML-telepítési jegyzékében beállított főbb tulajdonságokat ismerteti:

| Tulajdonság | Definíció |
| --------- | ------------ |
| `inheritedMetadata` | A CNPG-operátorra jellemző. A metaadatokat a fürthöz kapcsolódó összes objektum örökli. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | DNS-címke az írásvédett és írásvédett Postgres-fürtvégpontok közzétételekor. |
| `labels: azure.workload.identity/use: "true"` | Azt jelzi, hogy az AKS-nek be kell fecskendeznie a számítási feladatok identitásfüggőségeit a PostgreSQL-fürtpéldányokat üzemeltető podokba. |
| `topologySpreadConstraints` | Különböző zónák és különböző, címkével `"workload=postgres"`ellátott csomópontok megkövetelése. |
| `resources` | Konfigurálja a Garantált szolgáltatásminőség (QoS) osztályt**. Éles környezetben ezek az értékek kulcsfontosságúak a mögöttes csomópont virtuális gép használatának maximalizálásához, és a használt Azure-beli virtuálisgép-termékváltozattól függően változnak. |
| `bootstrap` | A CNPG-operátorra jellemző. Inicializálás üres alkalmazásadatbázissal. |
| `storage` / `walStorage` | A CNPG-operátorra jellemző. Tárolósablonokat határoz meg a PersistentVolumeClaims (PVCs) számára az adatokhoz és a naplótároláshoz. A nagyobb IOP-k esetében a tablespace-ek számára is megadható a horizontálisan feldarabolási tároló. |
| `replicationSlots` | A CNPG-operátorra jellemző. Lehetővé teszi a replikációs pontok magas rendelkezésre állását. |
| `postgresql` | A CNPG-operátorra jellemző. Leképezi a beállításokat a következőhöz `postgresql.conf`: , `pg_hba.conf`és `pg_ident.conf config`. |
| `serviceAccountTemplate` | Tartalmazza a szolgáltatásfiókok létrehozásához szükséges sablont, és leképezi az AKS összevont identitás hitelesítő adatait a UAMI-ra, hogy engedélyezze az AKS számítási feladat identitásának hitelesítését a PostgreSQL-példányokat futtató podokról külső Azure-erőforrásokra. |
| `barmanObjectStore` | A CNPG-operátorra jellemző. Konfigurálja a barman-cloud eszközcsomagot az AKS számítási feladatok identitásának használatával az Azure Blob Storage objektumtárolóba való hitelesítéshez. |

1. Helyezze üzembe a PostgreSQL-fürtöt a fürt CRD-vel a [`kubectl apply`][kubectl-apply] paranccsal.

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

1. Ellenőrizze, hogy az elsődleges PostgreSQL-fürt sikeresen létrejött-e a [`kubectl get`][kubectl-get] paranccsal. A CNPG-fürt CRD-je három példányt adott meg, amelyek a futtatott podok megtekintésével ellenőrizhetők, miután minden példányt előhoztak és csatlakoztattak a replikációhoz. Legyen türelmes, mert mindhárom példány online állapotba kerül, és csatlakozhat a fürthöz.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Példakimenet

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Ellenőrizze, hogy a Prometheus PodMonitor fut-e

A CNPG-operátor automatikusan létrehoz egy PodMonitort az elsődleges példányhoz a Prometheus Community telepítése[ során ](#install-the-prometheus-podmonitors)létrehozott rögzítési szabályok használatával.

1. Ellenőrizze, hogy a PodMonitor fut-e a [`kubectl get`][kubectl-get] paranccsal.

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Példakimenet

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Ha az Azure Monitor for Managed Prometheus szolgáltatást használja, egy másik podmonitort kell hozzáadnia az egyéni csoportnév használatával. A felügyelt Prometheus nem veszi fel az egyéni erőforrás-definíciókat (CRD-ket) a Prometheus-közösségből. A csoportnéven kívül a CRD-k megegyeznek. Ez lehetővé teszi, hogy a felügyelt Prometheus podmonitorai egymás mellett létezhessenek a közösségi podmonitort használók között. Ha nem felügyelt Prometheust használ, ezt kihagyhatja. Hozzon létre egy új podmonitort:

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

Ellenőrizze, hogy létrejött-e a podmonitor (figyelje meg a csoportnév különbségét).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### A lehetőség – Azure Monitor-munkaterület

Miután üzembe helyezte a Postgres-fürtöt és a podmonitort, megtekintheti a metrikákat az Azure Portal használatával egy Azure Monitor-munkaterületen.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Képernyőkép egy Azure Monitor-munkaterület metrikáiról." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### B lehetőség – Felügyelt Grafana

Másik lehetőségként a Postgres-fürt és a podmonitor üzembe helyezése után létrehozhat egy metrikák irányítópultot az üzembe helyezési szkript által létrehozott felügyelt Grafana-példányon az Azure Monitor-munkaterületre exportált metrikák megjelenítéséhez. A felügyelt Grafana az Azure Portalon érhető el. Keresse meg az üzembe helyezési szkript által létrehozott felügyelt Grafana-példányt, és kattintson a Végpont hivatkozásra az itt látható módon:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Képernyőkép egy Azure Managed Grafana-példányról." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

A Végpont hivatkozásra kattintva megnyílik egy új böngészőablak, ahol irányítópultokat hozhat létre a Felügyelt Grafana-példányon. Az Azure Monitor-adatforrás[ konfigurálására ](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in)vonatkozó utasításokat követve vizualizációkat adhat hozzá a Postgres-fürtből származó metrikák irányítópultjának létrehozásához. Az adatforrás-kapcsolat beállítása után a főmenüben kattintson az Adatforrások lehetőségre, és az adatforrás-kapcsolat adatforrás-beállításainak halmazát kell látnia az itt látható módon:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Képernyőkép az adatforrás beállításairól." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

A Managed Prometheus (Felügyelt Prometheus) beállításban kattintson az irányítópult létrehozásához az irányítópult-szerkesztő megnyitásához. Miután megnyílik a szerkesztőablak, kattintson a Vizualizáció hozzáadása lehetőségre, majd a Felügyelt Prometheus lehetőségre a Postgres-fürt metrikáinak tallózásához. Miután kiválasztotta a vizualizálni kívánt metrikát, kattintson a Lekérdezések futtatása gombra a vizualizáció adatainak lekéréséhez az itt látható módon:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Képernyőkép a szerkezet irányítópultjáról." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

A Mentés gombra kattintva hozzáadhatja a panelt az irányítópulthoz. További panelek hozzáadásához kattintson a Hozzáadás gombra az irányítópult-szerkesztőben, és ismételje meg ezt a folyamatot más metrikák megjelenítéséhez. A metrikák vizualizációinak hozzáadásakor a következőképpen kell kinéznie:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Képernyőkép a mentési irányítópultról." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Az irányítópult mentéséhez kattintson a Mentés ikonra.

## Az üzembe helyezett PostgreSQL-fürt vizsgálata

Ellenőrizze, hogy a PostgreSQL több rendelkezésre állási zónában van-e elosztva az AKS-csomópont részleteinek lekérésével a [`kubectl get`][kubectl-get] parancs használatával.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

A kimenetnek az alábbi példakimenethez kell hasonlítania az egyes csomópontok rendelkezésre állási zónájával:

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

## Csatlakozás a PostgreSQL-hez és mintaadatkészlet létrehozása

Ebben a szakaszban létrehoz egy táblát, és beszúr néhány adatot a korábban üzembe helyezett CNPG-fürt CRD-jében létrehozott alkalmazás-adatbázisba. Ezekkel az adatokkal ellenőrizheti a PostgreSQL-fürt biztonsági mentési és visszaállítási műveleteit.

* Hozzon létre egy táblát, és szúrjon be adatokat az alkalmazásadatbázisba az alábbi parancsokkal:

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

    A kimenetnek a következő példakimenethez kell hasonlítania:

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
## Csatlakozás írásvédett PostgreSQL-replikákhoz

* Csatlakozzon a PostgreSQL írásvédett replikáihoz, és ellenőrizze a mintaadatkészletet a következő parancsokkal:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Példakimenet

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

    Példakimenet

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Igény szerinti és ütemezett PostgreSQL-biztonsági mentések beállítása a Barman használatával

1. Ellenőrizze, hogy a PostgreSQL-fürt hozzáfér-e a CNPG-fürt CRD-jében megadott Azure-tárfiókhoz, és hogy a `Working WAL archiving` jelentés `OK` a következő parancsot használja:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Példakimenet

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Helyezzen üzembe egy igény szerinti biztonsági mentést az Azure Storage-ban, amely az AKS számítási feladatok identitásának integrációját használja a parancsot tartalmazó YAML-fájl használatával [`kubectl apply`][kubectl-apply] .

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

1. Ellenőrizze az igény szerinti biztonsági mentés állapotát a [`kubectl describe`][kubectl-describe] paranccsal.

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Példakimenet

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Ellenőrizze, hogy a fürt rendelkezik-e az első helyrehozhatósági ponttal az alábbi paranccsal:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Példakimenet

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Konfiguráljon egy ütemezett biztonsági mentést *óránként 15 perccel az óra* elteltével a YAML-fájl használatával a [`kubectl apply`][kubectl-apply] paranccsal.

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

1. Ellenőrizze az ütemezett biztonsági mentés állapotát a [`kubectl describe`][kubectl-describe] paranccsal.

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Tekintse meg az elsődleges fürt azure blobtárolóján tárolt biztonsági mentési fájlokat a [`az storage blob list`][az-storage-blob-list] paranccsal.

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    A kimenetnek a következő példakimenethez kell hasonlítania, és sikeres volt a biztonsági mentés ellenőrzése:

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

## Az igény szerinti biztonsági mentés visszaállítása új PostgreSQL-fürtre

Ebben a szakaszban visszaállítja a korábban létrehozott igény szerinti biztonsági mentést a CNPG-operátorral egy új példányba a bootstrap-fürt CRD használatával. A rendszer egyetlen példányfürtöt használ az egyszerűség kedvéért. Ne feledje, hogy az AKS számítási feladat identitása (a CNPG inheritFromAzureAD-n keresztül) hozzáfér a biztonsági mentési fájlokhoz, és a helyreállítási fürt neve a helyreállítási fürtre vonatkozó új Kubernetes-szolgáltatásfiók létrehozásához használatos.

Egy második összevont hitelesítő adatot is létrehoz, amely megfelelteti az új helyreállítási fürtszolgáltatás-fiókot a meglévő UAMI-hoz, amely "Storage Blob Data Contributor" hozzáféréssel rendelkezik a Blob Storage biztonsági mentési fájljaihoz.

1. Hozzon létre egy második összevont identitás-hitelesítő adatot a [`az identity federated-credential create`][az-identity-federated-credential-create] paranccsal.

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

1. Állítsa vissza az igény szerinti biztonsági mentést a fürt CRD-jével a [`kubectl apply`][kubectl-apply] paranccsal.

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

1. Csatlakozzon a helyreállított példányhoz, majd ellenőrizze, hogy a teljes biztonsági mentést tartalmazó eredeti fürtön létrehozott adathalmaz a következő paranccsal van-e jelen:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Példakimenet

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Törölje a helyreállított fürtöt a következő paranccsal:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Törölje az összevont identitás hitelesítő adatait a [`az identity federated-credential delete`][az-identity-federated-credential-delete] paranccsal.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## A PostgreSQL-fürt közzététele nyilvános terheléselosztóval

Ebben a szakaszban konfigurálja a szükséges infrastruktúrát, hogy nyilvánosan elérhetővé tegye a PostgreSQL írásvédett és írásvédett végpontjait IP-forráskorlátozásokkal az ügyfél-munkaállomás nyilvános IP-címén.

A fürt IP-szolgáltatásából a következő végpontokat is lekéri:

* *Egy* elsődleges olvasási-írási végpont, amely a következővel `*-rw`végződik: .
* *Nulla–N* (a replikák számától függően) írásvédett végpontok, amelyek a következővel `*-ro`végződnek: .
* *Egy* replikációs végpont, amely ezzel `*-r`végződik: .

1. Kérje le a fürt IP-szolgáltatásának adatait a [`kubectl get`][kubectl-get] parancs használatával.

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Példakimenet

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Három szolgáltatás létezik: `namespace/cluster-name-ro` az 5433-as portra van leképezve, `namespace/cluster-name-rw`és `namespace/cluster-name-r` az 5433-ra van leképezve. Fontos, hogy ne használja ugyanazt a portot, mint a PostgreSQL-adatbázisfürt olvasási/írási csomópontja. Ha azt szeretné, hogy az alkalmazások csak a PostgreSQL-adatbázisfürt írásvédett replikáját érjék el, irányítsa őket az 5433-at. A végső szolgáltatást általában adatmentésekhez használják, de írásvédett csomópontként is használhatók.

1. Kérje le a szolgáltatás részleteit a [`kubectl get`][kubectl-get] parancs használatával.

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

1. Konfigurálja a terheléselosztó szolgáltatást a következő YAML-fájlokkal a [`kubectl apply`][kubectl-apply] parancs használatával.

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

1. Kérje le a szolgáltatás részleteit a [`kubectl describe`][kubectl-describe] parancs használatával.

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

### Nyilvános PostgreSQL-végpontok ellenőrzése

Ebben a szakaszban ellenőrzi, hogy az Azure Load Balancer megfelelően van-e beállítva a korábban létrehozott statikus IP-cím és az elsődleges írásvédett és írásvédett replikák útválasztási kapcsolatainak használatával, és a psql CLI használatával mindkettőhöz csatlakozik.

Ne feledje, hogy az elsődleges olvasási-írási végpont az 5432-s TCP-portra, az írásvédett replikavégpontok pedig az 5433-as portra lesznek leképezve, hogy ugyanazt a PostgreSQL DNS-nevet lehessen használni az olvasók és írók számára.

> [!NOTE]
> Szüksége van a PostgreSQL-hez korábban létrehozott és a környezeti változóban tárolt egyszerű postgreSQL-jelszó alkalmazásfelhasználói jelszavának `$PG_DATABASE_APPUSER_SECRET` értékére.

* Ellenőrizze a nyilvános PostgreSQL-végpontokat az alábbi `psql` parancsokkal:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Példakimenet

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

    Példakimenet

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Ha sikeresen csatlakozik az elsődleges írási-olvasási végponthoz, a PostgreSQL függvény hamis* értéket *ad vissza`f`, ami azt jelzi, hogy az aktuális kapcsolat írható.

    Replikához csatlakoztatva a függvény igaz* értéket ad `t` *vissza, jelezve, hogy az adatbázis csak helyreállítási és írásvédett állapotban van.

## Nem tervezett feladatátvétel szimulálása

Ebben a szakaszban hirtelen hibát aktivál az elsődlegest futtató pod törlésével, amely a PostgreSQL elsődleges csomóponthoz való hirtelen összeomlást vagy hálózati kapcsolat megszakadását szimulálja.

1. Ellenőrizze a futó podpéldányok állapotát az alábbi paranccsal:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Példakimenet

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Törölje az elsődleges podot a [`kubectl delete`][kubectl-delete] paranccsal.

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Ellenőrizze, hogy a `pg-primary-cnpg-sryti1qf-2` podpéldány most már az elsődleges-e az alábbi paranccsal:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Példakimenet

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Állítsa alaphelyzetbe a `pg-primary-cnpg-sryti1qf-1` podpéldányt elsődlegesként az alábbi paranccsal:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Ellenőrizze, hogy a podpéldányok visszatértek-e az eredeti állapotukba a nem tervezett feladatátvételi teszt előtt a következő paranccsal:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Példakimenet

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Az erőforrások eltávolítása

* Ha végzett az üzembe helyezés áttekintésével, törölje az ebben az útmutatóban létrehozott összes erőforrást a [`az group delete`][az-group-delete] paranccsal.

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Következő lépések

Ebben az útmutatóban megtanulta, hogyan:

* Többzónás AKS-fürt létrehozása az Azure CLI használatával.
* Helyezzen üzembe egy magas rendelkezésre állású PostgreSQL-fürtöt és -adatbázist a CNPG operátorral.
* A PostgreSQL monitorozásának beállítása a Prometheus és a Grafana használatával.
* Helyezzen üzembe egy mintaadatkészletet a PostgreSQL-adatbázisban.
* PostgreSQL- és AKS-fürtfrissítések végrehajtása.
* Fürtkimaradás és PostgreSQL-replika feladatátvételének szimulálása.
* Végezze el a PostgreSQL-adatbázis biztonsági mentését és visszaállítását.

További információ az AKS számítási feladatokhoz való használatáról: [Mi az Az Azure Kubernetes Service (AKS)?][what-is-aks]

## Közreműködők

*Ezt a cikket a Microsoft tartja karban. Eredetileg a következő közreműködők* írták:

* Ken Kilty | Egyszerű TPM
* Russell de | Egyszerű TPM
* Adrian Joian | Vezető ügyfélmérnök
* Jenny Hayes | Vezető tartalomfejlesztő
* Carol Smith | Vezető tartalomfejlesztő
* Erin Schaffer | Tartalomfejlesztő 2
* Adam Sharif | 2. ügyfélmérnök

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
