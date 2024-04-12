---
title: 'Hızlı Başlangıç: Azure CLI kullanarak Azure Kubernetes Service (AKS) kümesi dağıtma'
description: Azure CLI kullanarak Bir Kubernetes kümesini hızla dağıtmayı ve Azure Kubernetes Service'te (AKS) uygulama dağıtmayı öğrenin.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Hızlı Başlangıç: Azure CLI kullanarak Azure Kubernetes Service (AKS) kümesi dağıtma

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS), kümeleri hızla dağıtmanızı ve yönetmenizi sağlayan yönetilen bir Kubernetes hizmetidir. Bu hızlı başlangıçta şunları yapmayı öğrenirsiniz:

- Azure CLI kullanarak aks kümesi dağıtma.
- Bir grup mikro hizmet ve web ön ucuyla perakende senaryosu simülasyonu yaparak örnek bir çok kapsayıcılı uygulama çalıştırın.

> [!NOTE]
> Aks kümesini hızlı bir şekilde sağlamaya başlamak için, bu makale yalnızca değerlendirme amacıyla varsayılan ayarlarla küme dağıtma adımlarını içerir. Üretime hazır bir kümeyi dağıtmadan önce, iş gereksinimlerinizle nasıl uyumlu olduğunu göz önünde bulundurmak için temel başvuru mimarimizi [][baseline-reference-architecture] tanımanızı öneririz.

## Başlamadan önce

