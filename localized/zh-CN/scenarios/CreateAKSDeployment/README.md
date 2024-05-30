---
title: 快速入门：使用 Azure CLI 部署 Azure Kubernetes 服务 (AKS) 群集
description: 了解如何使用 Azure CLI 快速部署 Kubernetes 群集和在 Azure Kubernetes 服务 (AKS) 中部署应用程序。
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# 快速入门：使用 Azure CLI 部署 Azure Kubernetes 服务 (AKS) 群集

[![部署到 Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes 服务 (AKS) 是可用于快速部署和管理群集的托管式 Kubernetes 服务。 此快速入门介绍如何：

- 使用 Azure CLI 部署 AKS 群集。
- 使用一组微服务和模拟零售场景的 Web 前端运行示例多容器应用程序。

> [!NOTE]
> 为了开始快速预配 AKS 群集，本文介绍了仅针对评估目的部署具有默认设置的群集的步骤。 在部署生产就绪群集之前，建议熟悉我们的[基线参考体系结构][baseline-reference-architecture]，考虑它如何与你的业务需求保持一致。

## 开始之前

本快速入门假设读者基本了解 Kubernetes 的概念。 有关详细信息，请参阅 [Azure Kubernetes 服务 (AKS) 的 Kubernetes 核心概念][kubernetes-concepts]。

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- 本文需要 Azure CLI 版本 2.0.64 或更高版本。 如果你使用的是 Azure Cloud Shell，则表示已安装最新版本。
- 确保用于创建群集的标识具有合适的的最低权限。 有关 AKS 访问和标识的详细信息，请参阅 [Azure Kubernetes Service (AKS) 的访问和标识选项](../concepts-identity.md)。
- 如果有多个 Azure 订阅，请使用 [az account set](/cli/azure/account#az-account-set) 命令选择应在其中计收资源费用的相应订阅 ID。

## 定义环境变量

定义在本快速入门中使用的以下环境变量：

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## 创建资源组

[Azure 资源组][azure-resource-group]是用于部署和管理 Azure 资源的逻辑组。 创建资源组时，系统会提示你指定一个位置。 此位置是资源组元数据的存储位置，也是资源在 Azure 中运行的位置（如果你在创建资源期间未指定其他区域）。

使用 [`az group create`][az-group-create] 命令创建资源组。

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

结果：
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

## 创建 AKS 群集

使用 [`az aks create`][az-aks-create] 命令创建 AKS 群集。 以下示例使用一个节点创建一个群集，并启用系统分配的托管标识。

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> 当你创建新群集时，AKS 会自动创建第二个资源组来存储 AKS 资源。 有关详细信息，请参阅[为什么使用 AKS 创建两个资源组？](../faq.md#why-are-two-resource-groups-created-with-aks)

## 连接到群集

若要管理 Kubernetes 群集，请使用 Kubernetes 命令行客户端 [kubectl][kubectl]。 如果使用的是 Azure Cloud Shell，则 `kubectl` 已安装。 若要在本地安装 `kubectl`，请使用 [`az aks install-cli`][az-aks-install-cli] 命令。

1. 使用 [az aks get-credentials][az-aks-get-credentials] 命令将 `kubectl` 配置为连接到你的 Kubernetes 群集。 此命令将下载凭据，并将 Kubernetes CLI 配置为使用这些凭据。

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. 使用 [kubectl get][kubectl-get] 命令验证与群集之间的连接。 此命令将返回群集节点的列表。

    ```azurecli-interactive
    kubectl get nodes
    ```

## 部署应用程序

若要部署应用程序，请使用清单文件创建运行 [AKS 应用商店应用程序](https://github.com/Azure-Samples/aks-store-demo)所需的所有对象。 [Kubernetes 清单文件][kubernetes-deployment]定义群集的所需状态，例如，要运行哪些容器映像。 该清单包含以下 Kubernetes 部署和服务：

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Azure 应用商店示例体系结构的屏幕截图。" lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- 门店：Web 应用程序，供客户查看产品和下单。
- 产品服务：显示产品信息。
- 订单服务：下单。
- Rabbit MQ：订单队列的消息队列。

> [!NOTE]
> 不建议在没有持久性存储用于生产的情况下，运行有状态容器（例如 Rabbit MQ）。 为简单起见，建议使用托管服务，例如 Azure CosmosDB 或 Azure 服务总线。

1. 创建名为 `aks-store-quickstart.yaml` 的文件，并将以下清单复制到其中：

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

    有关 YAML 清单文件的明细，请参阅[部署和 YAML 清单](../concepts-clusters-workloads.md#deployments-and-yaml-manifests)。

    如果在本地创建并保存 YAML 文件，则可以通过选择“**上传/下载文件**”按钮并从本地文件系统中选择文件，将清单文件上传到 CloudShell 中的默认目录。

1. 使用 [`kubectl apply`][kubectl-apply] 命令部署应用程序，并指定 YAML 清单的名称。

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## 测试应用程序

可以通过访问公共 IP 地址或应用程序 URL 来验证应用程序是否正在运行。

使用以下命令来获取应用程序 URL：

```azurecli-interactive
runtime="5 minutes"
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

结果：
<!-- expected_similarity=0.3 -->
```HTML
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

```output
echo "You can now visit your web server at $IP_ADDRESS"
```

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="AKS 应用商店示例应用程序的屏幕截图。" lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## 删除群集

如果不打算完成 [AKS 教程][aks-tutorial]，请清理不必要的资源以避免产生 Azure 费用。 可以使用 [`az group delete`][az-group-delete] 命令删除资源组、容器服务和所有相关资源。

> [!NOTE]
> AKS 群集是使用系统分配的托管标识创建的，这是本快速入门中使用的默认标识选项。 平台将负责管理此标识，因此你无需手动删除它。

## 后续步骤

在本快速入门中，你部署了一个 Kubernetes 群集，然后在其中部署了示例多容器应用程序。 此示例应用程序仅用于演示目的，并未展示出 Kubernetes 应用程序的所有最佳做法。 有关使用生产版 AKS 创建完整解决方案的指南，请参阅 [AKS 解决方案指南][aks-solution-guidance]。

若要详细了解 AKS 并演练完整的代码到部署示例，请继续阅读 Kubernetes 群集教程。

> [!div class="nextstepaction"]
> [AKS 教程][aks-tutorial]

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
