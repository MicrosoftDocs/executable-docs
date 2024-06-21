---
title: Implantar um cluster de Serviço Kubernetes do Azure Escalável ou Seguro usando a CLI do Azure
description: Este tutorial onde vamos levá-lo passo a passo na criação de um Aplicativo Web Kubernetes do Azure que é protegido via https.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# Guia de início rápido: implantar um cluster do Serviço Kubernetes do Azure Escalável ou Seguro usando a CLI do Azure

[![Implementar no Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

Bem-vindo a este tutorial, onde iremos levá-lo passo a passo na criação de um Aplicativo Web Kubernetes do Azure que é protegido via https. Este tutorial pressupõe que você já esteja conectado à CLI do Azure e tenha selecionado uma assinatura para usar com a CLI. Também pressupõe que você tenha o Helm instalado ([as instruções podem ser encontradas aqui](https://helm.sh/docs/intro/install/)).

## Definir variáveis de ambiente

O primeiro passo neste tutorial é definir variáveis de ambiente.

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

## Criar um grupo de recursos

Um grupo de recursos é um contêiner para recursos relacionados. Todos os recursos devem ser colocados em um grupo de recursos. Vamos criar um para este tutorial. O comando a seguir cria um grupo de recursos com os parâmetros $MY_RESOURCE_GROUP_NAME e $REGION definidos anteriormente.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Resultados:

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

## Criar uma rede virtual e uma sub-rede

Uma rede virtual é o bloco de construção fundamental para redes privadas no Azure. A Rede Virtual do Azure permite que recursos do Azure, como VMs, se comuniquem com segurança entre si e com a Internet.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Resultados:

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

## Registe-se no AKS Azure Resource Providers

Verifique se os provedores Microsoft.OperationsManagement e Microsoft.OperationalInsights estão registrados em sua assinatura. Esses são os provedores de recursos do Azure necessários para dar suporte [a insights](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview) de contêiner. Para verificar o status do registro, execute os seguintes comandos

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## Criar cluster AKS

Crie um cluster AKS usando o comando az aks create com o parâmetro de monitoramento --enable-addons para habilitar insights de contêiner. O exemplo a seguir cria um cluster habilitado para zona de disponibilidade de dimensionamento automático.

Esta operação irá demorar alguns minutos.

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

## Ligar ao cluster

Para gerenciar um cluster Kubernetes, use o cliente de linha de comando Kubernetes, kubectl. kubectl já está instalado se você usar o Azure Cloud Shell.

1. Instale az aks CLI localmente usando o comando az aks install-cli

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. Configure o kubectl para se conectar ao cluster do Kubernetes usando o comando az aks get-credentials. O seguinte comando:

   - Baixa credenciais e configura a CLI do Kubernetes para usá-las.
   - Usa ~/.kube/config, o local padrão para o arquivo de configuração do Kubernetes. Especifique um local diferente para o arquivo de configuração do Kubernetes usando o argumento --file.

   > [!WARNING]
   > Isso substituirá quaisquer credenciais existentes com a mesma entrada

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. Verifique a conexão com seu cluster usando o comando kubectl get. Este comando retorna uma lista dos nós do cluster.

   ```bash
   kubectl get nodes
   ```

## Instalar NGINX Ingress Controller

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

## Implantar o aplicativo

Um arquivo de manifesto do Kubernetes define o estado desejado de um cluster, como quais imagens de contêiner devem ser executadas.

Neste início rápido, você usará um manifesto para criar todos os objetos necessários para executar o aplicativo Azure Vote. Esse manifesto inclui duas implantações do Kubernetes:

- O exemplo de aplicativos Python do Azure Vote.
- Uma instância Redis.

Dois Serviços Kubernetes também são criados:

- Um serviço interno para a instância Redis.
- Um serviço externo para acessar o aplicativo Azure Vote da Internet.

Finalmente, um recurso de Ingresso é criado para rotear o tráfego para o aplicativo Azure Vote.

Um arquivo YML do aplicativo de votação de teste já está preparado. 

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

Para implantar este aplicativo, execute o seguinte comando

```bash
kubectl apply -f azure-vote-start.yml
```

## Teste o aplicativo

Valide se o aplicativo está sendo executado visitando o ip público ou a URL do aplicativo. A url do aplicativo pode ser encontrada executando o seguinte comando:

> [!Note]
> Muitas vezes, leva de 2 a 3 minutos para que os PODs sejam criados e o site seja acessível via HTTP

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

Resultados:

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

## Adicionar terminação HTTPS ao domínio personalizado

Neste ponto do tutorial, você tem um aplicativo web AKS com NGINX como controlador de ingresso e um domínio personalizado que você pode usar para acessar seu aplicativo. A próxima etapa é adicionar um certificado SSL ao domínio para que os usuários possam acessar seu aplicativo com segurança via HTTPS.

## Configurar o Cert Manager

Para adicionar HTTPS, vamos usar o Cert Manager. O Cert Manager é uma ferramenta de código aberto usada para obter e gerenciar o certificado SSL para implantações do Kubernetes. O Cert Manager obterá certificados de uma variedade de Emissores, tanto emissores públicos populares quanto emissores privados, e garantirá que os certificados sejam válidos e atualizados, e tentará renovar certificados em um momento configurado antes do vencimento.

1. Para instalar o cert-manager, devemos primeiro criar um namespace para executá-lo. Este tutorial instalará o cert-manager no namespace cert-manager. É possível executar o cert-manager em um namespace diferente, embora você precise fazer modificações nos manifestos de implantação.

   ```bash
   kubectl create namespace cert-manager
   ```

2. Agora podemos instalar o cert-manager. Todos os recursos são incluídos em um único arquivo de manifesto YAML. Isso pode ser instalado executando o seguinte:

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. Adicione o rótulo certmanager.k8s.io/disable-validation: "true" ao namespace cert-manager executando o seguinte. Isso permitirá que os recursos do sistema que o cert-manager requer para inicializar o TLS sejam criados em seu próprio namespace.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Obter certificado via Helm Charts

O Helm é uma ferramenta de implantação do Kubernetes para automatizar a criação, empacotamento, configuração e implantação de aplicativos e serviços para clusters Kubernetes.

O Cert-manager fornece gráficos Helm como um método de instalação de primeira classe no Kubernetes.

1. Adicionar o repositório Jetstack Helm

   Este repositório é a única fonte suportada de gráficos cert-manager. Existem alguns outros espelhos e cópias na Internet, mas estes são totalmente não oficiais e podem representar um risco de segurança.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. Atualizar o cache do repositório Helm Chart local

   ```bash
   helm repo update
   ```

3. Instale o addon Cert-Manager via helm executando o seguinte:

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. Aplicar arquivo YAML do emissor do certificado

   ClusterIssuers são recursos do Kubernetes que representam autoridades de certificação (CAs) que são capazes de gerar certificados assinados honrando solicitações de assinatura de certificado. Todos os certificados de gestor de certificados requerem um emissor referenciado que esteja em condições de estar pronto para tentar honrar o pedido.
   O emissor que estamos a utilizar pode ser encontrado no `cluster-issuer-prod.yml file`
    
    ```bash
    cat << EOF > cluster-issuer-prod.yml
    #!/bin/bash
    #kubectl apply -f - <<EOF
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
    #EOF

    # References:
    # https://docs.microsoft.com/azure/application-gateway/ingress-controller-letsencrypt-certificate-application-gateway
    # https://cert-manager.io/docs/configuration/acme/
    # kubectl delete -f clusterIssuer.yaml
    # kubectl apply -f clusterIssuer-prod.yaml 
    EOF  
    ```

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

5. Atualize o aplicativo de votação para usar o Cert-Manager para obter um certificado SSL.

   O arquivo YAML completo pode ser encontrado em `azure-vote-nginx-ssl.yml`

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

## Navegue pelo seu AKS Deployment Secured via HTTPS

Execute o seguinte comando para obter o ponto de extremidade HTTPS para seu aplicativo:

> [!Note]
> Muitas vezes, leva de 2 a 3 minutos para que o certificado SSL seja proposto e o site seja acessível via HTTPS.

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

## Passos Seguintes

- [Documentação do Serviço Kubernetes do Azure](https://learn.microsoft.com/azure/aks/)
- [Criar um Registro de Contêiner do Azure](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [Dimensione sua Aplicação no AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [Atualize a sua aplicação no AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)