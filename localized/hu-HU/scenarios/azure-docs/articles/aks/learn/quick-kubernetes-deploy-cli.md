---
title: 'Rövid útmutató: Azure Kubernetes Service- (AKS-) fürt üzembe helyezése az Azure CLI használatával'
description: 'Megtudhatja, hogyan helyezhet üzembe gyorsan egy Kubernetes-fürtöt, és hogyan helyezhet üzembe alkalmazásokat az Azure Kubernetes Service-ben (AKS) az Azure CLI használatával.'
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Rövid útmutató: Azure Kubernetes Service- (AKS-) fürt üzembe helyezése az Azure CLI használatával

[![Üzembe helyezés az Azure-ban](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Az Azure Kubernetes Service (AKS) egy felügyelt Kubernetes-szolgáltatás, amely lehetővé teszi a fürtök gyors üzembe helyezését és kezelését. Ezen rövid útmutató segítségével megtanulhatja a következőket:

- AKS-fürt üzembe helyezése az Azure CLI használatával.
- Többtárolós mintaalkalmazás futtatása mikroszolgáltatások és webes kezelőfelületek egy kiskereskedelmi forgatókönyvet szimuláló csoportjával.

> [!NOTE]
> Az AKS-fürtök gyors üzembe helyezésének megkezdéséhez ez a cikk a csak kiértékelési célokra alapértelmezett beállításokkal rendelkező fürtök üzembe helyezésének lépéseit tartalmazza. Az éles üzemre kész fürtök üzembe helyezése előtt javasoljuk, hogy ismerkedjen meg az alapszintű referenciaarchitektúrával[][baseline-reference-architecture], és gondolja át, hogyan igazodik az üzleti követelményekhez.

## Mielőtt elkezdené

A rövid útmutató feltételezi, hogy rendelkezik a Kubernetes használatára vonatkozó alapvető ismeretekkel. További információkért tekintse meg [az Azure Kubernetes Service (AKS)][kubernetes-concepts] Kubernetes alapfogalmait.

- [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Ez a cikk az Azure CLI 2.0.64-es vagy újabb verzióját igényli. Az Azure Cloud Shell használata esetén a legújabb verzió már telepítve van.
- Győződjön meg arról, hogy a fürt létrehozásához használt identitás rendelkezik a megfelelő minimális engedélyekkel. Az AKS-hez való hozzáféréssel és identitással kapcsolatos további részletekért tekintse meg [az Azure Kubernetes Service (AKS)](../concepts-identity.md) hozzáféréssel és identitással kapcsolatos lehetőségeit.
- Ha több Azure-előfizetéssel rendelkezik, válassza ki a megfelelő előfizetés-azonosítót, amelyben az erőforrásokat az [az account set](/cli/azure/account#az-account-set) paranccsal kell számlázni. További információ: [Azure-előfizetések kezelése – Azure CLI](/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-subscription).

## Környezeti változók definiálása

Adja meg a következő környezeti változókat a rövid útmutatóban való használathoz:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Erőforráscsoport létrehozása

Az [Azure-erőforráscsoportok][azure-resource-group] olyan logikai csoportok, amelyekben az Azure-erőforrások üzembe helyezése és kezelése történik. Erőforráscsoport létrehozásakor a rendszer kérni fogja, hogy adjon meg egy helyet. Ez a hely az erőforráscsoport metaadatainak tárolási helye, és ahol az erőforrások az Azure-ban futnak, ha nem ad meg egy másik régiót az erőforrás létrehozása során.

Hozzon létre egy erőforráscsoportot a [`az group create`][az-group-create] paranccsal.

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Eredmények:
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

## AKS-fürt létrehozása

Hozzon létre egy AKS-fürtöt a [`az aks create`][az-aks-create] paranccsal. Az alábbi példa egy egy csomóponttal rendelkező fürtöt hoz létre, és engedélyezi a rendszer által hozzárendelt felügyelt identitást.

```azurecli-interactive
az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --node-count 1 \
    --generate-ssh-keys
```

> [!NOTE]
> Új fürt létrehozásakor az AKS automatikusan létrehoz egy második erőforráscsoportot az AKS-erőforrások tárolásához. További információ: [Miért jön létre két erőforráscsoport az AKS-sel?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Csatlakozás a fürthöz

Kubernetes-fürt kezeléséhez használja a Kubernetes parancssori ügyfelet, [a kubectl-et][kubectl]. `kubectl` az Azure Cloud Shell használata esetén már telepítve van. A helyi telepítéshez `kubectl` használja a [`az aks install-cli`][az-aks-install-cli] parancsot.

1. Konfigurálja `kubectl` a Kubernetes-fürthöz való csatlakozást az az aks [get-credentials][az-aks-get-credentials] paranccsal. Ez a parancs letölti a hitelesítő adatokat, és konfigurálja a Kubernetes parancssori felületét a használatukhoz.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Ellenőrizze a fürthöz való kapcsolatot a [kubectl get][kubectl-get] paranccsal. Ez a parancs a fürtcsomópontok listáját adja vissza.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Az alkalmazás üzembe helyezése

Az alkalmazás üzembe helyezéséhez egy jegyzékfájl használatával hozza létre az AKS Store-alkalmazás[ futtatásához ](https://github.com/Azure-Samples/aks-store-demo)szükséges összes objektumot. A [Kubernetes-jegyzékfájl][kubernetes-deployment] meghatározza a fürt kívánt állapotát, például hogy mely tárolólemezképeket kell futtatni. A jegyzék a következő Kubernetes-üzemelő példányokat és szolgáltatásokat tartalmazza:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Képernyőkép az Azure Store mintaarchitektúrájáról." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Áruházi előtér**: Webalkalmazás az ügyfelek számára termékek megtekintésére és megrendelések leadására.
- **Termékszolgáltatás**: A termékinformációkat jeleníti meg.
- **Rendelési szolgáltatás**: Rendeléseket rendel.
- **Nyúl MQ**: Üzenetsor rendelési üzenetsorhoz.

> [!NOTE]
> Nem javasoljuk az állapotalapú tárolók( például a Rabbit MQ) futtatását az éles környezetben tartós tárolás nélkül. Ezeket itt az egyszerűség kedvéért használjuk, de olyan felügyelt szolgáltatások használatát javasoljuk, mint az Azure CosmosDB vagy az Azure Service Bus.

1. Hozzon létre egy fájlt, `aks-store-quickstart.yaml` és másolja a következő jegyzékbe:

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

    A YAML-jegyzékfájlok lebontásához tekintse meg [az üzembe helyezéseket és a YAML-jegyzékeket](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Ha helyileg hozza létre és menti a YAML-fájlt, feltöltheti a jegyzékfájlt az alapértelmezett könyvtárba a CloudShellben a **Fájlok** feltöltése/letöltése gombra kattintva, majd kiválasztva a fájlt a helyi fájlrendszerből.

1. Telepítse az alkalmazást a [`kubectl apply`][kubectl-apply] paranccsal, és adja meg a YAML-jegyzék nevét.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Az alkalmazás tesztelése

A nyilvános IP-cím vagy az alkalmazás URL-címének megtekintésével ellenőrizheti, hogy az alkalmazás fut-e.

Kérje le az alkalmazás URL-címét a következő parancsokkal:

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

Eredmények:
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Képernyőkép az AKS Store mintaalkalmazásról." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## A fürt törlése

Ha nem tervezi végigvezetni az [AKS-oktatóanyagot][aks-tutorial], törölje a felesleges erőforrásokat az Azure-díjak elkerülése érdekében. A parancs használatával eltávolíthatja az erőforráscsoportot, a tárolószolgáltatást és az összes kapcsolódó erőforrást [`az group delete`][az-group-delete] .

> [!NOTE]
> Az AKS-fürt egy rendszer által hozzárendelt felügyelt identitással lett létrehozva, amely az ebben a rövid útmutatóban használt alapértelmezett identitásbeállítás. A platform kezeli ezt az identitást, így önnek nem kell manuálisan eltávolítania.

## Következő lépések

Ebben a rövid útmutatóban üzembe helyezett egy Kubernetes-fürtöt, majd üzembe helyezett egy egyszerű többtárolós alkalmazást. Ez a mintaalkalmazás csak bemutató célokra készült, és nem képviseli a Kubernetes-alkalmazások ajánlott eljárásait. Az éles AKS-sel való teljes megoldások létrehozásáról az AKS-megoldásokkal kapcsolatos útmutatást[ talál][aks-solution-guidance].

Ha többet szeretne megtudni az AKS-ről, és végig szeretne járni egy teljes kód–üzembe helyezési példán, folytassa a Kubernetes-fürt oktatóanyagával.

> [!div class="nextstepaction"]
> [AKS-oktatóanyag][aks-tutorial]

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