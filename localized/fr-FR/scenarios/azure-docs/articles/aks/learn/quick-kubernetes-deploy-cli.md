---
title: "Démarrage rapide\_: Déployer un cluster AKS (Azure Kubernetes\_Service) avec Azure CLI"
description: Découvrez comment déployer rapidement un cluster Kubernetes et déployer une application dans Azure Kubernetes Service (AKS) à l’aide d’Azure CLI.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: 'H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content'
---

# Démarrage rapide : Déployer un cluster AKS (Azure Kubernetes Service) avec Azure CLI

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

AKS (Azure Kubernetes Service) est un service Kubernetes managé qui vous permet de déployer et de gérer rapidement des clusters. Dans ce guide de démarrage rapide, vous apprenez à :

- Déployer un cluster AKS dans le portail Azure.
- Exécutez un exemple d’application multiconteneur avec un groupe de microservices et de serveurs web frontaux simulant un scénario de vente au détail.

> [!NOTE]
> Dans cet article, vous trouverez les étapes à suivre pour déployer rapidement un cluster AKS. Les paramètres par défaut sont utilisés à des fins d'évaluation uniquement. Avant de déployer un cluster prêt pour la production, nous vous recommandons de vous familiariser avec notre [architecture de référence de base][baseline-reference-architecture] pour prendre en compte la façon dont elle s’aligne sur vos besoins métier.

## Avant de commencer

