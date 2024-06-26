---
title: Een schaalbaar en beveiligd Azure Kubernetes Service-cluster implementeren met behulp van de Azure CLI
description: In deze zelfstudie wordt u stapsgewijs begeleid bij het maken van een Azure Kubernetes-webtoepassing die is beveiligd via https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Quickstart: Een schaalbaar en beveiligd Azure Kubernetes Service-cluster implementeren met behulp van de Azure CLI

[![Implementeren naar Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Welkom bij deze zelfstudie waarin we u stapsgewijs zullen volgen bij het maken van een Azure Kubernetes-webtoepassing die is beveiligd via https. In deze zelfstudie wordt ervan uitgegaan dat u al bent aangemeld bij Azure CLI en een abonnement hebt geselecteerd voor gebruik met de CLI. Er wordt ook van uitgegaan dat Helm is geïnstalleerd ([hier vindt](https://helm.sh/docs/intro/install/) u instructies).

## Omgevingsvariabelen definiëren

De eerste stap in deze zelfstudie is het definiëren van omgevingsvariabelen.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export NETWORK_PREFIX="$(($RANDOM % 254 + 1))"
export SSL_EMAIL_ADDRESS="$(az account show --query user.name --output tsv)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="westeurope"
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
export MY_PUBLIC_IP_NAME="myPublicIP$RANDOM_ID"
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_VNET_NAME="myVNet$RANDOM_ID"
export MY_VNET_PREFIX="10.$NETWORK_PREFIX.0.0/16"
export MY_SN_NAME="mySN$RANDOM_ID"
export MY_SN_PREFIX="10.$NETWORK_PREFIX.0.0/22"
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
```

## Een brongroep maken

Een resourcegroep is een container voor gerelateerde resources. Alle resources moeten in een resourcegroep worden geplaatst. We maken er een voor deze zelfstudie. Met de volgende opdracht maakt u een resourcegroep met de eerder gedefinieerde parameters $MY_RESOURCE_GROUP_NAME en $REGION parameters.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultaten:

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

## Registreren bij AKS Azure-resourceproviders

Controleer of microsoft.OperationsManagement- en Microsoft.OperationalInsights-providers zijn geregistreerd in uw abonnement. Dit zijn Azure-resourceproviders die ondersteuning bieden voor [Container Insights](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Voer de volgende opdrachten uit om de registratiestatus te controleren

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## AKS-cluster maken

Maak een AKS-cluster met behulp van de opdracht az aks create met de bewakingsparameter --enable-addons om Container Insights in te schakelen. In het volgende voorbeeld wordt een cluster met automatische schaalaanpassing, beschikbaarheidszone ingeschakeld.

Dit kan enkele minuten duren.

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

## De toepassing implementeren

Een Kubernetes-manifestbestand definieert de gewenste status van een cluster, zoals welke containerinstallatiekopieën moeten worden uitgevoerd.

In deze quickstart gebruikt u een manifest om alle objecten te maken die nodig zijn om de Azure Vote-toepassing uit te voeren. Dit manifest bevat twee Kubernetes-implementaties:

- De Azure Vote Python-voorbeeldtoepassingen.
- Een Redis-exemplaar.

Er worden ook twee Kubernetes-services gemaakt:

- Een interne service voor het Redis-exemplaar.
- Een externe service voor toegang tot de Azure Vote-toepassing vanaf internet.

Ten slotte wordt er een toegangsbeheerresource gemaakt om verkeer naar de Azure Vote-toepassing te routeren.

Er is al een YML-bestand voorbereid op een test stem-app. 

```bash
cat << EOF > azure-vote-start.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: azure-vote-back
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: azure-vote-back
  template:
    metadata:
      labels:
        app: azure-vote-back
    spec:
      nodeSelector:
        "kubernetes.io/os": linux
      containers:
      - name: azure-vote-back
        image: docker.io/bitnami/redis:6.0.8
        env:
        - name: ALLOW_EMPTY_PASSWORD
          value: "yes"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 250m
            memory: 256Mi
        ports:
        - containerPort: 6379
          name: redis
---
apiVersion: v1
kind: Service
metadata:
  name: azure-vote-back
  namespace: default
spec:
  ports:
  - port: 6379
  selector:
    app: azure-vote-back
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: azure-vote-front
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: azure-vote-front
  template:
    metadata:
      labels:
        app: azure-vote-front
    spec:
      nodeSelector:
        "kubernetes.io/os": linux
      containers:
      - name: azure-vote-front
        image: mcr.microsoft.com/azuredocs/azure-vote-front:v1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 250m
            memory: 256Mi
        ports:
        - containerPort: 80
        env:
        - name: REDIS
          value: "azure-vote-back"
---
apiVersion: v1
kind: Service
metadata:
  name: azure-vote-front
  namespace: default
spec:
  ports:
  - port: 80
  selector:
    app: azure-vote-front
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vote-ingress
  namespace: default
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: azure-vote-front
            port:
              number: 80
EOF
```

Voer de volgende opdracht uit om deze app te implementeren

```bash
kubectl apply -f azure-vote-start.yml
```

## De toepassing testen

Controleer of de toepassing wordt uitgevoerd door naar het openbare IP-adres of de toepassings-URL te gaan. U kunt de toepassings-URL vinden door de volgende opdracht uit te voeren:

> [!Note]
> Het duurt vaak 2-3 minuten voordat de POD's zijn gemaakt en de site bereikbaar is via HTTP

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

Resultaten:

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

## HTTPS-beëindiging toevoegen aan aangepast domein

Op dit moment in de zelfstudie hebt u een AKS-web-app met NGINX als de ingangscontroller en een aangepast domein dat u kunt gebruiken voor toegang tot uw toepassing. De volgende stap is het toevoegen van een SSL-certificaat aan het domein, zodat gebruikers uw toepassing veilig kunnen bereiken via HTTPS.

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
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. YAML-bestand van certificaatverlener toepassen

   ClusterIssuers zijn Kubernetes-resources die certificeringsinstanties (CA's) vertegenwoordigen die ondertekende certificaten kunnen genereren door aanvragen voor certificaatondertekening te respecteren. Voor alle certificaten van certificaatbeheer is een verlener vereist waarnaar wordt verwezen, die in een kant-en-klare voorwaarde staat om te proberen de aanvraag te respecteren.
   De uitgever die we gebruiken, vindt u in de `cluster-issuer-prod.yml file`
        
    ```bash
    cat <<EOF > cluster-issuer-prod.yml
    apiVersion: cert-manager.io/v1
    kind: ClusterIssuer
    metadata:
      name: letsencrypt-prod
    spec:
      acme:
        # You must replace this email address with your own.
        # Let's Encrypt will use this to contact you about expiring
        # certificates, and issues related to your account.
        email: $SSL_EMAIL_ADDRESS
        # ACME server URL for Let’s Encrypt’s prod environment.
        # The staging environment will not issue trusted certificates but is
        # used to ensure that the verification process is working properly
        # before moving to production
        server: https://acme-v02.api.letsencrypt.org/directory
        # Secret resource used to store the account's private key.
        privateKeySecretRef:
          name: letsencrypt
        # Enable the HTTP-01 challenge provider
        # you prove ownership of a domain by ensuring that a particular
        # file is present at the domain
        solvers:
        - http01:
            ingress:
              class: nginx
            podTemplate:
              spec:
                nodeSelector:
                  "kubernetes.io/os": linux
    EOF
    ```

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yml)
    ```

5. Upate Voting App Application to use Cert-Manager to obtain an SSL Certificate.

   Het volledige YAML-bestand vindt u in `azure-vote-nginx-ssl.yml`

```bash
cat << EOF > azure-vote-nginx-ssl.yml
---
# INGRESS WITH SSL PROD
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vote-ingress
  namespace: default
  annotations:
    kubernetes.io/tls-acme: "true"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - $FQDN
    secretName: azure-vote-nginx-secret
  rules:
    - host: $FQDN
      http:
        paths:
        - path: /
          pathType: Prefix
          backend:
            service:
              name: azure-vote-front
              port:
                number: 80
EOF
```

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

## Bladeren door uw AKS-implementatie die is beveiligd via HTTPS

Voer de volgende opdracht uit om het HTTPS-eindpunt voor uw toepassing op te halen:

> [!Note]
> Het duurt vaak 2-3 minuten voordat het SSL-certificaat is gepropogate en de site bereikbaar is via HTTPS.

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

## Volgende stappen

- [Documentatie voor Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Een Azure Container Registry maken](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Uw applciatie schalen in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Uw toepassing bijwerken in AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)