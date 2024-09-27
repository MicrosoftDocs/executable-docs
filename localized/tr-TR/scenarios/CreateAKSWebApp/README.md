---
title: Azure CLI kullanarak Ölçeklenebilir ve Güvenli Azure Kubernetes Service kümesi dağıtma
description: 'Bu öğreticide, https aracılığıyla güvenliği sağlanan bir Azure Kubernetes Web Uygulaması oluşturma adım adım izlenecektir.'
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Hızlı Başlangıç: Azure CLI kullanarak Ölçeklenebilir ve Güvenli Azure Kubernetes Service kümesi dağıtma

[![Azure’a dağıtın](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2286416)

Https aracılığıyla güvenliği sağlanan bir Azure Kubernetes Web Uygulaması oluşturma adım adım size adım adım izleyebileceğiniz bu öğreticiye hoş geldiniz. Bu öğreticide, Azure CLI'de zaten oturum açtığınız ve CLI ile kullanmak üzere bir abonelik seçtiğiniz varsayılır. Ayrıca Helm'in yüklü olduğu varsayılır ([Yönergeler burada](https://helm.sh/docs/intro/install/) bulunabilir).

## Ortam Değişkenlerini Tanımlama

Bu öğreticinin ilk adımı ortam değişkenlerini tanımlamaktır.

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

## Kaynak grubu oluşturma

Kaynak grubu, ilgili kaynaklar için bir kapsayıcıdır. Tüm kaynaklar bir kaynak grubuna yerleştirilmelidir. Bu öğretici için bir tane oluşturacağız. Aşağıdaki komut, önceden tanımlanmış $MY_RESOURCE_GROUP_NAME ve $REGION parametreleriyle bir kaynak grubu oluşturur.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Sonuçlar:

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

## Sanal ağ ve alt ağ oluşturma

Sanal ağ, Azure'daki özel ağlar için temel yapı taşıdır. Azure Sanal Ağ, VM'ler gibi Azure kaynaklarının birbirleriyle ve İnternet ile güvenli bir şekilde iletişim kurmasını sağlar.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Sonuçlar:

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

## AKS Azure Kaynak Sağlayıcılarına kaydolma

Microsoft.OperationsManagement ve Microsoft.OperationalInsights sağlayıcılarının aboneliğinizde kayıtlı olduğunu doğrulayın. Bunlar, Kapsayıcı içgörülerini desteklemek [için gereken Azure kaynak sağlayıcılarıdır](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview). Kayıt durumunu denetlemek için aşağıdaki komutları çalıştırın

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## AKS Kümesi Oluşturma

Kapsayıcı içgörülerini etkinleştirmek için --enable-addons izleme parametresiyle az aks create komutunu kullanarak bir AKS kümesi oluşturun. Aşağıdaki örnek, otomatik ölçeklendirme, kullanılabilirlik alanı etkin bir küme oluşturur.

Bu işlem birkaç dakika alır.

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

## Kümeye bağlanma

Kubernetes kümesini yönetmek için kubectl adlı Kubernetes komut satırı istemcisini kullanın. Azure Cloud Shell kullanıyorsanız kubectl zaten yüklüdür.

1. az aks install-cli komutunu kullanarak az aks CLI'yi yerel olarak yükleme

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. az aks get-credentials komutunu kullanarak kubectl'yi Kubernetes kümenize bağlanacak şekilde yapılandırın. Aşağıdaki komut:

   - Kimlik bilgilerini indirir ve Kubernetes CLI'sini bunları kullanacak şekilde yapılandırılır.
   - Kubernetes yapılandırma dosyasının varsayılan konumu olan ~/.kube/config kullanır. --file bağımsız değişkenini kullanarak Kubernetes yapılandırma dosyanız için farklı bir konum belirtin.

   > [!WARNING]
   > Bu, aynı girişe sahip mevcut kimlik bilgilerinin üzerine yazar

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. kubectl get komutunu kullanarak kümenize bağlantıyı doğrulayın. Bu komut, küme düğümlerinin listesini döndürür.

   ```bash
   kubectl get nodes
   ```

## NGINX Giriş Denetleyicisini Yükleme

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

## Uygulamayı Dağıtma

Kubernetes bildirim dosyası, hangi kapsayıcı görüntülerinin çalıştırıldığı gibi kümenin istenen durumunu tanımlar.

Bu hızlı başlangıçta, Azure Vote uygulamasını çalıştırmak için gereken tüm nesneleri oluşturmak için bir bildirim kullanacaksınız. Bu bildirim iki Kubernetes dağıtımı içerir:

- Örnek Azure Vote Python uygulamaları.
- Redis örneği.

İki Kubernetes Hizmeti de oluşturulur:

- Redis örneği için bir iç hizmet.
- İnternet'ten Azure Vote uygulamasına erişmek için bir dış hizmet.

Son olarak, trafiği Azure Vote uygulamasına yönlendirmek için bir Giriş kaynağı oluşturulur.

Test oylama uygulaması YML dosyası zaten hazır. 

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

Bu uygulamayı dağıtmak için aşağıdaki komutu çalıştırın

```bash
kubectl apply -f azure-vote-start.yml
```

## Uygulamayı test edin

Genel IP'yi veya uygulama URL'sini ziyaret ederek uygulamanın çalıştığını doğrulayın. Uygulama URL'si aşağıdaki komutu çalıştırarak bulunabilir:

> [!Note]
> POD'lerin oluşturulması ve sitenin HTTP üzerinden erişilebilir olması genellikle 2-3 dakika sürer

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

Sonuçlar:

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

## Özel etki alanına HTTPS sonlandırma ekleme

Öğreticinin bu noktasında, giriş denetleyicisi olarak NGINX içeren bir AKS web uygulamanız ve uygulamanıza erişmek için kullanabileceğiniz özel bir etki alanınız vardır. Sonraki adım, kullanıcıların HTTPS aracılığıyla uygulamanıza güvenli bir şekilde ulaşabilmesi için etki alanına bir SSL sertifikası eklemektir.

## Sertifika Yöneticisini Ayarlama

HTTPS eklemek için Cert Manager'ı kullanacağız. Cert Manager, Kubernetes dağıtımları için SSL sertifikası almak ve yönetmek için kullanılan bir açık kaynak aracıdır. Sertifika Yöneticisi, hem popüler genel Verenler hem de özel Verenler olmak üzere çeşitli Verenlerden sertifika alır ve sertifikaların geçerli ve güncel olduğundan emin olur ve sertifikaları süresi dolmadan önce yapılandırılmış bir zamanda yenilemeyi dener.

1. cert-manager'ı yüklemek için önce içinde çalıştırılacak bir ad alanı oluşturmamız gerekir. Bu öğretici cert-manager ad alanına cert-manager yükler. Dağıtım bildirimlerinde değişiklik yapmanız gerekse de cert-manager'ı farklı bir ad alanında çalıştırmak mümkündür.

   ```bash
   kubectl create namespace cert-manager
   ```

2. Artık cert-manager'ı yükleyebiliriz. Tüm kaynaklar tek bir YAML bildirim dosyasına eklenir. Bu, aşağıdakiler çalıştırılarak yüklenebilir:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Aşağıdakini çalıştırarak cert-manager ad alanına certmanager.k8s.io/disable-validation: "true" etiketini ekleyin. Bu, cert-manager'ın kendi ad alanında oluşturulması için TLS'yi önyüklemesini gerektiren sistem kaynaklarını sağlar.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Helm Charts aracılığıyla sertifika alma

Helm, kubernetes kümelerine uygulama ve hizmet oluşturma, paketleme, yapılandırma ve dağıtımı otomatikleştirmeye yönelik bir Kubernetes dağıtım aracıdır.

Cert-manager, Kubernetes'te birinci sınıf bir yükleme yöntemi olarak Helm grafikleri sağlar.

1. Jetstack Helm deposunu ekleme

   Bu depo, cert-manager grafiklerinin desteklenen tek kaynağıdır. İnternet'te başka aynalar ve kopyalar vardır, ancak bunlar tamamen resmi değildir ve bir güvenlik riski sunabilir.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Yerel Helm Grafiği depo önbelleğini güncelleştirme

   ```bash
   helm repo update
   ```

3. Aşağıdakileri çalıştırarak helm aracılığıyla Cert-Manager eklentisini yükleyin:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Sertifika Veren YAML Dosyası Uygula

   ClusterIssuers, sertifika imzalama isteklerine göre imzalı sertifikalar oluşturabilen sertifika yetkililerini (CA) temsil eden Kubernetes kaynaklarıdır. Tüm sertifika yöneticisi sertifikaları, isteği yerine getirme girişiminde bulunmak için hazır durumda olan, başvuruda bulunu olan bir veren gerektirir.
   Kullanmakta olduğumuz veren, `cluster-issuer-prod.yml file`
        
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

5. Ssl Sertifikası almak için Cert-Manager'ı kullanmak için Oylama Uygulaması Uygulaması Oluşturun.

   Tam YAML dosyası `azure-vote-nginx-ssl.yml`

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

## HTTPS ile Güvenliği Sağlanan AKS Dağıtımınıza Göz Atın

Uygulamanızın HTTPS uç noktasını almak için aşağıdaki komutu çalıştırın:

> [!Note]
> SSL sertifikasının yayılması ve sitenin HTTPS üzerinden ulaşılabilir olması genellikle 2-3 dakika sürer.

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

## Sonraki Adımlar

- [Azure Kubernetes Service Belgeleri](https://learn.microsoft.com/azure/aks/)
- [Azure Container Registry oluşturma](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [AKS'de Applciation'ınızı ölçeklendirme](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [AKS'de uygulamanızı güncelleştirme](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)