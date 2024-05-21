---
title: 'Snabbstart: Distribuera ett AKS-kluster (Azure Kubernetes Service) med Azure CLI'
description: Lär dig hur du snabbt distribuerar ett Kubernetes-kluster och distribuerar ett program i Azure Kubernetes Service (AKS) med Azure CLI.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Snabbstart: Distribuera ett AKS-kluster (Azure Kubernetes Service) med Azure CLI

[![Distribuera till Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) är en hanterad Kubernetes-tjänst som gör att du snabbt kan distribuera och hantera kluster. I den här snabbstarten lär du dig att:

- Distribuera ett AKS-kluster med hjälp av Azure CLI.
- Kör ett exempelprogram med flera containrar med en grupp mikrotjänster och webbklientdelar som simulerar ett detaljhandelsscenario.

> [!NOTE]
> För att komma igång med att snabbt etablera ett AKS-kluster innehåller den här artikeln steg för att distribuera ett kluster med standardinställningar endast i utvärderingssyfte. Innan du distribuerar ett produktionsklart kluster rekommenderar vi att du bekantar dig med vår [referensarkitektur][baseline-reference-architecture] för baslinje för att överväga hur det överensstämmer med dina affärskrav.

## Innan du börjar

Den här snabbstarten förutsätter grundläggande kunskaper om Kubernetes-begrepp. Mer information finns i [Viktiga koncept för Azure Kubernetes Service (AKS)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Den här artikeln kräver version 2.0.64 eller senare av Azure CLI. Om du använder Azure Cloud Shell är den senaste versionen redan installerad där.
- Kontrollera att den identitet som du använder för att skapa klustret har lämpliga minimibehörigheter. Mer information om åtkomst och identitet för AKS finns i [Åtkomst- och identitetsalternativ för Azure Kubernetes Service (AKS)](../concepts-identity.md).
- Om du har flera Azure-prenumerationer väljer du lämpligt prenumerations-ID där resurserna ska faktureras med [kommandot az account set](/cli/azure/account#az-account-set) .

## Definiera miljövariabler

Definiera följande miljövariabler för användning under den här snabbstarten:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Skapa en resursgrupp

En [Azure-resursgrupp][azure-resource-group] är en logisk grupp där Azure-resurser distribueras och hanteras. När du skapar en resursgrupp uppmanas du att ange en plats. Den här platsen är lagringsplatsen för dina resursgruppsmetadata och där dina resurser körs i Azure om du inte anger en annan region när du skapar resurser.

Skapa en resursgrupp med kommandot [`az group create`][az-group-create] .

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultat:
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

## Skapa ett AKS-kluster

Skapa ett AKS-kluster med kommandot [`az aks create`][az-aks-create] . I följande exempel skapas ett kluster med en nod och en systemtilldelad hanterad identitet aktiveras.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> När du skapar ett nytt kluster skapar AKS automatiskt en andra resursgrupp för att lagra AKS-resurserna. Mer information finns i [Varför skapas två resursgrupper med AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Anslut till klustret

Om du vill hantera ett Kubernetes-kluster använder du Kubernetes-kommandoradsklienten [kubectl][kubectl]. `kubectl` är redan installerat om du använder Azure Cloud Shell. Om du vill installera `kubectl` lokalt använder du [`az aks install-cli`][az-aks-install-cli] kommandot .

1. Konfigurera `kubectl` för att ansluta till kubernetes-klustret med [kommandot az aks get-credentials][az-aks-get-credentials] . Det här kommandot laddar ned autentiseringsuppgifter och konfigurerar Kubernetes CLI för att använda dem.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Kontrollera anslutningen till klustret med kommandot [kubectl get][kubectl-get] . Det här kommandot returnerar en lista över klusternoderna.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Distribuera programmet

För att distribuera programmet använder du en manifestfil för att skapa alla objekt som krävs för att köra [AKS Store-programmet](https://github.com/Azure-Samples/aks-store-demo). En [Kubernetes-manifestfil][kubernetes-deployment] definierar ett klusters önskade tillstånd, till exempel vilka containeravbildningar som ska köras. Manifestet innehåller följande Kubernetes-distributioner och -tjänster:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Skärmbild av Azure Store-exempelarkitektur." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Butiksfront**: Webbprogram där kunder kan visa produkter och göra beställningar.
- **Produkttjänst**: Visar produktinformation.
- **Ordertjänst**: Gör beställningar.
- **Rabbit MQ**: Meddelandekö för en orderkö.

> [!NOTE]
> Vi rekommenderar inte att du kör tillståndskänsliga containrar, till exempel Rabbit MQ, utan beständig lagring för produktion. Dessa används här för enkelhetens skull, men vi rekommenderar att du använder hanterade tjänster, till exempel Azure CosmosDB eller Azure Service Bus.

1. Skapa en fil med namnet `aks-store-quickstart.yaml` och kopiera i följande manifest:

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

    En uppdelning av YAML-manifestfiler [finns i Distributioner och YAML-manifest](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Om du skapar och sparar YAML-filen lokalt kan du ladda upp manifestfilen till standardkatalogen **i CloudShell genom att välja knappen Ladda upp/ladda ned filer** och välja filen från det lokala filsystemet.

1. Distribuera programmet med kommandot [`kubectl apply`][kubectl-apply] och ange namnet på ditt YAML-manifest.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Testa programmet

Du kan kontrollera att programmet körs genom att besöka den offentliga IP-adressen eller program-URL:en.

Hämta program-URL:en med hjälp av följande kommandon:

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

Resultat:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Skärmbild av AKS Store-exempelprogrammet." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Ta bort klustret

Om du inte planerar att gå igenom AKS-självstudien [][aks-tutorial]rensar du onödiga resurser för att undvika Azure-avgifter. Du kan ta bort resursgruppen, containertjänsten och alla relaterade resurser med kommandot [`az group delete`][az-group-delete] .

> [!NOTE]
> AKS-klustret skapades med en systemtilldelad hanterad identitet, vilket är standardalternativet för identitet som används i den här snabbstarten. Plattformen hanterar den här identiteten så att du inte behöver ta bort den manuellt.

## Nästa steg

I den här snabbstarten distribuerade du ett Kubernetes-kluster och distribuerade sedan ett enkelt program med flera containrar till det. Det här exempelprogrammet är endast i demosyfte och representerar inte alla metodtips för Kubernetes-program. Vägledning om hur du skapar fullständiga lösningar med AKS för produktion finns i [AKS-lösningsvägledning][aks-solution-guidance].

Om du vill veta mer om AKS och gå igenom ett komplett exempel på kod-till-distribution fortsätter du till självstudiekursen för Kubernetes-klustret.

> [!div class="nextstepaction"]
> [Självstudiekurs om AKS][aks-tutorial]

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
