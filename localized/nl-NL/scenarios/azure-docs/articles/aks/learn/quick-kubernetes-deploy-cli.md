---
title: 'Quickstart: Een AKS-cluster (Azure Kubernetes Service) implementeren met behulp van Azure CLI'
description: Meer informatie over het snel implementeren van een Kubernetes-cluster en het implementeren van een toepassing in Azure Kubernetes Service (AKS) met behulp van Azure CLI.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Quickstart: Een AKS-cluster (Azure Kubernetes Service) implementeren met behulp van Azure CLI

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) is een beheerde Kubernetes-service waarmee u snel clusters kunt implementeren en beheren. In deze snelstart leert u de volgende zaken:

- Implementeer een AKS-cluster met behulp van de Azure CLI.
- Voer een voorbeeldtoepassing met meerdere containers uit met een groep microservices en webfront-ends die een retailscenario simuleren.

> [!NOTE]
> Om snel aan de slag te gaan met het snel inrichten van een AKS-cluster, bevat dit artikel stappen voor het implementeren van een cluster met alleen standaardinstellingen voor evaluatiedoeleinden. Voordat u een cluster implementeert dat gereed is voor productie, raden we u aan vertrouwd te raken met de referentiearchitectuur[ van de ][baseline-reference-architecture]basislijn om na te gaan hoe dit overeenkomt met uw bedrijfsvereisten.

## Voordat u begint

In deze snelstart wordt ervan uitgegaan dat u een basisbegrip hebt van Kubernetes-concepten. Zie [Kubernetes-kernconcepten voor Azure Kubernetes Service (AKS)][kubernetes-concepts] voor meer informatie.

