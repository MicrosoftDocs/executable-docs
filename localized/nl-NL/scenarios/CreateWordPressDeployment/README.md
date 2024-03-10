---
title: Een schaalbaar en beveiligd WordPress-exemplaar implementeren op AKS
description: Deze zelfstudie laat zien hoe u een Scalable & Secure WordPress-exemplaar implementeert op AKS via CLI
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Quickstart: Een schaalbaar en beveiligd WordPress-exemplaar implementeren op AKS

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

Welkom bij deze zelfstudie waarin we u stapsgewijs zullen volgen bij het maken van een Azure Kubernetes-webtoepassing die is beveiligd via https. In deze zelfstudie wordt ervan uitgegaan dat u al bent aangemeld bij Azure CLI en een abonnement hebt geselecteerd voor gebruik met de CLI. Er wordt ook van uitgegaan dat Helm is geïnstalleerd ([hier vindt](https://helm.sh/docs/intro/install/) u instructies).

## Omgevingsvariabelen definiëren

De eerste stap in deze zelfstudie is het definiëren van omgevingsvariabelen.

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

## Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. We maken er een voor deze zelfstudie. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde parameters $MY_RESOURCE_GROUP_NAME en $REGION parameters.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Resultaten:

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

## Een virtueel netwerk en een subnet maken

Een virtueel netwerk is de fundamentele bouwsteen voor privénetwerken in Azure. Met Azure Virtual Network kunnen Azure-resources, zoals VM's, veilig met elkaar en internet communiceren.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Resultaten:

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

## Azure Database for MySQL - flexibele server maken

Azure Database for MySQL - Flexible Server is een beheerde service die u kunt gebruiken voor het uitvoeren, beheren en schalen van maximaal beschikbare MySQL-servers in de cloud. Maak een flexibele server met de [opdracht az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) . Een server kan meerdere databases bevatten. Met de volgende opdracht maakt u een server met behulp van servicestandaarden en variabele waarden uit de lokale omgeving van uw Azure CLI:

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

Resultaten:

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

De gemaakte server heeft de volgende kenmerken:

- De servernaam, de gebruikersnaam van de beheerder, het beheerderswachtwoord, de naam van de resourcegroep, de locatie zijn al opgegeven in de lokale contextomgeving van de Cloud Shell en worden gemaakt op dezelfde locatie als u de resourcegroep en de andere Azure-onderdelen bent.
- Servicestandaarden voor resterende serverconfiguraties: rekenlaag (Burstable), rekengrootte/SKU (Standard_B2s), bewaarperiode voor back-ups (7 dagen) en MySQL-versie (8.0.21)
- De standaardverbindingsmethode is Privétoegang (VNet-integratie) met een gekoppeld virtueel netwerk en een automatisch gegenereerd subnet.

> [!NOTE]
> De verbindingsmethode kan niet worden gewijzigd na het maken van de server. Als u bijvoorbeeld tijdens het maken hebt geselecteerd `Private access (VNet Integration)` , kunt u deze niet wijzigen `Public access (allowed IP addresses)` na het maken. U kunt het beste een server met privétoegang maken om veilig toegang te krijgen tot uw server met behulp van VNet-integratie. Meer informatie over persoonlijke toegang vindt u in het [artikel over concepten](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Als u een standaardinstelling wilt wijzigen, raadpleegt u de [referentiedocumentatie](https://learn.microsoft.com/cli/azure//mysql/flexible-server) van Azure CLI voor de complete lijst van configureerbare CLI-parameters.

## De status van Azure Database for MySQL - Flexible Server controleren

Het duurt enkele minuten om de Azure Database for MySQL Flexibele server en ondersteunende resources te maken.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Serverparameters configureren in Azure Database for MySQL - Flexibele server

U kunt de configuratie van Azure Database for MySQL - Flexible Server beheren met behulp van serverparameters. De serverparameters worden geconfigureerd met de standaardwaarde en aanbevolen waarde wanneer u de server maakt.

Geef de details van de serverparameter weer om details weer te geven over een bepaalde parameter voor een server, voert u de [opdracht az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) uit.

### Azure Database for MySQL - SSL-verbindingsparameter flexibele server uitschakelen voor WordPress-integratie

U kunt ook de waarde van bepaalde serverparameters wijzigen, waarmee de onderliggende configuratiewaarden voor de MySQL-serverengine worden bijgewerkt. Als u de serverparameter wilt bijwerken, gebruikt u de [opdracht az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Resultaten:

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

## AKS-cluster maken

Maak een AKS-cluster met behulp van de opdracht az aks create met de bewakingsparameter --enable-addons om Container Insights in te schakelen. In het volgende voorbeeld wordt een cluster met automatische schaalaanpassing, beschikbaarheidszone met de naam myAKSCluster gemaakt:

Dit duurt enkele minuten

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

## Verbinding maken met het cluster

Als u een Kubernetes-cluster wilt beheren, gebruikt u de Kubernetes-opdrachtregelclient kubectl. kubectl is al geïnstalleerd als u Azure Cloud Shell gebruikt.

1. Installeer az aks CLI lokaal met behulp van de opdracht az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Configureer kubectl om verbinding te maken met uw Kubernetes-cluster met behulp van de opdracht az aks get-credentials. De volgende opdracht:

    - Hiermee downloadt u referenties en configureert u de Kubernetes CLI om deze te gebruiken.
    - Maakt gebruik van ~/.kube/config, de standaardlocatie voor het Kubernetes-configuratiebestand. Geef een andere locatie op voor uw Kubernetes-configuratiebestand met behulp van het argument --file.

    > [!WARNING]
    > Hiermee worden alle bestaande referenties met dezelfde vermelding overschreven

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Controleer de verbinding met uw cluster met behulp van de opdracht kubectl get. Met deze opdracht wordt een lijst met de clusterknooppunten geretourneerd.

    ```bash
    kubectl get nodes
    ```

## NGINX-ingangscontroller installeren

U kunt uw ingangscontroller configureren met een statisch openbaar IP-adres. Het statische openbare IP-adres blijft behouden als u de ingangscontroller verwijdert. Het IP-adres blijft niet behouden als u uw AKS-cluster verwijdert.
Wanneer u uw ingangscontroller bijwerken, moet u een parameter doorgeven aan de Helm-release om ervoor te zorgen dat de controllerservice voor inkomend verkeer op de hoogte wordt gesteld van de load balancer die eraan wordt toegewezen. Voor een correcte werking van de HTTPS-certificaten gebruikt u een DNS-label om een FQDN te configureren voor het IP-adres van de ingangscontroller.
Uw FQDN moet dit formulier volgen: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Voeg de aantekeningen --set controller.service.annotaties toe. service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" parameter. Het DNS-label kan worden ingesteld wanneer de ingangscontroller voor het eerst wordt geïmplementeerd of later kan worden geconfigureerd. Voeg de parameter --set controller.service.loadBalancerIP="<STATIC_IP>" toe. Geef uw eigen openbare IP-adres op dat in de vorige stap is gemaakt.

1. De Helm-opslagplaats voor inkomend verkeer toevoegen

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Cache van lokale Helm-grafiekopslagplaats bijwerken

    ```bash
    helm repo update
    ```

3. Installeer de invoegtoepassing ingress-nginx via Helm door het volgende uit te voeren:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## HTTPS-beëindiging toevoegen aan aangepast domein

Op dit moment in de zelfstudie hebt u een AKS-web-app met NGINX als de ingangscontroller en een aangepast domein dat u kunt gebruiken voor toegang tot uw toepassing. De volgende stap is het toevoegen van een SSL-certificaat aan het domein, zodat gebruikers uw toepassing veilig kunnen bereiken via https.

## Certificaatbeheer instellen

Om HTTPS toe te voegen gaan we Cert Manager gebruiken. Cert Manager is een opensource-hulpprogramma dat wordt gebruikt voor het verkrijgen en beheren van SSL-certificaat voor Kubernetes-implementaties. Cert Manager verkrijgt certificaten van verschillende verleners, zowel populaire openbare verleners als privéverleners, en zorgt ervoor dat de certificaten geldig en up-to-date zijn en proberen certificaten te vernieuwen op een geconfigureerd tijdstip voordat ze verlopen.

1. Als u cert-manager wilt installeren, moet u eerst een naamruimte maken om deze in uit te voeren. In deze zelfstudie wordt certificaatbeheer geïnstalleerd in de naamruimte cert-manager. Het is mogelijk om certificaatbeheer uit te voeren in een andere naamruimte, hoewel u wijzigingen moet aanbrengen in de implementatiemanifesten.

    ```bash
    kubectl create namespace cert-manager
    ```

2. We kunnen nu certificaatbeheer installeren. Alle resources zijn opgenomen in één YAML-manifestbestand. Dit kan worden geïnstalleerd door het volgende uit te voeren:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Voeg het label certmanager.k8s.io/disable-validation: 'true' toe aan de naamruimte cert-manager door het volgende uit te voeren. Hierdoor kunnen de systeembronnen die certificaatbeheer vereist, TLS opstarten om te worden gemaakt in een eigen naamruimte.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Certificaat verkrijgen via Helm-grafieken

Helm is een Kubernetes-implementatieprogramma voor het automatiseren van het maken, verpakken, configureren en implementeren van toepassingen en services voor Kubernetes-clusters.

Cert-manager biedt Helm-grafieken als een eersteklas installatiemethode op Kubernetes.

1. De Jetstack Helm-opslagplaats toevoegen

    Deze opslagplaats is de enige ondersteunde bron van cert-manager-grafieken. Er zijn enkele andere spiegels en kopieën via internet, maar die zijn volledig onofficiële en kunnen een beveiligingsrisico opleveren.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Cache van lokale Helm-grafiekopslagplaats bijwerken

    ```bash
    helm repo update
    ```

3. Installeer de Cert-Manager-invoegtoepassing via Helm door het volgende uit te voeren:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. YAML-bestand van certificaatverlener toepassen

    ClusterIssuers zijn Kubernetes-resources die certificeringsinstanties (CA's) vertegenwoordigen die ondertekende certificaten kunnen genereren door aanvragen voor certificaatondertekening te respecteren. Voor alle certificaten van certificaatbeheer is een verlener vereist waarnaar wordt verwezen, die in een kant-en-klare voorwaarde staat om te proberen de aanvraag te respecteren.
    De uitgever die we gebruiken, vindt u in de `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Een aangepaste opslagklasse maken

De standaardopslagklassen zijn geschikt voor de meest voorkomende scenario's, maar niet allemaal. In sommige gevallen wilt u mogelijk uw eigen opslagklasse aanpassen met uw eigen parameters. Gebruik bijvoorbeeld het volgende manifest om de mountOptions van de bestandsshare te configureren.
De standaardwaarde voor fileMode en dirMode is 0755 voor gekoppelde Kubernetes-bestandsshares. U kunt de verschillende koppelingsopties voor het opslagklasseobject opgeven.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## WordPress implementeren op AKS-cluster

Voor dit document gebruiken we een bestaande Helm-grafiek voor WordPress die is gebouwd door Bitnami. Bitnami Helm-grafiek maakt bijvoorbeeld gebruik van lokale MariaDB als de database en we moeten deze waarden overschrijven om de app te gebruiken met Azure Database for MySQL. Alle onderdrukkingswaarden U kunt de waarden overschrijven en de aangepaste instellingen vindt u in het bestand `helm-wp-aks-values.yaml`

1. De Wordpress Bitnami Helm-opslagplaats toevoegen

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Cache van lokale Helm-grafiekopslagplaats bijwerken

    ```bash
    helm repo update
    ```

3. Installeer de Wordpress-workload via Helm door het volgende uit te voeren:

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

Resultaten:

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

## Bladeren door uw AKS-implementatie die is beveiligd via HTTPS

Voer de volgende opdracht uit om het HTTPS-eindpunt voor uw toepassing op te halen:

> [!NOTE]
> Het duurt vaak 2-3 minuten voordat het SSL-certificaat is gepropogaat en ongeveer 5 minuten om alle WordPress POD-replica's gereed te hebben en de site volledig bereikbaar te zijn via https.

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

Controleren of WordPress-inhoud correct wordt geleverd.

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Resultaten:

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

De website kan worden bezocht door de onderstaande URL te volgen:

```bash
echo "You can now visit your web server at https://$FQDN"
```
