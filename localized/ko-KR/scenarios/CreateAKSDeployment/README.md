---
title: '빠른 시작: Azure CLI를 사용하여 AKS(Azure Kubernetes Service) 클러스터 배포'
description: Azure CLI를 사용하여 Kubernetes 클러스터를 빠르게 배포하고 AKS(Azure Kubernetes Service)에서 애플리케이션을 배포하는 방법을 알아봅니다.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# 빠른 시작: Azure CLI를 사용하여 AKS(Azure Kubernetes Service) 클러스터 배포

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

AKS(Azure Kubernetes Service)는 클러스터를 빠르게 배포하고 관리할 수 있는 관리형 Kubernetes 서비스입니다. 이 빠른 시작에서 다음을 수행하는 방법을 알아봅니다.

- Azure CLI를 사용하여 AKS 클러스터를 배포합니다.
- 소매 시나리오를 시뮬레이션하는 마이크로 서비스 및 웹 프런트 엔드 그룹을 사용하여 샘플 다중 컨테이너 애플리케이션을 실행합니다.

> [!NOTE]
> AKS 클러스터 프로비전을 빠르게 시작하기 위해 이 문서에는 평가 목적으로만 기본 설정으로 클러스터를 배포하는 단계가 포함되어 있습니다. 프로덕션에 즉시 사용 가능한 클러스터를 배포하기 전에 [기본 참조 아키텍처][baseline-reference-architecture]를 숙지하여 비즈니스 요구 사항에 어떻게 부합하는지 고려하는 것이 좋습니다.

## 시작하기 전에

