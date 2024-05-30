---
title: 'Szybki start: wdrażanie klastra usługi Azure Kubernetes Service (AKS) przy użyciu interfejsu wiersza polecenia platformy Azure'
description: 'Dowiedz się, jak szybko wdrożyć klaster Kubernetes i wdrożyć aplikację w usłudze Azure Kubernetes Service (AKS) przy użyciu interfejsu wiersza polecenia platformy Azure.'
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Szybki start: wdrażanie klastra usługi Azure Kubernetes Service (AKS) przy użyciu interfejsu wiersza polecenia platformy Azure

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) to zarządzana usługa platformy Kubernetes, która umożliwia szybkie wdrażanie klastrów i zarządzanie nimi. W tym przewodniku Szybki start zawarto informacje na temat wykonywania następujących czynności:

- Wdrażanie klastra usługi AKS przy użyciu interfejsu wiersza polecenia platformy Azure.
- Uruchom przykładową aplikację z wieloma kontenerami z grupą mikrousług i frontonów internetowych symulujących scenariusz sprzedaży detalicznej.

> [!NOTE]
> Aby rozpocząć szybkie aprowizowanie klastra usługi AKS, ten artykuł zawiera kroki wdrażania klastra z ustawieniami domyślnymi tylko do celów ewaluacyjnych. Przed wdrożeniem klastra gotowego do produkcji zalecamy zapoznanie się z naszą [architekturą][baseline-reference-architecture] referencyjną punktu odniesienia, aby wziąć pod uwagę, jak jest ona zgodna z wymaganiami biznesowymi.

## Zanim rozpoczniesz

