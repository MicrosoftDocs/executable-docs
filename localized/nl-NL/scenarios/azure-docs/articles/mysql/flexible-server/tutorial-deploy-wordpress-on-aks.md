---
title: 'Zelfstudie: WordPress implementeren in een AKS-cluster met behulp van Azure CLI'
description: 'Meer informatie over hoe u WordPress snel kunt bouwen en implementeren op AKS met Azure Database for MySQL: flexibele server.'
ms.service: mysql
ms.subservice: flexible-server
author: mksuni
ms.author: sumuth
ms.topic: tutorial
ms.date: 3/20/2024
ms.custom: 'vc, devx-track-azurecli, innovation-engine, linux-related-content'
---

# Zelfstudie: WordPress-app implementeren op AKS met Azure Database for MySQL - Flexible Server

[!INCLUDE[applies-to-mysql-flexible-server](../includes/applies-to-mysql-flexible-server.md)]

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

In deze zelfstudie implementeert u een schaalbare WordPress-toepassing die is beveiligd via HTTPS op een AKS-cluster (Azure Kubernetes Service) met Azure Database for MySQL flexibele server met behulp van de Azure CLI.
**[AKS](../../aks/intro-kubernetes.md)** is een beheerde Kubernetes-service waarmee u snel clusters kunt implementeren en beheren. **[Azure Database for MySQL flexibele server](overview.md)** is een volledig beheerde databaseservice die is ontworpen om gedetailleerdere controle en flexibiliteit te bieden voor databasebeheerfuncties en configuratie-instellingen.

> [!NOTE]
> In deze zelfstudie wordt ervan uitgegaan dat u basiskennis hebt van Kubernetes-concepten, WordPress en MySQL.

[!INCLUDE [flexible-server-free-trial-note](../includes/flexible-server-free-trial-note.md)]

## Vereisten 

