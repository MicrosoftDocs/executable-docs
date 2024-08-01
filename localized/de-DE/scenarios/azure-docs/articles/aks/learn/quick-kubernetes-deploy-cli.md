---
title: "Schnellstart: Bereitstellen eines Azure Kubernetes Service-Clusters (AKS) mit Azure\_CLI"
description: 'Hier erfahren Sie, wie Sie über Azure CLI schnell ein Kubernetes-Cluster und eine Anwendung in Azure Kubernetes Service (AKS) bereitstellen.'
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Schnellstart: Bereitstellen eines Azure Kubernetes Service-Clusters (AKS) mit Azure CLI

[![Bereitstellung in Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) ist ein verwalteter Kubernetes-Dienst, mit dem Sie schnell Cluster bereitstellen und verwalten können. In dieser Schnellstartanleitung wird Folgendes vermittelt:

- Bereitstellen eines AKS-Clusters mithilfe der Azure CLI
- Führen Sie eine Beispielanwendung mit mehreren Containern mit einer Gruppe von Microservices und Web-Front-Ends aus, die ein Einzelhandelsszenario simulieren.

> [!NOTE]
> Um schnell mit der Bereitstellung eines AKS-Clusters zu beginnen, enthält dieser Artikel Schritte zum Bereitstellen eines Clusters mit Standardeinstellungen nur zu Evaluierungszwecken. Bevor Sie einen produktionsbereiten Cluster bereitstellen, empfehlen wir Ihnen, sich mit unserer [Baselinereferenzarchitektur][baseline-reference-architecture] vertraut zu machen, um zu prüfen, inwiefern sie Ihren Geschäftsanforderungen entspricht.

## Voraussetzungen

Für diese Schnellstartanleitung werden Grundkenntnisse in Bezug auf die Kubernetes-Konzepte vorausgesetzt. Weitere Informationen finden Sie unter [Grundlegende Kubernetes-Konzepte für Azure Kubernetes Service (AKS)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Für diesen Artikel ist mindestens Version 2.0.64 der Azure CLI erforderlich. Bei Verwendung von Azure Cloud Shell ist die aktuelle Version bereits installiert.
- Stellen Sie sicher, dass die Identität, die Sie zum Erstellen Ihres Clusters verwenden, über die erforderlichen Mindestberechtigungen verfügt. Weitere Informationen zu Zugriff und Identität für AKS finden Sie unter [Zugriffs- und Identitätsoptionen für Azure Kubernetes Service (AKS)](../concepts-identity.md).
- Wenn Sie über mehrere Azure-Abonnements verfügen, wählen Sie mithilfe des Befehls [az account set](/cli/azure/account#az-account-set) die ID des Abonnements aus, in dem die Ressourcen fakturiert werden sollen. Weitere Informationen finden Sie unter [Verwalten von Azure-Abonnementen – Azure CLI](/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-subscription).

## Definieren von Umgebungsvariablen

Definieren Sie die folgenden Umgebungsvariablen für die Verwendung in dieser Schnellstartanleitung:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Erstellen einer Ressourcengruppe

Eine [Azure-Ressourcengruppe][azure-resource-group] ist eine logische Gruppe, in der Azure-Ressourcen bereitgestellt und verwaltet werden. Wenn Sie eine Ressourcengruppe erstellen, werden Sie zur Angabe eines Speicherorts aufgefordert. An diesem Speicherort werden die Metadaten Ihrer Ressourcengruppe gespeichert. Darüber hinaus werden dort die Ressourcen in Azure ausgeführt, wenn Sie während der Ressourcenerstellung keine andere Region angeben.

Erstellen Sie mit dem Befehl [`az group create`][az-group-create] eine Ressourcengruppe.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Ergebnisse:
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

## Erstellen eines AKS-Clusters

Erstellen Sie mit dem Befehl [`az aks create`][az-aks-create] einen AKS-Cluster. Im folgenden Beispiel wird ein Cluster mit einem Knoten erstellt und eine systemseitig zugewiesene verwaltete Identität aktiviert.

```azurecli-interactive
az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --node-count 1 \
    --generate-ssh-keys
```

> [!NOTE]
> Beim Erstellen eines neuen Clusters erstellt AKS automatisch eine zweite Ressourcengruppe, um die AKS-Ressourcen zu speichern. Weitere Informationen finden Sie unter [Warum werden zwei Ressourcengruppen mit AKS erstellt?](../faq.md#why-are-two-resource-groups-created-with-aks).

## Herstellen einer Verbindung mit dem Cluster

Verwenden Sie zum Verwalten eines Kubernetes-Clusters den Kubernetes-Befehlszeilenclient [kubectl][kubectl]. `kubectl` ist bei Verwendung von Azure Cloud Shell bereits installiert. Um `kubectl` lokal zu installieren, verwenden Sie den Befehl [`az aks install-cli`][az-aks-install-cli].

1. Mit dem Befehl [az aks get-credentials][az-aks-get-credentials] können Sie `kubectl` für die Verbindungsherstellung mit Ihrem Kubernetes-Cluster konfigurieren. Mit diesem Befehl werden die Anmeldeinformationen heruntergeladen, und die Kubernetes-Befehlszeilenschnittstelle wird für deren Verwendung konfiguriert.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Überprüfen Sie die Verbindung mit dem Cluster mithilfe des Befehls [kubectl get][kubectl-get]. Dieser Befehl gibt eine Liste der Clusterknoten zurück.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Bereitstellen der Anwendung

Zum Bereitstellen der Anwendung verwenden Sie eine Manifestdatei, um alle Objekte zu erstellen, die für die Ausführung der [AKS Store-Anwendung](https://github.com/Azure-Samples/aks-store-demo)erforderlich sind. Eine [Kubernetes-Manifestdatei][kubernetes-deployment] definiert den gewünschten Zustand (Desired State) eines Clusters – also beispielsweise, welche Containerimages ausgeführt werden sollen. Das Manifest umfasst die folgenden Kubernetes-Bereitstellungen und -Dienste:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Screenshot: Beispielarchitektur für einen Azure-Store." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Store Front:** Webanwendung für Kund*innen zum Anzeigen von Produkten und Aufgeben von Bestellungen
- **Product Service:** zeigt Produktinformationen an.
- **Order Service:** dient der Aufgabe von Bestellungen.
- **Rabbit MQ:** Nachrichtenwarteschlange für eine Bestellwarteschlange

> [!NOTE]
> Zustandsbehaftete Container wie Rabbit MQ sollten nicht ohne permanenten Speicher für die Produktion ausgeführt werden. Sie werden hier der Einfachheit halber verwendet, jedoch sollten verwaltete Dienste wie Azure CosmosDB oder Azure Service Bus verwendet werden.

1. Erstellen Sie eine Datei namens `aks-store-quickstart.yaml`, und fügen Sie das folgende Manifest ein:

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

    Eine Aufschlüsselung der YAML-Manifestdateien finden Sie unter [Bereitstellungen und YAML-Manifeste](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Wenn Sie die YAML-Datei lokal erstellen und speichern, können Sie die Manifestdatei in Ihr Standardverzeichnis in CloudShell hochladen, indem Sie die Schaltfläche **Dateien hochladen/herunterladen** auswählen und die Datei aus Ihrem lokalen Dateisystem auswählen.

1. Stellen Sie die Anwendung über den Befehl „[`kubectl apply`][kubectl-apply]“ bereit, und geben Sie den Namen Ihres YAML-Manifests an.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Testen der App

Sie können überprüfen, ob die Anwendung ausgeführt wird, indem Sie die öffentliche IP-Adresse oder die Anwendungs-URL aufrufen.

Rufen Sie die Anwendungs-URL mit den folgenden Befehlen ab:

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

Ergebnisse:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Screenshot: Beispielanwendung für einen AKS-Store." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Löschen des Clusters

Wenn Sie nicht planen, das [AKS-Tutorial][aks-tutorial] zu durchlaufen, bereinigen Sie unnötige Ressourcen, um Azure-Gebühren zu vermeiden. Sie können die Ressourcengruppe, den Containerdienst und alle zugehörigen Ressourcen mithilfe des Befehls [`az group delete`][az-group-delete] entfernen.

> [!NOTE]
> Der AKS-Cluster wurde mit einer systemseitig zugewiesenen verwalteten Identität erstellt. Dies ist die Standardidentitätsoption, die in dieser Schnellstartanleitung verwendet wird. Die Plattform verwaltet diese Identität, sodass Sie sie nicht manuell entfernen müssen.

## Nächste Schritte

In dieser Schnellstartanleitung haben Sie einen Kubernetes-Cluster und eine Beispielanwendung mit mehreren Containern dafür bereitgestellt. Diese Beispielanwendung dient nur zu Demozwecken und stellt nicht alle bewährten Methoden für Kubernetes-Anwendungen dar. Anleitungen zum Erstellen vollständiger Lösungen mit AKS für die Produktion finden Sie unter [AKS-Lösungsleitfaden][aks-solution-guidance].

Weitere Informationen zu Azure Kubernetes Service (AKS) sowie ein vollständiges Beispiel vom Code bis zur Bereitstellung finden Sie im Tutorial zu Kubernetes-Clustern.

> [!div class="nextstepaction"]
> [AKS-Tutorial][aks-tutorial]

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