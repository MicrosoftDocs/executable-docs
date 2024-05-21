---
title: 'クイック スタート: Azure CLI を使用して Azure Kubernetes Service (AKS) クラスターをデプロイする'
description: Azure CLI を使用して Kubernetes クラスターのデプロイ、および Azure Kubernetes Service (AKS) でのアプリケーションのデプロイを、迅速に行う方法を学習します。
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# クイック スタート: Azure CLI を使用して Azure Kubernetes Service (AKS) クラスターをデプロイする

[![Azure に配置する](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) は、クラスターをすばやくデプロイおよび管理することができる、マネージド Kubernetes サービスです。 このクイックスタートでは、次の方法について説明します。

- Azure CLI を使用して AKS クラスターをデプロイします。
- マイクロサービスのグループと、小売シナリオをシミュレートする Web フロントエンドを使用して、サンプルのマルチコンテナー アプリケーションを実行します。

> [!NOTE]
> AKS クラスターの迅速なプロビジョニングを開始するため、この記事には、評価のみを目的とした既定の設定でクラスターをデプロイする手順が含まれています。 運用環境に対応したクラスターをデプロイする前に、[ベースライン参照アーキテクチャ][baseline-reference-architecture]を理解して、ビジネス要件にどの程度合致しているかを検討することをお勧めします。

## 開始する前に

このクイックスタートは、Kubernetes の基本的な概念を理解していることを前提としています。 詳細については、「[Azure Kubernetes Services (AKS) における Kubernetes の中心概念][kubernetes-concepts]」を参照してください。

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- この記事では、Azure CLI のバージョン 2.0.64 以降が必要です。 Azure Cloud Shell を使用している場合は、最新バージョンが既にインストールされています。
- クラスターの作成に使用している ID に、適切な最小限のアクセス許可が与えられていることを確認します。 AKS のアクセスと ID の詳細については、「[Azure Kubernetes Service (AKS) でのアクセスと ID オプション](../concepts-identity.md)」を参照してください。
- 複数の Azure サブスクリプションをお持ちの場合は、[az account set](/cli/azure/account#az-account-set) コマンドを使用して、リソースが課金の対象となる適切なサブスクリプション ID を選択してください。

## 環境変数を定義する

このクイックスタート全体で使用するために、以下の環境変数を定義します。

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## リソース グループを作成する

[Azure リソース グループ][azure-resource-group]は、Azure リソースが展開され管理される論理グループです。 リソース グループを作成する際は、場所の指定を求めるプロンプトが表示されます。 この場所は、リソース グループのメタデータが格納される場所です。また、リソースの作成時に別のリージョンを指定しない場合は、Azure でリソースが実行される場所でもあります。

[`az group create`][az-group-create] コマンドを使用して、リソース グループを作成します。

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

結果:
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

## AKS クラスターを作成する

[`az aks create`][az-aks-create] コマンドを使用して、AKS クラスターを作成します。 次の例では、1 つのノードを含むクラスターを作成し、システム割り当てマネージド ID を有効にします。

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> 新しいクラスターを作成すると、AKS リソースを保存するための 2 つ目のリソース グループが自動的に作成されます。 詳細については、「[AKS と一緒にリソース グループが 2 つ作成されるのはなぜでしょうか?](../faq.md#why-are-two-resource-groups-created-with-aks)」を参照してください。

## クラスターに接続する

Kubernetes クラスターを管理するには、Kubernetes のコマンドライン クライアントである [kubectl][kubectl] を使います。 Azure Cloud Shell を使用している場合、`kubectl` は既にインストールされています。 `kubectl` をローカルにインストールするには、[`az aks install-cli`][az-aks-install-cli] コマンドを使用します。

1. [az aks get-credentials][az-aks-get-credentials] コマンドを使用して、Kubernetes クラスターに接続するように `kubectl` を構成します。 このコマンドは、資格情報をダウンロードし、それを使用するように Kubernetes CLI を構成します。

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. [kubectl get][kubectl-get] コマンドを使用して、ご利用のクラスターへの接続を確認します。 このコマンドでは、クラスター ノードの一覧が返されます。

    ```azurecli-interactive
    kubectl get nodes
    ```

## アプリケーションを展開する

アプリケーションをデプロイするには、マニフェスト ファイルを使用して、[AKS ストア アプリケーション](https://github.com/Azure-Samples/aks-store-demo)の実行に必要なすべてのオブジェクトを作成します。 [Kubernetes のマニフェスト ファイル][kubernetes-deployment]では、どのコンテナー イメージを実行するかなど、クラスターの望ましい状態を定義します。 マニフェストには、次の Kubernetes のデプロイとサービスが含まれています。

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Azure Store サンプル アーキテクチャのスクリーンショット。" lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **ネットショップ**: 顧客が製品を見て注文するための Web アプリケーション。
- **製品サービス**: 製品情報が表示されます。
- **注文サービス**: 注文を行います。
- **Rabbit MQ**: 注文キューのメッセージ キュー。

> [!NOTE]
> 運用環境の永続ストレージを使用せずに Rabbit MQ などのステートフル コンテナーを実行することはお勧めしません。 これらはわかりやすくするためにここで使用しますが、Azure CosmosDB や Azure Service Bus などのマネージド サービスを使用することをお勧めします。

1. `aks-store-quickstart.yaml` という名前のファイルを作成し、そこに次のマニフェストをコピーします。

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

    YAML マニフェスト ファイルの内訳については、「[デプロイと YAML マニフェスト](../concepts-clusters-workloads.md#deployments-and-yaml-manifests)」を参照してください。

    YAML ファイルをローカルに作成して保存する場合は、**[ファイルのアップロード/ダウンロード]** ボタンを選択し、ローカル ファイル システムからファイルを選択することで、CloudShell の既定のディレクトリにマニフェスト ファイルをアップロードできます。

1. [`kubectl apply`][kubectl-apply] コマンドを使用してアプリケーションをデプロイし、ご利用の YAML マニフェストの名前を指定します。

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## アプリケーションをテストする

パブリック IP アドレスまたはアプリケーション URL にアクセスすることで、アプリケーションが実行されていることを確認できます。

以下のコマンドを使用してアプリケーション URL を取得します。

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

結果:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="AKS Store サンプル アプリケーションのスクリーンショット。" lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## クラスターを削除する

「[AKS チュートリアル][aks-tutorial]」を実行しない場合は、Azure の課金を回避するために不要なリソースをクリーンアップします。 [`az group delete`][az-group-delete] コマンドを使用して、リソース グループ、コンテナー サービス、およびすべての関連リソースを削除できます。

> [!NOTE]
> AKS クラスターは、本クイックスタートの既定の ID オプションであるシステム割り当てマネージド ID を使用して作成されています。 この ID はプラットフォームによって管理されるため、手動で削除する必要はありません。

## 次のステップ

このクイック スタートでは、Kubernetes クラスターをデプロイし、シンプルな複数コンテナー アプリケーションをそこにデプロイしました。 このサンプル アプリケーションはデモ専用であり、Kubernetes アプリケーションのすべてのベスト プラクティスを表すわけではありません。 実稼動用に AKS を使用した完全なソリューションを作成するうえでのガイダンスについては、[AKS ソリューション ガイダンス][aks-solution-guidance]に関する記事を参照してください。

AKS の詳細を確認し、完全なコードからデプロイの例までを確認するには、Kubernetes クラスターのチュートリアルに進んでください。

> [!div class="nextstepaction"]
> [AKS チュートリアル][aks-tutorial]

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
