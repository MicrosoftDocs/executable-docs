---
title: Implantar um banco de dados PostgreSQL altamente disponível no AKS com a CLI do Azure
description: 'Neste artigo, você implantará um banco de dados PostgreSQL altamente disponível no AKS usando o operador CloudNativePG.'
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Implantar um banco de dados PostgreSQL altamente disponível no AKS

Neste artigo, você implantará um banco de dados PostgreSQL altamente disponível no AKS.

* Se você ainda não criou a infraestrutura necessária para essa implantação, siga as etapas em [Criar infraestrutura para implantar um banco de dados PostgreSQL altamente disponível no AKS][create-infrastructure] para ser configurado e, em seguida, você poderá retornar a este artigo.

## Criar segredo para o usuário do aplicativo bootstrap

1. Gere um segredo para validar a implantação do PostgreSQL por meio de logon interativo para um usuário do aplicativo bootstrap usando o comando [`kubectl create secret`][kubectl-create-secret].

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. Valide se o segredo foi criado com êxito usando o comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Definir variáveis de ambiente para o cluster PostgreSQL

* Implante um ConfigMap para definir variáveis de ambiente para o cluster PostgreSQL usando o seguinte comando [`kubectl apply`][kubectl-apply]:

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

## Instalar o Prometheus PodMonitors

O Prometheus cria PodMonitors para as instâncias CNPG usando um conjunto de regras de gravação padrão armazenadas no repositório de exemplos do GitHub CNPG. Em um ambiente de produção, essas regras seriam modificadas conforme necessário.

