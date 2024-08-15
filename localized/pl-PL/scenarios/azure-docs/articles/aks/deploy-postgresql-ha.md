---
title: Wdrażanie bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu interfejsu wiersza polecenia platformy Azure
description: W tym artykule wdrożysz bazę danych PostgreSQL o wysokiej dostępności w usłudze AKS przy użyciu operatora CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Wdrażanie bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS

W tym artykule wdrożysz bazę danych PostgreSQL o wysokiej dostępności w usłudze AKS.

* Jeśli nie utworzono jeszcze wymaganej infrastruktury dla tego wdrożenia, wykonaj kroki opisane w [temacie Tworzenie infrastruktury wdrażania bazy danych PostgreSQL o wysokiej dostępności w usłudze AKS][create-infrastructure] , aby się skonfigurować, a następnie możesz wrócić do tego artykułu.

## Tworzenie wpisu tajnego dla użytkownika aplikacji bootstrap

1. Wygeneruj wpis tajny w celu zweryfikowania wdrożenia bazy danych PostgreSQL przez logowanie interakcyjne dla użytkownika aplikacji bootstrap przy użyciu [`kubectl create secret`][kubectl-create-secret] polecenia .

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Sprawdź, czy wpis tajny został pomyślnie utworzony przy użyciu [`kubectl get`][kubectl-get] polecenia .

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Ustawianie zmiennych środowiskowych dla klastra PostgreSQL

* Wdróż ConfigMap, aby ustawić zmienne środowiskowe dla klastra PostgreSQL przy użyciu następującego [`kubectl apply`][kubectl-apply] polecenia:

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

## Instalowanie monitorów zasobników Prometheus

Prometheus tworzy podMonitors dla wystąpień CNPG przy użyciu zestawu domyślnych reguł rejestrowania przechowywanych w repozytorium przykładów CNPG GitHub. W środowisku produkcyjnym te reguły zostaną zmodyfikowane zgodnie z potrzebami.

1. Dodaj repozytorium Programu Helm społeczności Prometheus przy użyciu [`helm repo add`][helm-repo-add] polecenia .

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Uaktualnij repozytorium Programu Helm Społeczności Prometheus i zainstaluj je w klastrze podstawowym przy użyciu [`helm upgrade`][helm-upgrade] polecenia z flagą .`--install`

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Sprawdź, czy monitor zasobnika został utworzony.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Tworzenie poświadczeń federacyjnych

W tej sekcji utworzysz poświadczenie tożsamości federacyjnej dla kopii zapasowej postgreSQL, aby umożliwić cnPG używanie tożsamości obciążenia usługi AKS do uwierzytelniania w miejscu docelowym konta magazynu na potrzeby kopii zapasowych. Operator CNPG tworzy konto usługi Kubernetes o takiej samej nazwie jak klaster o nazwie używanej w manifeście wdrożenia klastra CNPG.

1. Pobierz adres URL wystawcy OIDC klastra przy użyciu [`az aks show`][az-aks-show] polecenia .

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Utwórz poświadczenia tożsamości federacyjnej przy użyciu [`az identity federated-credential create`][az-identity-federated-credential-create] polecenia .

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Wdrażanie klastra PostgreSQL o wysokiej dostępności

W tej sekcji wdrożysz klaster PostgreSQL o wysokiej dostępności przy użyciu niestandardowej [definicji zasobów klastra CPG (CRD).][cluster-crd]

W poniższej tabeli przedstawiono właściwości klucza ustawione w manifeście wdrożenia YAML dla klastra CRD:

| Właściwości | Definicja |
| --------- | ------------ |
| `inheritedMetadata` | Specyficzny dla operatora CNPG. Metadane są dziedziczone przez wszystkie obiekty powiązane z klastrem. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Etykieta DNS do użycia podczas uwidaczniania punktów końcowych klastra Postgres tylko do odczytu i zapisu. |
| `labels: azure.workload.identity/use: "true"` | Wskazuje, że usługa AKS powinna wprowadzać zależności tożsamości obciążenia do zasobników hostujących wystąpienia klastra PostgreSQL. |
| `topologySpreadConstraints` | Wymagaj różnych stref i różnych węzłów z etykietą `"workload=postgres"`. |
| `resources` | Konfiguruje klasę Jakości usług (QoS) gwarantowanej**. W środowisku produkcyjnym te wartości są kluczem do maksymalizacji użycia podstawowej maszyny wirtualnej węzła i różnią się w zależności od używanej jednostki SKU maszyny wirtualnej platformy Azure. |
| `bootstrap` | Specyficzny dla operatora CNPG. Inicjuje pustą bazę danych aplikacji. |
| `storage` / `walStorage` | Specyficzny dla operatora CNPG. Definiuje szablony magazynu dla funkcji PersistentVolumeClaims (PVCs) dla magazynu danych i dzienników. Istnieje również możliwość określenia magazynu dla przestrzeni tabel w celu dzielenia na fragmenty dla zwiększonych operacji we/wy na sekundę. |
| `replicationSlots` | Specyficzny dla operatora CNPG. Włącza miejsca replikacji w celu zapewnienia wysokiej dostępności. |
| `postgresql` | Specyficzny dla operatora CNPG. Ustawienia map dla `postgresql.conf`, `pg_hba.conf`i `pg_ident.conf config`. |
| `serviceAccountTemplate` | Zawiera szablon wymagany do wygenerowania kont usług i mapowania poświadczeń tożsamości federacyjnej usługi AKS do interfejsu użytkownika w celu włączenia uwierzytelniania tożsamości obciążenia usługi AKS z zasobników hostających wystąpienia bazy danych PostgreSQL do zewnętrznych zasobów platformy Azure. |
| `barmanObjectStore` | Specyficzny dla operatora CNPG. Konfiguruje pakiet narzędzi barman-cloud przy użyciu tożsamości obciążenia usługi AKS na potrzeby uwierzytelniania w magazynie obiektów usługi Azure Blob Storage. |

1. Wdróż klaster PostgreSQL przy użyciu klastra CRD przy użyciu [`kubectl apply`][kubectl-apply] polecenia .

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

1. Sprawdź, czy podstawowy klaster PostgreSQL został pomyślnie utworzony przy użyciu [`kubectl get`][kubectl-get] polecenia . Klaster CNPG CRD określił trzy wystąpienia, które można zweryfikować, wyświetlając uruchomione zasobniki po uruchomieniu każdego wystąpienia i przyłączone do replikacji. Bądź cierpliwy, ponieważ może upłynąć trochę czasu, aż wszystkie trzy wystąpienia zostaną dołączone do klastra w trybie online.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Przykładowe dane wyjściowe

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Sprawdź, czy uruchomiono narzędzie Prometheus PodMonitor

