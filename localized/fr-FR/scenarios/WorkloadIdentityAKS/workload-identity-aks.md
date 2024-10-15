---
title: Déployer et configurer un cluster AKS avec une identité de charge de travail
description: 'Dans cet article Azure Kubernetes Service (AKS), vous déployez un cluster Azure Kubernetes Service et le configurez avec une identité Microsoft Entra Workload ID.'
author: tamram
ms.topic: article
ms.subservice: aks-security
ms.custom: devx-track-azurecli
ms.date: 05/28/2024
ms.author: tamram
---

# Déployer et configurer une identité de charge de travail dans un cluster Azure Kubernetes Service (AKS)

AKS (Azure Kubernetes Service) est un service Kubernetes managé qui vous permet de déployer et de gérer rapidement des clusters Kubernetes. Cet article vous montre comment :

* Déployez un cluster AKS à l’aide d’Azure CLI avec l’émetteur OpenID Connect et une identité de charge de travail Microsoft Entra.
* Créer Microsoft Entra Workload ID et un compte de service Kubernetes.
* Configurez l’identité managée pour la fédération de jeton.
* Déployez la charge de travail et vérifiez l’authentification avec l’identité de la charge de travail.
* Accordez éventuellement à un pod dans le cluster l’accès aux secrets dans un coffre de clés Azure.

Cet article part du principe que vous avez une compréhension de base des concepts de Kubernetes. Pour plus d’informations, consultez [Concepts de base de Kubernetes pour AKS (Azure Kubernetes Service)][kubernetes-concepts]. Si vous ne connaissez pas le concept Microsoft Entra Workload ID, consultez l’article [Vue d’ensemble][workload-identity-overview] suivant.

## Prérequis

* [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]
* Cet article nécessite la version 2.47.0 ou ultérieure de Azure CLI. Si vous utilisez Azure Cloud Shell, la version la plus récente est déjà installée.
* Vérifiez que l’identité que vous utilisez pour créer votre cluster dispose des autorisations minimales appropriées. Pour plus d’informations concernant l’accès et l’identité pour AKS, consultez [Options d’accès et d’identité pour Kubernetes Azure Service (AKS)][aks-identity-concepts].
* Si vous avez plusieurs abonnements Azure, sélectionnez l’identifiant d’abonnement approprié dans lequel les ressources doivent être facturées avec la commande [az account set][az-account-set].

> [!NOTE]
> Vous pouvez utiliser le _Connecteur de services_ pour vous aider à configurer automatiquement certaines étapes. Consultez également : [Tutoriel : Se connecter à un compte Stockage Azure dans Azure Kubernetes Service (AKS) avec le Connecteur de services à l’aide de l’identité de charge de travail][tutorial-python-aks-storage-workload-identity].

## Créer un groupe de ressources

Un [groupe de ressources Azure][azure-resource-group] est un groupe logique dans lequel des ressources Azure sont déployées et gérées. Lorsque vous créez un groupe de ressources, vous êtes invité à spécifier un emplacement. Cet emplacement est l'emplacement de stockage des métadonnées de votre groupe de ressources et l'endroit où vos ressources s'exécutent dans Azure si vous ne spécifiez pas une autre région lors de la création de la ressource.

Créez un groupe de ressources avec la commande [az group create][az-group-create] :

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export RESOURCE_GROUP="myResourceGroup$RANDOM_ID"
export LOCATION="centralindia"
az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
```

L’exemple de sortie suivant montre la création réussie d’un groupe de ressources :

Résultats :
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Créer un cluster AKS

Créez un cluster AKS à l’aide de la commande [az aks create][az-aks-create] avec le paramètre `--enable-oidc-issuer` pour activer l’émetteur OIDC. L’exemple suivant crée un cluster contenant un nœud unique :

```azurecli-interactive
export CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity \
    --generate-ssh-keys
```

Au bout de quelques minutes, la commande se termine et retourne des informations au format JSON sur le cluster.

> [!NOTE]
> Lors de la création d’un cluster AKS, un deuxième groupe de ressources est automatiquement créé pour stocker les ressources AKS. Pour plus d’informations, consultez [Pourquoi deux groupes de ressources sont-ils créés avec AKS ?][aks-two-resource-groups].

## Mettre à jour un cluster AKS existant

Vous pouvez mettre à jour un cluster AKS afin qu’il utilise l’émetteur OIDC et activer l’identité de charge de travail à l’aide de la commande [az aks update][az aks update] avec les paramètres `--enable-oidc-issuer` et `--enable-workload-identity`. L’exemple suivant met à jour un cluster existant :

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-oidc-issuer \
    --enable-workload-identity
```