Ce guide de démarrage rapide suppose une compréhension élémentaire des concepts liés à Kubernetes. Pour plus d’informations, consultez [Concepts de base de Kubernetes pour AKS (Azure Kubernetes Service)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](../../../includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- Cet article nécessite la version 2.0.64 ou ultérieure de l’interface Azure CLI. Si vous utilisez Azure Cloud Shell, sachez que la dernière version y est déjà installée.
- Veillez à ce que l’identité que vous utilisez pour créer votre cluster dispose des autorisations minimales appropriées. Pour plus d’informations sur l’accès et l’identité pour AKS, consultez [Options d’accès et d’identité pour Kubernetes Azure Service (AKS)](../concepts-identity.md).
- Si vous avez plusieurs abonnements Azure, sélectionnez l’identifiant d’abonnement approprié dans lequel les ressources doivent être facturées avec la commande [az account set](/cli/azure/account#az-account-set).

## Définissez des variables d’environnement

Définissez les variables d’environnement suivantes à utiliser dans ce guide de démarrage rapide :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
```

## Créer un groupe de ressources

Un [groupe de ressources Azure][azure-resource-group] est un groupe logique dans lequel des ressources Azure sont déployées et gérées. Lorsque vous créez un groupe de ressources, vous êtes invité à spécifier un emplacement. Cet emplacement est l'emplacement de stockage des métadonnées de votre groupe de ressources et l'endroit où vos ressources s'exécutent dans Azure si vous ne spécifiez pas une autre région lors de la création de la ressource.

Créez un groupe de ressources avec la commande [`az group create`][az-group-create].

```azurecli-interactive
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Résultats :
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

## Créer un cluster AKS

Créez un cluster AKS avec la commande [`az aks create`][az-aks-create]. L’exemple suivant crée un cluster avec un nœud et active une identité managée affectée par le système.

```azurecli-interactive
az aks create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --enable-managed-identity --node-count 1 --generate-ssh-keys
```

> [!NOTE]
> Lors de la création d’un nouveau cluster, un deuxième groupe de ressources est automatiquement créé par AKS pour stocker les ressources AKS. Pour plus d’informations, consultez [Pourquoi deux groupes de ressources sont-ils créés avec AKS ?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Se connecter au cluster

Pour gérer un cluster Kubernetes, utilisez [kubectl][kubectl], le client de ligne de commande Kubernetes. Si vous utilisez Azure Cloud Shell, `kubectl` est déjà installé. Pour installer `kubectl` localement, utilisez la commande [`az aks install-cli`][az-aks-install-cli] .

1. Configurez `kubectl` afin de vous connecter à votre cluster Kubernetes avec la commande [az aks get-credentials][az-aks-get-credentials]. Cette commande télécharge les informations d’identification et configure l’interface CLI Kubernetes pour les utiliser.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Pour vérifier la connexion à votre cluster, exécutez la commande [kubectl get][kubectl-get]. Cette commande renvoie la liste des nœuds de cluster.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Déployer l’application

Pour déployer l'application, vous utilisez un fichier manifeste pour créer tous les objets nécessaires à l'exécution de l'[application AKS Store](https://github.com/Azure-Samples/aks-store-demo). Un [fichier manifeste Kubernetes][kubernetes-deployment] définit un état souhaité d’un cluster, notamment les images conteneur à exécuter. Le manifeste inclut les déploiements et services Kubernetes suivants :

:::image type="content" source="media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Capture d’écran de l’architecture d’exemple Azure Store." lightbox="media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Vitrine** : application web permettant aux clients d’afficher les produits et de passer des commandes.
- **Service de produit** : affiche les informations sur le produit.
- **Service de commande** : passe des commandes.
- **Rabbit MQ** : file d’attente de messages pour une file d’attente de commandes.

> [!NOTE]
> Nous ne recommandons pas l'exécution de conteneurs avec état, comme Rabbit MQ, sans stockage persistant pour la production. Ils sont utilisés ici par souci de simplicité, mais nous vous recommandons d’utiliser des services gérés, tels qu’Azure CosmosDB ou Azure Service Bus.

1. Créez un fichier nommé `aks-store-quickstart.yaml` et copiez-y le manifeste suivant :

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

    Pour obtenir une décomposition des fichiers manifeste YAML, consultez [Déploiements et manifestes YAML](../concepts-clusters-workloads.md#deployments-and-yaml-manifests).

    Si vous créez et que vous enregistrez le fichier YAML localement, vous pouvez charger le fichier manifeste dans votre répertoire par défaut dans CloudShell en sélectionnant le bouton **Charger/télécharger des fichiers**, puis en sélectionnant le fichier dans votre système de fichiers local.

1. Déployez l’application à l’aide de la commande [`kubectl apply`][kubectl-apply] et spécifiez le nom de votre manifeste YAML.

    ```azurecli-interactive
    kubectl apply -f aks-store-quickstart.yaml
    ```

## Tester l’application

Vous pouvez vérifier que l’application est en cours d’exécution en consultant l’adresse IP publique ou l’URL de l’application.

Obtenez l’URL de l’application à l’aide des commandes suivantes :

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

Résultats :
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

:::image type="content" source="media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Capture d’écran de l’exemple d’application AKS Store." lightbox="media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Supprimer le cluster

Pour éviter les frais Azure, si vous ne prévoyez pas de suivre le [Tutoriel AKS][aks-tutorial], nettoyez vos ressources inutiles. Vous pouvez supprimer le groupe de ressources, le service conteneur et toutes les ressources associées à l’aide de la commande [`az group delete`][az-group-delete].

> [!NOTE]
> Le cluster AKS a été créé avec une identité managée affectée par le système, qui est l’option d’identité par défaut utilisée dans ce guide de démarrage rapide. La plateforme gère cette identité afin que vous n’ayez pas besoin de la supprimer manuellement.

## Étapes suivantes

Dans ce Démarrage rapide, vous avez déployé un cluster Kubernetes dans lequel vous avez ensuite déployé une application de plusieurs conteneurs. Cet exemple d’application est fourni à des fins de version de démonstration uniquement et ne représente pas toutes les meilleures pratiques pour les applications Kubernetes. Pour obtenir des conseils sur la création de solutions complètes avec AKS pour la production, consultez [Conseils pour les solutions AKS][aks-solution-guidance].

Pour en savoir plus sur AKS et parcourir l’exemple complet allant du code au déploiement, passez au tutoriel sur le cluster Kubernetes.

> [!div class="nextstepaction"]
> [Didacticiel AKS][aks-tutorial]

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
