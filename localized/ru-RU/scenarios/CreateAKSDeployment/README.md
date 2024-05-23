---
title: Краткое руководство. Развертывание кластера Служба Azure Kubernetes (AKS) с помощью Azure CLI
description: 'Узнайте, как быстро развернуть кластер Kubernetes и развернуть приложение в Служба Azure Kubernetes (AKS) с помощью Azure CLI.'
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Краткое руководство. Развертывание кластера Служба Azure Kubernetes (AKS) с помощью Azure CLI

[![Развертывание в Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Служба Azure Kubernetes (AKS) — это управляемая служба Kubernetes, которая позволяет быстро развертывать кластеры и управлять ими. Из этого краткого руководства вы узнаете, как выполнять следующие задачи:

- Развертывание кластера AKS с помощью Azure CLI.
- Запустите пример мультиконтейнерного приложения с группой микрослужб и веб-интерфейсов с имитацией сценария розничной торговли.

> [!NOTE]
> Чтобы приступить к быстрой подготовке кластера AKS, в этой статье содержатся действия по развертыванию кластера с параметрами по умолчанию только для оценки. Прежде чем развертывать готовый к работе кластер, рекомендуется ознакомиться с базовой [эталонной архитектурой][baseline-reference-architecture] , чтобы понять, как она соответствует вашим бизнес-требованиям.

## Подготовка к работе

В этом руководстве предполагается, что у вас есть некоторое представление о функциях Kubernetes. Дополнительные сведения см. в статье [Ключевые концепции Kubernetes для службы Azure Kubernetes (AKS)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Для работы с этой статьей требуется Azure CLI версии 2.0.64 или более поздней. Если вы используете Azure Cloud Shell, последняя версия уже установлена там.
- Убедитесь, что удостоверение, которое вы используете для создания кластера, имеет соответствующие минимальные разрешения. Дополнительные сведения о доступе и удостоверении для AKS см. в статье [Возможности контроля доступа и идентификации в Службе Azure Kubernetes (AKS)](../concepts-identity.md).
- Если у вас несколько подписок Azure, выберите соответствующий идентификатор подписки, в котором необходимо выставлять счета за ресурсы с помощью [команды az account set](/cli/azure/account#az-account-set) .

## Определение переменных среды

Определите следующие переменные среды для использования в этом кратком руководстве.

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Создание или изменение группы ресурсов

[Группа ресурсов Azure][azure-resource-group] — это логическая группа, в которой развертываются и управляются ресурсы Azure. При создании группы ресурсов вам будет предложено указать расположение. Это расположение хранилища метаданных группы ресурсов и место, где ресурсы выполняются в Azure, если вы не указываете другой регион во время создания ресурса.

Создайте группу ресурсов с помощью [`az group create`][az-group-create] команды.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Результаты.
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

## Создание кластера AKS

Создайте кластер AKS с помощью [`az aks create`][az-aks-create] команды. В следующем примере создается кластер с одним узлом и включается управляемое удостоверение, назначаемое системой.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> При создании нового кластера AKS автоматически создает вторую группу ресурсов для хранения ресурсов AKS. Дополнительные сведения см. в разделе [Почему с AKS создаются две группы ресурсов?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Подключение к кластеру

Кластером Kubernetes можно управлять при помощи [kubectl][kubectl] клиента командной строки Kubernetes. Если вы используете Azure Cloud Shell, `kubectl` уже установлен. Чтобы установить `kubectl` локально, используйте [`az aks install-cli`][az-aks-install-cli] команду.

1. Настройте в `kubectl` подключение к кластеру Kubernetes, выполнив команду [az aks get-credentials][az-aks-get-credentials]. Эта команда скачивает учетные данные и настраивает интерфейс командной строки Kubernetes для их использования.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Проверьте подключение к кластеру, выполнив команду [kubectl get][kubectl-get]. Эта команда возвращает список узлов кластера.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Развертывание приложения

Чтобы развернуть приложение, используйте файл манифеста для создания всех объектов, необходимых для запуска [приложения](https://github.com/Azure-Samples/aks-store-demo) AKS Store. [Файл манифеста Kubernetes][kubernetes-deployment] используется для определения требуемого состояния кластера, например выполняемых в нем образов контейнеров. Манифест включает следующие развертывания и службы Kubernetes:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Снимок экрана: пример архитектуры Магазина Azure." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Интерфейс** магазина: веб-приложение для пользователей для просмотра продуктов и размещения заказов.
- **Служба** продуктов: отображает сведения о продукте.
- **Служба** заказов: помещает заказы.
- **Rabbit MQ**: очередь сообщений для очереди заказов.

> [!NOTE]
> Не рекомендуется запускать контейнеры с отслеживанием состояния, такие как Rabbit MQ, без постоянного хранения для рабочей среды. Они используются здесь для простоты, но мы рекомендуем использовать управляемые службы, такие как Azure CosmosDB или Служебная шина Azure.

1. Создайте файл с именем `aks-store-quickstart.yaml` и скопируйте его в следующем манифесте:

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

    Сведения о разбивке файлов манифеста YAML см. в разделе ["Развертывания" и "Манифесты](../concepts-clusters-workloads.md#deployments-and-yaml-manifests) YAML".

    Если вы создаете и сохраняете файл YAML локально, вы можете отправить файл манифеста в каталог по умолчанию в CloudShell, нажав **кнопку "Отправить и скачать файлы** " и выбрав файл из локальной файловой системы.

1. Разверните приложение с помощью [`kubectl apply`][kubectl-apply] команды и укажите имя манифеста YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Тестирование приложения

Чтобы убедиться, что приложение запущено, посетите общедоступный IP-адрес или URL-адрес приложения.

Получите URL-адрес приложения с помощью следующих команд:

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

Результаты.
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Снимок экрана: пример приложения AKS Store." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Удаление кластера

Если вы не планируете использовать [учебник][aks-tutorial] AKS, очистите ненужные ресурсы, чтобы избежать расходов Azure. Вы можете удалить группу ресурсов, службу контейнеров и все связанные ресурсы с помощью [`az group delete`][az-group-delete] команды.

> [!NOTE]
> Кластер AKS был создан с управляемым удостоверением, назначенным системой, который является параметром удостоверения по умолчанию, используемым в этом кратком руководстве. Платформа управляет этим удостоверением, чтобы удалить его вручную не нужно.

## Следующие шаги

С помощью этого краткого руководства вы развернули кластер Kubernetes и простое многоконтейнерное приложение в нем. Этот пример приложения предназначен только для демонстрационных целей и не представляет все рекомендации для приложений Kubernetes. Рекомендации по созданию полных решений с помощью AKS для рабочей среды см [. в руководстве по][aks-solution-guidance] решению AKS.

Чтобы узнать больше об AKS и ознакомиться с полным примером кода к развертыванию, перейдите к руководству по кластеру Kubernetes.

> [!div class="nextstepaction"]
> [Руководство по AKS][aks-tutorial]

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
