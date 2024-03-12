---
title: AKS에서 확장 가능 및 보안 WordPress 인스턴스 배포
description: 이 자습서에서는 CLI를 통해 AKS에 확장 가능 및 보안 WordPress 인스턴스를 배포하는 방법을 보여 줍니다.
author: adrian.joian
ms.author: adrian.joian
ms.topic: article
ms.date: 12/06/2023
ms.custom: innovation-engine
---

# 빠른 시작: AKS에서 확장 가능 및 보안 WordPress 인스턴스 배포

[![Azure에 배포](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262843)

https를 통해 보호되는 Azure Kubernetes 웹 애플리케이션을 만드는 단계를 단계별로 수행하는 이 자습서를 시작합니다. 이 자습서에서는 사용자가 이미 Azure CLI에 로그인하고 CLI와 함께 사용할 구독을 선택했다고 가정합니다. 또한 Helm이 설치되어 있다고 가정합니다([지침은 여기에서](https://helm.sh/docs/intro/install/) 찾을 수 있음).

## 환경 변수 정의

이 자습서의 첫 번째 단계는 환경 변수를 정의하는 것입니다.

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

## 리소스 그룹 만들기

리소스 그룹은 관련 리소스에 대한 컨테이너입니다. 모든 리소스는 리소스 그룹에 배치해야 합니다. 이 자습서에 대해 만들겠습니다. 다음 명령은 이전에 정의된 $MY_RESOURCE_GROUP_NAME 및 $REGION 매개 변수를 사용하여 리소스 그룹을 만듭니다.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION
```

결과:

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

결과:

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

## Azure Database for MySQL - 유연한 서버 만들기

Azure Database for MySQL - 유연한 서버는 클라우드에서 고가용성 MySQL 서버를 실행, 관리 및 확장하는 데 사용할 수 있는 관리형 서비스입니다. az mysql flexible-server [create 명령을 사용하여 유연한 서버를 만듭니](https://learn.microsoft.com/cli/azure/mysql/flexible-server#az-mysql-flexible-server-create) 다. 서버는 여러 데이터베이스를 포함할 수 있습니다. 다음 명령은 Azure CLI의 로컬 환경에서 서비스 기본값 및 변수 값을 사용하여 서버를 만듭니다.

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

결과:

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

생성된 서버에는 다음과 같은 특성이 있습니다.

- 서버 이름, 관리자 사용자 이름, 관리자 암호, 리소스 그룹 이름, 위치는 클라우드 셸의 로컬 컨텍스트 환경에 이미 지정되어 있으며 리소스 그룹 및 다른 Azure 구성 요소와 동일한 위치에 만들어집니다.
- 서버 구성을 다시 기본 서비스 기본값: 컴퓨팅 계층(버스트 가능), 컴퓨팅 크기/SKU(Standard_B2s), 백업 보존 기간(7일) 및 MySQL 버전(8.0.21)
- 기본 연결 방법은 연결된 가상 네트워크와 자동 생성된 서브넷을 사용하는 프라이빗 액세스(VNet 통합)입니다.

> [!NOTE]
> 서버를 만든 후에는 연결 방법을 변경할 수 없습니다. 예를 들어 만드는 동안 선택한 `Private access (VNet Integration)` 경우 만든 후로 `Public access (allowed IP addresses)` 변경할 수 없습니다. VNet 통합을 사용하여 서버에 안전하게 액세스하려면 프라이빗 액세스 권한이 있는 서버를 만드는 것이 좋습니다. [개념 문서](https://learn.microsoft.com/azure/mysql/flexible-server/concepts-networking-vnet)에서 프라이빗 액세스에 대해 자세히 알아보세요.

기본값을 변경하려는 경우 구성 가능한 CLI 매개 변수의 전체 목록에 대한 Azure CLI [참조 설명서](https://learn.microsoft.com/cli/azure//mysql/flexible-server)를 참조하세요.

## Azure Database for MySQL - 유연한 서버 상태 확인

Azure Database for MySQL - 유연한 서버 및 지원 리소스를 만드는 데 몇 분 정도 걸립니다.

```bash
runtime="10 minute"; endtime=$(date -ud "$runtime" +%s); while [[ $(date -u +%s) -le $endtime ]]; do STATUS=$(az mysql flexible-server show -g $MY_RESOURCE_GROUP_NAME -n $MY_MYSQL_DB_NAME --query state -o tsv); echo $STATUS; if [ "$STATUS" = 'Ready' ]; then break; else sleep 10; fi; done
```

## Azure Database for MySQL - 유연한 서버에서 서버 매개 변수 구성

서버 매개 변수를 사용하여 Azure Database for MySQL - 유연한 서버 구성을 관리할 수 있습니다. 서버 매개 변수는 서버를 만들 때 기본/권장 값으로 구성됩니다.

서버 매개 변수 세부 정보 표시 서버의 특정 매개 변수에 대한 세부 정보를 표시하려면 az mysql flexible-server parameter show[ 명령을 실행](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter)합니다.

### Azure Database for MySQL 사용 안 함 - WordPress 통합을 위한 유연한 서버 SSL 연결 매개 변수

MySQL 서버 엔진에 대한 기본 구성 값을 업데이트하는 특정 서버 매개 변수의 값을 수정할 수도 있습니다. 서버 매개 변수를 업데이트하려면 [az mysql flexible-server parameter set](https://learn.microsoft.com/cli/azure/mysql/flexible-server/parameter#az-mysql-flexible-server-parameter-set) 명령을 사용합니다.

```bash
az mysql flexible-server parameter set \
    -g $MY_RESOURCE_GROUP_NAME \
    -s $MY_MYSQL_DB_NAME \
    -n require_secure_transport -v "OFF" -o JSON
```

결과:

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

## AKS 클러스터 만들기

--enable-addons monitoring 매개 변수와 함께 az aks create 명령을 사용하여 AKS 클러스터를 만들고 컨테이너 인사이트를 사용하도록 설정합니다. 다음 예제에서는 myAKSCluster라는 자동 크기 조정 가용성 영역 사용 클러스터를 만듭니다.

몇 분 정도 걸립니다.

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

고정 공용 IP 주소를 사용하여 수신 컨트롤러를 구성할 수 있습니다. 수신 컨트롤러를 삭제하면 고정 공용 IP 주소가 다시 기본. AKS 클러스터를 삭제하면 IP 주소가 다시 기본 않습니다.
수신 컨트롤러를 업그레이드할 때 수신 컨트롤러 서비스가 할당될 부하 분산 장치를 인식하도록 Helm 릴리스에 매개 변수를 전달해야 합니다. HTTPS 인증서가 올바르게 작동하려면 DNS 레이블을 사용하여 수신 컨트롤러 IP 주소에 대한 FQDN을 구성합니다.
FQDN은 $MY_DNS_LABEL 형식을 따라야 합니다. AZURE_REGION_NAME.cloudapp.azure.com.

```bash
export MY_STATIC_IP=$(az network public-ip create --resource-group MC_${MY_RESOURCE_GROUP_NAME}_${MY_AKS_CLUSTER_NAME}_${REGION} --location ${REGION} --name ${MY_PUBLIC_IP_NAME} --dns-name ${MY_DNS_LABEL} --sku Standard --allocation-method static --version IPv4 --zone 1 2 3 --query publicIp.ipAddress -o tsv)
```

--set controller.service.annotations를 추가합니다." service\.beta\.kubernetes\.io/azure-dns-label-name"="<DNS_LABEL>" 매개 변수. 수신 컨트롤러를 처음 배포할 때 DNS 레이블을 설정하거나 나중에 구성할 수 있습니다. --set controller.service.loadBalancerIP="<STATIC_IP>" 매개 변수를 추가합니다. 이전 단계에서 만든 사용자 고유의 공용 IP 주소를 입력합니다.

1. ingress-nginx Helm 리포지토리 추가

    ```bash
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    ```

2. 로컬 Helm 차트 리포지토리 캐시 업데이트

    ```bash
    helm repo update
    ```

3. 다음을 실행하여 Helm을 통해 ingress-nginx 추가 기능을 설치합니다.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$MY_DNS_LABEL \
        --set controller.service.loadBalancerIP=$MY_STATIC_IP \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
        --wait --timeout 10m0s
    ```

## 사용자 지정 수행에 HTTPS 종료를 추가합니다기본

자습서의 이 시점에서 수신 컨트롤러로 NGINX를 사용하는 AKS 웹앱과 애플리케이션에 액세스하는 데 사용할 수 있는 사용자 지정 기본 있습니다. 다음 단계는 사용자가 https를 통해 안전하게 애플리케이션에 연결할 수 있도록 할 기본 SSL 인증서를 추가하는 것입니다.

## Cert Manager 설정

HTTPS를 추가하기 위해 Cert Manager를 사용합니다. Cert Manager는 Kubernetes 배포에 대한 SSL 인증서를 가져오고 관리하는 데 사용되는 오픈 소스 도구입니다. 인증서 관리자는 널리 사용되는 공용 발급자뿐만 아니라 개인 발급자 등 다양한 발급자로부터 인증서를 가져오고 인증서가 유효하고 최신 상태인지 확인하고 만료 전에 구성된 시간에 인증서를 갱신하려고 시도합니다.

1. cert-manager를 설치하려면 먼저 네임스페이스를 만들어 실행해야 합니다. 이 자습서에서는 cert-manager 네임스페이스에 cert-manager를 설치합니다. 배포 매니페스트를 수정해야 하지만 다른 네임스페이스에서 cert-manager를 실행할 수 있습니다.

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

## Helm 차트를 통해 인증서 가져오기

Helm은 Kubernetes 클러스터에 애플리케이션 및 서비스의 생성, 패키징, 구성 및 배포를 자동화하기 위한 Kubernetes 배포 도구입니다.

Cert-manager는 Kubernetes에 설치하는 일류 방법으로 Helm 차트를 제공합니다.

1. Jetstack Helm 리포지토리 추가

    이 리포지토리는 cert-manager 차트에서 유일하게 지원되는 원본입니다. 인터넷을 통해 다른 미러 및 사본이 있지만 완전히 비공식적이며 보안 위험을 초래할 수 있습니다.

    ```bash
    helm repo add jetstack https://charts.jetstack.io
    ```

2. 로컬 Helm 차트 리포지토리 캐시 업데이트

    ```bash
    helm repo update
    ```

3. 다음을 실행하여 Helm을 통해 Cert-Manager 추가 기능을 설치합니다.

    ```bash
    helm upgrade --install --cleanup-on-fail --atomic \
        --namespace cert-manager \
        --version v1.7.0 \
        --wait --timeout 10m0s \
        cert-manager jetstack/cert-manager
    ```

4. 인증서 발급자 YAML 파일 적용

    ClusterIssuers는 인증서 서명 요청을 적용하여 서명된 인증서를 생성할 수 있는 CA(인증 기관)를 나타내는 Kubernetes 리소스입니다. 모든 인증서 관리자 인증서에는 요청을 적용하기 위해 준비된 상태에 있는 참조된 발급자가 필요합니다.
    사용 중인 발급자는 다음에서 찾을 수 있습니다. `cluster-issuer-prod.yml file` 

    ```bash
    cluster_issuer_variables=$(<cluster-issuer-prod.yaml)
    echo "${cluster_issuer_variables//\$SSL_EMAIL_ADDRESS/$SSL_EMAIL_ADDRESS}" | kubectl apply -f -
    ```

## 사용자 지정 스토리지 클래스 만들기

기본 스토리지 클래스는 가장 일반적인 시나리오에 적합하지만, 일부는 아닙니다. 경우에 따라 고유한 매개 변수를 사용하여 고유 스토리지 클래스를 사용자 지정해야 할 수 있습니다. 예를 들어 다음 매니페스트를 사용하여 파일 공유의 mountOptions를 구성합니다.
fileMode 및 dirMode의 기본값은 Kubernetes 탑재 파일 공유의 경우 0755입니다. 스토리지 클래스 개체에 다른 탑재 옵션을 지정할 수 있습니다.

```bash
kubectl apply -f wp-azurefiles-sc.yaml
```

## AKS 클러스터에 WordPress 배포

이 문서에서는 Bitnami에서 빌드한 WordPress용 기존 Helm 차트를 사용합니다. 예를 들어 Bitnami Helm 차트는 로컬 MariaDB를 데이터베이스로 사용하며 Azure Database for MySQL에서 앱을 사용하려면 이러한 값을 재정의해야 합니다. 모든 재정의 값 값을 재정의할 수 있으며 사용자 지정 설정은 파일에서 찾을 수 있습니다. `helm-wp-aks-values.yaml` 

1. Wordpress Bitnami Helm 리포지토리 추가

    ```bash
    helm repo add bitnami https://charts.bitnami.com/bitnami
    ```

2. 로컬 Helm 차트 리포지토리 캐시 업데이트

    ```bash
    helm repo update
    ```

3. 다음을 실행하여 Helm을 통해 Wordpress 워크로드를 설치합니다.

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

결과:

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

## HTTPS를 통해 보호된 AKS 배포 찾아보기

다음 명령을 실행하여 애플리케이션에 대한 HTTPS 엔드포인트를 가져옵니다.

> [!NOTE]
> SSL 인증서가 전파되는 데 2~3분, 모든 WordPress POD 복제본(replica) 준비되고 사이트가 https를 통해 완전히 연결할 수 있도록 하는 데 약 5분이 걸리는 경우가 많습니다.

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

WordPress 콘텐츠가 올바르게 배달되고 있는지 확인합니다.

```bash
if curl -I -s -f https://$FQDN > /dev/null ; then 
    curl -L -s -f https://$FQDN 2> /dev/null | head -n 9
else 
    exit 1
fi;
```

결과:

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

아래 URL에 따라 웹 사이트를 방문할 수 있습니다.

```bash
echo "You can now visit your web server at https://$FQDN"
```
