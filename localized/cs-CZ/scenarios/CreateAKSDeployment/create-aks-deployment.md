---
title: 'Rychlý start: Nasazení clusteru Azure Kubernetes Service (AKS) pomocí Azure CLI'
description: 'Zjistěte, jak rychle nasadit cluster Kubernetes a nasadit aplikaci ve službě Azure Kubernetes Service (AKS) pomocí Azure CLI.'
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Rychlý start: Nasazení clusteru Azure Kubernetes Service (AKS) pomocí Azure CLI

[![Nasazení do Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) je spravovaná služba Kubernetes, která umožňuje rychle nasazovat a spravovat clustery. V tomto rychlém startu se naučíte:

- Nasaďte cluster AKS pomocí Azure CLI.
- Spusťte ukázkovou vícekontenerovou aplikaci se skupinou mikroslužeb a webových front-endů simulujících scénář maloobchodního prodeje.

> [!NOTE]
> Pokud chcete začít rychle zřizovat cluster AKS, najdete v tomto článku postup nasazení clusteru s výchozím nastavením pouze pro účely vyhodnocení. Před nasazením clusteru připraveného pro produkční prostředí doporučujeme seznámit se s naší [referenční architekturou][baseline-reference-architecture] podle směrného plánu a zvážit, jak je v souladu s vašimi obchodními požadavky.

## Než začnete

Tento rychlý start předpokládá základní znalosti konceptů Kubernetes. Další informace najdete v tématu [Základní koncepty Kubernetes pro Službu Azure Kubernetes Service (AKS).][kubernetes-concepts]

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Tento článek vyžaduje verzi 2.0.64 nebo novější azure CLI. Pokud používáte Azure Cloud Shell, je tam už nainstalovaná nejnovější verze.
- Ujistěte se, že identita, kterou používáte k vytvoření clusteru, má odpovídající minimální oprávnění. Další podrobnosti o přístupu a identitě pro AKS najdete v tématu [Možnosti přístupu a identit pro Službu Azure Kubernetes Service (AKS).](../concepts-identity.md)
- Pokud máte více předplatných Azure, vyberte odpovídající ID předplatného, ve kterém se mají prostředky fakturovat pomocí [příkazu az account set](/cli/azure/account#az-account-set) .

## Definování proměnných prostředí

V tomto rychlém startu definujte následující proměnné prostředí:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Vytvoření skupiny zdrojů

Skupina [][azure-resource-group] prostředků Azure je logická skupina, ve které se nasazují a spravují prostředky Azure. Při vytváření skupiny prostředků se zobrazí výzva k zadání umístění. Toto umístění je umístění úložiště metadat vaší skupiny prostředků a místo, kde vaše prostředky běží v Azure, pokud během vytváření prostředků nezadáte jinou oblast.

Pomocí příkazu vytvořte skupinu [`az group create`][az-group-create] prostředků.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Výsledky:
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

## Vytvoření clusteru AKS

Pomocí příkazu vytvořte cluster [`az aks create`][az-aks-create] AKS. Následující příklad vytvoří cluster s jedním uzlem a povolí spravovanou identitu přiřazenou systémem.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> Když vytvoříte nový cluster, AKS automaticky vytvoří druhou skupinu prostředků pro uložení prostředků AKS. Další informace najdete v tématu [Proč se v AKS vytvářejí dvě skupiny prostředků?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Připojení ke clusteru

Ke správě clusteru Kubernetes použijte klienta příkazového řádku Kubernetes kubectl[][kubectl]. `kubectl` je už nainstalovaný, pokud používáte Azure Cloud Shell. Pokud chcete nainstalovat `kubectl` místně, použijte [`az aks install-cli`][az-aks-install-cli] příkaz.

1. Nakonfigurujte `kubectl` připojení ke clusteru Kubernetes pomocí [příkazu az aks get-credentials][az-aks-get-credentials] . Tento příkaz stáhne přihlašovací údaje a nakonfiguruje rozhraní příkazového řádku Kubernetes tak, aby je používalo.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Pomocí příkazu kubectl get[ ověřte připojení ke clusteru][kubectl-get]. Tento příkaz vrátí seznam uzlů clusteru.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Nasazení aplikace

K nasazení aplikace použijete soubor manifestu k vytvoření všech objektů potřebných ke spuštění [aplikace](https://github.com/Azure-Samples/aks-store-demo) AKS Store. [Soubor][kubernetes-deployment] manifestu Kubernetes definuje požadovaný stav clusteru, například které image kontejneru se mají spustit. Manifest zahrnuje následující nasazení a služby Kubernetes:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Snímek obrazovky s ukázkovou architekturou Azure Storu" lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Store front**: Webová aplikace pro zákazníky k zobrazení produktů a objednávání.
- **Produktová služba**: Zobrazuje informace o produktu.
- **Objednávka:** Objednávky.
- **Rabbit MQ**: Fronta zpráv pro frontu objednávek.

> [!NOTE]
> Nedoporučujeme spouštět stavové kontejnery, jako je Rabbit MQ, bez trvalého úložiště pro produkční prostředí. Tady se používají pro zjednodušení, ale doporučujeme používat spravované služby, jako je Azure CosmosDB nebo Azure Service Bus.

1. Vytvořte soubor s názvem `aks-store-quickstart.yaml` a zkopírujte ho v následujícím manifestu:

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

    Rozpis souborů manifestu YAML najdete v tématu [Nasazení a manifesty](../concepts-clusters-workloads.md#deployments-and-yaml-manifests) YAML.

    Pokud soubor YAML vytvoříte a uložíte místně, můžete soubor manifestu nahrát do výchozího adresáře v CloudShellu tak **, že vyberete tlačítko Nahrát/Stáhnout soubory** a vyberete soubor z místního systému souborů.

1. Nasaďte aplikaci pomocí [`kubectl apply`][kubectl-apply] příkazu a zadejte název manifestu YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Testování aplikace

Aplikaci můžete ověřit tak, že navštívíte veřejnou IP adresu nebo adresu URL aplikace.

Adresu URL aplikace získejte pomocí následujících příkazů:

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

Výsledky:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Snímek obrazovky ukázkové aplikace AKS Store" lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Odstranění clusteru

Pokud nechcete projít [kurzem][aks-tutorial] AKS, vyčistěte nepotřebné prostředky, abyste se vyhnuli poplatkům za Azure. Pomocí příkazu můžete odebrat skupinu prostředků, službu kontejneru a všechny související prostředky [`az group delete`][az-group-delete] .

> [!NOTE]
> Cluster AKS byl vytvořen se spravovanou identitou přiřazenou systémem, což je výchozí možnost identity použitá v tomto rychlém startu. Tato identita spravuje platforma, takže ji nemusíte ručně odebírat.

## Další kroky

V tomto rychlém startu jste nasadili cluster Kubernetes a pak jste do něj nasadili jednoduchou vícekontenerovou aplikaci. Tato ukázková aplikace slouží jenom pro ukázkové účely a nepředstavuje všechny osvědčené postupy pro aplikace Kubernetes. Pokyny k vytváření úplných řešení pomocí AKS pro produkční prostředí najdete [v pokynech k][aks-solution-guidance] řešení AKS.

Pokud chcete získat další informace o AKS a projít si kompletní příklad nasazení kódu na nasazení, pokračujte kurzem clusteru Kubernetes.

> [!div class="nextstepaction"]
> [Kurz AKS][aks-tutorial]

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