Operator CNPG automatycznie tworzy podMonitor dla wystąpienia podstawowego przy użyciu reguł rejestrowania utworzonych podczas [instalacji](#install-the-prometheus-podmonitors) programu Prometheus Community.

1. Sprawdź, czy narzędzie PodMonitor jest uruchomione [`kubectl get`][kubectl-get] przy użyciu polecenia .

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Przykładowe dane wyjściowe

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Jeśli używasz usługi Azure Monitor dla zarządzanego rozwiązania Prometheus, musisz dodać kolejny monitor zasobnika przy użyciu nazwy grupy niestandardowej. Zarządzany prometheus nie pobiera niestandardowych definicji zasobów (CRD) ze społeczności Prometheus. Oprócz nazwy grupy identyfikatory CRD są takie same. Dzięki temu monitory zasobników zarządzanego rozwiązania Prometheus mogą istnieć obok siebie, które korzystają z monitora zasobnika społeczności. Jeśli nie używasz zarządzanego rozwiązania Prometheus, możesz pominąć tę opcję. Utwórz nowy monitor zasobnika:

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

Sprawdź, czy monitor zasobnika został utworzony (zwróć uwagę na różnicę w nazwie grupy).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Opcja A — obszar roboczy usługi Azure Monitor

Po wdrożeniu klastra Postgres i monitora zasobnika można wyświetlić metryki przy użyciu witryny Azure Portal w obszarze roboczym usługi Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Zrzut ekranu przedstawiający metryki w obszarze roboczym usługi Azure Monitor." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Opcja B — zarządzana Grafana

Alternatywnie po wdrożeniu monitorów klastra Postgres i zasobnika można utworzyć pulpit nawigacyjny metryk na zarządzanym wystąpieniu narzędzia Grafana utworzonym przez skrypt wdrożenia, aby zwizualizować metryki wyeksportowane do obszaru roboczego usługi Azure Monitor. Dostęp do aplikacji Managed Grafana można uzyskać za pośrednictwem witryny Azure Portal. Przejdź do wystąpienia zarządzanego narzędzia Grafana utworzonego przez skrypt wdrożenia i kliknij link Punkt końcowy, jak pokazano poniżej:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Zrzut ekranu przedstawiający wystąpienie usługi Azure Managed Grafana." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Kliknięcie linku Punkt końcowy spowoduje otwarcie nowego okna przeglądarki, w którym można tworzyć pulpity nawigacyjne w wystąpieniu zarządzanego narzędzia Grafana. Postępując zgodnie z instrukcjami [konfigurowania źródła](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) danych usługi Azure Monitor, możesz dodać wizualizacje, aby utworzyć pulpit nawigacyjny metryk z klastra Postgres. Po skonfigurowaniu połączenia ze źródłem danych w menu głównym kliknij opcję Źródła danych i powinien zostać wyświetlony zestaw opcji źródła danych dla połączenia ze źródłem danych, jak pokazano poniżej:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Zrzut ekranu przedstawiający opcje źródła danych." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

W opcji Zarządzany prometheus kliknij opcję skompilowania pulpitu nawigacyjnego, aby otworzyć edytor pulpitu nawigacyjnego. Po otworzie okna edytora kliknij opcję Dodaj wizualizację, a następnie kliknij opcję Zarządzany prometheus, aby przejrzeć metryki z klastra Postgres. Po wybraniu metryki, którą chcesz wizualizować, kliknij przycisk Uruchom zapytania, aby pobrać dane wizualizacji, jak pokazano poniżej:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Zrzut ekranu przedstawiający tworzenie pulpitu nawigacyjnego." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Kliknij przycisk Zapisz, aby dodać panel do pulpitu nawigacyjnego. Możesz dodać inne panele, klikając przycisk Dodaj w edytorze pulpitu nawigacyjnego i powtarzając ten proces, aby zwizualizować inne metryki. Dodanie wizualizacji metryk powinno wyglądać następująco:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Zrzut ekranu przedstawiający zapisywanie pulpitu nawigacyjnego." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Kliknij ikonę Zapisz, aby zapisać pulpit nawigacyjny.

## Sprawdzanie wdrożonego klastra PostgreSQL

Sprawdź, czy usługa PostgreSQL jest rozłożona na wiele stref dostępności, pobierając szczegóły węzła usługi AKS przy użyciu [`kubectl get`][kubectl-get] polecenia .

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Dane wyjściowe powinny przypominać następujące przykładowe dane wyjściowe ze strefą dostępności wyświetlaną dla każdego węzła:

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

## Nawiązywanie połączenia z bazą danych PostgreSQL i tworzenie przykładowego zestawu danych

W tej sekcji utworzysz tabelę i wstawisz dane do bazy danych aplikacji, która została utworzona w wdrożonym wcześniej pliku CRD klastra CPG. Te dane służą do weryfikowania operacji tworzenia kopii zapasowych i przywracania dla klastra PostgreSQL.

* Utwórz tabelę i wstaw dane do bazy danych aplikacji przy użyciu następujących poleceń:

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

    Dane wyjściowe powinny przypominać następujące przykładowe dane wyjściowe:

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
## Nawiązywanie połączenia z replikami tylko do odczytu bazy danych PostgreSQL

* Połącz się z replikami tylko do odczytu bazy danych PostgreSQL i zweryfikuj przykładowy zestaw danych przy użyciu następujących poleceń:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Przykładowe dane wyjściowe

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

    Przykładowe dane wyjściowe

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Konfigurowanie kopii zapasowych na żądanie i zaplanowanych kopii zapasowych PostgreSQL przy użyciu narzędzia Barman

1. Sprawdź, czy klaster PostgreSQL może uzyskać dostęp do konta usługi Azure Storage określonego w CRLD klastra CNPG i że `Working WAL archiving` raportuje jako `OK` przy użyciu następującego polecenia:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Przykładowe dane wyjściowe

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Wdróż kopię zapasową na żądanie w usłudze Azure Storage, która używa integracji tożsamości obciążenia usługi AKS przy użyciu pliku YAML z poleceniem [`kubectl apply`][kubectl-apply] .

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

1. Zweryfikuj stan kopii zapasowej na żądanie przy użyciu [`kubectl describe`][kubectl-describe] polecenia .

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Przykładowe dane wyjściowe

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Sprawdź, czy klaster ma pierwszy punkt możliwości odzyskiwania, używając następującego polecenia:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Przykładowe dane wyjściowe

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Skonfiguruj zaplanowaną kopię zapasową co godzinę o *15 minut po godzinie* przy użyciu pliku YAML za [`kubectl apply`][kubectl-apply] pomocą polecenia .

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

1. Zweryfikuj stan zaplanowanej kopii zapasowej przy użyciu [`kubectl describe`][kubectl-describe] polecenia .

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Wyświetl pliki kopii zapasowej przechowywane w magazynie obiektów blob platformy Azure dla klastra podstawowego [`az storage blob list`][az-storage-blob-list] przy użyciu polecenia .

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Dane wyjściowe powinny przypominać następujące przykładowe dane wyjściowe, sprawdzanie poprawności kopii zapasowej zakończyło się pomyślnie:

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

## Przywracanie kopii zapasowej na żądanie do nowego klastra PostgreSQL

W tej sekcji przywrócisz utworzoną wcześniej kopię zapasową na żądanie przy użyciu operatora CNPG w nowym wystąpieniu przy użyciu klastra rozruchowego CRD. Jeden klaster wystąpień jest używany dla uproszczenia. Należy pamiętać, że tożsamość obciążenia usługi AKS (za pośrednictwem cnPG inheritFromAzureAD) uzyskuje dostęp do plików kopii zapasowych i że nazwa klastra odzyskiwania jest używana do generowania nowego konta usługi Kubernetes specyficznego dla klastra odzyskiwania.

Utworzysz również drugie poświadczenie federacyjne, aby zamapować nowe konto usługi klastra odzyskiwania na istniejące UAMI z dostępem "Współautor danych obiektu blob usługi Storage" do plików kopii zapasowych w magazynie obiektów blob.

1. Utwórz drugie poświadczenie tożsamości federacyjnej przy użyciu [`az identity federated-credential create`][az-identity-federated-credential-create] polecenia .

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

1. Przywróć kopię zapasową na żądanie przy użyciu klastra CRD za [`kubectl apply`][kubectl-apply] pomocą polecenia .

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

1. Połącz się z odzyskanym wystąpieniem, a następnie sprawdź, czy zestaw danych utworzony w oryginalnym klastrze, w którym wykonano pełną kopię zapasową, jest obecny przy użyciu następującego polecenia:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Przykładowe dane wyjściowe

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Usuń odzyskany klaster przy użyciu następującego polecenia:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Usuń poświadczenia tożsamości federacyjnej przy użyciu [`az identity federated-credential delete`][az-identity-federated-credential-delete] polecenia .

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Uwidacznianie klastra PostgreSQL przy użyciu publicznego modułu równoważenia obciążenia

W tej sekcji skonfigurujesz niezbędną infrastrukturę do publicznego uwidocznienia punktów końcowych odczytu i zapisu i tylko do odczytu postgreSQL z ograniczeniami źródła adresów IP do publicznego adresu IP stacji roboczej klienta.

Możesz również pobrać następujące punkty końcowe z usługi adresów IP klastra:

* *Jeden* podstawowy punkt końcowy odczytu i zapisu kończący się ciągiem `*-rw`.
* *Zero do N* (w zależności od liczby replik) punktów końcowych tylko do odczytu, które kończą się na .`*-ro`
* *Jeden* punkt końcowy replikacji kończący się ciągiem `*-r`.

1. Pobierz szczegóły usługi adresów IP klastra [`kubectl get`][kubectl-get] przy użyciu polecenia .

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Przykładowe dane wyjściowe

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Istnieją trzy usługi: `namespace/cluster-name-ro` zamapowane na port 5433, `namespace/cluster-name-rw`i `namespace/cluster-name-r` zamapowane na port 5433. Należy unikać używania tego samego portu co węzeł odczytu/zapisu klastra bazy danych PostgreSQL. Jeśli chcesz, aby aplikacje uzyskiwały dostęp tylko do repliki bazy danych PostgreSQL tylko do odczytu, skierować je do portu 5433. Ostateczna usługa jest zwykle używana do tworzenia kopii zapasowych danych, ale może również działać jako węzeł tylko do odczytu.

1. Pobierz szczegóły usługi przy użyciu [`kubectl get`][kubectl-get] polecenia .

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

1. Skonfiguruj usługę modułu równoważenia obciążenia przy użyciu następujących plików YAML przy użyciu [`kubectl apply`][kubectl-apply] polecenia .

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

1. Pobierz szczegóły usługi przy użyciu [`kubectl describe`][kubectl-describe] polecenia .

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

### Weryfikowanie publicznych punktów końcowych postgreSQL

W tej sekcji sprawdzisz, czy usługa Azure Load Balancer jest prawidłowo skonfigurowana przy użyciu statycznego adresu IP utworzonego wcześniej i rozsyłania połączeń z podstawowymi replikami do odczytu i zapisu i tylko do odczytu oraz używać interfejsu wiersza polecenia psql do nawiązywania połączenia z obydwoma.

Należy pamiętać, że podstawowy punkt końcowy odczytu i zapisu mapuje się na port TCP 5432 i punkty końcowe repliki tylko do odczytu mapować na port 5433, aby umożliwić używanie tej samej nazwy DNS bazy danych PostgreSQL dla czytelników i pisarzy.

> [!NOTE]
> Potrzebna jest wartość hasła użytkownika aplikacji dla podstawowego uwierzytelniania postgreSQL wygenerowanego wcześniej i przechowywanego w zmiennej środowiskowej `$PG_DATABASE_APPUSER_SECRET` .

* Zweryfikuj publiczne punkty końcowe PostgreSQL przy użyciu następujących `psql` poleceń:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Przykładowe dane wyjściowe

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

    Przykładowe dane wyjściowe

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Po pomyślnym nawiązaniu połączenia z podstawowym punktem końcowym odczytu i zapisu funkcja PostgreSQL zwraca `f` *wartość false*, co oznacza, że bieżące połączenie jest możliwe do zapisu.

    Po nawiązaniu połączenia z repliką funkcja zwraca `t` *wartość true*, co wskazuje, że baza danych jest w odzyskiwaniu i tylko do odczytu.

## Symulowanie nieplanowanego trybu failover

W tej sekcji wyzwolono nagły błąd, usuwając zasobnik z uruchomioną podstawową bazą danych, co symuluje nagłe awarie lub utratę łączności sieciowej z węzłem hostujący podstawowy serwer PostgreSQL.

1. Sprawdź stan uruchomionych wystąpień zasobnika przy użyciu następującego polecenia:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Przykładowe dane wyjściowe

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Usuń zasobnik podstawowy przy użyciu [`kubectl delete`][kubectl-delete] polecenia .

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Sprawdź, czy `pg-primary-cnpg-sryti1qf-2` wystąpienie zasobnika jest teraz podstawowym, używając następującego polecenia:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Przykładowe dane wyjściowe

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Zresetuj `pg-primary-cnpg-sryti1qf-1` wystąpienie zasobnika jako podstawowe przy użyciu następującego polecenia:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Sprawdź, czy wystąpienia zasobników zostały zwrócone do stanu pierwotnego przed nieplanowanym testem trybu failover przy użyciu następującego polecenia:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Przykładowe dane wyjściowe

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Czyszczenie zasobów

* Po zakończeniu przeglądania wdrożenia usuń wszystkie zasoby utworzone w tym przewodniku [`az group delete`][az-group-delete] przy użyciu polecenia .

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Następne kroki

W tym przewodniku z instrukcjami przedstawiono następujące zagadnienia:

* Użyj interfejsu wiersza polecenia platformy Azure, aby utworzyć klaster usługi AKS z wieloma strefami.
* Wdróż klaster i bazę danych PostgreSQL o wysokiej dostępności przy użyciu operatora CNPG.
* Konfigurowanie monitorowania bazy danych PostgreSQL przy użyciu rozwiązań Prometheus i Grafana.
* Wdróż przykładowy zestaw danych w bazie danych PostgreSQL.
* Wykonaj uaktualnienia klastrów PostgreSQL i AKS.
* Symulowanie przerw w działaniu klastra i trybu failover repliki PostgreSQL.
* Wykonaj kopię zapasową i przywracanie bazy danych PostgreSQL.

Aby dowiedzieć się więcej na temat sposobu korzystania z usługi AKS dla obciążeń, zobacz [Co to jest usługa Azure Kubernetes Service (AKS)?][what-is-aks]

## Współautorzy

*Ten artykuł jest obsługiwany przez firmę Microsoft. Pierwotnie został napisany przez następujących współautorów*:

* Ken Kilty | Moduł TPM podmiotu zabezpieczeń
* Russell de Pina | Moduł TPM podmiotu zabezpieczeń
* Adrian Joian | Starszy inżynier klienta
* Jenny Hayes | Starszy deweloper zawartości
* Carol Smith | Starszy deweloper zawartości
* Erin Schaffer | Content Developer 2
* Adam Sharif | Inżynier klienta 2

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
