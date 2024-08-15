---
title: Déployer une base de données PostgreSQL à haute disponibilité sur AKS avec Azure CLI
description: 'Dans cet article, vous déployez une base de données PostgreSQL à haute disponibilité sur AKS en utilisant l’opérateur CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Déployer une base de données PostgreSQL à haute disponibilité sur AKS

Dans cet article, vous déployez une base de données PostgreSQL à haute disponibilité sur AKS.

* Si vous n’avez pas déjà créé l’infrastructure requise pour ce déploiement, suivez les étapes décrites dans [Créer une infrastructure pour déployer une base de données PostgreSQL à haute disponibilité sur AKS][create-infrastructure] pour être préparé, puis vous pouvez revenir à cet article.

## Créer un secret pour un utilisateur d’application d’amorçage

1. Générez un secret pour valider le déploiement PostgreSQL par connexion interactive pour un utilisateur d’application d’amorçage en utilisant la commande [`kubectl create secret`][kubectl-create-secret].

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Vérifiez que le secret a été créé avec succès en utilisant la commande [`kubectl get`][kubectl-get].

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Définir des variables d’environnement pour le cluster PostgreSQL

* Déployez un ConfigMap pour définir les variables d’environnement du cluster PostgreSQL en utilisant la commande [`kubectl apply`][kubectl-apply] qui suit :

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

## Installer Prometheus PodMonitors

Prometheus crée PodMonitors pour les instances CNPG en utilisant un ensemble de règles d’enregistrement par défaut stockées sur le référentiel d’exemples GitHub CNPG. Dans un environnement de production, ces règles seraient modifiées selon les besoins.

