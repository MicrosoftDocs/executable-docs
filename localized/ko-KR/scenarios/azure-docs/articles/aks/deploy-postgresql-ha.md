---
title: Azure CLI를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스 배포
description: 이 문서에서는 CloudNativePG 연산자를 사용하여 AKS에 고가용성 PostgreSQL 데이터베이스를 배포합니다.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# AKS에 고가용성 PostgreSQL 데이터베이스 배포

이 문서에서는 AKS에 고가용성 PostgreSQL 데이터베이스를 배포합니다.

* 이 배포에 필요한 인프라를 아직 만들지 않은 경우 [AKS에 고가용성 PostgreSQL 데이터베이스 배포를 위한 인프라 만들기][create-infrastructure]의 단계에 따라 설정한 다음 이 문서로 돌아올 수 있습니다.

## 부트스트랩 앱 사용자를 위한 비밀 만들기

1. [`kubectl create secret`][kubectl-create-secret] 명령을 사용하여 부트스트랩 앱 사용자에 대한 대화형 로그인으로 PostgreSQL 배포의 유효성을 검사하기 위한 비밀을 생성합니다.

    ```bash
    PG_DATABASE_APPUSER_SECRET=$(echo -n | openssl rand -base64 16)

    kubectl create secret generic db-user-pass \
        --from-literal=username=app \
        --from-literal=password="${PG_DATABASE_APPUSER_SECRET}" \
        --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

1. [`kubectl get`][kubectl-get] 명령을 사용하여 비밀이 성공적으로 만들어졌는지 유효성을 검사합니다.

    ```bash
    kubectl get secret db-user-pass --namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## PostgreSQL 클러스터에 대한 환경 변수 설정

* 다음 [`kubectl apply`][kubectl-apply] 명령을 사용하여 PostgreSQL 클러스터에 대한 환경 변수를 설정하려면 ConfigMap을 배포합니다.

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

## Prometheus PodMonitors 설치

Prometheus는 CNPG GitHub 샘플 리포지토리에 저장된 기본 녹음/녹화 규칙 집합을 사용하여 CNPG 인스턴스에 대한 PodMonitor를 만듭니다. 프로덕션 환경에서는 이러한 규칙이 필요에 따라 수정됩니다.

1. [`helm repo add`][helm-repo-add] 명령을 사용하여 Prometheus Community Helm 리포지토리를 추가합니다.

    ```bash
    helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts
    ```

2. Prometheus Community Helm 리포지토리를 업그레이드하고 `--install` 플래그와 함께 [`helm upgrade`][helm-upgrade] 명령을 사용하여 기본 클러스터에 설치합니다.

    ```bash
    helm upgrade --install \
        --namespace $PG_NAMESPACE \
        -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/samples/monitoring/kube-stack-config.yaml \
        prometheus-community \
        prometheus-community/kube-prometheus-stack \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME
    ```

