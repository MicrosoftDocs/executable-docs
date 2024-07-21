---
title: 'Guida introduttiva: distribuire un cluster del servizio Azure Kubernetes (AKS) con l’interfaccia della riga di comando di Azure'
description: 'Informazioni su come distribuire rapidamente un cluster Kubernetes e un''applicazione nel servizio Azure Kubernetes (AKS), usando l’interfaccia della riga di comando di Azure.'
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Guida introduttiva: distribuire un cluster del servizio Azure Kubernetes (AKS) con l’interfaccia della riga di comando di Azure

[![Distribuzione in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Il servizio Azure Kubernetes è un servizio Kubernetes gestito che permette di distribuire e gestire rapidamente i cluster. In questa guida introduttiva si apprende come:

- Distribuire un cluster del servizio Azure Kubernetes usando l'interfaccia della riga di comando di Azure.
- Eseguire un'applicazione multi-contenitore di esempio con un gruppo di microservizi e front-end web, simulando uno scenario di vendita al dettaglio.

> [!NOTE]
> Per iniziare ad effettuare un veloce provisioning di un cluster del servizio Azure Kubernetes, questo articolo include i passaggi per la distribuzione di un cluster con impostazioni predefinite a solo scopo di valutazione. Prima di distribuire un cluster pronto per la produzione, è consigliabile acquisire familiarità con l'[architettura di riferimento di base][baseline-reference-architecture] per valutare il modo in cui è allineato ai requisiti aziendali.

## Operazioni preliminari

Questa guida introduttiva presuppone una comprensione di base dei concetti relativi a Kubernetes. Per altre informazioni, vedere [Concetti di base relativi a Kubernetes per il servizio Azure Kubernetes][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Questo articolo richiede la versione 2.0.64 o successiva dell'interfaccia della riga di comando di Azure. Se si sta usando Azure Cloud Shell, la versione più recente è già installata.
- Assicurarsi che l'identità usata per creare il cluster disponga delle autorizzazioni minime adeguate. Per maggiori informazioni sull'accesso e l'identità per il servizio Azure Kubernetes, vedere [Opzioni di accesso e identità per il servizio Azure Kubernetes (AKS)](../concepts-identity.md).
- Se si hanno più sottoscrizioni di Azure, selezionare l'ID sottoscrizione appropriato in cui devono essere fatturate le risorse, usando il comando [set account az](/cli/azure/account#az-account-set).

## Definire le variabili di ambiente

Definire le variabili di ambiente seguenti da usare in questa guida introduttiva:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Creare un gruppo di risorse

Un [gruppo di risorse][azure-resource-group] di Azure è un gruppo logico in cui le risorse di Azure vengono distribuite e gestite. Quando si crea un gruppo di risorse, viene richiesto di specificare una posizione. Questa posizione è la posizione di archiviazione dei metadati del gruppo di risorse e dove le risorse vengono eseguite in Azure se non si specifica un'altra regione durante la creazione della risorsa.

Creare un gruppo di risorse usando il comando [`az group create`][az-group-create].

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Risultati:
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

## Creare un cluster del servizio Azure Kubernetes

Creare un cluster del servizio Azure Kubernetes usando il comando [`az aks create`][az-aks-create]. L'esempio seguente crea un cluster con un nodo e abilita un'identità gestita assegnata dal sistema.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> Quando si crea un nuovo cluster, il servizio Azure Kubernetes crea automaticamente un secondo gruppo di risorse per archiviare le risorse del servizio Azure Kubernetes. Per altre informazioni, vedere [Perché vengono creati due gruppi di risorse con servizio Azure Kubernetes?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Stabilire la connessione al cluster

Per gestire un cluster Kubernetes, usare il client da riga di comando kubernetes [kubectl][kubectl]. `kubectl` è già installato se si usa Azure Cloud Shell. Per eseguire l'installazione `kubectl` in locale, usare il [`az aks install-cli`][az-aks-install-cli] comando .

1. Configurare `kubectl` per connettersi al cluster Kubernetes usando il comando [az aks get-credentials][az-aks-get-credentials]. Questo comando scarica le credenziali e configura l'interfaccia della riga di comando di Kubernetes per usarli.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Verificare la connessione al cluster usando il comando [kubectl get][kubectl-get]. Questo comando restituisce un elenco dei nodi del cluster.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Distribuire l'applicazione

Per distribuire l'applicazione, usare un file manifesto per creare tutti gli oggetti necessari per eseguire l'[applicazione di Archiviazione del servizio Azure Kubernetes](https://github.com/Azure-Samples/aks-store-demo). Un [file manifesto Kubernetes][kubernetes-deployment] definisce lo stato desiderato di un cluster, ad esempio le immagini del contenitore da eseguire. Il manifesto include le distribuzioni e i servizi Kubernetes seguenti:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Screenshot dell'architettura di esempio di Azure Store." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Front-store**: applicazione Web per i clienti per visualizzare i prodotti ed effettuare ordini.
- **Servizio prodotto**: mostra le informazioni sul prodotto.
- **Servizio ordini**: effettua ordini.
- **Rabbit MQ**: coda di messaggi per una coda di ordini.

> [!NOTE]
> Non è consigliabile eseguire contenitori con stato, ad esempio Rabbit MQ, senza l'archiviazione permanente per la produzione. Questi vengono usati qui per semplicità, ma è consigliabile usare servizi gestiti, ad esempio Azure CosmosDB o il bus di servizio di Azure.

1. Creare un file denominato `aks-store-quickstart.yaml` e copiarlo nel manifesto seguente:

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

    Per un dettaglio dei file manifesto YAML, vedere [Distribuzioni e manifesti YAML](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Se si crea e si salva il file YAML in locale, è possibile caricare il file manifesto nella directory predefinita in CloudShell selezionando il pulsante **Carica/Scarica file** e selezionando il file dal file system locale.

1. Distribuire l'applicazione usando il comando [`kubectl apply`][kubectl-apply] e specificare il nome del manifesto YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Testare l'applicazione

È possibile verificare che l'applicazione sia in esecuzione visitando l'indirizzo IP pubblico o l'URL dell'applicazione.

Ottenere l'URL dell'applicazione usando i comandi seguenti:

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

Risultati:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Screenshot dell'applicazione di esempio dello Store del servizio Azure Kubernetes." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Eliminare il cluster

Se non si prevede di eseguire l'[esercitazione del servizio Azure Kubernetes][aks-tutorial], ripulire le risorse non necessarie per evitare addebiti di Azure. È possibile rimuovere il gruppo di risorse, il servizio contenitore e tutte le risorse correlate usando il [`az group delete`][az-group-delete] comando .

> [!NOTE]
> Il cluster del servizio Azure Kubernetes è stato creato con un'identità gestita assegnata dal sistema, che è l'opzione di identità predefinita usata in questo avvio rapido. Questa identità è gestita dalla piattaforma, pertanto non è necessario rimuoverla manualmente.

## Passaggi successivi

In questa guida introduttiva, è stato distribuito un cluster Kubernetes, successivamente è stata distribuita una semplice applicazione multi-contenitore. Questa applicazione di esempio è solo a scopo dimostrativo e non rappresenta tutte le procedure consigliate per le applicazioni Kubernetes. Per indicazioni sulla creazione di soluzioni complete con il servizio Azure Kubernetes per la produzione, vedere [Linee guida per le soluzioni del servizio Azure Kubernetes][aks-solution-guidance].

Per altre informazioni sul servizio Azure Kubernetes e per un esempio completo di distribuzione del codice, passare all'esercitazione sul cluster Kubernetes.

> [!div class="nextstepaction"]
> [Esercitazione sul servizio Azure Container][aks-tutorial]

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
