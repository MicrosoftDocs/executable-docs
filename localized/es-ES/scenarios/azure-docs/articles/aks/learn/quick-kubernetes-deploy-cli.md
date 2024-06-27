# Inicio rápido: Implementación de un clúster de Azure Kubernetes Service (AKS) con la CLI de Azure

[![Implementación en Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) es un servicio de Kubernetes administrado que le permite implementar y administrar clústeres rápidamente. En esta guía de inicio rápido, ha aprendido a hacer lo siguiente:

- Implementación de un clúster de AKS con la CLI de Azure.
- Ejecute una aplicación de varios contenedores de ejemplo con un grupo de microservicios y front-end web simulando un escenario comercial.

> [!NOTE]
> Para empezar a aprovisionar rápidamente un clúster de AKS, en este artículo se incluyen los pasos para implementar un clúster con la configuración predeterminada solo con fines de evaluación. Antes de implementar un clúster listo para producción, se recomienda familiarizarse con nuestra [arquitectura de referencia de línea de base][baseline-reference-architecture] para considerar cómo se alinea con sus requisitos empresariales.

## Antes de empezar

En esta guía rápida se presupone un conocimiento básico de los conceptos de Kubernetes. Para más información, consulte [Conceptos básicos de Kubernetes de Azure Kubernetes Service (AKS)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- En este artículo se necesita la versión 2.0.64 de la CLI de Azure, o cualquier versión posterior. Si usa Azure Cloud Shell, ya está instalada allí la versión más reciente.
- Asegúrese de que la identidad que usará para crear el clúster tenga los permisos mínimos adecuados. Para más información sobre el acceso y la identidad en AKS, consulte [Opciones de acceso e identidad en Azure Kubernetes Service (AKS)](../concepts-identity.md).
- Si tiene varias suscripciones de Azure, seleccione el identificador de suscripción adecuado en el que se deben facturar los recursos con el comando [az account set](/cli/azure/account#az-account-set). Para más información, consulte [Administración de suscripciones de Azure: CLI de Azure](/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-subscription).

## Definición de las variables de entorno

Defina las siguientes variables de entorno para usarlas en este inicio rápido:

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Crear un grupo de recursos

Un [grupo de recursos de Azure][azure-resource-group] es un grupo lógico en el que se implementan y administran recursos de Azure. Cuando crea un grupo de recursos, se le pide que especifique una ubicación. Esta ubicación es la ubicación de almacenamiento de los metadatos del grupo de recursos y donde se ejecutan los recursos en Azure si no se especifica otra región durante la creación de recursos.

Cree un grupo de recursos con el comando [`az group create`][az-group-create].

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

## Creación de un clúster de AKS

Cree un clúster de AKS con el comando [`az aks create`][az-aks-create]. En el ejemplo siguiente se crea un clúster con un nodo y se habilita una identidad administrada asignada por el sistema.

```azurecli-interactive
az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --node-count 1 \
    --generate-ssh-keys
```

> [!NOTE]
> Al crear un nuevo clúster, AKS crea automáticamente un segundo grupo de recursos para almacenar los recursos de AKS. Para más información, consulte [¿Por qué se crean dos grupos de recursos con AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Conectarse al clúster

Para administrar un clúster de Kubernetes, use [kubectl][kubectl], el cliente de línea de comandos de Kubernetes. Si usa Azure Cloud Shell, `kubectl` ya está instalado. Para instalar `kubectl` localmente, use el comando [`az aks install-cli`][az-aks-install-cli].

1. Para configurar `kubectl` para conectarse a su clúster de Kubernetes, use el comando [az aks get-credentials][az-aks-get-credentials]. Con este comando se descargan las credenciales y se configura la CLI de Kubernetes para usarlas.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Compruebe la conexión al clúster con el comando [kubectl get][kubectl-get]. Este comando devuelve una lista de los nodos del clúster.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Implementación de la aplicación

Para implementar la aplicación, se usa un archivo de manifiesto para crear todos los objetos necesarios para ejecutar la [aplicación AKS Store](https://github.com/Azure-Samples/aks-store-demo). Un [archivo de manifiesto de Kubernetes][kubernetes-deployment] define el estado deseado del clúster, por ejemplo, qué imágenes de contenedor se van a ejecutar. El manifiesto incluye las siguientes implementaciones y servicios de Kubernetes:

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Captura de pantalla de la arquitectura de ejemplo de Azure Store." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Escaparate**: aplicación web para que los clientes vean productos y realicen pedidos.
- **Servicio de producto**: muestra información del producto.
- **Servicio de pedidos**: realiza pedidos.
- **Rabbit MQ**: cola de mensajes para una cola de pedidos.

> [!NOTE]
> No se recomienda ejecutar contenedores con estado, como Rabbit MQ, sin almacenamiento persistente para producción. Estos se usan aquí para simplificar, pero se recomienda usar servicios administrados, como Azure CosmosDB o Azure Service Bus.

1. Cree un archivo denominado `aks-store-quickstart.yaml` y cópielo en el siguiente manifiesto:

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

    Para obtener un desglose de los archivos de manifiesto de YAML, consulte [Implementaciones y manifiestos de YAML](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Si crea y guarda el archivo YAML localmente, para cargar el archivo de manifiesto en el directorio predeterminado de CloudShell, seleccione el botón **Cargar y descargar archivos** y elija el archivo en el sistema de archivos local.

1. Implemente la aplicación mediante el comando [`kubectl apply`][kubectl-apply] y especifique el nombre del manifiesto de YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Prueba de la aplicación

Puede validar que la aplicación se está ejecutando visitando la dirección IP pública o la dirección URL de la aplicación.

Obtenga la dirección URL de la aplicación mediante los siguientes comandos:

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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Captura de pantalla de la aplicación de ejemplo de la Tienda AKS." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Eliminación del clúster

Si no tiene previsto seguir el [tutorial de AKS][aks-tutorial], limpie los recursos innecesarios para evitar cargos de Azure. Puede quitar el grupo de recursos, el servicio de contenedor y todos los recursos relacionados mediante el comando [`az group delete`][az-group-delete].

> [!NOTE]
> El clúster de AKS se creó con una identidad administrada asignada por el sistema, que es la opción de identidad predeterminada utilizada en este inicio rápido. La plataforma administra esta identidad para que no tenga que quitarla manualmente.

## Pasos siguientes

En este inicio rápido, ha implementado un clúster de Kubernetes y luego ha implementado en él una aplicación simple de varios contenedores. Esta aplicación de ejemplo es solo para fines de demostración y no representa todos los procedimientos recomendados para las aplicaciones de Kubernetes. Para instrucciones sobre cómo crear soluciones completas con AKS para producción, consulte [Guía de soluciones de AKS][aks-solution-guidance].

Para obtener más información sobre AKS y un ejemplo completo desde el código hasta la implementación, continúe con el tutorial del clúster de Kubernetes.

> [!div class="nextstepaction"]
> [Tutorial de AKS][aks-tutorial]

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
