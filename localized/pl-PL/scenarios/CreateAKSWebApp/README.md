---
title: Wdrażanie skalowalnego i bezpiecznego klastra usługi Azure Kubernetes Service przy użyciu interfejsu wiersza polecenia platformy Azure
description: 'Ten samouczek, w którym wykonamy krok po kroku tworzenie aplikacji internetowej platformy Azure Kubernetes zabezpieczonej za pośrednictwem protokołu https.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Szybki start: wdrażanie skalowalnego i bezpiecznego klastra usługi Azure Kubernetes Service przy użyciu interfejsu wiersza polecenia platformy Azure

[![Wdróż na platformie Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2286416)

Witamy w tym samouczku, w którym wykonamy krok po kroku tworzenie aplikacji internetowej platformy Azure Kubernetes zabezpieczonej za pośrednictwem protokołu HTTPS. W tym samouczku założono, że zalogowano się już do interfejsu wiersza polecenia platformy Azure i wybrano subskrypcję do użycia z interfejsem wiersza polecenia. Przyjęto również założenie, że masz zainstalowane narzędzie Helm ([instrukcje można znaleźć tutaj](https://helm.sh/docs/intro/install/)).

## Definiowanie zmiennych środowiskowych

Pierwszym krokiem w tym samouczku jest zdefiniowanie zmiennych środowiskowych.

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

## Tworzenie grupy zasobów

Grupa zasobów to kontener powiązanych zasobów. Wszystkie zasoby należy umieścić w grupie zasobów. Utworzymy go na potrzeby tego samouczka. Następujące polecenie tworzy grupę zasobów z wcześniej zdefiniowanymi parametrami $MY_RESOURCE_GROUP_NAME i $REGION.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Wyniki:

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

## Tworzenie sieci wirtualnej i podsieci

Sieć wirtualna to podstawowy blok konstrukcyjny dla sieci prywatnych na platformie Azure. Usługa Azure Virtual Network umożliwia zasobom platformy Azure, takich jak maszyny wirtualne, bezpieczne komunikowanie się ze sobą i Internetem.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Wyniki:

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

## Rejestrowanie się u dostawców zasobów platformy Azure w usłudze AKS

Sprawdź, czy dostawcy Microsoft.OperationsManagement i Microsoft.OperationalInsights są zarejestrowani w twojej subskrypcji. Są to dostawcy zasobów platformy Azure, którzy muszą obsługiwać szczegółowe [informacje](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview) o kontenerze. Aby sprawdzić stan rejestracji, uruchom następujące polecenia

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Tworzenie klastra usługi AKS

Utwórz klaster usługi AKS przy użyciu polecenia az aks create z parametrem monitorowania --enable-addons, aby włączyć szczegółowe informacje o kontenerze. W poniższym przykładzie tworzony jest klaster z włączoną skalowaniem automatycznym i strefą dostępności.

Operacja potrwa kilka minut.

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

## Łączenie z klastrem

Aby zarządzać klastrem Kubernetes, użyj klienta wiersza polecenia kubernetes kubectl. Narzędzie kubectl jest już zainstalowane, jeśli używasz usługi Azure Cloud Shell.

1. Zainstaluj interfejs wiersza polecenia az aks lokalnie przy użyciu polecenia az aks install-cli

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Skonfiguruj narzędzie kubectl, aby nawiązać połączenie z klastrem Kubernetes przy użyciu polecenia az aks get-credentials. Następujące polecenie:

   - Pobiera poświadczenia i konfiguruje interfejs wiersza polecenia platformy Kubernetes do ich używania.
   - Używa polecenia ~/.kube/config, domyślnej lokalizacji pliku konfiguracji kubernetes. Określ inną lokalizację pliku konfiguracji platformy Kubernetes przy użyciu argumentu --file.

   > [!WARNING]
   > Spowoduje to zastąpienie wszystkich istniejących poświadczeń przy użyciu tego samego wpisu

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Sprawdź połączenie z klastrem przy użyciu polecenia kubectl get. To polecenie zwraca listę węzłów klastra.

   ```bash
   kubectl get nodes
   ```

## Instalowanie kontrolera ruchu przychodzącego NGINX

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

## Wdrażanie aplikacji

Plik manifestu kubernetes definiuje żądany stan klastra, taki jak obrazy kontenerów do uruchomienia.

W tym przewodniku Szybki start utworzysz wszystkie obiekty potrzebne do uruchomienia aplikacji Azure Vote za pomocą manifestu. Ten manifest obejmuje dwa wdrożenia platformy Kubernetes:

- Przykładowe aplikacje azure Vote Python.
- Wystąpienie usługi Redis.

Tworzone są również dwie usługi Kubernetes:

- Wewnętrzna usługa dla wystąpienia usługi Redis.
- Usługa zewnętrzna w celu uzyskania dostępu do aplikacji Azure Vote z Internetu.

Na koniec zostanie utworzony zasób ruchu przychodzącego w celu kierowania ruchu do aplikacji Azure Vote.

Plik YML aplikacji do głosowania testowego jest już przygotowany. 

```bash
cat << EOF > azure-vote-start.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rabbitmq
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      nodeSelector:
        "kubernetes.io/os": linux
      containers:
      - name: rabbitmq
        image: mcr.microsoft.com/mirror/docker/library/rabbitmq:3.10-management-alpine
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
        volumeMounts:
        - name: rabbitmq-enabled-plugins
          mountPath: /etc/rabbitmq/enabled_plugins
          subPath: enabled_plugins
      volumes:
      - name: rabbitmq-enabled-plugins
        configMap:
          name: rabbitmq-enabled-plugins
          items:
          - key: rabbitmq_enabled_plugins
            path: enabled_plugins
---
apiVersion: v1
data:
  rabbitmq_enabled_plugins: |
    [rabbitmq_management,rabbitmq_prometheus,rabbitmq_amqp1_0].
kind: ConfigMap
metadata:
  name: rabbitmq-enabled-plugins
---
apiVersion: v1
kind: Service
metadata:
  name: rabbitmq
spec:
  selector:
    app: rabbitmq
  ports:
    - name: rabbitmq-amqp
      port: 5672
      targetPort: 5672
    - name: rabbitmq-http
      port: 15672
      targetPort: 15672
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      nodeSelector:
        "kubernetes.io/os": linux
      containers:
      - name: order-service
        image: ghcr.io/azure-samples/aks-store-demo/order-service:latest
        ports:
        - containerPort: 3000
        env:
        - name: ORDER_QUEUE_HOSTNAME
          value: "rabbitmq"
        - name: ORDER_QUEUE_PORT
          value: "5672"
        - name: ORDER_QUEUE_USERNAME
          value: "username"
        - name: ORDER_QUEUE_PASSWORD
          value: "password"
        - name: ORDER_QUEUE_NAME
          value: "orders"
        - name: FASTIFY_ADDRESS
          value: "0.0.0.0"
        resources:
          requests:
            cpu: 1m
            memory: 50Mi
          limits:
            cpu: 75m
            memory: 128Mi
      initContainers:
      - name: wait-for-rabbitmq
        image: busybox
        command: ['sh', '-c', 'until nc -zv rabbitmq 5672; do echo waiting for rabbitmq; sleep 2; done;']
        resources:
          requests:
            cpu: 1m
            memory: 50Mi
          limits:
            cpu: 75m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 3000
    targetPort: 3000
  selector:
    app: order-service
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: product-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: product-service
  template:
    metadata:
      labels:
        app: product-service
    spec:
      nodeSelector:
        "kubernetes.io/os": linux
      containers:
      - name: product-service
        image: ghcr.io/azure-samples/aks-store-demo/product-service:latest
        ports:
        - containerPort: 3002
        resources:
          requests:
            cpu: 1m
            memory: 1Mi
          limits:
            cpu: 1m
            memory: 7Mi
---
apiVersion: v1
kind: Service
metadata:
  name: product-service
spec:
  type: ClusterIP
  ports:
  - name: http
    port: 3002
    targetPort: 3002
  selector:
    app: product-service
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: store-front
spec:
  replicas: 1
  selector:
    matchLabels:
      app: store-front
  template:
    metadata:
      labels:
        app: store-front
    spec:
      nodeSelector:
        "kubernetes.io/os": linux
      containers:
      - name: store-front
        image: ghcr.io/azure-samples/aks-store-demo/store-front:latest
        ports:
        - containerPort: 8080
          name: store-front
        env:
        - name: VUE_APP_ORDER_SERVICE_URL
          value: "http://order-service:3000/"
        - name: VUE_APP_PRODUCT_SERVICE_URL
          value: "http://product-service:3002/"
        resources:
          requests:
            cpu: 1m
            memory: 200Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: store-front
spec:
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: store-front
  type: LoadBalancer
EOF
```

Aby wdrożyć tę aplikację, uruchom następujące polecenie

```bash
kubectl apply -f azure-vote-start.yml
```

## Testowanie aplikacji

Sprawdź, czy aplikacja jest uruchomiona, odwiedzając publiczny adres IP lub adres URL aplikacji. Adres URL aplikacji można znaleźć, uruchamiając następujące polecenie:

> [!Note]
> Utworzenie identyfikatorów POD i dotarcie do witryny za pośrednictwem protokołu HTTP trwa często 2–3 minuty

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

Wyniki:

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

## Dodawanie zakończenia protokołu HTTPS do domeny niestandardowej

W tym momencie w samouczku masz aplikację internetową usługi AKS z serwerem NGINX jako kontrolerem ruchu przychodzącego i domeną niestandardową, której można użyć do uzyskiwania dostępu do aplikacji. Następnym krokiem jest dodanie certyfikatu SSL do domeny, aby użytkownicy mogli bezpiecznie uzyskać dostęp do aplikacji za pośrednictwem protokołu HTTPS.

## Konfigurowanie menedżera certyfikatów

Aby dodać protokół HTTPS, użyjemy menedżera certyfikatów. Cert Manager to narzędzie typu open source służące do uzyskiwania certyfikatu SSL dla wdrożeń platformy Kubernetes i zarządzania nim. Menedżer certyfikatów uzyska certyfikaty od różnych wystawców, zarówno popularnych publicznych wystawców, jak i prywatnych wystawców, i zapewni, że certyfikaty są prawidłowe i aktualne, a następnie podejmie próbę odnowienia certyfikatów w skonfigurowanym czasie przed wygaśnięciem.

1. Aby zainstalować program cert-manager, musimy najpierw utworzyć przestrzeń nazw, aby ją uruchomić. W tym samouczku zostanie zainstalowany menedżer certyfikatów w przestrzeni nazw menedżera certyfikatów. Istnieje możliwość uruchomienia menedżera certyfikatów w innej przestrzeni nazw, chociaż konieczne będzie wprowadzenie modyfikacji manifestów wdrożenia.

   ```bash
   kubectl create namespace cert-manager
   ```

2. Teraz możemy zainstalować program cert-manager. Wszystkie zasoby znajdują się w jednym pliku manifestu YAML. Można to zainstalować, uruchamiając następujące polecenie:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Dodaj etykietę certmanager.k8s.io/disable-validation: "true" do przestrzeni nazw menedżera certyfikatów, uruchamiając następujące polecenie. Pozwoli to na utworzenie zasobów systemowych, których narzędzie cert-manager wymaga uruchomienia protokołu TLS we własnej przestrzeni nazw.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Uzyskiwanie certyfikatu za pomocą pakietów Helm

Helm to narzędzie wdrażania platformy Kubernetes służące do automatyzowania tworzenia, tworzenia, tworzenia pakietów, konfiguracji i wdrażania aplikacji i usług w klastrach Kubernetes.

Narzędzie Cert-manager udostępnia wykresy Helm jako pierwszą klasę instalacji na platformie Kubernetes.

1. Dodawanie repozytorium Narzędzia Helm jetstack

   To repozytorium jest jedynym obsługiwanym źródłem wykresów cert-manager. Istnieją inne lustra i kopie w Internecie, ale są one całkowicie nieoficjalne i mogą stanowić zagrożenie bezpieczeństwa.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Aktualizowanie lokalnej pamięci podręcznej repozytorium programu Helm Chart

   ```bash
   helm repo update
   ```

3. Zainstaluj dodatek Cert-Manager za pomocą narzędzia helm, uruchamiając następujące polecenie:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Stosowanie pliku YAML wystawcy certyfikatu

   ClusterIssuers to zasoby kubernetes reprezentujące urzędy certyfikacji, które mogą generować podpisane certyfikaty, honorując żądania podpisywania certyfikatów. Wszystkie certyfikaty menedżera certyfikatów wymagają wystawcy, do którego odwołuje się odwołanie, który jest w stanie gotowości, aby spróbować rozpoznać żądanie.
   Wystawca, z których korzystamy, można znaleźć w `cluster-issuer-prod.yml file`
        
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

5. Upate Voting App to use Cert-Manager to obtain an SSL Certificate .Upate Voting App to use Cert-Manager to obtain an SSL Certificate (Upate Voting App Application to use Cert-Manager to obtain an SSL Certificate).

   Pełny plik YAML można znaleźć w witrynie `azure-vote-nginx-ssl.yml`

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

## Przeglądanie wdrożenia usługi AKS Zabezpieczone za pośrednictwem protokołu HTTPS

Uruchom następujące polecenie, aby uzyskać punkt końcowy HTTPS dla aplikacji:

> [!Note]
> Propogate certyfikatu SSL często trwa od 2 do 3 minut, a lokacja może być osiągalna za pośrednictwem protokołu HTTPS.

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

## Następne kroki

- [Dokumentacja usługi Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Tworzenie usługi Azure Container Registry](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Skalowanie aplikacji w usłudze AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Aktualizowanie aplikacji w usłudze AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)