## Obtenir l’URL de l’émetteur OIDC

Pour obtenir l’URL de l’émetteur OIDC et l’enregistrer dans une variable d’environnement, exécutez la commande suivante :

```azurecli-interactive
export AKS_OIDC_ISSUER="$(az aks show --name "${CLUSTER_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "oidcIssuerProfile.issuerUrl" \
    --output tsv)"
```

La variable d’environnement doit contenir l’URL de l’émetteur, comme décrit dans l’exemple suivant :

```output
https://eastus.oic.prod-aks.azure.com/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/
```

Par défaut, l’émetteur est défini pour utiliser l’URL de base `https://{region}.oic.prod-aks.azure.com/{tenant_id}/{uuid}`, avec la valeur de `{region}` qui correspond à l’emplacement de déploiement du cluster AKS. La valeur `{uuid}` représente la clé OIDC générée de manière aléatoire pour chaque cluster immuable.

## Créer une identité managée

Appelez la commande [az identity create][az-identity-create] pour créer une identité managée.

```azurecli-interactive
export SUBSCRIPTION="$(az account show --query id --output tsv)"
export USER_ASSIGNED_IDENTITY_NAME="myIdentity$RANDOM_ID"
az identity create \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --location "${LOCATION}" \
    --subscription "${SUBSCRIPTION}"
```

L’exemple de sortie suivant illustre la création réussie d’une identité managée :

Résultats :
<!-- expected_similarity=0.3 -->
```output
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroupxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentityxxxxxx",
  "location": "centralindia",
  "name": "myIdentityxxxxxx",
  "principalId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "resourceGroup": "myResourceGroupxxxxxx",
  "systemData": null,
  "tags": {},
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "type": "Microsoft.ManagedIdentity/userAssignedIdentities"
}
```

Ensuite, créez une variable pour l’ID client de l’identité managée.

```azurecli-interactive
export USER_ASSIGNED_CLIENT_ID="$(az identity show \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --query 'clientId' \
    --output tsv)"
```

## Créer un compte de service Kubernetes

Créez un compte de service Kubernetes et annotez-le avec l’ID client de l’identité managée créée à l’étape précédente. Utilisez la commande [az aks get-credentials][az-aks-get-credentials] et remplacez les valeurs pour le nom du cluster et le nom du groupe de ressources.

```azurecli-interactive
az aks get-credentials --name "${CLUSTER_NAME}" --resource-group "${RESOURCE_GROUP}"
```

Copiez et collez l’entrée multiligne suivante dans Azure CLI.

```azurecli-interactive
export SERVICE_ACCOUNT_NAMESPACE="default"
export SERVICE_ACCOUNT_NAME="workload-identity-sa$RANDOM_ID"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${USER_ASSIGNED_CLIENT_ID}"
  name: "${SERVICE_ACCOUNT_NAME}"
  namespace: "${SERVICE_ACCOUNT_NAMESPACE}"
EOF
```

La sortie suivante montre la création réussie de l’identité de charge de travail :

```output
serviceaccount/workload-identity-sa created
```

## Créer les informations d’identification de l’identité fédérée

Utilisez la commande [az identity federated-credential create][az-identity-federated-credential-create] pour créer les informations d’identification de l’identité fédérée entre l’identité managée, l’émetteur du compte de service et le sujet. Pour plus d’informations sur les informations d’identification d’identité fédérée dans Microsoft Entra, consultez [Vue d’ensemble des informations d’identification d’identité fédérée dans Microsoft Entra ID][federated-identity-credential].

```azurecli-interactive
export FEDERATED_IDENTITY_CREDENTIAL_NAME="myFedIdentity$RANDOM_ID"
az identity federated-credential create \
    --name ${FEDERATED_IDENTITY_CREDENTIAL_NAME} \
    --identity-name "${USER_ASSIGNED_IDENTITY_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject system:serviceaccount:"${SERVICE_ACCOUNT_NAMESPACE}":"${SERVICE_ACCOUNT_NAME}" \
    --audience api://AzureADTokenExchange
```

> [!NOTE]
> Il faut quelques secondes pour que les informations d’identification de l’identité fédérée se propagent après avoir été ajoutées. Si une demande de jeton est effectuée immédiatement après l’ajout des informations d’identification de l’identité fédérée, la demande peut échouer jusqu’à ce que le cache soit actualisé. Pour éviter ce problème, vous pouvez ajouter un léger délai après l’ajout des informations d’identification d’identité fédérée.

## Déployer votre application