Voordat u aan de slag gaat, moet u ervoor zorgen dat u bent aangemeld bij Azure CLI en een abonnement hebt geselecteerd dat u wilt gebruiken met de CLI. Zorg ervoor dat Helm is [geïnstalleerd](https://helm.sh/docs/intro/install/).

> [!NOTE]
> Als u de opdrachten in deze zelfstudie lokaal uitvoert in plaats van Azure Cloud Shell, voert u de opdrachten uit als beheerder.

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

Een Azure-resourcegroep is een logische groep waarin Azure-resources worden geïmplementeerd en beheerd. Alle resources moeten in een resourcegroep worden geplaatst. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde `$MY_RESOURCE_GROUP_NAME` parameters.`$REGION`

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

> [!NOTE]
> De locatie voor de resourcegroep is de plaats waar de metagegevens van de resourcegroep worden opgeslagen. Hier worden uw resources ook uitgevoerd in Azure als u geen andere regio opgeeft tijdens het maken van resources.

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

## Een exemplaar van een flexibele Azure Database for MySQL-server maken

Flexibele Azure Database for MySQL-server is een beheerde service die u kunt gebruiken voor het uitvoeren, beheren en schalen van maximaal beschikbare MySQL-servers in de cloud. Maak een exemplaar van een flexibele Azure Database for MySQL-server met de [opdracht az mysql flexible-server create](/cli/azure/mysql/flexible-server) . Een server kan meerdere databases bevatten. Met de volgende opdracht maakt u een server met behulp van servicestandaarden en variabele waarden vanuit de lokale context van uw Azure CLI:

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

- Er wordt een nieuwe lege database gemaakt wanneer de server voor het eerst wordt ingericht.
- De servernaam, de gebruikersnaam van de beheerder, het beheerderswachtwoord, de naam van de resourcegroep en de locatie zijn al opgegeven in de lokale contextomgeving van de cloudshell en bevinden zich op dezelfde locatie als uw resourcegroep en andere Azure-onderdelen.
- De standaardinstellingen voor de overige serverconfiguraties zijn de rekenlaag (Burstable), de rekenkracht/SKU (Standard_B2s), de bewaarperiode voor back-ups (zeven dagen) en de MySQL-versie (8.0.21).
- De standaardverbindingsmethode is Privétoegang (integratie van virtueel netwerk) met een gekoppeld virtueel netwerk en een automatisch gegenereerd subnet.

> [!NOTE]
> De verbindingsmethode kan niet worden gewijzigd na het maken van de server. Als u bijvoorbeeld tijdens het maken hebt geselecteerd `Private access (VNet Integration)` , kunt u niet wijzigen `Public access (allowed IP addresses)` in na het maken. U kunt het beste een server met privétoegang maken om veilig toegang te krijgen tot uw server met behulp van VNet-integratie. Meer informatie over persoonlijke toegang vindt u in het [artikel over concepten](./concepts-networking-vnet.md).

Als u de standaardinstellingen wilt wijzigen, raadpleegt u de Azure CLI-referentiedocumentatie [](/cli/azure//mysql/flexible-server) voor de volledige lijst met configureerbare CLI-parameters.

## De status van Azure Database for MySQL - Flexible Server controleren

Het duurt enkele minuten om de Azure Database for MySQL Flexibele server en ondersteunende resources te maken.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Serverparameters configureren in Azure Database for MySQL - Flexibele server

U kunt de configuratie van Azure Database for MySQL - Flexible Server beheren met behulp van serverparameters. De serverparameters worden geconfigureerd met de standaardwaarde en aanbevolen waarde wanneer u de server maakt.

Als u details over een bepaalde parameter voor een server wilt weergeven, voert u de [opdracht az mysql flexible-server parameter show](/cli/azure/mysql/flexible-server/parameter) uit.

### Azure Database for MySQL - SSL-verbindingsparameter flexibele server uitschakelen voor WordPress-integratie

U kunt ook de waarde van bepaalde serverparameters wijzigen om de onderliggende configuratiewaarden voor de MySQL-serverengine bij te werken. Als u de serverparameter wilt bijwerken, gebruikt u de [opdracht az mysql flexible-server parameter set](/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

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

## Een AKS-cluster maken

Als u een AKS-cluster wilt maken met Container Insights, gebruikt u de [opdracht az aks create](/cli/azure/aks#az-aks-create) met de **bewakingsparameter --enable-addons** . In het volgende voorbeeld wordt een cluster met automatische schaalaanpassing, beschikbaarheidszone ingeschakeld met de naam **myAKSCluster** gemaakt:

Deze actie duurt enkele minuten.

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
> [!NOTE]
> Wanneer een AKS-cluster wordt gemaakt, wordt automatisch een tweede resourcegroep gemaakt om de AKS-resources in op te slaan. Zie [Waarom worden er twee resourcegroepen gemaakt met AKS?](../../aks/faq.md#why-are-two-resource-groups-created-with-aks)

## Verbinding maken met het cluster

Als u een Kubernetes-cluster wilt beheren, gebruikt u [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/), de Kubernetes-opdrachtregelclient. Als u Azure Cloud Shell gebruikt, is `kubectl` al geïnstalleerd. In het volgende voorbeeld wordt `kubectl` lokaal geïnstalleerd met behulp van de [opdracht az aks install-cli](/cli/azure/aks#az-aks-install-cli) . 

 ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
```

`kubectl` Configureer vervolgens om verbinding te maken met uw Kubernetes-cluster met behulp van de [opdracht az aks get-credentials](/cli/azure/aks#az-aks-get-credentials). Bij deze opdracht worden referenties gedownload en wordt Kubernetes CLI geconfigureerd voor het gebruik van deze referenties. De opdracht maakt gebruik `~/.kube/config`van de standaardlocatie voor het [Kubernetes-configuratiebestand](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/). U kunt een andere locatie opgeven voor uw Kubernetes-configuratiebestand met behulp van het **argument --file** .

> [!WARNING]
> Met deze opdracht worden alle bestaande referenties met dezelfde vermelding overschreven.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
```

Als u de verbinding met uw cluster wilt controleren, gebruikt u de opdracht [kubectl get]( https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get) om een lijst met clusterknooppunten te retourneren.

```bash
kubectl get nodes
```

## NGINX-ingangscontroller installeren

U kunt uw ingangscontroller configureren met een statisch openbaar IP-adres. Het statische openbare IP-adres blijft behouden als u de ingangscontroller verwijdert. Het IP-adres blijft niet behouden als u uw AKS-cluster verwijdert.
Wanneer u uw ingangscontroller bijwerken, moet u een parameter doorgeven aan de Helm-release om ervoor te zorgen dat de controllerservice voor inkomend verkeer op de hoogte wordt gesteld van de load balancer die eraan wordt toegewezen. Gebruik een DNS-label om een FQDN (Fully Qualified Domain Name) te configureren voor het IP-adres van de ingangscontroller om de HTTPS-certificaten correct te laten werken. Uw FQDN moet dit formulier volgen: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Vervolgens voegt u de ingress-nginx Helm-opslagplaats toe, werkt u de cache van de lokale Helm-grafiekopslagplaats bij en installeert u de ingress-nginx-invoegtoepassing via Helm. U kunt het DNS-label instellen met de **aantekeningen --set controller.service.annotaties. service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>"** parameter ofwel wanneer u de ingangscontroller voor het eerst implementeert of hoger. In dit voorbeeld geeft u uw eigen openbare IP-adres op dat u in de vorige stap hebt gemaakt met de **parameter** --set controller.service.loadBalancerIP="<STATIC_IP>".

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

## HTTPS-beëindiging toevoegen aan aangepast domein

Op dit moment in de zelfstudie hebt u een AKS-web-app met NGINX als ingangscontroller en een aangepast domein dat u kunt gebruiken voor toegang tot uw toepassing. De volgende stap is het toevoegen van een SSL-certificaat aan het domein, zodat gebruikers uw toepassing veilig kunnen bereiken via https.

### Certificaatbeheer instellen

We gaan Cert Manager gebruiken om HTTPS toe te voegen. Cert Manager is een opensource-hulpprogramma voor het verkrijgen en beheren van SSL-certificaten voor Kubernetes-implementaties. Cert Manager verkrijgt certificaten van populaire openbare verleners en particuliere verleners, zorgt ervoor dat de certificaten geldig en up-to-date zijn en probeert certificaten te vernieuwen op een geconfigureerd tijdstip voordat ze verlopen.

1. Als u cert-manager wilt installeren, moet u eerst een naamruimte maken om deze in uit te voeren. In deze zelfstudie wordt cert-manager geïnstalleerd in de naamruimte cert-manager. U kunt certificaatbeheer uitvoeren in een andere naamruimte, maar u moet wijzigingen aanbrengen in de implementatiemanifesten.

    ```bash
    kubectl create namespace cert-manager
    ```

2. We kunnen nu certificaatbeheer installeren. Alle resources zijn opgenomen in één YAML-manifestbestand. Installeer het manifestbestand met de volgende opdracht:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Voeg het `certmanager.k8s.io/disable-validation: "true"` label toe aan de naamruimte cert-manager door het volgende uit te voeren. Hierdoor kunnen de systeembronnen die certificaatbeheer vereist, TLS opstarten om te worden gemaakt in een eigen naamruimte.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Certificaat verkrijgen via Helm-grafieken

Helm is een Kubernetes-implementatieprogramma voor het automatiseren van het maken, verpakken, configureren en implementeren van toepassingen en services in Kubernetes-clusters.

Cert-manager biedt Helm-grafieken als een eersteklas installatiemethode op Kubernetes.

1. Voeg de Jetstack Helm-opslagplaats toe. Deze opslagplaats is de enige ondersteunde bron van cert-manager-grafieken. Er zijn andere spiegels en kopieën via internet, maar die zijn niet officieel en kunnen een beveiligingsrisico opleveren.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Cache van lokale Helm-grafiekopslagplaats bijwerken.

    ```bash
    helm repo update
    ```

3. Installeer de Cert-Manager-invoegtoepassing via Helm.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Pas het YAML-bestand van de certificaatverlener toe. ClusterIssuers zijn Kubernetes-resources die certificeringsinstanties (CA's) vertegenwoordigen die ondertekende certificaten kunnen genereren door aanvragen voor certificaatondertekening te respecteren. Voor alle certificaten van certificaatbeheer is een verlener vereist waarnaar wordt verwezen, die in een kant-en-klare voorwaarde staat om te proberen de aanvraag te respecteren. U kunt de verlener vinden die we in de `cluster-issuer-prod.yml file`.

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Een aangepaste opslagklasse maken

De standaardopslagklassen zijn geschikt voor de meest voorkomende scenario's, maar niet allemaal. In sommige gevallen wilt u mogelijk uw eigen opslagklasse aanpassen met uw eigen parameters. Gebruik bijvoorbeeld het volgende manifest om de **mountOptions** van de bestandsshare te configureren.
De standaardwaarde voor **fileMode** en **dirMode** is **0755** voor gekoppelde Kubernetes-bestandsshares. U kunt de verschillende koppelingsopties voor het opslagklasseobject opgeven.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## WordPress implementeren op AKS-cluster

Voor deze zelfstudie gebruiken we een bestaande Helm-grafiek voor WordPress die is gebouwd door Bitnami. De Bitnami Helm-grafiek maakt gebruik van een lokale MariaDB als de database. Daarom moeten we deze waarden overschrijven om de app te gebruiken met Azure Database for MySQL. U kunt de waarden en de aangepaste instellingen van het `helm-wp-aks-values.yaml` bestand overschrijven.

1. Voeg de Wordpress Bitnami Helm-opslagplaats toe.

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Cache van lokale Helm-grafiekopslagplaats bijwerken.

    ```bash
    helm repo update
    ```

3. Installeer de Wordpress-workload via Helm.

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
> Het duurt vaak 2-3 minuten voordat het SSL-certificaat is doorgegeven en ongeveer 5 minuten dat alle WordPress POD-replica's gereed zijn en de site volledig bereikbaar is via https.

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

Controleer of WordPress-inhoud correct wordt geleverd met behulp van de volgende opdracht:

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

Ga naar de website via de volgende URL:

```bash
echo "You can now visit your web server at https://$FQDN"
```

## De resources opschonen (optioneel)

Om Azure-kosten te vermijden, moet u overbodige resources opschonen. Wanneer u het cluster niet meer nodig hebt, gebruikt u de [opdracht az group delete](/cli/azure/group#az-group-delete) om de resourcegroep, containerservice en alle gerelateerde resources te verwijderen. 

> [!NOTE]
> Wanneer u het cluster verwijdert, wordt de Microsoft Entra-service-principal die door het AKS-cluster wordt gebruikt, niet verwijderd. Zie [Overwegingen voor en verwijdering van AKS service-principal](../../aks/kubernetes-service-principal.md#other-considerations) voor stappen voor het verwijderen van de service-principal. Als u een beheerde identiteit hebt gebruikt, wordt de identiteit beheerd door het platform en hoeft deze niet te worden verwijderd.

## Volgende stappen

- Leer hoe u [toegang krijgt tot het Kubernetes-dashboard](../../aks/kubernetes-dashboard.md) voor uw AKS-cluster
- Leer hoe u uw [cluster kunt schalen](../../aks/tutorial-kubernetes-scale.md)
- Meer informatie over het beheren van uw [flexibele Azure Database for MySQL-serverexemplaren](./quickstart-create-server-cli.md)
- Meer informatie over het [configureren van serverparameters](./how-to-configure-server-parameters-cli.md) voor uw databaseserver
