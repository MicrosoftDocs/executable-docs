---
title: Azure CLI를 사용하여 확장 가능한 보안 Azure Kubernetes Service 클러스터 배포
description: 이 자습서에서는 https를 통해 보호되는 Azure Kubernetes 웹 애플리케이션을 만드는 단계를 단계별로 설명합니다.
author: mbifeld
ms.author: mbifeld
ms.topic: article
ms.date: 11/28/2023
ms.custom: innovation-engine
---

# 빠른 시작: Azure CLI를 사용하여 확장 가능하고 안전한 Azure Kubernetes Service 클러스터 배포

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/?Microsoft_Azure_CloudNative_clientoptimizations=false&feature.canmodifyextensions=true#view/Microsoft_Azure_CloudNative/SubscriptionSelectionPage.ReactView/tutorialKey/CreateAKSDeployment)

https를 통해 보호되는 Azure Kubernetes 웹 애플리케이션을 만드는 단계를 단계별로 수행하는 이 자습서를 시작합니다. 이 자습서에서는 사용자가 이미 Azure CLI에 로그인하고 CLI와 함께 사용할 구독을 선택했다고 가정합니다. 또한 Helm이 설치되어 있다고 가정합니다([지침은 여기에서](https://helm.sh/docs/intro/install/) 찾을 수 있음).

## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

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

## 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치되어야 합니다. 이 자습서에 대해 만들겠습니다. 다음 명령은 이전에 정의된 $MY_RESOURCE_GROUP_NAME 및 $REGION 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

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

## 가상 네트워크 및 서브넷 만들기

가상 네트워크는 Azure에서 개인 네트워크의 기본 구성 요소입니다. Azure Virtual Network를 통해 VM과 같은 Azure 리소스가 상호 간 및 인터넷과 안전하게 통신할 수 있습니다.

```bash
az network vnet create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --name $MY_VNET_NAME \
    --address-prefix $MY_VNET_PREFIX \
    --subnet-name $MY_SN_NAME \
    --subnet-prefixes $MY_SN_PREFIX
```

Results:

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

## AKS Azure 리소스 공급자에 등록

Microsoft.OperationsManagement 및 Microsoft.OperationalInsights 공급자가 구독에 등록되어 있는지 확인합니다. [컨테이너 인사이트](https://docs.microsoft.com/azure/azure-monitor/containers/container-insights-overview)를 지원하는 데 필요한 Azure 리소스 공급자입니다. 등록 상태를 확인하려면 다음 명령을 실행합니다.

```bash
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.OperationalInsights
```

## AKS 클러스터 만들기

--enable-addons monitoring 매개 변수와 함께 az aks create 명령을 사용하여 AKS 클러스터를 만들고 컨테이너 인사이트를 사용하도록 설정합니다. 다음 예제에서는 자동 크기 조정, 가용성 영역 사용 클러스터를 만듭니다.

이 작업은 몇 분 정도 걸립니다.

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

## 클러스터에 연결

Kubernetes 클러스터를 관리하려면 Kubernetes 명령줄 클라이언트인 kubectl을 사용합니다. Azure Cloud Shell을 사용하는 경우 kubectl이 이미 설치되어 있습니다.

1. az aks install-cli 명령을 사용하여 az aks CLI를 로컬로 설치

   ```bash
   if ! [ -x "$(command -v kubectl)" ]; then az aks install-cli; fi
   ```

2. az aks get-credentials 명령을 사용하여 Kubernetes 클러스터에 연결하도록 kubectl을 구성합니다. 다음 명령은 아래와 같은 작업을 수행합니다.

   - 자격 증명을 다운로드하고 이를 사용하도록 Kubernetes CLI를 구성합니다.
   - Kubernetes 구성 파일의 기본 위치인 ~/.kube/config를 사용합니다. --file 인수를 사용하여 Kubernetes 구성 파일의 다른 위치를 지정합니다.

   > [!WARNING]
   > 이렇게 하면 동일한 항목으로 기존 자격 증명을 덮어쓰게 됩니다.

   ```bash
   az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME --overwrite-existing
   ```

3. kubectl get 명령을 사용하여 클러스터에 대한 연결을 확인합니다. 이 명령은 클러스터 노드 목록을 반환합니다.

   ```bash
   kubectl get nodes
   ```

## NGINX 수신 컨트롤러 설치

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

## 애플리케이션 배포

Kubernetes 매니페스트 파일은 실행할 컨테이너 이미지와 같은 클러스터에 대해 원하는 상태를 정의합니다.

이 빠른 시작에서는 매니페스트를 사용하여 Azure Vote 애플리케이션을 실행하는 데 필요한 모든 개체를 만듭니다. 이 매니페스트에는 다음과 같은 두 개의 Kubernetes 배포가 포함됩니다.

- 샘플 Azure Vote Python 애플리케이션.
- Redis 인스턴스.

다음과 같은 두 개의 Kubernetes 서비스도 생성됩니다.

- Redis 인스턴스에 대한 내부 서비스.
- 인터넷에서 Azure Vote 애플리케이션에 액세스하기 위한 외부 서비스.

마지막으로 Azure Vote 애플리케이션에 트래픽을 라우팅하기 위한 수신 리소스가 만들어집니다.

테스트 투표 앱 YML 파일이 이미 준비되었습니다. 

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

이 앱을 배포하려면 다음 명령을 실행합니다.

```bash
kubectl apply -f azure-vote-start.yml
```

## 애플리케이션 테스트

공용 IP 또는 애플리케이션 URL을 방문하여 애플리케이션이 실행되고 있는지 확인합니다. 애플리케이션 URL은 다음 명령을 실행하여 찾을 수 있습니다.

> [!Note]
> POD를 만들고 HTTP를 통해 사이트에 연결할 수 있는 데 2-3분이 걸리는 경우가 많습니다.

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

Results:

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

## 사용자 지정 도메인에 HTTPS 종료 추가

자습서의 이 시점에서 수신 컨트롤러로 NGINX를 사용하는 AKS 웹앱과 애플리케이션에 액세스하는 데 사용할 수 있는 사용자 지정 도메인이 있습니다. 다음 단계는 사용자가 HTTPS를 통해 애플리케이션에 안전하게 연결할 수 있도록 도메인에 SSL 인증서를 추가하는 것입니다.

## 인증서 관리자 설정

HTTPS를 추가하기 위해 Cert Manager를 사용합니다. Cert Manager는 Kubernetes 배포에 대한 SSL 인증서를 가져오고 관리하는 데 사용되는 오픈 소스 도구입니다. 인증서 관리자는 널리 사용되는 공용 발급자뿐만 아니라 개인 발급자 등 다양한 발급자로부터 인증서를 가져오고 인증서가 유효하고 최신 상태인지 확인하고 만료 전에 구성된 시간에 인증서를 갱신하려고 시도합니다.

1. cert-manager를 설치하려면 먼저 이를 실행할 네임스페이스를 만들어야 합니다. 이 자습서에서는 cert-manager 네임스페이스에 cert-manager를 설치합니다. 배포 매니페스트를 수정해야 하지만 다른 네임스페이스에서 cert-manager를 실행할 수 있습니다.

   ```bash
   kubectl create namespace cert-manager
   ```

2. 이제 cert-manager를 설치할 수 있습니다. 모든 리소스는 단일 YAML 매니페스트 파일에 포함됩니다. 다음을 실행하여 설치할 수 있습니다.

   ```bash
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.7.0/cert-manager.crds.yaml
   ```

3. 다음을 실행하여 cert-manager 네임스페이스에 "true" 레이블을 certmanager.k8s.io/disable-validation 추가합니다. 이렇게 하면 인증서 관리자가 TLS를 부트스트랩해야 하는 시스템 리소스를 자체 네임스페이스에 만들 수 있습니다.

   ```bash
   kubectl label namespace cert-manager certmanager.k8s.io/disable-validation=true
   ```

## Helm Charts를 통해 인증서 가져오기

Helm은 Kubernetes 클러스터에 애플리케이션 및 서비스의 생성, 패키징, 구성 및 배포를 자동화하기 위한 Kubernetes 배포 도구입니다.

Cert-manager는 Kubernetes에 대한 최고 수준의 설치 방법으로 Helm 차트를 제공합니다.

1. Jetstack Helm 리포지토리 추가

   이 리포지토리는 cert-manager 차트의 유일하게 지원되는 원본입니다. 인터넷을 통해 다른 거울과 사본이 있지만 완전히 비공식적이며 보안 위험을 초래할 수 있습니다.

   ```bash
   helm repo add jetstack https://charts.jetstack.io
   ```

2. 로컬 Helm 차트 리포지토리 캐시 업데이트

   ```bash
   helm repo update
   ```

3. 다음을 실행하여 helm을 통해 Cert-Manager 추가 기능을 설치합니다.

   ```bash
   helm install cert-manager jetstack/cert-manager --namespace cert-manager --version v1.7.0
   ```

4. 인증서 발급자 YAML 파일 적용

   ClusterIssuers는 인증서 서명 요청을 적용하여 서명된 인증서를 생성할 수 있는 CA(인증 기관)를 나타내는 Kubernetes 리소스입니다. 모든 cert-manager 인증서에는 요청을 이행할 준비가 되어 있는 참조 발급자가 필요합니다.
   사용 중인 발급자는 다음에서 찾을 수 있습니다. `cluster-issuer-prod.yml file` 
    
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

5. Cert-Manager를 사용하여 SSL 인증서를 가져오도록 Voting App 애플리케이션을 업테이트합니다.

   전체 YAML 파일은 다음에서 찾을 수 있습니다. `azure-vote-nginx-ssl.yml` 

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

## HTTPS를 통해 보호된 AKS 배포 찾아보기

다음 명령을 실행하여 애플리케이션에 대한 HTTPS 엔드포인트를 가져옵니다.

> [!Note]
> SSL 인증서가 전파되고 사이트가 HTTPS를 통해 연결할 수 있는 데 2-3분이 걸리는 경우가 많습니다.

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

## 다음 단계

- [Azure Kubernetes Service 설명서](https://learn.microsoft.com/azure/aks/)
- [Azure Container Registry 만들기](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-prepare-acr?tabs=azure-cli)
- [AKS에서 Applciation 크기 조정](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-scale?tabs=azure-cli)
- [AKS에서 애플리케이션 업데이트](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-app-update?tabs=azure-cli)