Lorsque vous déployez vos pods d’application, le manifeste doit référencer le compte de service créé lors de l’étape **Créer un compte de service Kubernetes**. Le manifeste suivant montre comment référencer le compte, en particulier les propriétés _metadata\namespace_ et _spec\serviceAccountName_. Veillez à spécifier une image pour `<image>` et un nom de conteneur pour `<containerName>` :

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sample-workload-identity
  namespace: ${SERVICE_ACCOUNT_NAMESPACE}  # Replace with your namespace
  labels:
    azure.workload.identity/use: "true"  # Required. Only pods with this label can use workload identity.
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}  # Replace with your service account name
  containers:
    - name: rabbitmq  # Replace with your container name
      image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine  # Replace with your Docker image
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
EOF
```

> [!IMPORTANT]
> Vérifiez que les pods d’application utilisant l’identité de charge de travail incluent l’étiquette `azure.workload.identity/use: "true"` dans la spécification du pod. Dans le cas contraire, les pods échouent après avoir été redémarrés.

## Octroyez des autorisations pour accéder à Azure Key Vault

Les instructions de cette étape montrent comment accéder aux secrets, clés ou certificats dans un coffre de clés Azure à partir du pod. Les exemples de cette section configurent l’accès aux secrets dans le coffre de clés pour l’identité de charge de travail, mais vous pouvez effectuer des étapes similaires pour configurer l’accès aux clés ou aux certificats.

L’exemple suivant montre comment utiliser le modèle d’autorisation de contrôle d’accès en fonction du rôle Azure (Azure RBAC) pour accorder au pod l’accès au coffre de clés. Pour plus d’informations sur le modèle d’autorisation RBAC Azure pour Azure Key Vault, consultez [Accorder l’autorisation aux applications d’accéder à un coffre de clés Azure à l’aide d’Azure RBAC](/azure/key-vault/general/rbac-guide).

1. Créez un coffre de clés avec la protection contre le vidage et l’autorisation RBAC activée. Vous pouvez également utiliser un coffre de clés existant s’il est configuré pour la protection contre le vidage et l’autorisation RBAC :

    ```azurecli-interactive
    export KEYVAULT_NAME="keyvault-workload-id$RANDOM_ID"
    # Ensure the key vault name is between 3-24 characters
    if [ ${#KEYVAULT_NAME} -gt 24 ]; then
        KEYVAULT_NAME="${KEYVAULT_NAME:0:24}"
    fi
    az keyvault create \
        --name "${KEYVAULT_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --enable-purge-protection \
        --enable-rbac-authorization 
    ```

1. Attribuez-vous le rôle RBAC [Agent des secrets Key Vault](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-officer) afin de pouvoir créer un secret dans le nouveau coffre de clés :

    ```azurecli-interactive
    export KEYVAULT_RESOURCE_ID=$(az keyvault show --resource-group "${KEYVAULT_RESOURCE_GROUP}" \
        --name "${KEYVAULT_NAME}" \
        --query id \
        --output tsv)

    export CALLER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

    az role assignment create --assignee "${CALLER_OBJECT_ID}" \
    --role "Key Vault Secrets Officer" \
    --scope "${KEYVAULT_RESOURCE_ID}"
    ```

1. Créez un secret dans le coffre de clés :

    ```azurecli-interactive
    export KEYVAULT_SECRET_NAME="my-secret$RANDOM_ID"
    az keyvault secret set \
        --vault-name "${KEYVAULT_NAME}" \
        --name "${KEYVAULT_SECRET_NAME}" \
        --value "Hello\!"
    ```

1. Attribuez le rôle [Utilisateur des secrets Key Vault](/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user) à l’identité managée affectée par l’utilisateur que vous avez créée précédemment. Cette étape donne à l’identité managée l’autorisation de lire les secrets à partir du coffre de clés :

    ```azurecli-interactive
    export IDENTITY_PRINCIPAL_ID=$(az identity show \
        --name "${USER_ASSIGNED_IDENTITY_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query principalId \
        --output tsv)
    
    az role assignment create \
        --assignee-object-id "${IDENTITY_PRINCIPAL_ID}" \
        --role "Key Vault Secrets User" \
        --scope "${KEYVAULT_RESOURCE_ID}" \
        --assignee-principal-type ServicePrincipal
    ```

1. Créez une variable d’environnement pour l’URL du coffre de clés :

    ```azurecli-interactive
    export KEYVAULT_URL="$(az keyvault show \
        --resource-group ${RESOURCE_GROUP} \
        --name ${KEYVAULT_NAME} \
        --query properties.vaultUri \
        --output tsv)"
    ```

1. Déployez un pod qui référence le compte de service et l’URL du coffre de clés :

    ```bash
    cat <<EOF | kubectl apply -f -
    apiVersion: v1
    kind: Pod
    metadata:
    name: sample-workload-identity-key-vault
    namespace: ${SERVICE_ACCOUNT_NAMESPACE}
    labels:
        azure.workload.identity/use: "true"
    spec:
    serviceAccountName: ${SERVICE_ACCOUNT_NAME}
    containers:
        - image: ghcr.io/azure/azure-workload-identity/msal-go
        name: oidc
        env:
            - name: KEYVAULT_URL
            value: ${KEYVAULT_URL}
            - name: SECRET_NAME
            value: ${KEYVAULT_SECRET_NAME}
    nodeSelector:
        kubernetes.io/os: linux
    EOF
    ```

Pour vérifier si toutes les propriétés sont injectées correctement par le webhook, utilisez la commande [kubectl describe][kubectl-describe] :

```azurecli-interactive
kubectl describe pod sample-workload-identity-key-vault | grep "SECRET_NAME:"
```

Si l’opération réussit, la sortie doit ressembler à la suivante :

```output
      SECRET_NAME:                 ${KEYVAULT_SECRET_NAME}
```

Pour s’assurer que le pod est capable d’obtenir un jeton et d’accéder à la ressource, utilisez la commande kubectl logs :

```azurecli-interactive
kubectl logs sample-workload-identity-key-vault
```

Si l’opération réussit, la sortie doit ressembler à la suivante :

```output
I0114 10:35:09.795900       1 main.go:63] "successfully got secret" secret="Hello\\!"
```

> [!IMPORTANT]
> Les attributions de rôle RBAC Azure peuvent prendre jusqu’à dix minutes pour se propager. Si le pod ne parvient pas à accéder au secret, vous devrez peut-être attendre que l’attribution de rôle se propage. Pour plus d’informations, consultez [Résoudre les problèmes liés à RBAC Azure](/azure/role-based-access-control/troubleshooting#).

## Désactiver l’identité de charge de travail

Pour désactiver Microsoft Entra Workload ID sur le cluster AKS où elle a été activée et configurée, vous pouvez exécuter la commande suivante :

```azurecli-interactive
az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --disable-workload-identity
```

## Étapes suivantes

Dans cet article, vous avez déployé un cluster Kubernetes et l’avez configuré pour utiliser une identité de charge de travail en préparation des charges de travail d’application pour s’authentifier avec ces informations d’identification. Vous êtes maintenant prêt à déployer votre application et à la configurer pour utiliser l’identité de charge de travail avec la dernière version de la bibliothèque de client [Identité Azure][azure-identity-libraries]. Si vous ne pouvez pas réécrire votre application pour utiliser la dernière version de la bibliothèque de client, vous pouvez [configurer votre pod d’application][workload-identity-migration] pour vous authentifier en utilisant une identité managée avec une identité de charge de travail comme solution de migration à court terme.

L’intégration du [connecteur de services](/azure/service-connector/overview) permet de simplifier la configuration de la connexion pour les charges de travail AKS et les services de support Azure. Il gère en toute sécurité les configurations réseau et d’authentification et suit les meilleures pratiques de connexion aux services Azure. Pour plus d’informations, consultez [Se connecter à Azure OpenAI Service dans AKS à l’aide d’une identité de charge de travail](/azure/service-connector/tutorial-python-aks-openai-workload-identity) et [Introduction au connecteur de services](https://azure.github.io/AKS/2024/05/23/service-connector-intro).

<!-- EXTERNAL LINKS -->
[kubectl-describe]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#describe

<!-- INTERNAL LINKS -->
[kubernetes-concepts]: concepts-clusters-workloads.md
[workload-identity-overview]: workload-identity-overview.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-group-create]: /cli/azure/group#az-group-create
[aks-identity-concepts]: concepts-identity.md
[federated-identity-credential]: /graph/api/resources/federatedidentitycredentials-overview
[tutorial-python-aks-storage-workload-identity]: /azure/service-connector/tutorial-python-aks-storage-workload-identity
[az-aks-create]: /cli/azure/aks#az-aks-create
[az aks update]: /cli/azure/aks#az-aks-update
[aks-two-resource-groups]: faq.yml
[az-account-set]: /cli/azure/account#az-account-set
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-identity-federated-credential-create]: /cli/azure/identity/federated-credential#az-identity-federated-credential-create
[workload-identity-migration]: workload-identity-migrate-from-pod-identity.md
[azure-identity-libraries]: /azure/active-directory/develop/reference-v2-libraries