1. Ajoutez le dépôt Helm de la communauté Prometheus en utilisant la commande [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Mettez à niveau le référentiel Helm de la communauté Prometheus et installez-le sur le cluster principal en utilisant la commande [`helm upgrade`][helm-upgrade] avec l’indicateur `--install`.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Vérifiez que le moniteur de pod est créé.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Créer des informations d’identification fédérées

Dans cette section, vous créez un jeu d’identifiants d’identité fédérée pour la sauvegarde PostgreSQL, pour permettre à CNPG d’utiliser l’identité de charge de travail AKS pour s’authentifier auprès de la destination du compte de stockage des sauvegardes. L’opérateur CNPG crée un compte de service Kubernetes portant le même nom que le cluster nommé utilisé dans le manifeste de déploiement du cluster CNPG.

1. Obtenez l’URL de l’émetteur OIDC du cluster en utilisant la commande [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Créez des informations d’identification d’une identité fédérée à l’aide de la commande [`az identity federated-credential create`][az-identity-federated-credential-create].

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Déployer un cluster PostgreSQL à haute disponibilité

Dans cette section, vous déployez un cluster PostgreSQL à haute disponibilité en utilisant la [définition de ressource personnalisée (CRD) du cluster CNPG][cluster-crd].

Le tableau suivant présente les propriétés clés définies dans le manifeste de déploiement YAML pour la CRD de cluster :

| Propriété | Définition |
| --------- | ------------ |
| `inheritedMetadata` | Spécifique à l’opérateur CNPG. Les métadonnées sont héritées par tous les objets liés au cluster. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Étiquette DNS à utiliser lors de l’exposition des points de terminaison de cluster Postgres en lecture-écriture et en lecture seule. |
| `labels: azure.workload.identity/use: "true"` | Indique qu’AKS doit injecter des dépendances d’identité de charge de travail dans les pods hébergeant les instances de cluster PostgreSQL. |
| `topologySpreadConstraints` | Exiger différentes zones et différents nœuds avec l’étiquette `"workload=postgres"`. |
| `resources` | Configure une classe Qualité de service (QoS) *Garantie*. Dans un environnement de production, ces valeurs sont essentielles pour optimiser l’utilisation de la machine virtuelle de nœud sous-jacente et varient en fonction de la référence SKU de la machine virtuelle Azure utilisée. |
| `bootstrap` | Spécifique à l’opérateur CNPG. Initialise avec une base de données d’application vide. |
| `storage` / `walStorage` | Spécifique à l’opérateur CNPG. Définit des modèles de stockage pour les PersistentVolumeClaims (PVC) pour le stockage des données et des journaux. Il est également possible de spécifier le stockage pour les espaces de table à partitionner pour augmenter les IOPS. |
| `replicationSlots` | Spécifique à l’opérateur CNPG. Active les emplacements de réplication pour la haute disponibilité. |
| `postgresql` | Spécifique à l’opérateur CNPG. Mappe les paramètres pour `postgresql.conf`, `pg_hba.conf`et `pg_ident.conf config`. |
| `serviceAccountTemplate` | Contient le modèle nécessaire pour générer les comptes de service et mappe les identifiants d’identité fédérée AKS à l’UAMI pour activer l’authentification d’identité de charge de travail AKS depuis les pods hébergeant les instances PostgreSQL vers des ressources Azure externes. |
| `barmanObjectStore` | Spécifique à l’opérateur CNPG. Configure la suite d’outils barman-cloud à l’aide de l’identité de charge de travail AKS pour l’authentification auprès du magasin d’objets Stockage Blob Azure. |

1. Déployez le cluster PostgreSQL avec la CRD de cluster en utilisant la commande [`kubectl apply`][kubectl-apply].

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

1. Vérifiez que le cluster PostgreSQL principal a été correctement créé en utilisant la commande [`kubectl get`][kubectl-get]. La CRD de cluster CNPG a spécifié trois instances, ce qui peut être validé en consultant les pods en cours d’exécution une fois que chaque instance est générée et jointe pour la réplication. Soyez patient, car un certain temps peut être nécessaire pour que les trois instances soient en ligne et rejoignent le cluster.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Exemple de sortie

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Valider que Prometheus PodMonitor est en cours d’exécution

L’opérateur CNPG crée automatiquement un PodMonitor pour l’instance principale à l’aide des règles d’enregistrement créées pendant l’[installation de la communauté Prometheus](#install-the-prometheus-podmonitors).

1. Vérifiez que PodMonitor est en cours d’exécution en utilisant la commande [`kubectl get`][kubectl-get].

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Exemple de sortie

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Si vous utilisez Azure Monitor pour Managed Prometheus, vous devez ajouter un autre moniteur de pod en utilisant le nom de groupe personnalisé. Managed Prometheus ne récupère pas les définitions de ressources personnalisées (CRD) de la communauté Prometheus. Outre le nom du groupe, les CRD sont identiques. Cela permet aux moniteurs de pods pour Managed Prometheus d’exister côte à côte de ceux qui utilisent le moniteur de pods de la communauté. Si vous n’utilisez pas Managed Prometheus, vous pouvez ignorer cette partie. Créez un moniteur de pod :

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

Vérifiez que le moniteur de pod est créé (notez la différence dans le nom de groupe).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Option A : Espace de travail Azure Monitor

Une fois que vous avez déployé le cluster Postgres et le moniteur de pod, vous pouvez afficher les métriques en utilisant le Portail Azure dans un espace de travail Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Capture d’écran montrant les métriques dans un espace de travail Azure Monitor." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Option B : Managed Grafana

Vous pouvez également créer un tableau de bord de métriques sur l’instance Managed Grafana créée par le script de déploiement, pour visualiser les métriques exportées vers l’espace de travail Azure Monitor. Vous pouvez accéder à Managed Grafana via le Portail Azure. Accédez à l’instance Managed Grafana créée par le script de déploiement, puis cliquez sur le lien Point de terminaison, comme illustré ici :

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Capture d’écran montrant une instance Azure Managed Grafana." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Le fait de cliquer sur le lien Point de terminaison entraîne l’ouverture d’une nouvelle fenêtre de navigateur, dans laquelle vous pouvez créer des tableaux de bord sur l’instance Managed Grafana. En suivant les instructions pour [configurer une source de données Azure Monitor](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in), vous pouvez ensuite ajouter des visualisations pour créer un tableau de bord de métriques depuis le cluster Postgres. Après avoir configuré la connexion de source de données, dans le menu principal, cliquez sur l’option Sources de données et vous devez voir un ensemble d’options de source de données pour la connexion de source de données, comme illustré ici :

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Capture d’écran montrant les options de source de données." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Dans l’option Managed Prometheus, cliquez sur l’option de génération de tableau de bord pour ouvrir l’éditeur de tableau de bord. Une fois la fenêtre de l’éditeur ouverte, cliquez sur l’option Ajouter une visualisation, puis sur l’option Managed Prometheus pour parcourir les métriques depuis le cluster Postgres. Une fois que vous avez sélectionné la métrique que vous souhaitez visualiser, cliquez sur le bouton Exécuter des requêtes pour extraire les données de la visualisation, comme illustré ici :

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Capture d’écran montrant le tableau de bord de construction." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Cliquez sur le bouton Enregistrer pour ajouter le panneau à votre tableau de bord. Vous pouvez ajouter d’autres panneaux en cliquant sur le bouton Ajouter dans l’éditeur de tableau de bord et en répétant ce processus pour visualiser d’autres métriques. L’ajout des visualisations de métriques doit ressembler à ceci :

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Capture d’écran montrant enregistrer le tableau de bord." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Cliquez sur le bouton Enregistrer pour enregistrer vos modifications.

## Inspecter le cluster PostgreSQL déployé

Vérifiez que PostgreSQL est réparti sur plusieurs zones de disponibilité en récupérant les détails du nœud AKS en utilisant la commande [`kubectl get`][kubectl-get].

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Votre sortie doit ressembler à l’exemple de sortie suivant avec la zone de disponibilité indiquée pour chaque nœud :

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

## Se connecter à PostgreSQL et créer un exemple de jeu de données

Dans cette section, vous créez une table et insérez des données dans la base de données d’application créée dans la CRD du cluster CNPG que vous avez déployé précédemment. Vous utilisez ces données pour valider les opérations de sauvegarde et de restauration pour le cluster PostgreSQL.

* Créez une table et insérez des données dans la base de données d’application en utilisant les commandes suivantes :

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

    Votre sortie doit ressembler à l’exemple suivant :

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
## Se connecter à des réplicas en lecture seule PostgreSQL

* Connectez-vous aux réplicas en lecture seule PostgreSQL et validez l’exemple de jeu de données en utilisant les commandes suivantes :

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Exemple de sortie

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

    Exemple de sortie

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Configurer des sauvegardes PostgreSQL à la demande et planifiées en utilisant Barman

1. Vérifiez que le cluster PostgreSQL peut accéder au compte de stockage Azure spécifié dans la CRD du cluster CNPG et que `Working WAL archiving` indique `OK` en utilisant la commande suivante :

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Exemple de sortie

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Déployez une sauvegarde à la demande sur Stockage Azure, qui utilise l’intégration d’identité de charge de travail AKS, en utilisant le fichier YAML avec la commande [`kubectl apply`][kubectl-apply].

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

1. Validez l’état de la sauvegarde à la demande en utilisant la commande [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Exemple de sortie

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Vérifiez que le cluster a un premier point de récupération en utilisant la commande suivante :

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Exemple de sortie

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Configurez une sauvegarde planifiée *toutes les heures à 15 minutes après l’heure* en utilisant le fichier YAML avec la commande [`kubectl apply`][kubectl-apply].

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

1. Validez l’état de la sauvegarde planifiée en utilisant la commande [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Affichez les fichiers de sauvegarde stockés sur le Stockage Blob Azure pour le cluster principal en utilisant la commande [`az storage blob list`][az-storage-blob-list].

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Votre sortie doit ressembler à l’exemple de sortie suivant, validant la réussite de la sauvegarde :

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

## Restaurer la sauvegarde à la demande sur un nouveau cluster PostgreSQL

Dans cette section, vous restaurez la sauvegarde à la demande que vous avez créée précédemment à l’aide de l’opérateur CNPG dans une nouvelle instance en utilisant la CRD de cluster d’amorçage. Un cluster d’instance unique est utilisé par souci de simplicité. N’oubliez pas que l’identité de charge de travail AKS (via CNPG inheritFromAzureAD) accède aux fichiers de sauvegarde et que le nom du cluster de récupération est utilisé pour générer un nouveau compte de service Kubernetes spécifique au cluster de récupération.

Vous créez également un deuxième jeu d’identifiants fédérés pour mapper le nouveau compte de service de cluster de récupération à l’UAMI existant disposant d’un accès « Contributeur aux données blob de stockage » aux fichiers de sauvegarde sur le stockage d’objets blob.

1. Créez un second jeu d’identifiants d’identité fédérée en utilisant la commande [`az identity federated-credential create`][az-identity-federated-credential-create].

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

1. Restaurez la sauvegarde à la demande en utilisant la CRD de cluster avec la commande [`kubectl apply`][kubectl-apply].

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

1. Connectez-vous à l’instance récupérée, puis vérifiez que le jeu de données créé sur le cluster d’origine où la sauvegarde complète a été effectuée est présent en utilisant la commande suivante :

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Exemple de sortie

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Supprimez le cluster récupéré en utilisant la commande suivante :

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Supprimez le jeu d’identifiants d’identité fédérée en utilisant la commande [`az identity federated-credential delete`][az-identity-federated-credential-delete].

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Exposer le cluster PostgreSQL en utilisant un équilibreur de charge public

Dans cette section, vous configurez l’infrastructure nécessaire pour exposer publiquement les points de terminaison en lecture-écriture et en lecture seule PostgreSQL avec des restrictions de source IP à l’adresse IP publique de votre station de travail cliente.

Vous récupérez également les points de terminaison suivants depuis le service IP du cluster :

* *Un* point de terminaison en lecture-écriture principal qui se termine par `*-rw`.
* *Zéro à N* (en fonction du nombre de réplicas) points de terminaison en lecture seule qui se terminent par `*-ro`.
* *Un* point de terminaison de réplication qui se termine par `*-r`.

1. Obtenez les détails du service IP du cluster en utilisant la commande [`kubectl get`][kubectl-get].

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Exemple de sortie

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Il existe trois services : `namespace/cluster-name-ro` mappé au port 5433, `namespace/cluster-name-rw` et `namespace/cluster-name-r` mappé au port 5433. Il est important d’éviter d’utiliser le même port que le nœud de lecture/écriture du cluster de base de données PostgreSQL. Si vous voulez que les applications accèdent uniquement au réplica en lecture seule du cluster de base de données PostgreSQL, dirigez-les vers le port 5433. Le service final est généralement utilisé pour les sauvegardes de données, mais peut également fonctionner en tant que nœud en lecture seule.

1. Obtenez les détails du service en utilisant la commande [`kubectl get`][kubectl-get].

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

1. Configurer le service d’équilibreur de charge avec les fichiers YAML suivants en utilisant la commande [`kubectl apply`][kubectl-apply].

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

1. Obtenez les détails du service en utilisant la commande [`kubectl describe`][kubectl-describe].

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

### Valider les points de terminaison PostgreSQL publics

Dans cette section, vous vérifiez que l’Azure Load Balancer est correctement configuré en utilisant l’adresse IP statique que vous avez créée précédemment et achemine les connexions aux réplicas en lecture-écriture et en lecture seule primaires, et utilisez l’interface CLI psql pour vous connecter aux deux.

N’oubliez pas que le point de terminaison principal en lecture-écriture est mappé au port TCP 5432 et que les points de terminaison de réplica en lecture seule sont mappés au port 5433, pour autoriser le même nom DNS PostgreSQL à utiliser pour les lecteurs et les enregistreurs.

> [!NOTE]
> Vous avez besoin de la valeur du mot de passe utilisateur de l’application pour l’authentification de base PostgreSQL qui a été générée précédemment et stockée dans la variable d’environnement `$PG_DATABASE_APPUSER_SECRET`.

* Valider les points de terminaison PostgreSQL publics en utilisant les commandes suivantes `psql` :

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Exemple de sortie

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

    Exemple de sortie

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Lorsqu’elle est correctement connectée au point de terminaison en lecture-écriture principal, la fonction PostgreSQL retourne `f` pour *false*, indiquant que la connexion actuelle est accessible en écriture.

    Lorsqu’elle est connectée à un réplica, la fonction retourne `t` pour *true*, indiquant que la base de données est en cours de récupération et en lecture seule.

## Simuler un basculement non planifié

Dans cette section, vous déclenchez une défaillance soudaine en supprimant le pod exécutant le serveur principal, ce qui simule un blocage soudain ou une perte de connectivité réseau sur le nœud hébergeant le serveur principal PostgreSQL.

1. Vérifiez l’état des instances de pod en cours d’exécution en utilisant la commande suivante :

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Exemple de sortie

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Supprimez le pod principal en utilisant la commande [`kubectl delete`][kubectl-delete].

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Vérifiez que l’instance de pod `pg-primary-cnpg-sryti1qf-2` est désormais la principale en utilisant la commande suivante :

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Exemple de sortie

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Réinitialisez l’instance de pod `pg-primary-cnpg-sryti1qf-1` en tant que principale en utilisant la commande suivante :

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Vérifiez que les instances de pod sont retournées à leur état d’origine avant le test de basculement non planifié en utilisant la commande suivante :

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Exemple de sortie

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Nettoyer les ressources

* Une fois que vous avez terminé d’examiner votre déploiement, supprimez toutes les ressources que vous avez créées dans ce guide en utilisant la commande [`az group delete`][az-group-delete].

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Étapes suivantes

Dans ce guide pratique, vous avez appris à effectuer les opérations suivantes :

* Utiliser Azure CLI pour créer un cluster AKS multizone.
* Déployer un cluster et une base de données PostgreSQL à haute disponibilité en utilisant l’opérateur CNPG.
* Configurer la supervision pour PostgreSQL en utilisant Prometheus et Grafana.
* Déployer un exemple de jeu de données sur la base de données PostgreSQL.
* Effectuer des mises à niveau de cluster PostgreSQL et AKS.
* Simuler une interruption de cluster et un basculement de réplica PostgreSQL.
* Effectuer une sauvegarde et une restauration de la base de données PostgreSQL.

Pour en savoir plus sur la façon dont vous pouvez tirer profit d’AKS pour vos charges de travail, consultez [Qu’est-ce qu’Azure Kubernetes Service (AKS) ?][what-is-aks]

## Contributeurs

*Cet article est géré par Microsoft. Il a été écrit à l’origine par les contributeurs* suivants :

* Ken Kitty | Responsable de programme technique principal
* Russell de Pina | Responsable de programme technique principal
* Adrian Joian | Ingénieur client senior
* Jenny Hayes | Développeuse de contenu confirmée
* Carol Smith | Développeuse de contenu confirmée
* Erin Schaffer | Développeuse de contenu 2
* Adam Sharif | Ingénieur client 2

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
