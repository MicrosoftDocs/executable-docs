---
title: "Tutoriel\_: Déployer WordPress sur un cluster\_AKS à l’aide d’Azure\_CLI"
description: "Découvrez comment créer et déployer rapidement WordPress sur AKS avec Azure Database pour MySQL\_- Serveur flexible."
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Tutoriel : Déployer l’application WordPress sur AKS avec Azure Database pour MySQL - Serveur flexible

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Dans ce tutoriel, vous déployez une application WordPress évolutive sécurisée via HTTPS sur un cluster AKS (Azure Kubernetes Service) avec un serveur flexible Azure Database pour MySQL à l’aide d’Azure CLI.
**[AKS](../../aks/intro-kubernetes.md)** est un service Kubernetes managé qui vous permet de déployer et gérer rapidement des clusters. Un **[serveur flexible Azure Database pour MySQL](overview.md)** est un service de base de données complètement managé conçu pour offrir un contrôle et une flexibilité plus granulaires des fonctions de gestion de base de données et des paramètres de configuration.

> [!NOTE]
> Ce tutoriel suppose une compréhension élémentaire des concepts liés à Kubernetes, WordPress et MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Prérequis 

Avant de commencer, assurez-vous que vous êtes déjà connecté à Azure CLI et que vous avez sélectionné un abonnement à utiliser avec l’interface CLI. Assurez-vous d’avoir [Helm installé](https://helm.sh/docs/intro/install/).

> [!NOTE]
> Si vous exécutez les commandes mentionnées dans ce tutoriel localement (plutôt que dans Azure Cloud Shell), exécutez les commandes en tant qu’administrateur.

## Créer un groupe de ressources

Un groupe de ressources Azure est un groupe logique dans lequel des ressources Azure sont déployées et gérées. Toutes les ressources doivent être placées dans un groupe de ressources. La commande suivante crée un groupe de ressources avec les paramètres `$MY_RESOURCE_GROUP_NAME` et `$REGION` précédemment définis.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Résultats :
<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX",
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

> [!NOTE]
> L’emplacement du groupe de ressources correspond à l’endroit où sont stockées les métadonnées du groupe de ressources. C’est également là que vos ressources s’exécutent dans Azure si vous ne spécifiez pas une autre région lors de la création des ressources.

## Créer un réseau virtuel et un sous-réseau

Un réseau virtuel est l’élément de construction fondamental pour les réseaux privés dans Azure. Le réseau virtuel Microsoft Azure permet à des ressources Azure, comme des machines virtuelles, de communiquer de manière sécurisée entre elles et sur Internet.

```bash
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_SN_NAME="mySN$RANDOM_ID"
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Résultats :
<!-- expected_similarity=0.3 -->
```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.210.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX",
    "location": "eastus",
    "name": "myVNet210",
    "provisioningState": "Succeeded",
    "resourceGroup": "myWordPressAKSResourceGroupXXX",
    "subnets": [
      {
        "addressPrefix": "10.210.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/mySNXXX",
        "name": "mySN210",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myWordPressAKSResourceGroupXXX",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Créez une instance de serveur flexible Azure Database pour MySQL

Le serveur flexible Azure Database pour MySQL est un service géré que vous pouvez utiliser pour exécuter, gérer et mettre à l’échelle des serveurs MySQL hautement disponibles dans le cloud. Créez une instance de serveur flexible Azure Database pour MySQL avec la commande [az mysql flexible-server create](/cli/azure/mysql/flexible-server). Un serveur peut contenir plusieurs bases de données. La commande suivante crée un serveur en utilisant les valeurs par défaut du service et les valeurs variables issues du contexte local de votre interface Azure CLI :

```bash
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
az mysql flexible-server create \
    --admin-password $MY_MYSQL_ADMIN_PW \
    --admin-user $MY_MYSQL_ADMIN_USERNAME \
    --auto-scale-iops Disabled \
    --high-availability Disabled \
    --iops 500 \
    --location $REGION \
    --name $MY_MYSQL_DB_NAME \
    --database-name wordpress \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --sku-name Standard_B2s \
    --storage-auto-grow Disabled \
    --storage-size 20 \
    --subnet $MY_MYSQL_SN_NAME \
    --private-dns-zone $MY_DNS_LABEL.private.mysql.database.azure.com \
    --tier Burstable \
    --version 8.0.21 \
    --vnet $MY_VNET_NAME \
    --yes -o JSON
```

Résultats :
<!-- expected_similarity=0.3 -->
```json
{
  "databaseName": "wordpress",
  "host": "mydbxxx.mysql.database.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX",
  "location": "East US",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "skuname": "Standard_B2s",
  "subnetId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.Network/virtualNetworks/myVNetXXX/subnets/myMySQLSNXXX",
  "username": "dbadminxxx",
  "version": "8.0.21"
}
```

Le serveur créé possède les attributs suivants :

- Une nouvelle base de données vide est créée au moment du provisionnement initial du serveur.
- Le nom du serveur, le nom d'utilisateur de l'administrateur, le mot de passe de l'administrateur, le nom du groupe de ressources et l'emplacement sont déjà spécifiés dans l'environnement contextuel local du cloud shell et sont au même endroit que votre groupe de ressources et les autres composants Azure.
- Les valeurs par défaut du service pour les configurations de serveur restantes sont le niveau de calcul (Burstable), la taille de calcul/référence SKU (Standard_B2s), la période de rétention de sauvegarde (sept jours) et la version MySQL (8.0.21).
- La méthode de connectivité par défaut est Accès privé (intégration du réseau virtuel) avec un réseau virtuel lié et un sous-réseau généré automatiquement.

> [!NOTE]
> Une fois le serveur créé, la méthode de connectivité ne peut pas être modifiée. Par exemple, si vous avez sélectionné `Private access (VNet Integration)` pendant la création, vous ne pouvez pas passer à `Public access (allowed IP addresses)` après la création. Nous vous recommandons vivement de sélectionner l'Accès privé lors de la création d'un serveur afin de pouvoir y accéder en toute sécurité à l'aide de l'intégration au réseau virtuel. Pour en savoir plus sur l'accès privé, consultez l'[article consacré aux concepts](./concepts-networking-vnet.md).

Si vous souhaitez modifier des valeurs par défaut, reportez-vous à la [documentation de référence](/cli/azure//mysql/flexible-server) Azure CLI pour obtenir la liste complète des paramètres CLI configurables.

## Vérifiez Azure Database pour MySQL : état du serveur flexible

La création de Azure Database pour MySQL : serveur flexibile et des ressources correspondantes ne prend que quelques minutes.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configurer les paramètres de serveur dans Azure Database pour MySQL : serveur flexibile

Vous pouvez gérer la configuration d’Azure Database pour MySQL - Serveur flexible à l’aide des paramètres de serveur. Les paramètres de serveur sont configurés avec la valeur par défaut et la valeur recommandée lors de la création du serveur.

Pour afficher les détails d’un paramètre particulier pour un serveur, exécutez la commande [az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter).

### Désactiver Azure Database pour MySQL : paramètre de connexion SSL du serveur flexible pour l'intégration de WordPress

Vous pouvez également modifier la valeur de certains paramètres de serveur, ce qui a pour effet de mettre à jour les valeurs de configuration sous-jacente du moteur de serveur MySQL. Pour mettre à jour le paramètre de serveur, utilisez la commande [az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Résultats :
<!-- expected_similarity=0.3 -->
```json
{
  "allowedValues": "ON,OFF",
  "currentValue": "OFF",
  "dataType": "Enumeration",
  "defaultValue": "ON",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myWordPressAKSResourceGroupXXX/providers/Microsoft.DBforMySQL/flexibleServers/mydbXXX/configurations/require_secure_transport",
  "isConfigPendingRestart": "False",
  "isDynamicConfig": "True",
  "isReadOnly": "False",
  "name": "require_secure_transport",
  "resourceGroup": "myWordPressAKSResourceGroupXXX",
  "source": "user-override",
  "systemData": null,
  "type": "Microsoft.DBforMySQL/flexibleServers/configurations",
  "value": "OFF"
}
```

## Créer un cluster AKS

Pour créez un cluster AKS avec des insights de conteneur, utilisez la commande [az aks create](/cli/azure/aks#az-aks-create) avec le paramètre d’analyse **--enable-addons**. L’exemple suivant crée un cluster à mise à l’échelle automatique, compatible avec la zone de disponibilité, nommé **myAKSCluster** :

Cette action prend quelques minutes.

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"

az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --auto-upgrade-channel stable \
    --enable-cluster-autoscaler \
    --enable-addons monitoring \
    --location $REGION \
    --node-count 1 \
    --min-count 1 \
    --max-count 3 \
    --network-plugin azure \
    --network-policy azure \
    --vnet-subnet-id $MY_SN_ID \
    --no-ssh-key \
    --node-vm-size Standard_DS2_v2 \
    --service-cidr 10.255.0.0/24 \
    --dns-service-ip 10.255.0.10 \
    --zones 1 2 3
```
> [!NOTE]
> Lors de la création d’un cluster AKS, un deuxième groupe de ressources est automatiquement créé pour stocker les ressources AKS. Consultez [Pourquoi deux groupes de ressources sont-ils créés avec AKS ?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Se connecter au cluster

Pour gérer un cluster Kubernetes, utilisez [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), le client de ligne de commande Kubernetes. Si vous utilisez Azure Cloud Shell, `kubectl` est déjà installé. L’exemple suivant installe `kubectl` localement à l’aide de la commande [az aks install-cli](/cli/azure/aks#az-aks-install-cli). 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

Ensuite, configurez `kubectl` pour vous connecter à votre cluster Kubernetes avec la commande [az aks get-credentials](/cli/azure/aks#az-aks-get-credentials). Cette commande télécharge les informations d’identification et configure l’interface CLI Kubernetes pour les utiliser. La commande utilise `~/.kube/config`, l’emplacement par défaut du [fichier de configuration Kubernetes](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/). Vous pouvez spécifier un autre emplacement pour votre fichier de configuration Kubernetes en utilisant l’argument **--file**.

> [!WARNING]
> Cette commande remplace toutes les informations d’identification existantes par la même entrée.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Pour vérifier la connexion à votre cluster, utilisez la commande [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) pour retourner une liste des nœuds du cluster.

```bash
kubectl get nodes
```

## Installer le contrôleur d’entrée NGINX

Vous pouvez configurer votre contrôleur d’entrée avec une adresse IP publique statique. L’adresse IP publique statique reste si vous supprimez votre contrôleur d’entrée. L’adresse IP ne reste pas si vous supprimez votre cluster AKS.
Lorsque vous mettez à niveau votre contrôleur d’entrée, vous devez passer un paramètre à la version Helm pour vous assurer que le service du contrôleur d’entrée est informé de l’équilibreur de charge qui lui sera alloué. Pour que les certificats HTTPS fonctionnent correctement, utilisez une étiquette DNS pour configurer un nom de domaine complet (FQDN) pour l’adresse IP du contrôleur d’entrée. Votre nom de domaine complet doit suivre ce formulaire : $MY_DNS_LABEL.AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Ensuite, vous ajoutez le référentiel Helm ingress-nginx, mettez à jour le cache de référentiel Helm Chart local et installez le complément ingress-nginx via Helm. Vous pouvez définir l’étiquette DNS avec le paramètre **--set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"**, soit lorsque vous déployez le contrôleur d’entrée la première fois, soit ultérieurement. Dans cet exemple, vous spécifiez votre adresse IP publique que vous avez créée à l’étape précédente avec le paramètre **--set controller.service.loadBalancerIP="<STATIC_IP>"**.

```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
```

## Ajouter une terminaison HTTPS à un domaine personnalisé

À ce stade du tutoriel, vous avez une application web AKS avec NGINX comme contrôleur d’entrée, et un domaine personnalisé que vous pouvez utiliser pour accéder à votre application. L’étape suivante consiste à ajouter un certificat SSL au domaine afin que les utilisateurs puissent accéder à votre application de manière sécurisée via HTTPS.

### Configurer Cert Manager

Pour ajouter HTTPS, nous allons utiliser Cert Manager. Cert Manager est un outil open source pour obtenir et gérer les certificats SSL pour les déploiements Kubernetes. Cert Manager obtient des certificats des émetteurs publics populaires et des émetteurs privés, vérifie que les certificats sont valides et à jour et tente de renouveler les certificats à un moment configuré avant leur expiration.

1. Pour installer cert-manager, nous devons d’abord créer un espace de noms où pouvoir l’exécuter. Ce tutoriel installe cert-manager dans l’espace de noms cert-manager. Vous pouvez exécuter cert-manager dans un autre espace de noms mais vous devez faire des modifications dans les manifestes de déploiement.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Nous pouvons maintenant installer cert-manager. Toutes les ressources sont comprises dans un même fichier manifeste YAML. Installez le fichier manifeste à l’aide de la commande suivante :

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Ajoutez l’étiquette `certmanager.k8s.io/disable-validation: "true"` à l’espace de noms cert-manager en exécutant ce qui suit. Cela permet à cert-manager de créer dans son propre espace de noms les ressources système dont il a besoin pour démarrer TLS.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obtenir un certificat via des graphiques Helm

Helm est un outil de déploiement Kubernetes pour automatiser la création, l’empaquetage, la configuration et le déploiement d’applications et de services sur des clusters Kubernetes.

Cert-manager fournit des graphiques Helm comme méthode d’installation de première classe sur Kubernetes.

1. Ajoutez le référentiel Helm Jetstack. Ce dépôt est la seule source prise en charge des graphiques cert-manager. Il existe d’autres miroirs et copies sur Internet, mais ils sont non officiels et peuvent présenter un risque de sécurité.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Mettez à jour le cache du référentiel de graphiques Helm local.

    ```bash
    helm repo update
    ```

3. Installez le module complémentaire Cert-Manager via Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Appliquez le fichier YAML de l’émetteur de certificat. Les ClusterIssuers sont des ressources Kubernetes qui représentent des autorités de certification qui peuvent générer des certificats signés en honorant les demandes de signature de certificat. Tous les certificats cert-manager ont besoin d’un émetteur référencé prêt à tenter d’honorer la demande. Vous pouvez trouver l’émetteur dans lequel nous trouvons, le `cluster-issuer-prod.yml file`.

    ```bash
    export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Créer une classe de stockage personnalisée

Les classes de stockage par défaut sont adaptées aux scénarios les plus courants, mais pas à tous. Dans certains cas, vous souhaiterez peut-être personnaliser votre propre classe de stockage avec vos propres paramètres. Par exemple, utilisez le manifeste suivant pour configurer les **mountOptions** du partage de fichiers.
La valeur par défaut de **fileMode** et **dirMode** est **0755** pour les partages de fichiers montés Kubernetes. Vous pouvez spécifier les différentes options de montage sur l’objet de classe de stockage.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Déployer WordPress sur un cluster AKS

Pour ce tutoriel, nous utilisons un graphique Helm existant pour WordPress généré par Bitnami. Le graphique Bitnami Helm utilise une base de données locale MariaDB, nous devons donc remplacer ces valeurs pour utiliser l’application avec Azure Database pour MySQL. Vous pouvez remplacer les valeurs et les paramètres personnalisés du fichier `helm-wp-aks-values.yaml`.

1. Ajoutez le référentiel Wordpress Bitnami Helm.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Mettez à jour le cache de référentiel de graphiques Helm local.

    ```bash
    helm repo update
    ```

3. Installez la charge de travail Wordpress via Helm.

    ```bash
    export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
    export MY_WP_ADMIN_USER="wpcliadmin"
    export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
    helm upgrade --install --cleanup-on-fail \
        --wait --timeout 10m0s \
        --namespace wordpress \
        --create-namespace \
        --set wordpressUsername="$MY_WP_ADMIN_USER" \
        --set wordpressPassword="$MY_WP_ADMIN_PW" \
        --set wordpressEmail="$SSL_EMAIL_ADDRESS" \
        --set externalDatabase.host="$MY_MYSQL_HOSTNAME" \
        --set externalDatabase.user="$MY_MYSQL_ADMIN_USERNAME" \
        --set externalDatabase.password="$MY_MYSQL_ADMIN_PW" \
        --set ingress.hostname="$FQDN" \
        --values helm-wp-aks-values.yaml \
        wordpress bitnami/wordpress
    ```

Résultats :
<!-- expected_similarity=0.3 -->
```text
Release "wordpress" does not exist. Installing it now.
NAME: wordpress
LAST DEPLOYED: Tue Oct 24 16:19:35 2023
NAMESPACE: wordpress
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: wordpress
CHART VERSION: 18.0.8
APP VERSION: 6.3.2

** Please be patient while the chart is being deployed **

Your WordPress site can be accessed through the following DNS name from within your cluster:

    wordpress.wordpress.svc.cluster.local (port 80)

To access your WordPress site from outside the cluster follow the steps below:

1. Get the WordPress URL and associate WordPress hostname to your cluster external IP:

   export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
   echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
   echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts
    export CLUSTER_IP=$(minikube ip) # On Minikube. Use: `kubectl cluster-info` on others K8s clusters
    echo "WordPress URL: https://mydnslabelxxx.eastus.cloudapp.azure.com/"
    echo "$CLUSTER_IP  mydnslabelxxx.eastus.cloudapp.azure.com" | sudo tee -a /etc/hosts

2. Open a browser and access WordPress using the obtained URL.

3. Login with the following credentials below to see your blog:

    echo Username: wpcliadmin
    echo Password: $(kubectl get secret --namespace wordpress wordpress -o jsonpath="{.data.wordpress-password}" | base64 -d)
```

## Parcourir votre déploiement AKS sécurisé sur HTTPS

Exécutez la commande suivante pour obtenir le point de terminaison HTTPS de votre application :

> [!NOTE]
> Il faut souvent 2 à 3 minutes pour que le certificat SSL soit propagé et environ 5 minutes pour que tous les réplicas WordPress POD soient prêts et que le site soit entièrement accessible via HTTPS.

```bash
runtime="5 minute"
endtime=$(date -ud "$runtime" +%s)
while [[ $(date -u +%s) -le $endtime ]]; do
    export DEPLOYMENT_REPLICAS=$(kubectl -n wordpress get deployment wordpress -o=jsonpath='{.status.availableReplicas}');
    echo Current number of replicas "$DEPLOYMENT_REPLICAS/3";
    if [ "$DEPLOYMENT_REPLICAS" = "3" ]; then
        break;
    else
        sleep 10;
    fi;
done
```

Vérifiez que le contenu WordPress est correctement livré à l’aide de la commande suivante :

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Résultats :
<!-- expected_similarity=0.3 -->
```HTML
{
<!DOCTYPE html>
<html lang="en-US">
<head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name='robots' content='max-image-preview:large' />
<title>WordPress on AKS</title>
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/feed/" />
<link rel="alternate" type="application/rss+xml" title="WordPress on AKS &raquo; Comments Feed" href="https://mydnslabelxxx.eastus.cloudapp.azure.com/comments/feed/" />
}
```

Visitez le site web via l’URL suivante :

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Nettoyez les ressources (facultatif)

Pour éviter des frais Azure, vous devez nettoyer les ressources inutiles. Lorsque vous n’avez plus besoin du cluster, utilisez la commande [az group delete](/cli/azure/group#az-group-delete) pour supprimer le groupe de ressources, le service conteneur et toutes les ressources associées. 

> [!NOTE]
> Lorsque vous supprimez le cluster, le principal de service Microsoft Entra utilisé par le cluster AKS n’est pas supprimé. Pour obtenir des instructions sur la façon de supprimer le principal de service, consultez [Considérations et suppression du principal de service AKS](../../aks/kubernetes-service-principal.md#other-considerations). Si vous avez utilisé une identité managée, l’identité est managée par la plateforme et n’a pas besoin d’être supprimée.

## Étapes suivantes

- Découvrez comment [accéder au tableau de bord web Kubernetes](../../aks/kubernetes-dashboard.md) pour votre cluster AKS
- Découvrez comment [mettre votre cluster à l’échelle](../../aks/tutorial-kubernetes-scale.md)
- Découvrez comment gérer votre [instance de serveur flexible Azure Database pour MySQL](./quickstart-create-server-cli.md)
- Découvrir comment [configurer les paramètres serveur](./how-to-configure-server-parameters-cli.md) pour votre serveur de base de données