Bu hızlı başlangıç, Kubernetes kavramlarının temel olarak bilindiğini varsayar. Daha fazla bilgi için bkz [. Azure Kubernetes Service (AKS)][kubernetes-concepts] için Kubernetes temel kavramları.

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Bu makale, Azure CLI'nın 2.0.64 veya sonraki bir sürümünü gerektirir. Azure Cloud Shell kullanıyorsanız en son sürüm zaten orada yüklüdür.
- Kümenizi oluşturmak için kullandığınız kimliğin uygun minimum izinlere sahip olduğundan emin olun. AKS erişimi ve kimliği hakkında daha fazla bilgi için bkz [. Azure Kubernetes Service (AKS)](../concepts-identity.md) için erişim ve kimlik seçenekleri.
- Birden çok Azure aboneliğiniz varsa az account set[ komutu kullanılarak ](/cli/azure/account#az-account-set)kaynakların faturalandırılacağı uygun abonelik kimliğini seçin.

## Ortam değişkenlerini tanımlama

Bu hızlı başlangıç boyunca kullanmak üzere aşağıdaki ortam değişkenlerini tanımlayın:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Kaynak grubu oluşturma

[Azure kaynak grubu][azure-resource-group], Azure kaynaklarının dağıtıldığı ve yönetildiği mantıksal bir grupdur. Bir kaynak grubu oluşturduğunuzda, bir konum belirtmeniz istenir. Bu konum, kaynak grubu meta verilerinizin depolama konumudur ve kaynak oluşturma sırasında başka bir bölge belirtmezseniz kaynaklarınızın Azure'da çalıştırıldığı konumdur.

komutunu kullanarak [`az group create`][az-group-create] bir kaynak grubu oluşturun.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Sonuçlar:
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

## AKS kümesi oluşturma

komutunu kullanarak [`az aks create`][az-aks-create] bir AKS kümesi oluşturun. Aşağıdaki örnek, tek düğümlü bir küme oluşturur ve sistem tarafından atanan yönetilen kimliği etkinleştirir.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> Yeni bir küme oluşturduğunuzda AKS, AKS kaynaklarını depolamak için otomatik olarak ikinci bir kaynak grubu oluşturur. Daha fazla bilgi için bkz. [AKS ile neden iki kaynak grubu oluşturulur?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Kümeye bağlanma

Kubernetes kümesini yönetmek için kubectl[ adlı ][kubectl]Kubernetes komut satırı istemcisini kullanın. `kubectl` Azure Cloud Shell kullanıyorsanız zaten yüklüdür. Yerel olarak yüklemek `kubectl` için komutunu kullanın`az aks install-cli`[][az-aks-install-cli].

1. az aks get-credentials[ komutunu kullanarak ][az-aks-get-credentials]Kubernetes kümenize bağlanacak şekilde yapılandırın`kubectl`. Bu komut kimlik bilgilerini indirir ve Kubernetes CLI'yi bunları kullanacak şekilde yapılandırmaktadır.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. kubectl get[ komutunu kullanarak ][kubectl-get]kümenize bağlantıyı doğrulayın. Bu komut, küme düğümlerinin listesini döndürür.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Uygulamayı dağıtma

Uygulamayı dağıtmak için, AKS Store uygulamasını[ çalıştırmak ](https://github.com/Azure-Samples/aks-store-demo)için gereken tüm nesneleri oluşturmak için bir bildirim dosyası kullanırsınız. [Kubernetes bildirim dosyası][kubernetes-deployment], hangi kapsayıcı görüntülerinin çalıştırıldığı gibi kümenin istenen durumunu tanımlar. Bildirim aşağıdaki Kubernetes dağıtımlarını ve hizmetlerini içerir:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Azure Store örnek mimarisinin ekran görüntüsü." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Mağaza ön**: Müşterilerin ürünleri görüntülemesi ve sipariş vermesi için web uygulaması.
- **Ürün hizmeti**: Ürün bilgilerini gösterir.
- **Sipariş hizmeti**: Sipariş verir.
- **Rabbit MQ**: Sipariş kuyruğu için ileti kuyruğu.

> [!NOTE]
> Üretim için kalıcı depolama olmadan Rabbit MQ gibi durum bilgisi olan kapsayıcıları çalıştırmanızı önermiyoruz. Bunlar burada kolaylık sağlamak için kullanılır, ancak Azure CosmosDB veya Azure Service Bus gibi yönetilen hizmetleri kullanmanızı öneririz.

1. Adlı `aks-store-quickstart.yaml` bir dosya oluşturun ve aşağıdaki bildirimde kopyalayın:

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

    YAML bildirim dosyalarının dökümü için bkz [. Dağıtımlar ve YAML bildirimleri](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    YAML dosyasını yerel olarak oluşturur ve kaydederseniz, Dosyaları** Karşıya Yükle/İndir düğmesini seçip yerel dosya sisteminizden dosyayı seçerek **bildirim dosyasını CloudShell'deki varsayılan dizininize yükleyebilirsiniz.

1. komutunu kullanarak uygulamayı dağıtın [`kubectl apply`][kubectl-apply] ve YAML bildiriminizin adını belirtin.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Uygulamayı test etme

Genel IP adresini veya uygulama URL'sini ziyaret ederek uygulamanın çalıştığını doğrulayabilirsiniz.

Aşağıdaki komutları kullanarak uygulama URL'sini alın:

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

Sonuçlar:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="AKS Store örnek uygulamasının ekran görüntüsü." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Küme silme

AKS öğreticisini[ incelemeyi ][aks-tutorial]planlamıyorsanız, Azure ücretlerinden kaçınmak için gereksiz kaynakları temizleyin. komutunu kullanarak [`az group delete`][az-group-delete] kaynak grubunu, kapsayıcı hizmetini ve tüm ilgili kaynakları kaldırabilirsiniz.

> [!NOTE]
> AKS kümesi, bu hızlı başlangıçta kullanılan varsayılan kimlik seçeneği olan sistem tarafından atanan yönetilen kimlikle oluşturulmuştur. Platform bu kimliği yönetir, böylece bu kimliği el ile kaldırmanız gerekmez.

## Sonraki adımlar

Bu hızlı başlangıçta bir Kubernetes kümesi dağıttınız ve ardından basit bir çok kapsayıcılı uygulama dağıttınız. Bu örnek uygulama yalnızca tanıtım amaçlıdır ve Kubernetes uygulamaları için en iyi yöntemlerin tümünü temsil etmez. Üretim için AKS ile tam çözüm oluşturma yönergeleri için bkz [. AKS çözümü kılavuzu][aks-solution-guidance].

AKS hakkında daha fazla bilgi edinmek ve eksiksiz bir koddan dağıtım örneğine gitmek için Kubernetes kümesi öğreticisine geçin.

> [!div class="nextstepaction"]
> [AKS öğreticisi][aks-tutorial]

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