---
title: Déployez une instance WordPress évolutive et sécurisée sur AKS
description: Ce tutoriel montre comment déployer une instance WordPress évolutive et sécurisée sur AKS via l’interface de ligne de commande
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Démarrage rapide : déployer une instance WordPress évolutive et sécurisée sur AKS

Bienvenue dans ce tutoriel qui vous guide pas à pas dans la création d’une application web Azure Kubernetes sécurisée sur https. Ce tutoriel suppose que vous êtes déjà connecté à Azure CLI et que vous avez sélectionné un abonnement à utiliser avec l’interface CLI. Il suppose également que vous avez installé Helm ([Instructions disponibles ici](https://helm.sh/docs/intro/install/)).

## Définissez des variables d’environnement

La première étape de ce tutoriel définit des variables d’environnement.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export MY_MYSQL_DB_NAME="mydb$RANDOM_ID"
export MY_MYSQL_ADMIN_USERNAME="dbadmin$RANDOM_ID"
export MY_MYSQL_ADMIN_PW="$(openssl rand -base64 32)"
export MY_MYSQL_SN_NAME="myMySQLSN$RANDOM_ID"
export MY_MYSQL_HOSTNAME="$MY_MYSQL_DB_NAME.mysql.database.azure.com"
export MY_WP_ADMIN_PW="$(openssl rand -base64 32)"
export MY_WP_ADMIN_USER="wpcliadmin"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. Nous en créons un pour ce tutoriel. La commande suivante crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

```bash
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

## Créer un réseau virtuel et un sous-réseau

Un réseau virtuel est l’élément de construction fondamental pour les réseaux privés dans Azure. Le réseau virtuel Microsoft Azure permet à des ressources Azure, comme des machines virtuelles, de communiquer de manière sécurisée entre elles et sur Internet.

```bash
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

## Créer un serveur flexible Azure Database pour MySQL

Azure Database pour MySQL - Serveur flexible est un service managé qui vous permet d’exécuter, de gérer et de mettre à l’échelle des serveurs MySQL hautement disponibles dans le cloud. Créez un serveur flexible avec la commande [az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create). Un serveur peut contenir plusieurs bases de données. La commande suivante crée un serveur en utilisant les valeurs par défaut du service et les valeurs variables issues de l’environnement local de votre interface Azure CLI :

```bash
echo "Your MySQL user $MY_MYSQL_ADMIN_USERNAME password is: $MY_WP_ADMIN_PW" 
```

```bash
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

- Le nom du serveur, le nom d'utilisateur de l'administrateur, le mot de passe de l'administrateur, le nom du groupe de ressources et l'emplacement sont déjà spécifiés dans l'environnement contextuel local du cloud shell et seront créés au même endroit que votre groupe de ressources et les autres composants Azure.
- Valeurs par défaut du service pour les configurations restantes : Niveau de calcul (burstable), Taille de calcul/SKU (Standard_B2s), Période de rétention des sauvegardes (7 jours) et Version de MySQL (8.0.21)
- La méthode de connectivité par défaut est Accès privé (intégration au réseau virtuel), avec un réseau virtuel lié et un sous-réseau généré automatiquement.

> [!NOTE]
> Une fois le serveur créé, la méthode de connectivité ne peut pas être modifiée. Par exemple, si vous avez sélectionné `Private access (VNet Integration)` pendant la création, vous ne pouvez pas passer à `Public access (allowed IP addresses)` après la création. Nous vous recommandons vivement de sélectionner l'Accès privé lors de la création d'un serveur afin de pouvoir y accéder en toute sécurité à l'aide de l'intégration au réseau virtuel. Pour en savoir plus sur l'accès privé, consultez l'[article consacré aux concepts](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Si vous souhaitez changer des valeurs par défaut, reportez-vous à la [documentation de référence](https://learn.microsoft.com/cli/azure//mysql/flexible-server) d’Azure CLI pour obtenir la liste complète des paramètres CLI configurables.

## Vérifiez Azure Database pour MySQL : état du serveur flexible

La création de Azure Database pour MySQL : serveur flexibile et des ressources correspondantes ne prend que quelques minutes.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Configurer les paramètres de serveur dans Azure Database pour MySQL : serveur flexibile

Vous pouvez gérer la configuration d’Azure Database pour MySQL - Serveur flexible à l’aide des paramètres de serveur. Les paramètres de serveur sont configurés avec la valeur par défaut et la valeur recommandée lors de la création du serveur.

Afficher les détails d’un paramètre de serveur Pour afficher les détails d’un paramètre particulier pour un serveur, exécutez la commande [az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter).

### Désactiver Azure Database pour MySQL : paramètre de connexion SSL du serveur flexible pour l'intégration de WordPress

Vous pouvez également modifier la valeur de certains paramètres de serveur, ce qui a pour effet de mettre à jour les valeurs de configuration sous-jacentes du moteur de serveur MySQL. Pour mettre à jour le paramètre de serveur, utilisez la commande [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set).

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

Créez un cluster AKS à l’aide de la commande az aks create avec le paramètre --enable-addons monitoring pour activer les Insights de conteneur. L’exemple suivant crée un cluster à mise à l’échelle automatique, compatible avec la zone de disponibilité, nommé myAKSCluster :

Cette opération prendra quelques minutes

```bash
export MY_SN_ID=$(az network vnet subnet list --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "[0].id" --output tsv)

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

## Se connecter au cluster

Pour gérer un cluster Kubernetes, utilisez kubectl, le client de ligne de commande Kubernetes. Kubectl est déjà installé si vous utilisez Azure Cloud Shell.

1. Installez l’interface CLI az aks localement avec la commande az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configurez kubectl pour vous connecter à votre cluster Kubernetes à l’aide de la commande aks get-credentials. La commande ci-après effectue les opérations suivantes :

    - Cette étape télécharge les informations d’identification et configure l’interface de ligne de commande Kubernetes pour leur utilisation.
    - Utilise ~/.kube/config, emplacement par défaut du fichier de configuration Kubernetes. Spécifiez un autre emplacement pour votre fichier de configuration Kubernetes à l’aide de l’argument --file.

    > [!WARNING]
    > Cela remplace toutes les informations d’identification existantes par la même entrée

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Pour vérifier la connexion à votre cluster, exécutez la commande kubectl get. Cette commande renvoie la liste des nœuds de cluster.

    ```bash
    kubectl get nodes
    ```

## Installer le contrôleur d’entrée NGINX

Vous pouvez configurer votre contrôleur d’entrée avec une adresse IP publique statique. L’adresse IP publique statique reste si vous supprimez votre contrôleur d’entrée. L’adresse IP ne reste pas si vous supprimez votre cluster AKS.
Lorsque vous mettez à niveau votre contrôleur d’entrée, vous devez passer un paramètre à la version Helm pour vous assurer que le service du contrôleur d’entrée est informé de l’équilibreur de charge qui lui sera alloué. Pour que les certificats HTTPS fonctionnent correctement, vous utilisez une étiquette DNS pour configurer un FQDN pour l'adresse IP du contrôleur d'entrée.
Votre nom de domaine complet doit suivre ce formulaire : $MY_DNS_LABEL.AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Ajoutez le paramètre --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>". L’étiquette DNS peut être définie lors du premier déploiement du contrôleur d’entrée ou être configuré ultérieurement. Ajoutez le paramètre --set controller.service.loadBalancerIP="<STATIC_IP>". Spécifiez votre propre adresse IP publique, créée à l’étape précédente.

1. Ajoutez le référentiel Helm ingress-nginx

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Mettre à jour le cache du dépôt de graphiques Helm local

    ```bash
    helm repo update
    ```

3. Installez le module complémentaire ingress-nginx via Helm en exécutant les éléments suivants :

    ```bash
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

## Configurer Cert Manager

Pour ajouter HTTPS, nous utilisons Cert Manager. Cert Manager est un outil open source utilisé pour obtenir et gérer un certificat SSL pour les déploiements Kubernetes. Cert Manager obtient des certificats de divers émetteurs, des émetteurs publics populaires et des émetteurs privés, vérifie que les certificats sont valides et à jour, et tente de renouveler les certificats à un moment configuré avant l’expiration.

1. Pour installer cert-manager, nous devons d’abord créer un espace de noms où pouvoir l’exécuter. Ce tutoriel installe cert-manager dans l’espace de noms cert-manager. Vous pouvez exécuter cert-manager dans un autre espace de noms, mais vous devez faire des modifications dans les manifestes de déploiement.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Nous pouvons maintenant installer cert-manager. Toutes les ressources sont comprises dans un même fichier manifeste YAML. Vous pouvez l’installer en exécutant ce qui suit :

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Ajoutez l’étiquette certmanager.k8s.io/disable-validation: « true » à l’espace de noms cert-manager en exécutant ce qui suit. Cela permet à cert-manager de créer dans son propre espace de noms les ressources système dont il a besoin pour démarrer TLS.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Obtenir un certificat via des graphiques Helm

Helm est un outil de déploiement Kubernetes pour automatiser la création, l’empaquetage, la configuration et le déploiement d’applications et de services sur des clusters Kubernetes.

Cert-manager fournit des graphiques Helm comme méthode d’installation de première classe sur Kubernetes.

1. Ajouter le dépôt Helm Jetstack

    Ce dépôt est la seule source prise en charge des graphiques cert-manager. Il existe d’autres miroirs et copies sur Internet, mais ils sont complètement non officiels et peuvent présenter un risque de sécurité.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Mettre à jour le cache du dépôt de graphiques Helm local

    ```bash
    helm repo update
    ```

3. Installez le module complémentaire Cert-Manager via Helm en exécutant les éléments suivants :

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Appliquer le fichier YAML de l’émetteur de certificat

    Les ClusterIssuers sont des ressources Kubernetes qui représentent des autorités de certification capables de générer des certificats signés en honorant les demandes de signature de certificat. Tous les certificats cert-manager ont besoin d’un émetteur référencé prêt à tenter d’honorer la demande.
    L’émetteur que nous utilisons est disponible dans le `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Créer une classe de stockage personnalisée

Les classes de stockage par défaut sont adaptées aux scénarios les plus courants, mais pas à tous. Dans certains cas, vous souhaiterez peut-être personnaliser votre propre classe de stockage avec vos propres paramètres. Par exemple, utilisez le manifeste suivant pour configurer les mountOptions du partage de fichiers.
La valeur par défaut de fileMode et dirMode est 0755 pour les partages de fichiers montés par Kubernetes. Vous pouvez spécifier les différentes options de montage sur l’objet de classe de stockage.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Déployer WordPress sur un cluster AKS

Pour ce document, nous utilisons un graphique Helm existant pour WordPress généré par Bitnami. Par exemple, le graphique Bitnami Helm utilise la base de données locale MariaDB et nous devons remplacer ces valeurs pour utiliser l’application avec Azure Database pour MySQL. Toutes les valeurs de remplacement, vous pouvez remplacer les valeurs et les paramètres personnalisés sont disponibles dans le fichier `helm-wp-aks-values.yaml`

1. Ajoutez le référentiel Wordpress Bitnami Helm

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Mettre à jour le cache du dépôt de graphiques Helm local

    ```bash
    helm repo update
    ```

3. Installez la charge de travail Wordpress via Helm en exécutant les éléments suivants :

    ```bash
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

Vérification de la remise correcte du contenu WordPress.

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

Vous pouvez visiter le site web en suivant l’URL ci-dessous :

```bash
echo "You can now visit your web server at https://$FQDN"
```
