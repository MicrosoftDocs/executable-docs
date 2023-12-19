---
title: Distribuera en skalbar och säker WordPress-instans på AKS
description: Den här självstudien visar hur du distribuerar en skalbar och säker WordPress-instans på AKS via CLI
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# Snabbstart: Distribuera en skalbar och säker WordPress-instans på AKS

Välkommen till den här självstudien där vi tar dig steg för steg när du skapar ett Azure Kubernetes-webbprogram som skyddas via https. Den här självstudien förutsätter att du redan är inloggad i Azure CLI och har valt en prenumeration som ska användas med CLI. Det förutsätter också att du har Helm installerat ([instruktioner finns här](https://helm.sh/docs/intro/install/)).

## Definiera miljövariabler

Det första steget i den här självstudien är att definiera miljövariabler.

```bash
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export NETWORK_PREFIX="$(($RANDOM % 253 + 1))"
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myWordPressAKSResourceGroup$RANDOM_ID"
export REGION="eastus"
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

## Skapa en resursgrupp

En resursgrupp är en container för relaterade resurser. Alla resurser måste placeras i en resursgrupp. Vi skapar en för den här självstudien. Följande kommando skapar en resursgrupp med de tidigare definierade parametrarna $MY_RESOURCE_GROUP_NAME och $REGION.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

Resultat:

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

## Skapa ett virtuellt nätverk och ett undernät

Ett virtuellt nätverk är den grundläggande byggstenen för privata nätverk i Azure. Med Azure Virtual Network kan Azure-resurser som virtuella datorer kommunicera säkert med varandra och Internet.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Resultat:

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

## Skapa en Azure Database for MySQL – flexibel server

Azure Database for MySQL – Flexibel server är en hanterad tjänst som du kan använda för att köra, hantera och skala MySQL-servrar med hög tillgänglighet i molnet. Skapa en flexibel server med [kommandot az mysql flexible-server create](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) . En server kan innehålla flera databaser. Följande kommando skapar en server med tjänstens standardvärden och variabelvärden från azure CLI:s lokala miljö:

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

Resultat:

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

Servern som skapades har följande attribut:

- Servernamnet, administratörsanvändarnamnet, administratörslösenordet, resursgruppens namn, platsen har redan angetts i den lokala kontextmiljön för cloud shell och skapas på samma plats som du är resursgruppen och de andra Azure-komponenterna.
- Tjänstens standardvärden för återstående serverkonfigurationer: beräkningsnivå (burstable), beräkningsstorlek/SKU (Standard_B2s), kvarhållningsperiod för säkerhetskopiering (7 dagar) och MySQL-version (8.0.21)
- Standardanslutningsmetoden är Privat åtkomst (VNet-integrering) med ett länkat virtuellt nätverk och ett automatiskt genererat undernät.

> [!NOTE]
> Det går inte att ändra anslutningsmetoden när servern har skapats. Om du till exempel valde `Private access (VNet Integration)` under skapande kan du inte ändra till efter att `Public access (allowed IP addresses)` du har skapat. Vi rekommenderar starkt att du skapar en server med privat åtkomst för säker åtkomst till servern med hjälp av VNet-integrering. Läs mer om privat åtkomst i begreppsartikeln[](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet).

Om du vill ändra några standardvärden läser du referensdokumentationen[ för Azure CLI ](https://learn.microsoft.com/cli/azure//mysql/flexible-server)för den fullständiga listan över konfigurerbara CLI-parametrar.

## Kontrollera Status för Azure Database for MySQL – flexibel server

Det tar några minuter att skapa Azure Database for MySQL – flexibel server och stödresurser.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Konfigurera serverparametrar i Azure Database for MySQL – flexibel server

Du kan hantera Azure Database for MySQL – flexibel serverkonfiguration med hjälp av serverparametrar. Serverparametrarna konfigureras med standardvärdet och det rekommenderade värdet när du skapar servern.

Visa serverparameterinformation Om du vill visa information om en viss parameter för en server kör [du kommandot az mysql flexible-server parameter show](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter) .

### Inaktivera Azure Database for MySQL – SSL-anslutningsparameter för flexibel server för WordPress-integrering

Du kan också ändra värdet för vissa serverparametrar, vilket uppdaterar de underliggande konfigurationsvärdena för MySQL-servermotorn. Om du vill uppdatera serverparametern använder du [kommandot az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) .

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

Resultat:

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

## Skapa AKS-kluster

Skapa ett AKS-kluster med kommandot az aks create med övervakningsparametern --enable-addons för att aktivera containerinsikter. I följande exempel skapas ett automatiskt skalnings- och tillgänglighetszonaktiverat kluster med namnet myAKSCluster:

Det tar några minuter

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

## Anslut till klustret

Om du vill hantera ett Kubernetes-kluster använder du Kubernetes-kommandoradsklienten kubectl. kubectl är redan installerat om du använder Azure Cloud Shell.

1. Installera az aks CLI lokalt med kommandot az aks install-cli

    ```bash
    if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
    ```

2. Konfigurera kubectl för att ansluta till ditt Kubernetes-kluster med kommandot az aks get-credentials. Följande kommando:

    - Laddar ned autentiseringsuppgifter och konfigurerar Kubernetes CLI för att använda dem.
    - Använder ~/.kube/config, standardplatsen för Kubernetes-konfigurationsfilen. Ange en annan plats för kubernetes-konfigurationsfilen med argumentet --file.

    > [!WARNING]
    > Detta skriver över alla befintliga autentiseringsuppgifter med samma post

    ```bash
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
    ```

3. Kontrollera anslutningen till klustret med kommandot kubectl get. Det här kommandot returnerar en lista över klusternoderna.

    ```bash
    kubectl get nodes
    ```

## Installera NGINX-ingresskontrollant

Du kan konfigurera ingresskontrollanten med en statisk offentlig IP-adress. Den statiska offentliga IP-adressen finns kvar om du tar bort ingresskontrollanten. IP-adressen finns inte kvar om du tar bort AKS-klustret.
När du uppgraderar ingresskontrollanten måste du skicka en parameter till Helm-versionen för att säkerställa att ingresskontrollanttjänsten blir medveten om lastbalanseraren som ska allokeras till den. För att HTTPS-certifikaten ska fungera korrekt använder du en DNS-etikett för att konfigurera ett FQDN för ingresskontrollantens IP-adress.
Ditt FQDN bör följa det här formuläret: $MY_DNS_LABEL. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

Lägg till --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" parameter. DNS-etiketten kan anges antingen när ingresskontrollanten först distribueras eller så kan den konfigureras senare. Lägg till parametern --set controller.service.loadBalancerIP="<STATIC_IP>". Ange din egen offentliga IP-adress som skapades i föregående steg.

1. Lägg till Helm-lagringsplatsen ingress-nginx

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. Uppdatera den lokala Helm Chart-lagringsplatsens cache

    ```bash
    helm repo update
    ```

3. Installera ingress-nginx-tillägg via Helm genom att köra följande:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## Lägga till HTTPS-avslutning till anpassad domän

Nu i självstudien har du en AKS-webbapp med NGINX som ingresskontrollant och en anpassad domän som du kan använda för att komma åt ditt program. Nästa steg är att lägga till ett SSL-certifikat i domänen så att användarna kan nå ditt program på ett säkert sätt via https.

## Konfigurera Cert Manager

För att lägga till HTTPS använder vi Cert Manager. Cert Manager är ett öppen källkod verktyg som används för att hämta och hantera SSL-certifikat för Kubernetes-distributioner. Cert Manager hämtar certifikat från en mängd olika utfärdare, både populära offentliga utfärdare och privata utfärdare, och ser till att certifikaten är giltiga och uppdaterade och försöker förnya certifikat vid en konfigurerad tidpunkt innan de upphör att gälla.

1. För att kunna installera cert-manager måste vi först skapa ett namnområde för att köra det i. I den här självstudien installeras cert-manager i namnområdet cert-manager. Det går att köra cert-manager i ett annat namnområde, men du måste göra ändringar i distributionsmanifesten.

    ```bash
    kubectl create namespace cert-manager
    ```

2. Nu kan vi installera cert-manager. Alla resurser ingår i en enda YAML-manifestfil. Detta kan installeras genom att köra följande:

    ```bash
    kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
    ```

3. Lägg till etiketten certmanager.k8s.io/disable-validation: "true" i certifikathanterarens namnområde genom att köra följande. På så sätt kan systemresurserna som cert-manager kräver för att bootstrap TLS skapas i ett eget namnområde.

    ```bash
    kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
    ```

## Hämta certifikat via Helm-diagram

Helm är ett Kubernetes-distributionsverktyg för att automatisera skapande, paketering, konfiguration och distribution av program och tjänster till Kubernetes-kluster.

Cert-manager tillhandahåller Helm-diagram som en förstklassig installationsmetod på Kubernetes.

1. Lägg till Jetstack Helm-lagringsplatsen

    Den här lagringsplatsen är den enda källan till cert-manager-diagram som stöds. Det finns några andra speglar och kopior över internet, men de är helt inofficiella och kan utgöra en säkerhetsrisk.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. Uppdatera den lokala Helm Chart-lagringsplatsens cache

    ```bash
    helm repo update
    ```

3. Installera Cert-Manager-tillägget via Helm genom att köra följande:

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. Tillämpa YAML-fil för certifikatutfärdare

    ClusterIssuers är Kubernetes-resurser som representerar certifikatutfärdare som kan generera signerade certifikat genom att uppfylla begäranden om certifikatsignering. Alla cert-manager-certifikat kräver en refererad utfärdare som är i ett redo villkor för att försöka uppfylla begäran.
    Den utfärdare som vi använder finns i `cluster-issuer-prod.yml file`

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## Skapa en anpassad lagringsklass

Standardlagringsklasserna passar de vanligaste scenarierna, men inte alla. I vissa fall kanske du vill att din egen lagringsklass ska anpassas med dina egna parametrar. Använd till exempel följande manifest för att konfigurera mountOptions för filresursen.
Standardvärdet för fileMode och dirMode är 0755 för Kubernetes-monterade filresurser. Du kan ange de olika monteringsalternativen för lagringsklassobjektet.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## Distribuera WordPress till AKS-kluster

För det här dokumentet använder vi ett befintligt Helm-diagram för WordPress som skapats av Bitnami. Bitnami Helm-diagrammet använder till exempel lokal MariaDB som databas och vi måste åsidosätta dessa värden för att använda appen med Azure Database for MySQL. Alla åsidosättningsvärden Du kan åsidosätta värdena och de anpassade inställningarna finns i filen `helm-wp-aks-values.yaml`

1. Lägg till Wordpress Bitnami Helm-lagringsplatsen

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. Uppdatera den lokala Helm Chart-lagringsplatsens cache

    ```bash
    helm repo update
    ```

3. Installera Wordpress-arbetsbelastningen via Helm genom att köra följande:

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

Resultat:

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

## Bläddra i din AKS-distribution som skyddas via HTTPS

Kör följande kommando för att hämta HTTPS-slutpunkten för ditt program:

> [!NOTE]
> Det tar ofta 2-3 minuter för SSL-certifikatet att propogate och cirka 5 minuter att ha alla WordPress POD-repliker redo och webbplatsen att vara fullt nåbar via https.

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

Kontrollera att WordPress-innehåll levereras korrekt.

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

Resultat:

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

Webbplatsen kan besökas genom att följa URL:en nedan:

```bash
echo "You can now visit your web server at https://$FQDN"
```
