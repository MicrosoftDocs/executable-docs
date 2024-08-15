---
title: Créer une infrastructure pour déployer une base de données PostgreSQL hautement disponible sur AKS
description: Créez l’infrastructure nécessaire pour déployer une base de données PostgreSQL hautement disponible sur AKS à l’aide de l’opérateur CloudNativePG.
ms.topic: how-to
ms.date: 06/07/2024
author: kenkilty
ms.author: kkilty
ms.custom: 'innovation-engine, aks-related-content'
---

# Créer une infrastructure pour déployer une base de données PostgreSQL hautement disponible sur AKS

Dans cet article, vous allez créer l’infrastructure nécessaire pour déployer une base de données PostgreSQL hautement disponible sur AKS à l’aide de l’opérateur [CloudNativePG (CNPG)](https://cloudnative-pg.io/).

## Avant de commencer

* Passez en revue la vue d’ensemble du déploiement et vérifiez que vous remplissez toutes les conditions préalables requises dans [Comment déployer une base de données PostgreSQL hautement disponible sur AKS avec Azure CLI][postgresql-ha-deployment-overview].
* [Définissez des variables d’environnement](#set-environment-variables) à utiliser dans ce guide.
* [Installes les extensions requises](#install-required-extensions).

## Définir des variables d’environnement

Définissez les variables d’environnement suivantes à utiliser dans ce guide :

```bash
export SUFFIX=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
export LOCAL_NAME="cnpg"
export TAGS="owner=user"
export RESOURCE_GROUP_NAME="rg-${LOCAL_NAME}-${SUFFIX}"
export PRIMARY_CLUSTER_REGION="westus3"
export AKS_PRIMARY_CLUSTER_NAME="aks-primary-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_MANAGED_RG_NAME="rg-${LOCAL_NAME}-primary-aksmanaged-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_FED_CREDENTIAL_NAME="pg-primary-fedcred1-${LOCAL_NAME}-${SUFFIX}"
export AKS_PRIMARY_CLUSTER_PG_DNSPREFIX=$(echo $(echo "a$(openssl rand -hex 5 | cut -c1-11)"))
export AKS_UAMI_CLUSTER_IDENTITY_NAME="mi-aks-${LOCAL_NAME}-${SUFFIX}"
export AKS_CLUSTER_VERSION="1.29"
export PG_NAMESPACE="cnpg-database"
export PG_SYSTEM_NAMESPACE="cnpg-system"
export PG_PRIMARY_CLUSTER_NAME="pg-primary-${LOCAL_NAME}-${SUFFIX}"
export PG_PRIMARY_STORAGE_ACCOUNT_NAME="hacnpgpsa${SUFFIX}"
export PG_STORAGE_BACKUP_CONTAINER_NAME="backups"
export ENABLE_AZURE_PVC_UPDATES="true"
export MY_PUBLIC_CLIENT_IP=$(dig +short myip.opendns.com @resolver3.opendns.com)
```

## Installer les extensions requises

Les extensions `aks-preview`, `k8s-extension` et `amg` fournissent davantage de fonctionnalités pour la gestion des clusters Kubernetes et l’interrogation des ressources Azure. Installez ces extensions en utilisant les commandes [`az extension add`][az-extension-add] suivantes :

```bash
az extension add --upgrade --name aks-preview --yes --allow-preview true
az extension add --upgrade --name k8s-extension --yes --allow-preview false
az extension add --upgrade --name amg --yes --allow-preview false
```

En tant que prérequis pour l’utilisation de kubectl, il est essentiel d’installer d’abord [Krew][install-krew], puis le [plug-in CNPG][cnpg-plugin]. Cela permet de gérer l’opérateur PostgreSQL à l’aide des commandes suivantes.

```bash
(
  set -x; cd "$(mktemp -d)" &&
  OS="$(uname | tr '[:upper:]' '[:lower:]')" &&
  ARCH="$(uname -m | sed -e 's/x86_64/amd64/' -e 's/\(arm\)\(64\)\?.*/\1\2/' -e 's/aarch64$/arm64/')" &&
  KREW="krew-${OS}_${ARCH}" &&
  curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" &&
  tar zxvf "${KREW}.tar.gz" &&
  ./"${KREW}" install krew
)

export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"

kubectl krew install cnpg
```

## Créer un groupe de ressources

Créez un groupe de ressources pour contenir les ressources que vous créez dans ce guide à l’aide de la commande [`az group create`][az-group-create].

```bash
az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $PRIMARY_CLUSTER_REGION \
    --tags $TAGS \
    --query 'properties.provisioningState' \
    --output tsv
```

## Créer une identité managée attribuée par l’utilisateur

Dans cette section, vous allez créer une identité managée affectée par l’utilisateur (UAMI) pour permettre au CNPG PostgreSQL d’utiliser une identité de charge de travail AKS pour accéder au Stockage Blob Azure. Cette configuration permet au cluster PostgreSQL sur AKS de se connecter au Stockage Blob Azure sans secret.

1. Créez une identité managée affectée par l’utilisateur à l’aide de la commande [`az identity create`][az-identity-create].

    ```bash
    AKS_UAMI_WI_IDENTITY=$(az identity create \
        --name $AKS_UAMI_CLUSTER_IDENTITY_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --output json)
    ```

1. Activez l’identité de charge de travail AKS et générez un compte de service à utiliser plus loin dans ce guide à l’aide des commandes suivantes :

    ```bash
    export AKS_UAMI_WORKLOAD_OBJECTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.principalId')
    export AKS_UAMI_WORKLOAD_RESOURCEID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.id')
    export AKS_UAMI_WORKLOAD_CLIENTID=$( \
        echo "${AKS_UAMI_WI_IDENTITY}" | jq -r '.clientId')

    echo "ObjectId: $AKS_UAMI_WORKLOAD_OBJECTID"
    echo "ResourceId: $AKS_UAMI_WORKLOAD_RESOURCEID"
    echo "ClientId: $AKS_UAMI_WORKLOAD_CLIENTID"
    ```

L’ID d’objet est un identificateur unique pour l’ID client (également appelé ID d’application) qui identifie de manière unique un principal de sécurité de type *Application* au sein du locataire Entra ID. L’ID de ressource est un identificateur unique pour gérer et localiser une ressource dans Azure. Ces valeurs sont requises pour activer l’identité de charge de travail AKS.

L’opérateur CNPG génère automatiquement un compte de service appelé *postgres* que vous utilisez plus loin dans le guide pour créer des informations d’identification fédérées qui permettent l’accès OAuth à partir de PostgreSQL vers le Stockage Azure.

## Créer un compte de stockage dans la région principale

1. Créez un compte de stockage d’objets pour stocker les sauvegardes PostgreSQL dans la région principale à l’aide de la commande [`az storage account create`][az-storage-account-create].

    ```bash
    az storage account create \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard_ZRS \
        --kind StorageV2 \
        --query 'provisioningState' \
        --output tsv
    ```

1. Créez le conteneur de stockage pour stocker les journaux WAL (Write Ahead Logs) et PostgreSQL standard à la demande et les sauvegardes planifiées à l’aide de la commande [`az storage container create`][az-storage-container-create].

    ```bash
    az storage container create \
        --name $PG_STORAGE_BACKUP_CONTAINER_NAME \
        --account-name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --auth-mode login
    ```

    Exemple de sortie :

    ```output
    {
        "created": true
    }
    ```

    > [!NOTE]
    > Si vous rencontrez le message d’erreur : `The request may be blocked by network rules of storage account. Please check network rule set using 'az storage account show -n accountname --query networkRuleSet'. If you want to change the default action to apply when no rule matches, please use 'az storage account update'`. Veuillez vérifier les autorisations utilisateur pour le Stockage Blob Azure et, si **nécessaire**, élever votre rôle à `Storage Blob Data Owner` à l’aide des commandes fournies ci-dessous et réessayer ensuite la commande [`az storage container create`][az-storage-container-create].

    ```bash
    az role assignment list --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID --output table

    export USER_ID=$(az ad signed-in-user show --query id --output tsv)

    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    az role assignment create \
        --assignee-object-id $USER_ID \
        --assignee-principal-type User \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --role "Storage Blob Data Owner" \
        --output tsv
    ```

## Attribuer le contrôle d’accès en fonction du rôle (RBAC) aux comptes de stockage

Pour activer les sauvegardes, le cluster PostgreSQL doit lire et écrire dans un magasin d’objets. Le cluster PostgreSQL exécuté sur AKS utilise une identité de charge de travail pour accéder au compte de stockage via le paramètre de configuration de l’opérateur CNPG [`inheritFromAzureAD`][inherit-from-azuread].

1. Obtenez l’ID de ressource principale du compte de stockage à l’aide de la commande [`az storage account show`][az-storage-account-show].

    ```bash
    export STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID=$(az storage account show \
        --name $PG_PRIMARY_STORAGE_ACCOUNT_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query "id" \
        --output tsv)

    echo $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID
    ````

1. Attribuez le rôle intégré Azure « Contributeur aux données Blob du stockage » à l’ID d’objet avec l’étendue ID de ressource du compte de stockage pour l’UAMI associé à l’identité managée pour chaque cluster AKS à l’aide de la commande [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --role "Storage Blob Data Contributor" \
        --assignee-object-id $AKS_UAMI_WORKLOAD_OBJECTID \
        --assignee-principal-type ServicePrincipal \
        --scope $STORAGE_ACCOUNT_PRIMARY_RESOURCE_ID \
        --query "id" \
        --output tsv
    ```

## Configurer l’infrastructure de supervision

Dans cette section, vous déployez une instance d’Azure Managed Grafana, un espace de travail Azure Monitor et un espace de travail Log Analytics Azure Monitor pour activer la supervision du cluster PostgreSQL. Vous stockez également des références à l’infrastructure de supervision créée à utiliser comme entrée pendant le processus de création du cluster AKS plus loin dans le guide. Cette section peut prendre un certain temps.

> [!NOTE]
> Les instances Azure Managed Grafana et les clusters AKS sont facturés indépendamment. Pour plus d’informations sur la tarification, consultez la [tarification d’Azure Managed Grafana][azure-managed-grafana-pricing].

1. Créez une instance Azure Managed Grafana à l’aide de la commande [`az grafana create`][az-grafana-create].

    ```bash
    export GRAFANA_PRIMARY="grafana-${LOCAL_NAME}-${SUFFIX}"

    export GRAFANA_RESOURCE_ID=$(az grafana create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $GRAFANA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --zone-redundancy Enabled \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $GRAFANA_RESOURCE_ID
    ```

1. Créez un espace de travail Azure Monitor à l’aide de la commande [`az monitor account create`][az-monitor-account-create].

    ```bash
    export AMW_PRIMARY="amw-${LOCAL_NAME}-${SUFFIX}"

    export AMW_RESOURCE_ID=$(az monitor account create \
        --name $AMW_PRIMARY \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --tags $TAGS \
        --query "id" \
        --output tsv)

    echo $AMW_RESOURCE_ID
    ```

1. Créez un espace de travail Log Analytics Azure Monitor à l’aide de la commande [`az monitor log-analytics workspace create`][az-monitor-log-analytics-workspace-create].

    ```bash
    export ALA_PRIMARY="ala-${LOCAL_NAME}-${SUFFIX}"

    export ALA_RESOURCE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-name $ALA_PRIMARY \
        --location $PRIMARY_CLUSTER_REGION \
        --query "id" \
        --output tsv)

    echo $ALA_RESOURCE_ID
    ```

## Créer le cluster AKS pour héberger le cluster PostgreSQL

Dans cette section, vous allez créer un cluster AKS multizone avec un pool de nœuds système. Le cluster AKS héberge le réplica principal du cluster PostgreSQL et deux réplicas de secours, chacun aligné sur une zone de disponibilité différente pour permettre la redondance zonale.

Vous ajoutez également un pool de nœuds utilisateur au cluster AKS pour héberger le cluster PostgreSQL. L’utilisation d’un pool de nœuds distinct permet de contrôler les références SKU de machine virtuelle Azure utilisées pour PostgreSQL et permet au pool système AKS d’optimiser les performances et les coûts. Vous appliquez une étiquette au pool de nœuds utilisateur que vous pouvez référencer pour la sélection des nœuds lors du déploiement de l’opérateur CNPG plus loin dans ce guide. Cette section peut prendre un certain temps.

1. Créez un cluster AKS avec la commande [`az aks create`][az-aks-create].

    ```bash
    export SYSTEM_NODE_POOL_VMSKU="standard_d2s_v3"
    export USER_NODE_POOL_NAME="postgres"
    export USER_NODE_POOL_VMSKU="standard_d4s_v3"
    
    az aks create \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --tags $TAGS \
        --resource-group $RESOURCE_GROUP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --generate-ssh-keys \
        --node-resource-group $AKS_PRIMARY_MANAGED_RG_NAME \
        --enable-managed-identity \
        --assign-identity $AKS_UAMI_WORKLOAD_RESOURCEID \
        --network-plugin azure \
        --network-plugin-mode overlay \
        --network-dataplane cilium \
        --nodepool-name systempool \
        --enable-oidc-issuer \
        --enable-workload-identity \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 3 \
        --node-vm-size $SYSTEM_NODE_POOL_VMSKU \
        --enable-azure-monitor-metrics \
        --azure-monitor-workspace-resource-id $AMW_RESOURCE_ID \
        --grafana-resource-id $GRAFANA_RESOURCE_ID \
        --api-server-authorized-ip-ranges $MY_PUBLIC_CLIENT_IP \
        --tier standard \
        --kubernetes-version $AKS_CLUSTER_VERSION \
        --zones 1 2 3 \
        --output table
    ```

2. Ajoutez un pool de nœuds utilisateur au cluster AKS à l’aide de la commande [`az aks nodepool add`][az-aks-node-pool-add].

    ```bash
    az aks nodepool add \
        --resource-group $RESOURCE_GROUP_NAME \
        --cluster-name $AKS_PRIMARY_CLUSTER_NAME \
        --name $USER_NODE_POOL_NAME \
        --enable-cluster-autoscaler \
        --min-count 3 \
        --max-count 6 \
        --node-vm-size $USER_NODE_POOL_VMSKU \
        --zones 1 2 3 \
        --labels workload=postgres \
        --output table
    ```

> [!NOTE]
> Si vous recevez le message d’erreur `"(OperationNotAllowed) Operation is not allowed: Another operation (Updating) is in progress, please wait for it to finish before starting a new operation."` lors de l’ajout du pool de nœuds AKS, attendez quelques minutes que les opérations de cluster AKS se terminent, puis exécutez la commande `az aks nodepool add`.

## Se connecter au cluster AKS et créer des espaces de noms

Dans cette section, vous obtenez les informations d’identification du cluster AKS, qui servent de clés qui vous permettent d’authentifier et d’interagir avec le cluster. Une fois connecté, vous créez deux espaces de noms : un pour les services de gestionnaire de contrôleur CNPG et un autre pour le cluster PostgreSQL et ses services associés.

1. Obtenez les informations d’identification du cluster AKS à l’aide de la commande [`az aks get-credentials`][az-aks-get-credentials].

    ```bash
    az aks get-credentials \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --output none
     ```

2. Créez l’espace de noms pour les services du gestionnaire de contrôleur CNPG, le cluster PostgreSQL et ses services associés à l’aide de la commande [`kubectl create namespace`][kubectl-create-namespace].

    ```bash
    kubectl create namespace $PG_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    kubectl create namespace $PG_SYSTEM_NAMESPACE --context $AKS_PRIMARY_CLUSTER_NAME
    ```

## Mettre à jour l’infrastructure de supervision

L’espace de travail Azure Monitor pour Managed Prometheus et Azure Managed Grafana est automatiquement lié au cluster AKS pour les métriques et la visualisation pendant le processus de création du cluster. Dans cette section, vous allez activer la collecte de journaux avec AKS Container Insights et vérifier que Managed Prometheus récupère des métriques et Container Insights ingère les journaux.

1. Activez la supervision Container Insights sur le cluster AKS à l’aide de la commande [`az aks enable-addons`][az-aks-enable-addons].

    ```bash
    az aks enable-addons \
        --addon monitoring \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --workspace-resource-id $ALA_RESOURCE_ID \
        --output table
    ```

2. Vérifiez que Managed Prometheus récupère des métriques et Container Insights ingère des journaux à partir du cluster AKS en inspectant DaemonSet à l’aide de la commandes [`kubectl get`][kubectl-get] et [`az aks show`][az-aks-show].

    ```bash
    kubectl get ds ama-metrics-node \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    kubectl get ds ama-logs \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace=kube-system

    az aks show \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --query addonProfiles
    ```

    Votre sortie doit ressembler à l’exemple de sortie suivant, avec un total de *six* nœuds (trois pour le pool de nœuds système et trois pour le pool de nœuds PostgreSQL) et Container Insights montrant `"enabled": true` :

    ```output
    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-metrics-node   6         6         6       6            6           <none>       

    NAME               DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR
    ama-logs           6         6         6       6            6           <none>       

    {
      "omsagent": {
        "config": {
          "logAnalyticsWorkspaceResourceID": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-cnpg-9vbin3p8/providers/Microsoft.OperationalInsights/workspaces/ala-cnpg-9vbin3p8",
          "useAADAuth": "true"
        },
        "enabled": true,
        "identity": null
      }
    }
    ```

## Créer une adresse IP statique publique pour l’entrée de cluster PostgreSQL

Pour valider le déploiement du cluster PostgreSQL et utiliser les outils PostgreSQL clients, tels que *psql* et *PgAdmin*, vous devez exposer les réplicas principaux et en lecture seule à l’entrée. Dans cette section, vous allez créer une ressource d’adresse IP publique Azure que vous fournissez ultérieurement à un équilibreur de charge Azure pour exposer les points de terminaison PostgreSQL pour la requête.

1. Obtenez le nom du groupe de ressources du nœud de cluster AKS à l’aide de la commande [`az aks show`][az-aks-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME=$(az aks show \
        --name $AKS_PRIMARY_CLUSTER_NAME \
        --resource-group $RESOURCE_GROUP_NAME \
        --query nodeResourceGroup \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME
    ```

2. Créez l’adresse IP publique à l’aide de la commande [`az network public-ip create`][az-network-public-ip-create].

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_NAME="$AKS_PRIMARY_CLUSTER_NAME-pip"

    az network public-ip create \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --location $PRIMARY_CLUSTER_REGION \
        --sku Standard \
        --zone 1 2 3 \
        --allocation-method static \
        --output table
    ```

3. Obtenez l’adresse IP publique nouvellement créée à l’aide de la commande [`az network public-ip show`][az-network-public-ip-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS=$(az network public-ip show \
        --resource-group $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --name $AKS_PRIMARY_CLUSTER_PUBLICIP_NAME \
        --query ipAddress \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_PUBLICIP_ADDRESS
    ```

4. Obtenez l’ID de ressource du groupe de ressources de nœud à l’aide de la commande [`az group show`][az-group-show].

    ```bash
    export AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE=$(az group show --name \
        $AKS_PRIMARY_CLUSTER_NODERG_NAME \
        --query id \
        --output tsv)

    echo $AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE
    ```

5. Attribuez le rôle « Contributeur de réseau » à l’ID d’objet UAMI en utilisant l’étendue du groupe de ressources de nœud à l’aide de la commande [`az role assignment create`][az-role-assignment-create].

    ```bash
    az role assignment create \
        --assignee-object-id ${AKS_UAMI_WORKLOAD_OBJECTID} \
        --assignee-principal-type ServicePrincipal \
        --role "Network Contributor" \
        --scope ${AKS_PRIMARY_CLUSTER_NODERG_NAME_SCOPE}
    ```

## Installer l’opérateur CNPG dans le cluster AKS

Dans cette section, vous installez l’opérateur CNPG dans le cluster AKS à l’aide d’Helm ou d’un manifeste YAML.

### [Helm](#tab/helm)

1. Ajoutez le référentiel Helm CNPG à l’aide de la commande [`helm repo add`][helm-repo-add].

    ```bash
    helm repo add cnpg https://cloudnative-pg.github.io/charts
    ```

2. Mettez à niveau le référentiel Helm CNPG et installez-le sur le cluster AKS à l’aide de la commande [`helm upgrade`][helm-upgrade] avec l’indicateur `--install`.

    ```bash
    helm upgrade --install cnpg \
        --namespace $PG_SYSTEM_NAMESPACE \
        --create-namespace \
        --kube-context=$AKS_PRIMARY_CLUSTER_NAME \
        cnpg/cloudnative-pg
    ```

3. Vérifiez l’installation de l’opérateur sur le cluster AKS à l’aide de la commande [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-cloudnative-pg
    ```

### [YAML](#tab/yaml)

1. Installez l’opérateur CNPG sur le cluster AKS à l’aide de la commande [`kubectl apply`][kubectl-apply].

    ```bash
    kubectl apply --context $AKS_PRIMARY_CLUSTER_NAME \
        --namespace $PG_SYSTEM_NAMESPACE \
        --server-side -f \
        https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.23/releases/cnpg-1.23.1.yaml
    ```

2. Vérifiez l’installation de l’opérateur sur le cluster AKS à l’aide de la commande [`kubectl get`][kubectl-get].

    ```bash
    kubectl get deployment \
        --namespace $PG_SYSTEM_NAMESPACE cnpg-controller-manager \
        --context $AKS_PRIMARY_CLUSTER_NAME
    ```

---

## Étapes suivantes

> [!div class="nextstepaction"]
> [Déployer une base de données PostgreSQL hautement disponible sur le cluster AKS][deploy-postgresql]

## Contributeurs

*Cet article est géré par Microsoft. Il a été écrit à l’origine par les contributeurs* suivants :

* Ken Kitty | Responsable de programme technique principal
* Russell de Pina | Responsable de programme technique principal
* Adrian Joian | Ingénieur client senior
* Jenny Hayes | Développeuse de contenu confirmée
* Carol Smith | Développeuse de contenu confirmée
* Erin Schaffer | Développeuse de contenu 2

<!-- LINKS -->
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-grafana-create]: /cli/azure/grafana#az-grafana-create
[postgresql-ha-deployment-overview]: ./postgresql-ha-overview.md
[az-extension-add]: /cli/azure/extension#az_extension_add
[az-group-create]: /cli/azure/group#az_group_create
[az-storage-account-create]: /cli/azure/storage/account#az_storage_account_create
[az-storage-container-create]: /cli/azure/storage/container#az_storage_container_create
[inherit-from-azuread]: https://cloudnative-pg.io/documentation/1.23/appendixes/object_stores/#azure-blob-storage
[az-storage-account-show]: /cli/azure/storage/account#az_storage_account_show
[az-role-assignment-create]: /cli/azure/role/assignment#az_role_assignment_create
[az-monitor-account-create]: /cli/azure/monitor/account#az_monitor_account_create
[az-monitor-log-analytics-workspace-create]: /cli/azure/monitor/log-analytics/workspace#az_monitor_log_analytics_workspace_create
[azure-managed-grafana-pricing]: https://azure.microsoft.com/pricing/details/managed-grafana/
[az-aks-create]: /cli/azure/aks#az_aks_create
[az-aks-node-pool-add]: /cli/azure/aks/nodepool#az_aks_nodepool_add
[az-aks-get-credentials]: /cli/azure/aks#az_aks_get_credentials
[kubectl-create-namespace]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create/kubectl_create_namespace/
[az-aks-enable-addons]: /cli/azure/aks#az_aks_enable_addons
[kubectl-get]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-network-public-ip-create]: /cli/azure/network/public-ip#az_network_public_ip_create
[az-network-public-ip-show]: /cli/azure/network/public-ip#az_network_public_ip_show
[az-group-show]: /cli/azure/group#az_group_show
[helm-repo-add]: https://helm.sh/docs/helm/helm_repo_add/
[helm-upgrade]: https://helm.sh/docs/helm/helm_upgrade/
[kubectl-apply]: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/
[deploy-postgresql]: ./deploy-postgresql-ha.md
[install-krew]: https://krew.sigs.k8s.io/
[cnpg-plugin]: https://cloudnative-pg.io/documentation/current/kubectl-plugin/#using-krew
