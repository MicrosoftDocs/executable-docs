---
title: Distribuera ett skalbart och säkert Azure Kubernetes Service-kluster med hjälp av Azure CLI
description: Den här självstudien tar dig steg för steg när du skapar ett Azure Kubernetes-webbprogram som skyddas via https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Snabbstart: Distribuera ett skalbart och säkert Azure Kubernetes Service-kluster med hjälp av Azure CLI

[![Distribuera till Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Välkommen till den här självstudien där vi tar dig steg för steg när du skapar ett Azure Kubernetes-webbprogram som skyddas via https. Den här självstudien förutsätter att du redan är inloggad i Azure CLI och har valt en prenumeration som ska användas med CLI. Det förutsätter också att du har Helm installerat ([instruktioner finns här](https://helm.sh/docs/intro/install/)).

## Definiera miljövariabler

Det första steget i den här självstudien är att definiera miljövariabler.

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

## Skapa en resursgrupp

En resursgrupp är en container för relaterade resurser. Alla resurser måste placeras i en resursgrupp. Vi skapar en för den här självstudien. Följande kommando skapar en resursgrupp med de tidigare definierade parametrarna $MY_RESOURCE_GROUP_NAME och $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultat:

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

## Registrera dig för AKS Azure-resursprovidrar

Kontrollera att Microsoft.OperationsManagement- och Microsoft.OperationalInsights-leverantörer är registrerade i din prenumeration. Det här är Azure-resursprovidrar som krävs för att stödja [Container Insights](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Kontrollera registreringsstatusen genom att köra följande kommandon

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Skapa AKS-kluster

Skapa ett AKS-kluster med kommandot az aks create med övervakningsparametern --enable-addons för att aktivera containerinsikter. I följande exempel skapas ett kluster med automatisk skalning, tillgänglighetszonaktiverat.

Det tar bara några minuter.

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

## Distribuera programmet

En Kubernetes-manifestfil definierar ett klusters önskade tillstånd, till exempel vilka containeravbildningar som ska köras.

I den här snabbstarten använder du ett manifest för att skapa alla objekt som behövs för att köra Azure Vote-programmet. Det här manifestet innehåller två Kubernetes-distributioner:

- Azure Vote Python-exempelprogram.
- En Redis-instans.

Två Kubernetes-tjänster skapas också:

- En intern tjänst för Redis-instansen.
- En extern tjänst för åtkomst till Azure Vote-programmet från Internet.

Slutligen skapas en ingressresurs för att dirigera trafik till Azure Vote-programmet.

En YML-fil för teströstningsappen har redan förberetts. 

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

Om du vill distribuera den här appen kör du följande kommando

```bash
kubectl apply -f azure-vote-start.yml
```

## Testa programmet

Kontrollera att programmet körs genom att antingen besöka den offentliga ip-adressen eller program-URL:en. Du hittar program-URL:en genom att köra följande kommando:

> [!Note]
> Det tar ofta 2-3 minuter för POD:erna att skapas och webbplatsen kan nås via HTTP

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

Resultat:

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

## Lägga till HTTPS-avslutning till anpassad domän

Nu i självstudien har du en AKS-webbapp med NGINX som ingresskontrollant och en anpassad domän som du kan använda för att komma åt ditt program. Nästa steg är att lägga till ett SSL-certifikat i domänen så att användarna kan nå ditt program på ett säkert sätt via HTTPS.

## Konfigurera Cert Manager

För att lägga till HTTPS använder vi Cert Manager. Cert Manager är ett verktyg med öppen källkod som används för att hämta och hantera SSL-certifikat för Kubernetes-distributioner. Cert Manager hämtar certifikat från en mängd olika utfärdare, både populära offentliga utfärdare och privata utfärdare, och ser till att certifikaten är giltiga och uppdaterade och försöker förnya certifikat vid en konfigurerad tidpunkt innan de upphör att gälla.

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

3. Installera Cert-Manager-tillägget via helm genom att köra följande:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Tillämpa YAML-fil för certifikatutfärdare

   ClusterIssuers är Kubernetes-resurser som representerar certifikatutfärdare som kan generera signerade certifikat genom att uppfylla begäranden om certifikatsignering. Alla cert-manager-certifikat kräver en refererad utfärdare som är i ett redo villkor för att försöka uppfylla begäran.
   Den utfärdare som vi använder finns i `cluster-issuer-prod.yml file`
        
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

5. Upate Voting App Application för att använda Cert-Manager för att hämta ett SSL-certifikat.

   Den fullständiga YAML-filen finns i `azure-vote-nginx-ssl.yml`

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

## Bläddra i din AKS-distribution som skyddas via HTTPS

Kör följande kommando för att hämta HTTPS-slutpunkten för ditt program:

> [!Note]
> Det tar ofta 2–3 minuter för SSL-certifikatet att propogate och platsen kan nås via HTTPS.

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

## Nästa steg

- [Dokumentation om Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Skapa ett Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Skala din applciation i AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Uppdatera ditt program i AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)