- [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Voor dit artikel is versie 2.0.64 of hoger van Azure CLI vereist. Als u Azure Cloud Shell gebruikt, is de nieuwste versie daar al geïnstalleerd.
- Zorg ervoor dat de identiteit die u gebruikt om uw cluster te maken de juiste minimale machtigingen heeft. Zie Toegangs- en identiteitsopties voor Azure Kubernetes Service (AKS)[ voor meer informatie over toegang en identiteit voor AKS](../concepts-identity.md).
- Als u meerdere Azure-abonnementen hebt, selecteert u de juiste abonnements-id waarin de resources moeten worden gefactureerd met behulp van de [opdracht az account set](/cli/azure/account#az-account-set) . Zie [Azure-abonnementen beheren - Azure CLI](/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-subscription) voor meer informatie.

## Een brongroep maken

Een [Azure-resourcegroep][azure-resource-group] is een logische groep waarin Azure-resources worden geïmplementeerd en beheerd. Wanneer u een resourcegroep maakt, wordt u gevraagd een locatie op te geven. Deze locatie is de opslaglocatie van de metagegevens van uw resourcegroep en waar uw resources worden uitgevoerd in Azure als u geen andere regio opgeeft tijdens het maken van de resource.

Maak een resourcegroep met behulp van de [`az group create`][az-group-create] opdracht.

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultaten:
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

## Een AKS-cluster maken

Maak een AKS-cluster met behulp van de [`az aks create`][az-aks-create] opdracht. In het volgende voorbeeld wordt een cluster met één knooppunt gemaakt en wordt een door het systeem toegewezen beheerde identiteit ingeschakeld.

```azurecli-interactive
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --node-count 1 \
    --generate-ssh-keys
```

> [!NOTE]
> Wanneer u een nieuw cluster maakt, maakt AKS automatisch een tweede resourcegroep om de AKS-resources op te slaan. Zie voor meer informatie [Waarom worden er twee resourcegroepen gemaakt met AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Verbinding maken met het cluster

Als u een Kubernetes-cluster wilt beheren, gebruikt u de Kubernetes-opdrachtregelclient kubectl[][kubectl]. `kubectl` is al geïnstalleerd als u Azure Cloud Shell gebruikt. Als u lokaal wilt installeren `kubectl` , gebruikt u de [`az aks install-cli`][az-aks-install-cli] opdracht.

1. Configureer `kubectl` deze om verbinding te maken met uw Kubernetes-cluster met behulp van de [opdracht az aks get-credentials][az-aks-get-credentials] . Bij deze opdracht worden referenties gedownload en wordt Kubernetes CLI geconfigureerd voor het gebruik van deze referenties.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Controleer de verbinding met uw cluster met behulp van de [opdracht kubectl get][kubectl-get] . Met deze opdracht wordt een lijst met de clusterknooppunten geretourneerd.

    ```azurecli-interactive
    kubectl get nodes
    ```

## De toepassing implementeren

Als u de toepassing wilt implementeren, gebruikt u een manifestbestand om alle objecten te maken die nodig zijn om de [AKS Store-toepassing](https://github.com/Azure-Samples/aks-store-demo) uit te voeren. Een [Kubernetes-manifestbestand][kubernetes-deployment] definieert de gewenste status van een cluster, zoals welke containerinstallatiekopieën moeten worden uitgevoerd. Het manifest bevat de volgende Kubernetes-implementaties en -services:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Schermopname van azure Store-voorbeeldarchitectuur." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **** Webwinkel: Webtoepassing voor klanten om producten te bekijken en bestellingen te plaatsen.
- **Productservice**: toont productgegevens.
- **Orderservice**: Orders plaatsen.
- **Rabbit MQ**: Berichtenwachtrij voor een orderwachtrij.

> [!NOTE]
> Het is niet raadzaam stateful containers, zoals Rabbit MQ, uit te voeren zonder permanente opslag voor productie. Deze worden hier gebruikt voor het gemak, maar we raden u aan beheerde services te gebruiken, zoals Azure CosmosDB of Azure Service Bus.

1. Maak een bestand met de naam `aks-store-quickstart.yaml` en kopieer dit in het volgende manifest:

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

    Zie Implementaties en YAML-manifestmanifesten voor een uitsplitsing van YAML-manifestbestanden[](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Als u het YAML-bestand lokaal maakt en opslaat, kunt u het manifestbestand uploaden naar uw standaardmap in CloudShell door de **knop Bestanden** uploaden/downloaden te selecteren en het bestand in uw lokale bestandssysteem te selecteren.

1. Implementeer de toepassing met behulp van de [`kubectl apply`][kubectl-apply] opdracht en geef de naam van uw YAML-manifest op.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## De toepassing testen

U kunt controleren of de toepassing wordt uitgevoerd door naar het openbare IP-adres of de toepassings-URL te gaan.

Haal de toepassings-URL op met behulp van de volgende opdrachten:

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

Resultaten:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Schermopname van de AKS Store-voorbeeldtoepassing." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Het cluster verwijderen

Als u niet van plan bent om de [AKS-zelfstudie][aks-tutorial] te doorlopen, moet u overbodige resources opschonen om Azure-kosten te voorkomen. U kunt de resourcegroep, containerservice en alle gerelateerde resources verwijderen met behulp van de [`az group delete`][az-group-delete] opdracht.

> [!NOTE]
> Het AKS-cluster is gemaakt met een door het systeem toegewezen beheerde identiteit. Dit is de standaardidentiteitsoptie die in deze quickstart wordt gebruikt. Het platform beheert deze identiteit, zodat u deze niet handmatig hoeft te verwijderen.

## Volgende stappen

In deze quickstart hebt u een Kubernetes-cluster geïmplementeerd en vervolgens een eenvoudige toepassing met meerdere containers erop geïmplementeerd. Deze voorbeeldtoepassing is alleen bedoeld voor demodoeleinden en vertegenwoordigt niet alle aanbevolen procedures voor Kubernetes-toepassingen. Zie de richtlijnen[ voor AKS-oplossingen voor meer informatie over het maken van volledige oplossingen met AKS voor productie][aks-solution-guidance].

Als u meer wilt weten over AKS en een volledig voorbeeld van code-naar-implementatie wilt doorlopen, gaat u verder met de zelfstudie over het Kubernetes-cluster.

> [!div class="nextstepaction"]
> [AKS-zelfstudie][aks-tutorial]

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