W tym przewodniku Szybki start założono, że masz podstawową wiedzę na temat pojęć związanych z rozwiązaniem Kubernetes. Aby uzyskać więcej informacji, zobacz temat [Kubernetes core concepts for Azure Kubernetes Service (AKS)][kubernetes-concepts] (Kubernetes — podstawowe pojęcia dotyczące usługi Azure Kubernetes Service (AKS)).

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Ten artykuł wymaga wersji 2.0.64 lub nowszej interfejsu wiersza polecenia platformy Azure. Jeśli używasz usługi Azure Cloud Shell, najnowsza wersja jest już tam zainstalowana.
- Upewnij się, że tożsamość używana do utworzenia klastra ma odpowiednie minimalne uprawnienia. Aby uzyskać więcej informacji na temat dostępu i tożsamości dla usługi AKS, zobacz [Opcje dostępu i tożsamości dla usługi Azure Kubernetes Service (AKS).](../concepts-identity.md)
- Jeśli masz wiele subskrypcji platformy Azure, wybierz odpowiedni identyfikator subskrypcji, w którym mają być rozliczane zasoby przy użyciu [polecenia az account set](/cli/azure/account#az-account-set) .

## Definiowanie zmiennych środowiskowych

Zdefiniuj następujące zmienne środowiskowe do użycia w tym przewodniku Szybki start:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Tworzenie grupy zasobów

[Grupa][azure-resource-group] zasobów platformy Azure to grupa logiczna, w której zasoby platformy Azure są wdrażane i zarządzane. Podczas tworzenia grupy zasobów zostanie wyświetlony monit o określenie lokalizacji. Ta lokalizacja to lokalizacja magazynu metadanych grupy zasobów i lokalizacja, w której zasoby są uruchamiane na platformie Azure, jeśli nie określisz innego regionu podczas tworzenia zasobów.

Utwórz grupę zasobów przy użyciu [`az group create`][az-group-create] polecenia .

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Wyniki:
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

## Tworzenie klastra AKS

Utwórz klaster usługi AKS przy użyciu [`az aks create`][az-aks-create] polecenia . Poniższy przykład tworzy klaster z jednym węzłem i włącza tożsamość zarządzaną przypisaną przez system.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> Podczas tworzenia nowego klastra usługa AKS automatycznie tworzy drugą grupę zasobów do przechowywania zasobów usługi AKS. Aby uzyskać więcej informacji, zobacz [Dlaczego dwie grupy zasobów są tworzone za pomocą usługi AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Łączenie z klastrem

Aby zarządzać klastrem Kubernetes, użyj klienta wiersza polecenia kubernetes kubectl[][kubectl]. `kubectl` program jest już zainstalowany, jeśli używasz usługi Azure Cloud Shell. Aby zainstalować `kubectl` lokalnie, użyj [`az aks install-cli`][az-aks-install-cli] polecenia .

1. Skonfiguruj, `kubectl` aby nawiązać połączenie z klastrem Kubernetes przy użyciu [polecenia az aks get-credentials][az-aks-get-credentials] . To polecenie powoduje pobranie poświadczeń i zastosowanie ich w konfiguracji interfejsu wiersza polecenia Kubernetes.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Sprawdź połączenie z klastrem przy użyciu [polecenia kubectl get][kubectl-get] . To polecenie zwraca listę węzłów klastra.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Wdrażanie aplikacji

Aby wdrożyć aplikację, należy użyć pliku manifestu, aby utworzyć wszystkie obiekty wymagane do uruchomienia aplikacji[ sklepu ](https://github.com/Azure-Samples/aks-store-demo)AKS. [Plik][kubernetes-deployment] manifestu kubernetes definiuje żądany stan klastra, taki jak obrazy kontenerów do uruchomienia. Manifest obejmuje następujące wdrożenia i usługi Kubernetes:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Zrzut ekranu przedstawiający przykładową architekturę sklepu Azure Store." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **** Front sklepu: aplikacja internetowa dla klientów do wyświetlania produktów i składania zamówień.
- **Usługa** produktu: wyświetla informacje o produkcie.
- **Usługa** zamawiania: umieszcza zamówienia.
- **Rabbit MQ**: kolejka komunikatów dla kolejki zamówień.

> [!NOTE]
> Nie zalecamy uruchamiania kontenerów stanowych, takich jak Rabbit MQ, bez trwałego przechowywania w środowisku produkcyjnym. Są one używane tutaj dla uproszczenia, ale zalecamy korzystanie z usług zarządzanych, takich jak Azure CosmosDB lub Azure Service Bus.

1. Utwórz plik o nazwie `aks-store-quickstart.yaml` i skopiuj go w następującym manifeście:

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

    Aby uzyskać podział plików manifestu YAML, zobacz [Wdrożenia i manifesty](../concepts-clusters-workloads.md#deployments-and-yaml-manifests) YAML.

    Jeśli tworzysz i zapisujesz plik YAML lokalnie, możesz przekazać plik manifestu do katalogu domyślnego w programie CloudShell, wybierając **przycisk Przekaż/Pobierz pliki** i wybierając plik z lokalnego systemu plików.

1. Wdróż aplikację przy użyciu [`kubectl apply`][kubectl-apply] polecenia i określ nazwę manifestu YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Testowanie aplikacji

Możesz sprawdzić, czy aplikacja jest uruchomiona, odwiedzając publiczny adres IP lub adres URL aplikacji.

Pobierz adres URL aplikacji przy użyciu następujących poleceń:

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

Wyniki:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Zrzut ekranu przedstawiający przykładową aplikację sklepu AKS Store." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Usuwanie klastra

Jeśli nie planujesz przechodzenia przez samouczek[ usługi ][aks-tutorial]AKS, wyczyść niepotrzebne zasoby, aby uniknąć opłat za platformę Azure. Za pomocą polecenia możesz usunąć grupę zasobów, usługę [`az group delete`][az-group-delete] kontenera i wszystkie powiązane zasoby.

> [!NOTE]
> Klaster usługi AKS został utworzony przy użyciu przypisanej przez system tożsamości zarządzanej, która jest domyślną opcją tożsamości używaną w tym przewodniku Szybki start. Platforma zarządza tą tożsamością, aby nie trzeba było jej ręcznie usuwać.

## Następne kroki

W tym przewodniku Szybki start wdrożono klaster Kubernetes, a następnie wdrożono w nim prostą aplikację z wieloma kontenerami. Ta przykładowa aplikacja służy tylko do celów demonstracyjnych i nie reprezentuje wszystkich najlepszych rozwiązań dla aplikacji Kubernetes. Aby uzyskać wskazówki dotyczące tworzenia pełnych rozwiązań za pomocą usługi AKS dla środowiska produkcyjnego, zobacz [Wskazówki dotyczące][aks-solution-guidance] rozwiązania AKS.

Aby dowiedzieć się więcej na temat usługi AKS i zapoznać się z kompletnym przykładem kodu do wdrożenia, przejdź do samouczka dotyczącego klastra Kubernetes.

> [!div class="nextstepaction"]
> [Samouczek usługi AKS][aks-tutorial]

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
