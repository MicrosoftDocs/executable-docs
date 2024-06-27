# Guia de início rápido: implantar um cluster do Serviço Kubernetes do Azure (AKS) usando a CLI do Azure

[![Implementar no Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

O Serviço Kubernetes do Azure (AKS) é um serviço Kubernetes gerenciado que permite implantar e gerenciar clusters rapidamente. Neste início rápido, vai aprender a:

- Implante um cluster AKS usando a CLI do Azure.
- Execute um aplicativo de vários contêineres de exemplo com um grupo de microsserviços e front-ends da Web simulando um cenário de varejo.

> [!NOTE]
> Para começar a provisionar rapidamente um cluster AKS, este artigo inclui etapas para implantar um cluster com configurações padrão apenas para fins de avaliação. Antes de implantar um cluster pronto para produção, recomendamos que você se familiarize com nossa [arquitetura][baseline-reference-architecture] de referência de linha de base para considerar como ela se alinha aos seus requisitos de negócios.

## Antes de começar

Este guia de introdução parte do princípio de que possui conhecimentos básicos dos conceitos do Kubernetes. Para obter mais informações, consulte [Conceitos principais do Kubernetes para o Serviço Kubernetes do Azure (AKS).][kubernetes-concepts]

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Este artigo requer a versão 2.0.64 ou posterior da CLI do Azure. Se você estiver usando o Azure Cloud Shell, a versão mais recente já está instalada lá.
- Verifique se a identidade que você está usando para criar seu cluster tem as permissões mínimas apropriadas. Para obter mais detalhes sobre acesso e identidade para AKS, consulte [Opções de acesso e identidade para o Serviço Kubernetes do Azure (AKS).](../concepts-identity.md)
- Se você tiver várias assinaturas do Azure, selecione a ID de assinatura apropriada na qual os recursos devem ser cobrados usando o [comando az account set](/cli/azure/account#az-account-set) . Para obter mais informações, consulte [Como gerenciar assinaturas do Azure – CLI](/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-subscription) do Azure.

## Definir variáveis de ambiente

Defina as seguintes variáveis de ambiente para uso durante este início rápido:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Criar um grupo de recursos

Um [grupo][azure-resource-group] de recursos do Azure é um grupo lógico no qual os recursos do Azure são implantados e gerenciados. Ao criar um grupo de recursos, você será solicitado a especificar um local. Esse local é o local de armazenamento dos metadados do grupo de recursos e onde os recursos são executados no Azure se você não especificar outra região durante a criação do recurso.

Crie um grupo de recursos usando o [`az group create`][az-group-create] comando.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:
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

## Criar um cluster do AKS

Crie um cluster AKS usando o [`az aks create`][az-aks-create] comando. O exemplo a seguir cria um cluster com um nó e habilita uma identidade gerenciada atribuída ao sistema.

```azurecli-interactive
az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --node-count 1 \
    --generate-ssh-keys
```

> [!NOTE]
> Quando você cria um novo cluster, o AKS cria automaticamente um segundo grupo de recursos para armazenar os recursos do AKS. Para obter mais informações, consulte [Por que dois grupos de recursos são criados com o AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Ligar ao cluster

Para gerenciar um cluster Kubernetes, use o cliente de linha de comando Kubernetes, [kubectl][kubectl]. `kubectl` já está instalado se você usar o Azure Cloud Shell. Para instalar `kubectl` localmente, use o [`az aks install-cli`][az-aks-install-cli] comando.

1. Configure `kubectl` para se conectar ao cluster do Kubernetes usando o [comando az aks get-credentials][az-aks-get-credentials] . Este comando baixa credenciais e configura a CLI do Kubernetes para usá-las.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Verifique a conexão com seu cluster usando o [comando kubectl get][kubectl-get] . Este comando retorna uma lista dos nós do cluster.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Implementar a aplicação

Para implantar o aplicativo, use um arquivo de manifesto para criar todos os objetos necessários para executar o [aplicativo](https://github.com/Azure-Samples/aks-store-demo) AKS Store. Um [arquivo][kubernetes-deployment] de manifesto do Kubernetes define o estado desejado de um cluster, como quais imagens de contêiner devem ser executadas. O manifesto inclui as seguintes implantações e serviços do Kubernetes:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Captura de ecrã da arquitetura de exemplo da Loja Azure." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Vitrine**: aplicativo Web para que os clientes visualizem produtos e façam pedidos.
- **Serviço do** produto: Mostra as informações do produto.
- **Serviço de** pedidos: Faz pedidos.
- **Rabbit MQ**: Fila de mensagens para uma fila de pedidos.

> [!NOTE]
> Não recomendamos a execução de contêineres com monitoração de estado, como o Rabbit MQ, sem armazenamento persistente para produção. Eles são usados aqui para simplificar, mas recomendamos o uso de serviços gerenciados, como o Azure CosmosDB ou o Azure Service Bus.

1. Crie um arquivo nomeado `aks-store-quickstart.yaml` e copie no seguinte manifesto:

    ```bash
    cat << EOF > aks-store-quickstart.yaml
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
    EOF
    ```

    Para obter um detalhamento dos arquivos de manifesto YAML, consulte [Implantações e manifestos](../concepts-clusters-workloads.md#deployments-and-yaml-manifests) YAML.

    Se você criar e salvar o arquivo YAML localmente, poderá carregar o arquivo de manifesto para seu diretório padrão no CloudShell selecionando o **botão Upload/Download de arquivos** e selecionando o arquivo do seu sistema de arquivos local.

1. Implante o aplicativo usando o [`kubectl apply`][kubectl-apply] comando e especifique o nome do seu manifesto YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Testar a aplicação

Você pode validar se o aplicativo está em execução visitando o endereço IP público ou a URL do aplicativo.

Obtenha a URL do aplicativo usando os seguintes comandos:

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

Resultados:
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

```OUTPUT
echo "You can now visit your web server at $IP_ADDRESS"
```

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Captura de ecrã da aplicação de exemplo AKS Store." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Eliminar o cluster

Se você não planeja passar pelo tutorial[ do ][aks-tutorial]AKS, limpe recursos desnecessários para evitar cobranças do Azure. Você pode remover o grupo de recursos, o serviço de contêiner e todos os recursos relacionados usando o [`az group delete`][az-group-delete] comando.

> [!NOTE]
> O cluster AKS foi criado com uma identidade gerenciada atribuída ao sistema, que é a opção de identidade padrão usada neste início rápido. A plataforma gerencia essa identidade para que você não precise removê-la manualmente.

## Próximos passos

Neste início rápido, você implantou um cluster Kubernetes e, em seguida, implantou um aplicativo simples de vários contêineres nele. Este aplicativo de exemplo é apenas para fins de demonstração e não representa todas as práticas recomendadas para aplicativos Kubernetes. Para obter orientação sobre como criar soluções completas com o AKS para produção, consulte [Orientação][aks-solution-guidance] de solução AKS.

Para saber mais sobre o AKS e percorrer um exemplo completo de código para implantação, continue para o tutorial do cluster do Kubernetes.

> [!div class="nextstepaction"]
> [Tutorial do AKS][aks-tutorial]

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