Pod 모니터가 만들어졌는지 확인합니다.

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.monitoring.coreos.com \
    $PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```  

## 페더레이션 자격 증명 만들기

이 섹션에서는 CNPG가 AKS 워크로드 ID를 사용하여 백업용 스토리지 계정 대상에 인증할 수 있도록 PostgreSQL 백업용 페더레이션된 ID 자격 증명을 만듭니다. CNPG 운영자는 CNPG 클러스터 배포 매니페스트에 사용된 클러스터와 동일한 이름으로 Kubernetes Service 계정을 만듭니다.

1. [`az aks show`][az-aks-show] 명령을 사용하여 클러스터의 OIDC 발급자 URL을 가져옵니다.

    ```bash
    export AKS_PRIMARY_CLUSTER_OIDC_ISSUER="$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "oidcIssuerProfile.issuerUrl" \
        --output tsv)"
    ```

2. [`az identity federated-credential create`][az-identity-federated-credential-create] 명령을 사용하여 페더레이션 ID 자격 증명을 만듭니다.

    ```bash
    az identity federated-credential create \
        --name $AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME --issuer "${AKS_PRIMARY_CLUSTER_OIDC_ISSUER}" \
        --subject system:serviceaccount:"${PG_NAMESPACE}":"${PG_PRIMARY_CLUSTER_NAME}" \
        --audience api://AzureADTokenExchange
    ```

## 고가용성 PostgreSQL 클러스터 배포

이 섹션에서는 [CNPG 클러스터 CRD(사용자 지정 리소스 정의)][cluster-crd]를 사용하여 고가용성 PostgreSQL 클러스터를 배포합니다.

다음 표에는 클러스터 CRD에 대한 YAML 배포 매니페스트에 설정된 주요 속성이 간략하게 설명되어 있습니다.

| 속성 | 정의 |
| --------- | ------------ |
| `inheritedMetadata` | CNPG 운영자에게만 해당됩니다. 메타데이터는 클러스터와 관련된 모든 개체에 상속됩니다. |
| `annotations: service.beta.kubernetes.io/azure-dns-label-name` | 읽기-쓰기 및 읽기 전용 Postgres 클러스터 엔드포인트를 노출할 때 사용되는 DNS 레이블입니다. |
| `labels: azure.workload.identity/use: "true"` | AKS가 PostgreSQL 클러스터 인스턴스를 호스팅하는 Pod에 워크로드 ID 종속성을 삽입해야 함을 나타냅니다. |
| `topologySpreadConstraints` | 레이블이 `"workload=postgres"`인 다른 영역과 다른 노드가 필요합니다. |
| `resources` | *보장*의 QoS(서비스 품질) 클래스를 구성합니다. 프로덕션 환경에서 이러한 값은 기본 노드 VM의 사용량을 최대화하는 데 중요하며 사용되는 Azure VM SKU에 따라 달라집니다. |
| `bootstrap` | CNPG 운영자에게만 해당됩니다. 빈 앱 데이터베이스로 초기화합니다. |
| `storage` / `walStorage` | CNPG 운영자에게만 해당됩니다. 데이터 및 로그 스토리지를 위한 PVC(PertantVolumeClaim)용 스토리지 템플릿을 정의합니다. IOP 증가를 위해 분할할 테이블스페이스용 스토리지를 지정할 수도 있습니다. |
| `replicationSlots` | CNPG 운영자에게만 해당됩니다. 고가용성을 위해 복제 슬롯을 사용하도록 설정합니다. |
| `postgresql` | CNPG 운영자에게만 해당됩니다. `postgresql.conf`, `pg_hba.conf` 및 `pg_ident.conf config`에 대한 맵 설정입니다. |
| `serviceAccountTemplate` | 서비스 계정을 생성하고 AKS 페더레이션된 ID 자격 증명을 UAMI에 매핑하여 PostgreSQL 인스턴스를 호스팅하는 Pod에서 외부 Azure 리소스로 AKS 워크로드 ID 인증을 사용하도록 설정하는 데 필요한 템플릿이 포함되어 있습니다. |
| `barmanObjectStore` | CNPG 운영자에게만 해당됩니다. Azure Blob Storage 개체 저장소에 대한 인증을 위해 AKS 워크로드 ID를 사용하여 barman-cloud 도구 모음을 구성합니다. |

1. [`kubectl apply`][kubectl-apply] 명령을 사용하여 클러스터 CRD로 PostgreSQL 클러스터를 배포합니다.

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

1. [`kubectl get`][kubectl-get] 명령을 사용하여 기본 PostgreSQL 클러스터가 성공적으로 만들어졌는지 유효성을 검사합니다. CNPG 클러스터 CRD는 3개의 인스턴스를 지정했으며, 각 인스턴스가 복제를 위해 실행되고 조인되면 실행 중인 Pod를 확인하여 유효성을 검사할 수 있습니다. 세 인스턴스가 모두 온라인 상태가 되어 클러스터에 참가하는 데 시간이 걸릴 수 있으므로 인내심을 가지고 기다립니다.

    ```bash
    kubectl get pods --context $AKS_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    예제 출력

    ```output
    NAME                         READY   STATUS    RESTARTS   AGE
    pg-primary-cnpg-r8c7unrw-1   1/1     Running   0          4m25s
    pg-primary-cnpg-r8c7unrw-2   1/1     Running   0          3m33s
    pg-primary-cnpg-r8c7unrw-3   1/1     Running   0          2m49s
    ```

