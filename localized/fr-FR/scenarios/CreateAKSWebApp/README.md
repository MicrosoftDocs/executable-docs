---
title: Déployer un cluster Azure Kubernetes Service scalable et sécurisé avec Azure CLI
description: Ce tutoriel vous guide pas à pas dans la création d’une application web Azure Kubernetes sécurisée sur https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Démarrage rapide : Déployer un cluster Azure Kubernetes Service scalable et sécurisé avec Azure CLI

[![Déployer dans Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Bienvenue dans ce tutoriel qui vous guide pas à pas dans la création d’une application web Azure Kubernetes sécurisée sur https. Ce tutoriel suppose que vous êtes déjà connecté à Azure CLI et que vous avez sélectionné un abonnement à utiliser avec l’interface CLI. Il suppose également que vous avez installé Helm ([Instructions disponibles ici](https://helm.sh/docs/intro/install/)).

## Définissez des variables d’environnement

La première étape de ce tutoriel définit des variables d’environnement.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="eastus"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Créer un groupe de ressources

Un groupe de ressources est un conteneur de ressources associées. Toutes les ressources doivent être placées dans un groupe de ressources. Nous en créons un pour ce tutoriel. La commande suivante crée un groupe de ressources avec les paramètres $MY_RESOURCE_GROUP_NAME et $REGION précédemment définis.

```bash
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

```JSON
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.xxx.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx",
    "location": "eastus",
    "name": "myVNetxxx",
    "provisioningState": "Succeeded",
    "resourceGroup": "myAKSResourceGroupxxxxxx",
    "subnets": [
      {
        "addressPrefix": "10.xxx.0.0/22",
        "delegations": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/myAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/myVNetxxx/subnets/mySNxxx",
        "name": "mySNxxx",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "myAKSResourceGroupxxxxxx",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## S’inscrire à des fournisseurs de ressources Azure AKS

Vérifiez que les fournisseurs Microsoft.OperationsManagement et Microsoft.OperationalInsights sont inscrits dans votre abonnement. Ce sont des fournisseurs de ressources Azure nécessaires pour prendre en charge [Container Insights](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Pour vérifier l’état de l’inscription, exécutez les commandes suivantes

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Créer un cluster AKS

Créez un cluster AKS à l’aide de la commande az aks create avec le paramètre --enable-addons monitoring pour activer les Insights de conteneur. L’exemple suivant crée un cluster avec la mise à l’échelle automatique et une zone de disponibilité.

Cette opération prendra quelques minutes.

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

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
  --set controller.service.loadBalancerIP=$MY_STATIC_IP \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --wait
```

## Déployer l’application

Un fichier manifeste Kubernetes définit un état souhaité d’un cluster, notamment les images conteneur à exécuter.

Dans ce guide de démarrage rapide, un manifeste est utilisé afin de créer tous les objets nécessaires pour l’exécution de l’application Azure Vote. Ce manifeste comprend deux déploiements Kubernetes :

- Exemples d’applications Python pour Azure Vote.
- Une instance Redis.

Deux services Kubernetes sont également créés :

- Un service interne pour l’instance Redis.
- Un service externe pour accéder à l’application Azure vote à partir d’Internet.

Enfin, une ressource d’entrée est créée pour router le trafic vers l’application de vote Azure.

Un fichier de test YML de l’application de vote est déjà préparé. Pour déployer cette application, exécutez la commande suivante

```bash
kubectl apply -f azure-vote-start.yml
```

## Tester l’application

Vérifiez que l’application est en cours d’exécution en consultant l’IP publique ou l’URL de l’application. Vous pouvez rechercher l’URL de l’application en exécutant la commande suivante :

> [!Note]
> Il faut souvent 2 à 3 minutes pour que les POD soient créés et que le site soit accessible sur HTTP

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get pods -l app=azure-vote-front -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}'); echo $STATUS;
   if [ "$STATUS" == 'True' ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
curl "http://$FQDN"
```

Résultats :

<!-- expected_similarity=0.3 -->

```HTML
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <link rel="stylesheet" type="text/css" href="/static/default.css">
    <title>Azure Voting App</title>

    <script language="JavaScript">
        function send(form){
        }
    </script>

</head>
<body>
    <div id="container">
        <form id="form" name="form" action="/"" method="post"><center>
        <div id="logo">Azure Voting App</div>
        <div id="space"></div>
        <div id="form">
        <button name="vote" value="Cats" onclick="send()" class="button button1">Cats</button>
        <button name="vote" value="Dogs" onclick="send()" class="button button2">Dogs</button>
        <button name="vote" value="reset" onclick="send()" class="button button3">Reset</button>
        <div id="space"></div>
        <div id="space"></div>
        <div id="results"> Cats - 0 | Dogs - 0 </div>
        </form>
        </div>
    </div>
</body>
</html>
```

## Ajouter une terminaison HTTPS à un domaine personnalisé

À ce stade du tutoriel, vous avez une application web AKS avec NGINX comme contrôleur d’entrée, et un domaine personnalisé que vous pouvez utiliser pour accéder à votre application. L’étape suivante consiste à ajouter un certificat SSL au domaine afin que les utilisateurs puissent accéder à votre application de manière sécurisée sur HTTPS.

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

3. Installez le module complémentaire Cert-Manager via helm en exécutant ce qui suit :

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Appliquer le fichier YAML de l’émetteur de certificat

   Les ClusterIssuers sont des ressources Kubernetes qui représentent des autorités de certification capables de générer des certificats signés en honorant les demandes de signature de certificat. Tous les certificats cert-manager ont besoin d’un émetteur référencé prêt à tenter d’honorer la demande.
   L’émetteur que nous utilisons est disponible dans le `cluster-issuer-prod.yml file`

   ```bash
   cluster_issuer_variables=$(<cluster-issuer-prod.yml)
   echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
   ```

5. Mettez à jour l’application de vote pour qu’elle utilise Cert-Manager pour obtenir un certificat SSL.

   Le fichier YAML complet se trouve dans `azure-vote-nginx-ssl.yml`

   ```bash
   azure_vote_nginx_ssl_variables=$(<azure-vote-nginx-ssl.yml)
   echo "${azure_vote_nginx_ssl_variables//\$FQDN/$FQDN}" | kubectl apply -f -
   ```

<!--## Validate application is working

Wait for the SSL certificate to issue. The following command will query the 
status of the SSL certificate for 3 minutes. In rare occasions it may take up to 
15 minutes for Lets Encrypt to issue a successful challenge and 
the ready state to be 'True'

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(kubectl get certificate --output jsonpath={..status.conditions[0].status}); echo $STATUS; if [ "$STATUS" = 'True' ]; then break; else sleep 10; fi; done
```

Validate SSL certificate is True by running the follow command:

```bash
kubectl get certificate --output jsonpath={..status.conditions[0].status}
```

Results:

<!-- expected_similarity=0.3 -->
<!--
```ASCII
True
```
-->

## Parcourir votre déploiement AKS sécurisé sur HTTPS

Exécutez la commande suivante pour obtenir le point de terminaison HTTPS de votre application :

> [!Note]
> Il faut souvent 2 à 3 minutes pour que le certificat SSL soit propagé et que le site soit accessible sur HTTP.

```bash
runtime="5 minute";
endtime=$(date -ud "$runtime" +%s);
while [[ $(date -u +%s) -le $endtime ]]; do
   STATUS=$(kubectl get svc --namespace=ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}');
   echo $STATUS;
   if [ "$STATUS" == "$MY_STATIC_IP" ]; then
      break;
   else
      sleep 10;
   fi;
done
```

```bash
echo "You can now visit your web server at https://$FQDN"
```

## Étapes suivantes

- [Documentation Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Créer un registre de conteneurs Azure](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Mettre à l’échelle votre application dans AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Mettre à jour votre application dans AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)