이 빠른 시작에서는 Kubernetes 기본 개념을 이해하고 있다고 가정합니다. 자세한 내용은 [AKS(Azure Kubernetes Service)의 Kubernetes 핵심 개념][kubernetes-concepts]을 참조하세요.

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- 이 문서에는 Azure CLI 버전 2.0.64 이상이 필요합니다. Azure Cloud Shell을 사용하는 경우 최신 버전이 이미 설치되어 있습니다.
- 클러스터를 만드는 데 사용하는 ID에 적절한 최소 권한이 있는지 확인합니다. AKS의 액세스 및 ID에 대한 자세한 내용은 [AKS(Azure Kubernetes Service)에 대한 액세스 및 ID 옵션](../concepts-identity.md)을 참조하세요.
- Azure 구독이 여러 개인 경우 [az account set](/cli/azure/account#az-account-set) 명령을 사용하여 리소스가 청구되어야 하는 적절한 구독 ID를 선택합니다.

## 환경 변수 정의

이 빠른 시작 전체에서 사용할 다음 환경 변수를 정의합니다.

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## 리소스 그룹 만들기

[Azure 리소스 그룹][azure-resource-group]은 Azure 리소스가 배포되고 관리되는 논리 그룹입니다. 리소스 그룹을 만들 때 위치를 지정하라는 메시지가 표시됩니다. 이 위치는 리소스 그룹 메타데이터의 스토리지 위치이며 리소스를 만드는 중에 다른 지역을 지정하지 않은 경우 Azure에서 리소스가 실행되는 위치입니다.

[`az group create`][az-group-create] 명령을 사용하여 리소스 그룹을 만듭니다.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:
<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## AKS 클러스터 만들기

[`az aks create`][az-aks-create] 명령을 사용하여 AKS 클러스터를 만듭니다. 다음 예에서는 노드가 1개 있는 클러스터를 만들고 시스템 할당 관리 ID를 사용하도록 설정합니다.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> 새 클러스터를 만들면 AKS는 AKS 리소스를 저장할 두 번째 리소스 그룹을 자동으로 만듭니다. 자세한 내용은 [AKS를 통해 두 개의 리소스 그룹이 생성되는 이유는 무엇인가요?](../faq.md#why-are-two-resource-groups-created-with-aks)를 참조하세요.

## 클러스터에 연결

Kubernetes 클러스터를 관리하려면 Kubernetes 명령줄 클라이언트인 [kubectl][kubectl]을 사용합니다. Azure Cloud Shell을 사용하는 경우 `kubectl`이 이미 설치되어 있습니다. `kubectl`을 로컬로 설치하려면 [`az aks install-cli`][az-aks-install-cli] 명령을 사용합니다.

1. [az aks get-credentials][az-aks-get-credentials] 명령을 사용하여 Kubernetes 클러스터에 연결하도록 `kubectl`을 구성합니다. 이 명령은 자격 증명을 다운로드하고 Kubernetes CLI가 해당 자격 증명을 사용하도록 구성합니다.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. [kubectl get][kubectl-get] 명령을 사용하여 클러스터에 대한 연결을 확인합니다. 이 명령은 클러스터 노드 목록을 반환합니다.

    ```azurecli-interactive
    kubectl get nodes
    ```

## 애플리케이션 배포

응용 프로그램을 배포하려면 매니페스트 파일을 사용하여 [AKS Store 응용 프로그램](https://github.com/Azure-Samples/aks-store-demo)을 실행하는 데 필요한 모든 개체를 만듭니다. [Kubernetes 매니페스트 파일][kubernetes-deployment]은 실행할 컨테이너 이미지와 같은 클러스터에 대해 원하는 상태를 정의합니다. 매니페스트에는 다음 Kubernetes 배포 및 서비스가 포함됩니다.

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Azure Store 샘플 아키텍처의 스크린샷." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **스토어 프런트**: 고객이 제품을 보고 주문을 할 수 있는 웹 애플리케이션입니다.
- **제품 서비스**: 제품 정보를 표시합니다.
- **주문 서비스**: 주문을 합니다.
- **Rabbit MQ**: 주문 큐에 대한 메시지 큐입니다.

> [!NOTE]
> 프로덕션을 위한 영구 스토리지 없이 Rabbit MQ와 같은 상태 저장 컨테이너를 실행하지 않는 것이 좋습니다. 여기서는 단순화를 위해 사용되었지만 Azure CosmosDB 또는 Azure Service Bus와 같은 관리되는 서비스를 사용하는 것이 좋습니다.

1. 파일 `aks-store-quickstart.yaml`을 만들고 다음 매니페스트에 복사합니다.

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: rabbitmq
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: rabbitmq
      template:
        metadata:
          labels:
            app: rabbitmq
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: rabbitmq
            image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine
            ports:
            - containerPort: 5672
              name: rabbitmq-amqp
            - containerPort: 15672
              name: rabbitmq-http
            env:
            - name: RABBITMQ_DEFAULT_USER
              value: "username"
            - name: RABBITMQ_DEFAULT_PASS
              value: "password"
            resources:
              requests:
                cpu: 10m
                memory: 128Mi
              limits:
                cpu: 250m
                memory: 256Mi
            volumeMounts:
            - name: rabbitmq-enabled-plugins
              mountPath: /etc/rabbitmq/enabled_plugins
              subPath: enabled_plugins
          volumes:
          - name: rabbitmq-enabled-plugins
            configMap:
              name: rabbitmq-enabled-plugins
              items:
              - key: rabbitmq_enabled_plugins
                path: enabled_plugins
    ---
    apiVersion: v1
    data:
      rabbitmq_enabled_plugins: |
        [rabbitmq_management,rabbitmq_prometheus,rabbitmq_amqp1_0].
    kind: ConfigMap
    metadata:
      name: rabbitmq-enabled-plugins
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: rabbitmq
    spec:
      selector:
        app: rabbitmq
      ports:
        - name: rabbitmq-amqp
          port: 5672
          targetPort: 5672
        - name: rabbitmq-http
          port: 15672
          targetPort: 15672
      type: ClusterIP
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: order-service
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: order-service
      template:
        metadata:
          labels:
            app: order-service
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: order-service
            image: ghcr.io/azure-samples/aks-store-demo/order-service:latest
            ports:
            - containerPort: 3000
            env:
            - name: ORDER_QUEUE_HOSTNAME
              value: "rabbitmq"
            - name: ORDER_QUEUE_PORT
              value: "5672"
            - name: ORDER_QUEUE_USERNAME
              value: "username"
            - name: ORDER_QUEUE_PASSWORD
              value: "password"
            - name: ORDER_QUEUE_NAME
              value: "orders"
            - name: FASTIFY_ADDRESS
              value: "0.0.0.0"
            resources:
              requests:
                cpu: 1m
                memory: 50Mi
              limits:
                cpu: 75m
                memory: 128Mi
          initContainers:
          - name: wait-for-rabbitmq
            image: busybox
            command: ['sh', '-c', 'until nc -zv rabbitmq 5672; do echo waiting for rabbitmq; sleep 2; done;']
            resources:
              requests:
                cpu: 1m
                memory: 50Mi
              limits:
                cpu: 75m
                memory: 128Mi
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: order-service
    spec:
      type: ClusterIP
      ports:
      - name: http
        port: 3000
        targetPort: 3000
      selector:
        app: order-service
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: product-service
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: product-service
      template:
        metadata:
          labels:
            app: product-service
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: product-service
            image: ghcr.io/azure-samples/aks-store-demo/product-service:latest
            ports:
            - containerPort: 3002
            resources:
              requests:
                cpu: 1m
                memory: 1Mi
              limits:
                cpu: 1m
                memory: 7Mi
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: product-service
    spec:
      type: ClusterIP
      ports:
      - name: http
        port: 3002
        targetPort: 3002
      selector:
        app: product-service
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: store-front
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: store-front
      template:
        metadata:
          labels:
            app: store-front
        spec:
          nodeSelector:
            "kubernetes.io/os": linux
          containers:
          - name: store-front
            image: ghcr.io/azure-samples/aks-store-demo/store-front:latest
            ports:
            - containerPort: 8080
              name: store-front
            env:
            - name: VUE_APP_ORDER_SERVICE_URL
              value: "http://order-service:3000/"
            - name: VUE_APP_PRODUCT_SERVICE_URL
              value: "http://product-service:3002/"
            resources:
              requests:
                cpu: 1m
                memory: 200Mi
              limits:
                cpu: 1000m
                memory: 512Mi
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: store-front
    spec:
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: store-front
      type: LoadBalancer
    ```

    YAML 매니페스트 파일의 분석은 [배포 및 YAML 매니페스트](../concepts-clusters-workloads.md#deployments-and-yaml-manifests)를 참조하세요.

    YAML 파일을 로컬에서 만들고 저장하는 경우 **파일 업로드/다운로드** 단추를 선택하고 로컬 파일 시스템에서 파일을 선택하여 매니페스트 파일을 CloudShell의 기본 디렉터리에 업로드할 수 있습니다.

1. [`kubectl apply`][kubectl-apply] 명령을 사용하여 애플리케이션을 배포하고 YAML 매니페스트의 이름을 지정합니다.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## 애플리케이션 테스트

공용 IP 주소 또는 애플리케이션 URL을 방문하여 애플리케이션이 실행 중인지 유효성을 검사할 수 있습니다.

다음 명령을 사용하여 애플리케이션 URL을 가져옵니다.

```azurecli-interactive
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]
do
   STATUS=$(kubectl get pods -l app=store-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}')
   echo $STATUS
   if [ "$STATUS" == 'True' ]
   then
      export IP_ADDRESS=$(kubectl get service store-front --output 'jsonpath={..status.loadBalancer.ingress[0].ip}')
      echo "Service IP Address: $IP_ADDRESS"
      break
   else
      sleep 10
   fi
done
```

```azurecli-interactive
curl $IP_ADDRESS
```

Results:
<!-- expected_similarity=0.3 -->
```JSON
<!doctype html>
<html lang="">
   <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <link rel="icon" href="/favicon.ico">
      <title>store-front</title>
      <script defer="defer" src="/js/chunk-vendors.df69ae47.js"></script>
      <script defer="defer" src="/js/app.7e8cfbb2.js"></script>
      <link href="/css/app.a5dc49f6.css" rel="stylesheet">
   </head>
   <body>
      <div id="app"></div>
   </body>
</html>
```

```JSON
echo "You can now visit your web server at $IP_ADDRESS"
```

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="AKS 스토어 샘플 애플리케이션의 스크린샷." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## 클러스터 삭제

[AKS 자습서][aks-tutorial]를 진행할 계획이 없다면 불필요한 리소스를 정리하여 Azure 요금이 청구되지 않도록 합니다. [`az group delete`][az-group-delete] 명령을 사용하여 리소스 그룹, 컨테이너 서비스 및 모든 관련 리소스를 제거할 수 있습니다.

> [!NOTE]
> AKS 클러스터는 이 빠른 시작에서 사용되는 기본 ID 옵션인 시스템이 할당한 관리 ID를 사용하여 만들어졌습니다. 플랫폼이 이 ID를 관리하므로 수동으로 제거할 필요가 없습니다.

## 다음 단계

이 빠른 시작에서는 Kubernetes 클러스터를 배포한 다음, 해당 클러스터에 간단한 다중 컨테이너 애플리케이션을 배포했습니다. 이 샘플 응용 프로그램은 데모 목적으로만 사용되며 Kubernetes 응용 프로그램에 대한 모든 모범 사례를 나타내지는 않습니다. 프로덕션용 AKS를 사용하여 전체 솔루션을 만드는 방법에 대한 지침은 [AKS 솔루션 지침][aks-solution-guidance]을 참조하세요.

AKS에 대해 자세히 알아보고 배포 예제에 대한 전체 코드를 연습해 보려면 Kubernetes 클러스터 자습서를 계속 진행합니다.

> [!div class="nextstepaction"]
> [AKS 자습서][aks-tutorial]

<!-- LINKS - external -->
[kubectl]: https://kubernetes.io/docs/reference/kubectl/
[kubectl-apply]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
[kubectl-get]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get

<!-- LINKS - internal -->
[kubernetes-concepts]: ../concepts-clusters-workloads.md
[aks-tutorial]: ../tutorial-kubernetes-prepare-app.md
[azure-resource-group]: ../../azure-resource-manager/management/overview.md
[az-aks-create]: /cli/azure/aks#az-aks-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-aks-install-cli]: /cli/azure/aks#az-aks-install-cli
[az-group-create]: /cli/azure/group#az-group-create
[az-group-delete]: /cli/azure/group#az-group-delete
[kubernetes-deployment]: ../concepts-clusters-workloads.md#deployments-and-yaml-manifests
[aks-solution-guidance]: /azure/architecture/reference-architectures/containers/aks-start-here?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json
[baseline-reference-architecture]: /azure/architecture/reference-architectures/containers/aks/baseline-aks?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json