### Prometheus PodMonitor가 실행 중인지 유효성 검사

CNPG 운영자는 [Prometheus 커뮤니티 설치](#install-the-prometheus-podmonitors) 중에 만들어진 녹음/녹화 규칙을 사용하여 주 인스턴스에 대한 PodMonitor를 자동으로 만듭니다.

1. [`kubectl get`][kubectl-get] 명령을 사용하여 PodMonitor가 실행 중인지 유효성을 검사합니다.

    ```bash
    kubectl --namespace $PG_NAMESPACE \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        get podmonitors.monitoring.coreos.com \
        $PG_PRIMARY_CLUSTER_NAME \
        --output yaml
    ```

    예제 출력

    ```output
     kind: PodMonitor
     metadata:
      annotations:
        cnpg.io/operatorVersion: 1.23.1
    ...
    ```

관리되는 Prometheus용 Azure Monitor를 사용하는 경우 사용자 지정 그룹 이름을 사용하여 다른 Pod 모니터를 추가해야 합니다. 관리되는 Prometheus는 Prometheus 커뮤니티에서 CRD(사용자 지정 리소스 정의)를 선택하지 않습니다. 그룹 이름 외에 CRD는 동일합니다. 이를 통해 관리되는 Prometheus용 Pod 모니터가 커뮤니티 Pod 모니터를 사용하는 모니터와 병렬 존재할 수 있습니다. 관리되는 Prometheus를 사용하지 않는 경우 이 단계를 건너뛸 수 있습니다. 새 Pod 모니터를 만듭니다.

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

Pod 모니터가 만들어졌는지 확인합니다(그룹 이름 차이에 유의해야 함).

```bash
kubectl --namespace $PG_NAMESPACE \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    get podmonitors.azmonitoring.coreos.com \
    -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME \
    -o yaml
```

#### 옵션 A - Azure Monitor 작업 영역

Postgres 클러스터와 Pod 모니터를 배포한 후에는 Azure Monitor 작업 영역에서 Azure Portal을 사용하여 메트릭을 볼 수 있습니다.

:::image source="./media/deploy-postgresql-ha/prometheus-metrics.png" alt-text="Azure Monitor 작업 영역의 메트릭을 보여 주는 스크린샷" lightbox="./media/deploy-postgresql-ha/prometheus-metrics.png":::

#### 옵션 B - Managed Grafana

또는 Postgres 클러스터 및 Pod 모니터를 배포한 후 배포 스크립트로 만들어진 Managed Grafana 인스턴스에 메트릭 대시보드를 만들어 Azure Monitor 작업 영역으로 내보낸 메트릭을 시각화할 수 있습니다. Azure Portal을 통해 Managed Grafana에 액세스할 수 있습니다. 배포 스크립트에서 만들어진 Managed Grafana 인스턴스로 이동하고 여기에 표시된 대로 엔드포인트 링크를 클릭합니다.

:::image source="./media/deploy-postgresql-ha/grafana-metrics-1.png" alt-text="Azure Managed Grafana 인스턴스를 보여 주는 스크린샷" lightbox="./media/deploy-postgresql-ha/grafana-metrics-1.png":::

엔드포인트 링크를 클릭하면 Managed Grafana 인스턴스에서 대시보드를 만들 수 있는 새 브라우저 창이 열립니다. [Azure Monitor 데이터 원본 구성](../azure-monitor/visualize/grafana-plugin.md#configure-an-azure-monitor-data-source-plug-in) 지침에 따라 시각화를 추가하여 Postgres 클러스터에서 메트릭 대시보드를 만들 수 있습니다. 데이터 원본 연결을 설정한 후 기본 메뉴에서 데이터 원본 옵션을 클릭하면 다음과 같이 데이터 원본 연결에 대한 데이터 원본 옵션 집합이 표시됩니다.

:::image source="./media/deploy-postgresql-ha/grafana-metrics-2.png" alt-text="데이터 원본 옵션을 보여 주는 스크린샷" lightbox="./media/deploy-postgresql-ha/grafana-metrics-2.png":::

관리되는 Prometheus 옵션에서 대시보드 빌드 옵션을 클릭하여 대시보드 편집기를 엽니다. 편집기 창이 열리면 시각화 추가 옵션을 클릭한 다음 관리되는 Prometheus 옵션을 클릭하여 Postgres 클러스터에서 메트릭을 찾습니다. 시각화할 메트릭을 선택한 후 쿼리 실행 단추를 클릭하여 여기에 표시된 대로 시각화에 대한 데이터를 가져옵니다.

:::image source="./media/deploy-postgresql-ha/grafana-metrics-3.png" alt-text="생성 대시보드를 보여 주는 스크린샷." lightbox="./media/deploy-postgresql-ha/grafana-metrics-3.png":::

저장 단추를 클릭하여 대시보드에 패널을 추가합니다. 대시보드 편집기에서 추가 단추를 클릭하고 이 프로세스를 반복하여 다른 메트릭을 시각화함으로써 다른 패널을 추가할 수 있습니다. 메트릭 시각화를 추가하면 다음과 같은 모습이 됩니다.

:::image source="./media/deploy-postgresql-ha/grafana-metrics-4.png" alt-text="대시보드 저장을 보여 주는 스크린샷" lightbox="./media/deploy-postgresql-ha/grafana-metrics-4.png":::

대시보드를 저장하려면 저장 아이콘을 클릭합니다.

## 배포된 PostgreSQL 클러스터 검사

[`kubectl get`][kubectl-get] 명령을 사용하여 AKS 노드 세부 정보를 검색하여 PostgreSQL이 여러 가용성 영역에 분산되어 있는지 유효성을 검사합니다.

```bash
kubectl get nodes \
    --context $AKS_PRIMARY_CLUSTER_NAME \
    --namespace $PG_NAMESPACE \
    --output json | jq '.items[] | {node: .metadata.name, zone: .metadata.labels."failure-domain.beta.kubernetes.io/zone"}'
```

출력은 각 노드에 대해 표시된 가용성 영역이 포함된 다음 출력 예와 유사해야 합니다.

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

## PostgreSQL에 연결하고 샘플 데이터 세트 만들기

이 섹션에서는 테이블을 만들고 이전에 배포한 CNPG 클러스터 CRD에서 만들어진 앱 데이터베이스에 일부 데이터를 삽입합니다. 이 데이터를 사용하여 PostgreSQL 클러스터에 대한 백업 및 복원 작업의 유효성을 검사합니다.

* 다음 명령을 사용하여 테이블을 만들고 앱 데이터베이스에 데이터를 삽입합니다.

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

    다음 예와 유사하게 출력됩니다.

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
## PostgreSQL 읽기 전용 복제본에 연결

* PostgreSQL 읽기 전용 복제본에 연결하고 다음 명령을 사용하여 샘플 데이터 세트의 유효성을 검사합니다.

    ```bash
    kubectl cnpg psql --replica $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    ```sql
    #postgres=# 
    SELECT pg_is_in_recovery();
    ```

    예제 출력

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

    예제 출력

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

## Barman을 사용하여 주문형 및 예약된 PostgreSQL 백업 설정

1. 다음 명령을 사용하여 PostgreSQL 클러스터가 CNPG 클러스터 CRD에 지정된 Azure Storage 계정에 액세스할 수 있고 `Working WAL archiving`이 `OK`로 보고하는지 유효성을 검사합니다.

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    예제 출력

    ```output
    Continuous Backup status
    First Point of Recoverability:  Not Available
    Working WAL archiving:          OK
    WALs waiting to be archived:    0
    Last Archived WAL:              00000001000000000000000A   @   2024-07-09T17:18:13.982859Z
    Last Failed WAL:                -
    ```

1. [`kubectl apply`][kubectl-apply] 명령과 함께 YAML 파일을 사용하여 AKS 워크로드 ID 통합을 사용하는 Azure Storage에 주문형 백업을 배포합니다.

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

1. [`kubectl describe`][kubectl-describe] 명령을 사용하여 주문형 백업 상태의 유효성을 검사합니다.

    ```bash
    kubectl describe backup $BACKUP_ONDEMAND_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    예제 출력

    ```output
    Type    Reason     Age   From                   Message
     ----    ------     ----  ----                   -------
    Normal  Starting   6s    cloudnative-pg-backup  Starting backup for cluster pg-primary-cnpg-r8c7unrw
    Normal  Starting   5s    instance-manager       Backup started
    Normal  Completed  1s    instance-manager       Backup completed
    ```

1. 다음 명령을 사용하여 클러스터에 첫 번째 복구 지점이 있는지 유효성을 검사합니다.

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

    예제 출력

    ```output
    Continuous Backup status
    First Point of Recoverability:  2024-06-05T13:47:18Z
    Working WAL archiving:          OK
    ```

1. [`kubectl apply`][kubectl-apply] 명령과 함께 YAML 파일을 사용하여 *매시 15분*에 대한 예약된 백업을 구성합니다.

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

1. [`kubectl describe`][kubectl-describe] 명령을 사용하여 예약된 백업 상태의 유효성을 검사합니다.

    ```bash
    kubectl describe scheduledbackup $BACKUP_SCHEDULED_NAME \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. [`az storage blob list`][az-storage-blob-list] 명령을 사용하여 기본 클러스터의 Azure Blob Storage에 저장된 백업 파일을 봅니다.

    ```bash
    az storage blob list \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --container-name backups \
        --query "[*].name" \
        --only-show-errors 
    ```

    출력은 백업이 성공했는지 유효성을 검사하는 다음 출력 예와 유사해야 합니다.

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

## 새 PostgreSQL 클러스터로 주문형 백업 복원

이 섹션에서는 이전에 CNPG 연산자를 사용하여 만든 주문형 백업을 부트스트랩 클러스터 CRD를 사용하여 새 인스턴스로 복원합니다. 단순화를 위해 단일 인스턴스 클러스터가 사용됩니다. CNPG InheritFromAzureAD를 통한 AKS 워크로드 ID는 백업 파일에 액세스하고 복구 클러스터 이름은 복구 클러스터와 관련된 새 Kubernetes Service 계정을 생성하는 데 사용된다는 점에 유념해야 합니다.

또한 Blob Storage의 백업 파일에 대한 "Storage Blob 데이터 기여자" 액세스 권한이 있는 기존 UAMI에 새 복구 클러스터 서비스 계정을 매핑하기 위한 두 번째 페더레이션된 자격 증명도 만듭니다.

1. [`az identity federated-credential create`][az-identity-federated-credential-create] 명령을 사용하여 두 번째 페더레이션된 ID 자격 증명을 만듭니다.

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

1. [`kubectl apply`][kubectl-apply] 명령으로 클러스터 CRD를 사용하여 주문형 백업을 복원합니다.

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

1. 복구된 인스턴스에 연결한 후 다음 명령을 사용하여 전체 백업이 수행된 원래 클러스터에 만들어진 데이터 세트가 있는지 유효성을 검사합니다.

    ```bash
    kubectl cnpg psql $PG_PRIMARY_CLUSTER_NAME_RECOVERED --namespace $PG_NAMESPACE
    ```

    ```sql
    postgres=# SELECT COUNT(*) FROM datasample;
    ```

    예제 출력

    ```output
    # count
    #-------
    #     3
    #(1 row)

    # Type \q to exit psql
    ```

1. 다음 명령을 사용하여 복구된 클러스터를 삭제합니다.

    ```bash
    kubectl cnpg destroy $PG_PRIMARY_CLUSTER_NAME_RECOVERED 1 \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE
    ```

1. [`az identity federated-credential delete`][az-identity-federated-credential-delete] 명령을 사용하여 페더레이션된 ID 자격 증명을 삭제합니다.

    ```bash
    az identity federated-credential delete \
        --name $PG_PRIMARY_CLUSTER_NAME_RECOVERED \
        --identity-name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --yes
    ```

## 공용 부하 분산 장치를 사용하여 PostgreSQL 클러스터 노출

이 섹션에서는 IP 원본 제한이 있는 PostgreSQL 읽기-쓰기 및 읽기 전용 엔드포인트를 클라이언트 워크스테이션의 공용 IP 주소에 공개적으로 노출하는 데 필요한 인프라를 구성합니다.

또한 클러스터 IP 서비스에서 다음 엔드포인트를 검색합니다.

* `*-rw`로 끝나는 *1개의* 기본 읽기-쓰기 엔드포인트입니다.
* *0에서 N*(복제본 수에 따라 다름)은 `*-ro`로 끝나는 읽기 전용 엔드포인트입니다.
* `*-r`로 끝나는 *1개의* 복제 엔드포인트입니다.

1. [`kubectl get`][kubectl-get] 명령을 사용하여 클러스터 IP 서비스 세부 정보를 가져옵니다.

    ```bash
    kubectl get services \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_NAMESPACE \
        -l cnpg.io/cluster=$PG_PRIMARY_CLUSTER_NAME
    ```

    예제 출력

    ```output
    NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
    pg-primary-cnpg-sryti1qf-r    ClusterIP   10.0.193.27    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-ro   ClusterIP   10.0.237.19    <none>        5432/TCP   3h57m
    pg-primary-cnpg-sryti1qf-rw   ClusterIP   10.0.244.125   <none>        5432/TCP   3h57m
    ```

    > [!NOTE]
    > 포트 5433에 매핑된 `namespace/cluster-name-ro`, 포트 5433에 매핑된 `namespace/cluster-name-rw` 및 `namespace/cluster-name-r`의 세 가지 서비스가 있습니다. PostgreSQL 데이터베이스 클러스터의 읽기/쓰기 노드와 동일한 포트를 사용하지 않아야 합니다. 애플리케이션이 PostgreSQL 데이터베이스 클러스터의 읽기 전용 복제본에만 액세스하도록 하려면 포트 5433으로 연결합니다. 최종 서비스는 일반적으로 데이터 백업에 사용되지만 읽기 전용 노드로도 작동할 수 있습니다.

1. [`kubectl get`][kubectl-get] 명령을 사용하여 서비스 세부 정보를 가져옵니다.

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

1. [`kubectl apply`][kubectl-apply] 명령을 사용하여 다음 YAML 파일로 부하 분산 장치 서비스를 구성합니다.

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

1. [`kubectl describe`][kubectl-describe] 명령을 사용하여 서비스 세부 정보를 가져옵니다.

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

### 공용 PostgreSQL 엔드포인트 유효성 검사

이 섹션에서는 이전에 만든 고정 IP와 기본 읽기-쓰기 및 읽기 전용 복제본에 대한 라우팅 연결을 사용하여 Azure Load Balancer가 올바르게 설정되었는지 유효성을 검사하고 psql CLI를 사용하여 둘 다에 연결합니다.

기본 읽기-쓰기 엔드포인트는 TCP 포트 5432에 매핑되고 읽기 전용 복제본 엔드포인트는 포트 5433에 매핑되어 동일한 PostgreSQL DNS 이름을 읽기 권한자와 기록기에 사용할 수 있다는 점에 유념해야 합니다.

> [!NOTE]
> 이전에 생성되어 `$PG_DATABASE_APPUSER_SECRET` 환경 변수에 저장된 PostgreSQL 기본 인증을 위한 앱 사용자 암호 값이 필요합니다.

* 다음 `psql` 명령을 사용하여 공용 PostgreSQL 엔드포인트의 유효성을 검사합니다.

    ```bash
    echo "Public endpoint for PostgreSQL cluster: $AKS_PRIMARY_CLUSTER_ALB_DNSNAME"

    # Query the primary, pg_is_in_recovery = false
    
    psql -h $AKS_PRIMARY_CLUSTER_ALB_DNSNAME \
        -p 5432 -U app -d appdb -W -c "SELECT pg_is_in_recovery();"
    ```

    예제 출력

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

    예제 출력

    ```output
    # Example output
    
    pg_is_in_recovery
    -------------------
    t
    (1 row)
    ```

    기본 읽기-쓰기 엔드포인트에 성공적으로 연결되면 PostgreSQL 함수는 *false*에 대해 `f`를 반환하여 현재 연결이 쓰기 가능함을 나타냅니다.

    복제본에 연결되면 함수는 *true*에 대해 `t`를 반환합니다. 이는 데이터베이스가 복구 중이고 읽기 전용임을 나타냅니다.

## 계획되지 않은 장애 조치(failover) 시뮬레이션

이 섹션에서는 기본을 실행하는 Pod를 삭제하여 갑자스런 실패를 트리거합니다. 이는 PostgreSQL 기본을 호스팅하는 노드에 대한 갑작스런 크래시 또는 네트워크 연결 손실을 시뮬레이션합니다.

1. 다음 명령을 사용하여 실행 중인 Pod 인스턴스의 상태를 확인합니다.

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    예제 출력

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. [`kubectl delete`][kubectl-delete] 명령을 사용하여 기본 Pod를 삭제합니다.

    ```bash
    PRIMARY_POD=$(kubectl get pod \
        --namespace $PG_NAMESPACE \
        --no-headers \
        -o custom-columns=":metadata.name" \
        -l role=primary)
    
    kubectl delete pod $PRIMARY_POD --grace-period=1 --namespace $PG_NAMESPACE
    ```

1. 다음 명령을 사용하여 이제 `pg-primary-cnpg-sryti1qf-2` Pod 인스턴스가 기본 인스턴스인지 유효성을 검사합니다.

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    예제 출력

    ```output
    pg-primary-cnpg-sryti1qf-2  0/9000060   Primary         OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-1  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

1. 다음 명령을 사용하여 `pg-primary-cnpg-sryti1qf-1` Pod 인스턴스를 기본 인스턴스로 다시 설정합니다.

    ```bash
    kubectl cnpg promote $PG_PRIMARY_CLUSTER_NAME 1 --namespace $PG_NAMESPACE
    ```

1. 다음 명령을 사용하여 계획되지 않은 장애 조치(failover) 테스트 전에 Pod 인스턴스가 원래 상태로 돌아왔는지 유효성을 검사합니다.

    ```bash
    kubectl cnpg status $PG_PRIMARY_CLUSTER_NAME --namespace $PG_NAMESPACE
    ```

    예제 출력

    ```output
    Name                        Current LSN Rep role        Status  Node
    --------------------------- ----------- --------        ------- -----------
    pg-primary-cnpg-sryti1qf-1  0/9000060   Primary         OK      aks-postgres-32388626-vmss000000
    pg-primary-cnpg-sryti1qf-2  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000001
    pg-primary-cnpg-sryti1qf-3  0/9000060   Standby (sync)  OK      aks-postgres-32388626-vmss000002
    ```

## 리소스 정리

* 배포 검토를 마쳤으면 [`az group delete`][az-group-delete] 명령을 사용하여 이 가이드에서 만든 모든 리소스를 삭제합니다.

    ```bash
    az group delete --resource-group $RESOURCE_GROUP_NAME --no-wait --yes
    ```

## 다음 단계

이 방법 가이드에서는 다음 작업 방법을 배웁니다.

* Azure CLI를 사용하여 다중 영역 AKS 클러스터를 만듭니다.
* CNPG 연산자를 사용하여 고가용성 PostgreSQL 클러스터 및 데이터베이스를 배포합니다.
* Prometheus 및 Grafana를 사용하여 PostgreSQL에 대한 모니터링을 설정합니다.
* PostgreSQL 데이터베이스에 샘플 데이터 세트를 배포합니다.
* PostgreSQL 및 AKS 클러스터 업그레이드를 수행합니다.
* 클러스터 중단 및 PostgreSQL 복제본 장애 조치(failover)를 시뮬레이션합니다.
* PostgreSQL 데이터베이스의 백업 및 복원을 수행합니다.

워크로드에 AKS를 활용하는 방법에 대해 자세히 알아보려면 [AKS(Azure Kubernetes Service)란?][what-is-aks]을 참조하세요.

## 참가자

*이 문서는 Microsoft에서 유지 관리합니다. 원래 다음 기여자가 작성했습니다.*

* Ken Kilty | 수석 TPM
* Russell de Pina | 수석 TPM
* Adrian Joian | 선임 고객 엔지니어
* Jenny Hayes | 선임 콘텐츠 개발자
* Carol Smith | 선임 콘텐츠 개발자
* Erin Schaffer | 콘텐츠 개발자 2
* Adam Sharif | 고객 엔지니어 2

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