1. Adicione o repositório Prometheus Community Helm usando o comando [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Atualize o repositório Prometheus Community Helm e instale-o no cluster primário usando o comando [`helm upgrade`][helm-upgrade] com o sinalizador `--install`.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Verifique se o monitor do pod foi criado.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## Criar uma credencial federada

Nesta seção, você criará uma credencial de identidade federada para backup do PostgreSQL para permitir que o CNPG use a identidade de carga de trabalho do AKS para autenticar no destino da conta de armazenamento para backups. O operador CNPG cria uma conta de serviço do Kubernetes com o mesmo nome do cluster nomeado usado no manifesto de implantação do Cluster CNPG.

1. Obtenha a URL do emissor OIDC do cluster usando o comando [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. Crie uma credencial de identidade federada usando o comando [`az identity federated-credential create`][az-identity-federated-credential-create].

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## Implantar um cluster PostgreSQL altamente disponível

Nesta seção, você implantará um cluster PostgreSQL altamente disponível usando o [CRD (definição de recurso personalizado) do Cluster CNPG][cluster-crd].

A tabela a seguir descreve as propriedades de chave definidas no manifesto de implantação YAML para o CRD do cluster:

| Propriedade | Definição |
| --------- | ------------ |
| `inheritedMetadata` | Específico para o operador CNPG. Os metadados são herdados por todos os objetos relacionados ao cluster. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | Rótulo DNS para uso ao expor os pontos de extremidade de cluster postgres somente leitura e leitura. |
| `labels: azure.workload.identity/use: "true"` | Indica que o AKS deve injetar dependências de identidade de carga de trabalho nos pods que hospedam as instâncias de cluster do PostgreSQL. |
| `topologySpreadConstraints` | Exigir zonas diferentes e nós diferentes com rótulo `"workload=postgres"`. |
| `resources` | Configura uma classe QoS (Qualidade de Serviço) de *Garantia*. Em um ambiente de produção, esses valores são fundamentais para maximizar o uso da VM do nó subjacente e variam de acordo com a SKU da VM do Azure usada. |
| `bootstrap` | Específico para o operador CNPG. Inicializa com um banco de dados de aplicativo vazio. |
| `storage` / `walStorage` | Específico para o operador CNPG. Define modelos de armazenamento para os PVCs (PersistentVolumeClaims) para armazenamento de dados e logs. Também é possível especificar o armazenamento para os espaços de tabela serem fragmentados para IOPs maiores. |
| `replicationSlots` | Específico para o operador CNPG. Habilita slots de replicação para alta disponibilidade. |
| `postgresql` | Específico para o operador CNPG. Mapeia as configurações para `postgresql.conf`, `pg_hba.conf` e `pg_ident.conf config`. |
| `serviceAccountTemplate` | Contém o modelo necessário para gerar as contas de serviço e mapeia a credencial de identidade federada do AKS para a UAMI para habilitar a autenticação de identidade de carga de trabalho do AKS dos pods que hospedam as instâncias do PostgreSQL para recursos externos do Azure. |
| `barmanObjectStore` | Específico para o operador CNPG. Configura o conjunto de ferramentas barman-cloud usando a identidade da carga de trabalho do AKS para autenticação no repositório de objetos do Armazenamento de Blobs do Azure. |

1. Implante o cluster PostgreSQL com o CRD do Cluster usando o comando [`kubectl apply`][kubectl-apply].

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

1. Valide se o cluster postgreSQL primário foi criado com êxito usando o comando [`kubectl get`][kubectl-get]. O CRD do Cluster CNPG especificou três instâncias, que podem ser validadas exibindo pods em execução depois que cada instância é criada e unida para replicação. Seja paciente, pois pode levar algum tempo para as três instâncias ficarem online e ingressarem no cluster.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Saída de exemplo

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Validar se o Prometheus PodMonitor está em execução

O operador do CNPG cria automaticamente um PodMonitor para a instância primária usando as regras de registro criadas durante a [instalação da comunidade Prometheus](#install-the-prometheus-podmonitors).

1. Valide se o PodMonitor está em execução usando o comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    Saída de exemplo

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

Se você estiver usando o Azure Monitor para o Prometheus Gerenciado, precisará adicionar outro monitor de pod usando o nome do grupo personalizado. O Prometheus gerenciado não capta as CRDs (definições de recursos personalizados) na comunidade Prometheus. Além do nome do grupo, os CRDs são os mesmos. Isso permite que monitores de pod para o Prometheus Gerenciado existam lado a lado aqueles que usam o monitor de pod da comunidade. Se você não estiver usando o Prometheus Gerenciado, poderá ignorar isso. Crie um novo monitor de pod:

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

Verifique se o monitor do pod foi criado (observe a diferença no nome do grupo).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### Opção A – Workspace do Azure Monitor

Depois de implantar o cluster postgres e o monitor de pod, você pode exibir as métricas usando o portal do Azure em um workspace do Azure Monitor.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Captura de tela mostrando métricas em um workspace do Azure Monitor." lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### Opção B – Grafana Gerenciado

Como alternativa, depois de implantar os monitores de cluster e pod do Postgres, você pode criar um painel de métricas na instância do Grafana Gerenciada criada pelo script de implantação para visualizar as métricas exportadas para o workspace do Azure Monitor. Você pode acessar o Grafana Gerenciado por meio do portal do Azure. Navegue até a instância do Grafana Gerenciado criada pelo script de implantação e clique no link do Ponto de Extremidade, conforme mostrado aqui:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Captura de tela mostrando uma instância do Azure Managed Grafana." lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

Clicar no link do Ponto de Extremidade fará com que uma nova janela do navegador seja aberta, na qual você pode criar painéis na instância do Grafana Gerenciado. Seguindo as instruções para [configurar uma fonte de dados do Azure Monitor](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in), você pode adicionar visualizações para criar um painel de métricas do cluster Postgres. Depois de configurar a conexão da fonte de dados, no menu principal, clique na opção Fontes de dados e você deverá ver um conjunto de opções de fonte de dados para a conexão da fonte de dados, conforme mostrado aqui:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="Captura de tela mostrando as opções da fonte de dados." lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

Na opção Prometheus Gerenciado, clique na opção para criar um dashboard para abrir o editor do painel. Depois que a janela do editor for aberta, clique na opção Adicionar visualização e clique na opção Prometheus Gerenciado para navegar pelas métricas do cluster Postgres. Depois de selecionar a métrica que deseja visualizar, clique no botão Executar consultas para buscar os dados para a visualização, conforme mostrado aqui:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="Captura de tela mostrando o painel de construção." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

Clique no botão Salvar para adicionar o painel ao painel. Você pode adicionar outros painéis clicando no botão Adicionar no editor do painel e repetindo esse processo para visualizar outras métricas. Adicionando as visualizações de métricas, você deve ter algo parecido com este:

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="Captura de tela mostrando o painel de salvamento." lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

Clique no ícone Salvar para salvar seu painel.

## Inspecionar o cluster PostgreSQL implantado

Valide se o PostgreSQL está distribuído entre várias zonas de disponibilidade recuperando os detalhes do nó do AKS usando o comando [`kubectl get`][kubectl-get].

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

Sua saída deve ser semelhante à seguinte saída de exemplo com a zona de disponibilidade mostrada para cada nó:

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

## Conectar-se ao PostgreSQL e criar um conjunto de dados de exemplo

Nesta seção, você criará uma tabela e inserirá alguns dados no banco de dados do aplicativo que foi criado no CRD do Cluster CNPG que você implantou anteriormente. Você usa esses dados para validar as operações de backup e restauração para o cluster PostgreSQL.

* Crie uma tabela e insira dados no banco de dados do aplicativo usando os seguintes comandos:

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

    Sua saída deve ser parecida com o seguinte exemplo de saída:

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
## Conectar-se às réplicas somente leitura do PostgreSQL

* Conecte-se às réplicas somente leitura do PostgreSQL e valide o conjunto de dados de exemplo usando os seguintes comandos:

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    Saída de exemplo

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

    Saída de exemplo

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Configurar backups postgreSQL sob demanda e agendados usando o Barman

1. Valide se o cluster PostgreSQL pode acessar a conta de armazenamento do Azure especificada no CRD do Cluster CNPG e que `Working WAL archiving` relata como `OK` usando o seguinte comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Saída de exemplo

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. Implante um backup sob demanda no Armazenamento do Microsoft Azure, que usa a integração de identidade de carga de trabalho do AKS usando o arquivo YAML com o comando [`kubectl apply`][kubectl-apply].

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

1. Valide o status do backup sob demanda usando o comando [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Saída de exemplo

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. Valide se o cluster tem um primeiro ponto de capacidade de recuperação usando o seguinte comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    Saída de exemplo

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. Configure um backup agendado para *cada hora a 15 minutos após a hora* usando o arquivo YAML com o comando [`kubectl apply`][kubectl-apply].

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

1. Valide o status do backup agendado usando o comando [`kubectl describe`][kubectl-describe].

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Exiba os arquivos de backup armazenados no armazenamento de blobs do Azure para o cluster primário usando o comando [`az storage blob list`][az-storage-blob-list].

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    Sua saída deve ser semelhante à seguinte saída de exemplo, validando se o backup foi bem-sucedido:

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

## Restaurar o backup sob demanda para um novo cluster PostgreSQL

Nesta seção, você restaurará o backup sob demanda criado anteriormente usando o operador CNPG em uma nova instância usando o CRD do Cluster de inicialização. Um cluster de instância única é usado para simplificar. Lembre-se de que a identidade da carga de trabalho do AKS (por meio do CNPG inheritFromAzureAD) acessa os arquivos de backup e que o nome do cluster de recuperação é usado para gerar uma nova conta de serviço do Kubernetes específica para o cluster de recuperação.

Você também cria uma segunda credencial federada para mapear a nova conta de serviço de cluster de recuperação para a UAMI existente que tem acesso "Colaborador de Dados de Blobs de Armazenamento" aos arquivos de backup no armazenamento de blobs.

1. Crie uma segunda credencial de identidade federada usando o comando [`az identity federated-credential create`][az-identity-federated-credential-create].

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

1. Restaure o backup sob demanda usando o CRD do Cluster com o comando [`kubectl apply`][kubectl-apply].

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

1. Conecte-se à instância recuperada e valide se o conjunto de dados criado no cluster original em que o backup completo foi feito está presente usando o seguinte comando:

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    Saída de exemplo

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. Exclua o cluster recuperado usando o seguinte comando:

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. Exclua a credencial de identidade federada usando o comando [`az identity federated-credential delete`][az-identity-federated-credential-delete].

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## Expor o cluster PostgreSQL usando um balanceador de carga público

Nesta seção, você configurará a infraestrutura necessária para expor publicamente os pontos de extremidade de leitura e leitura do PostgreSQL com restrições de origem de IP para o endereço IP público da estação de trabalho do cliente.

Você também recupera os seguintes pontos de extremidade do serviço IP do cluster:

* *Um* ponto de extremidade de leitura/gravação primário que termina com `*-rw`.
* *Zero a N* (dependendo do número de réplicas) pontos de extremidade somente leitura que terminam com `*-ro`.
* *Um* ponto de extremidade de replicação que termina com `*-r`.

1. Obtenha os detalhes do serviço IP do cluster usando o comando [`kubectl get`][kubectl-get].

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    Saída de exemplo

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > Há três serviços: `namespace/cluster-name-ro` mapeados para a porta 5433 `namespace/cluster-name-rw` e `namespace/cluster-name-r` mapeados para a porta 5433. É importante evitar o uso da mesma porta que o nó de leitura/gravação do cluster de banco de dados PostgreSQL. Se você quiser que os aplicativos acessem apenas a réplica somente leitura do cluster de banco de dados PostgreSQL, direcione-os para a porta 5433. O serviço final normalmente é usado para backups de dados, mas também pode funcionar como um nó somente leitura.

1. Obtenha os detalhes do serviço usando o comando [`kubectl get`][kubectl-get].

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

1. Configure o serviço de balanceador de carga com os seguintes arquivos YAML usando o comando [`kubectl apply`][kubectl-apply].

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

1. Obtenha os detalhes do serviço usando o comando [`kubectl describe`][kubectl-describe].

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

### Validar pontos de extremidade postgreSQL públicos

Nesta seção, você valida que o Azure Load Balancer está configurado corretamente usando o IP estático que você criou anteriormente e roteando conexões para as réplicas primárias de leitura-gravação e somente leitura e usar a CLI psql para se conectar a ambas.

Lembre-se de que o ponto de extremidade de leitura/gravação primário é mapeado para a porta TCP 5432 e os pontos de extremidade de réplica somente leitura são mapeados para a porta 5433 para permitir que o mesmo nome DNS do PostgreSQL seja usado para leitores e gravadores.

> [!NOTE]
> Você precisa do valor da senha do usuário do aplicativo para a autenticação básica do PostgreSQL que foi gerada anteriormente e armazenada na variável de ambiente `$PG_DATABASE_APPUSER_SECRET`.

* Valide os pontos de extremidade postgreSQL públicos usando os seguintes comandos de `psql`:

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    Saída de exemplo

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

    Saída de exemplo

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    Quando conectada com êxito ao ponto de extremidade de leitura/gravação primário, a função PostgreSQL retorna `f` para *false*, indicando que a conexão atual é gravável.

    Quando conectada a uma réplica, a função retorna `t` para *true*, indicando que o banco de dados está em recuperação e somente leitura.

## Simular um failover não planejado

Nesta seção, você dispara uma falha repentina excluindo o pod que executa o primário, que simula uma falha repentina ou perda de conectividade de rede com o nó que hospeda o postgreSQL primário.

1. Verifique o status das instâncias de pod em execução usando o seguinte comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Saída de exemplo

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Exclua o pod primário usando o comando [`kubectl delete`][kubectl-delete].

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. Valide se a instância do pod `pg-primary-cnpg-sryti1qf-2` agora é a principal usando o seguinte comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Saída de exemplo

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. Redefina a instância do pod `pg-primary-cnpg-sryti1qf-1` como a primária usando o seguinte comando:

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. Valide se as instâncias de pod retornaram ao estado original antes do teste de failover não planejado usando o seguinte comando:

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    Saída de exemplo

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## Limpar os recursos

* Depois de concluir a revisão da implantação, exclua todos os recursos criados neste guia usando o comando [`az group delete`][az-group-delete].

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## Próximas etapas

Neste guia de instruções, você aprendeu como:

* Use a CLI do Azure para criar um cluster AKS de várias zonas.
* Implante um cluster e um banco de dados postgreSQL altamente disponíveis usando o operador CNPG.
* Configure o monitoramento para PostgreSQL usando Prometheus e Grafana.
* Implante um conjunto de dados de exemplo no banco de dados PostgreSQL.
* Execute atualizações de cluster do PostgreSQL e do AKS.
* Simule uma interrupção de cluster e failover de réplica do PostgreSQL.
* Execute um backup e uma restauração do banco de dados PostgreSQL.

Para saber mais sobre como você pode aproveitar o AKS para suas cargas de trabalho, confira [O que é o AKS (Serviço de Kubernetes do Azure)?][what-is-aks]

## Colaboradores

*Este artigo é mantido pela Microsoft. Foi originalmente escrito pelos seguintes colaboradores*:

* Ken Kilty | Principal TPM
* Russell de Pina | Principal TPM
* Adrian Joian | Engenheiro sênior de clientes
* Jenny Hayes | Desenvolvedora sênior de conteúdo
* Carol Smith | Desenvolvedora sênior de conteúdo
* Erin Schaffer | Desenvolvedora de Conteúdo 2
* Adam Sharif | Engenheiro de clientes 2

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
