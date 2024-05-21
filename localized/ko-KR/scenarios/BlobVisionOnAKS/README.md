# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  AKS 클러스터 + 컨테이너 레지스트리 만들기(12m 52.863s)  ##################################################
# 1.4264s P: 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362s P:7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --subnet-prefix 10.0.1.0/24 \
  --subnets "[{'name':'$POSTGRES_SUBNET_NAME', 'addressPrefix':'10.0.2.0/24'}]"

# 2.3869s P:3
subnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# 나중에 postgres에 액세스할 수 있도록 서브넷에 Microsoft.Storage 엔드포인트 추가 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# 애플리케이션을 포함할 ACR 만들기 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# ACR에 빌드 및 배포할 이미지의 이름
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# ACR에 연결하여 AKS 서브넷에서 AKS 만들기 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# 이미지를 빌드합니다. TODO: "buildx"를 제거하기 위해 이 항목을 업데이트해야 할 수 있습니다. 이는 M1 Mac에서 개발 중인 유일한 항목이기 때문일 수 있습니다.
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE. 

# ACR에 이미지 푸시 
# 53.5264s P:1
docker push $IMAGE 

##################################################  Blob Storage 만들기  ##################################################
# 스토리지 계정 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# 스토리지 계정 키 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# 스토리지 컨테이너 
# 1.5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access Blob 

# # 12.4040s P:7
# az storage cors add \
#   --services b \
#   --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  PSQL 데이터베이스 만들기  ##################################################
# Postgres 서브넷의 Vnet에서 만든 PSQL 데이터베이스 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABASE_SERVER_NAME \
  --database-name $MY_DATABASE_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --vnet $MY_VNET_NAME \
  --subnet $POSTGRES_SUBNET_NAME \
  --yes 

# PSQL 데이터베이스 연결 문자열
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Computer Vision 만들기  ##################################################
# 현재 포털에서 수동 단계가 필요합니다.
# 다음을 수행하지 않으면 이 오류가 발생합니다. 
# (ResourceKindRequireAcceptTerms) 이 구독은 이 리소스에 대한 책임 있는 AI 약관에 동의할 때까지 ComputerVision을 만들 수 없습니다. Azure Portal을 통해 리소스를 만든 다음 다시 시도하여 책임 있는 AI 용어에 동의할 수 있습니다. 자세한 내용은 다음을 참조하세요. https://go.microsoft.com/fwlink/?linkid=2164911 
# 코드: ResourceKindRequireAcceptTerms
# 메시지: 이 구독은 이 리소스에 대한 책임 있는 AI 약관에 동의할 때까지 ComputerVision을 만들 수 없습니다. Azure Portal을 통해 리소스를 만든 다음 다시 시도하여 책임 있는 AI 용어에 동의할 수 있습니다. 자세한 내용은 다음을 참조하세요. https://go.microsoft.com/fwlink/?linkid=2164911 

# 컴퓨터 비전
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# Computer Vision 엔드포인트
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Computer Vision 키
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  수신 컨트롤러 설치 및 애플리케이션 배포(1m 26.3481s)  ##################################################

# Nginx 수신 컨트롤러 TODO 설치: App Gateway로 업데이트할 수 있습니다. 
# 0.2217s P:1
helm 리포지토리 추가 ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# 배포 템플릿의 환경 변수를 스크립트의 변수로 대체하고 AKS에 배포할 새 배포 템플릿 만들기
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 수신에 대한 1.9233s + 5s
kubectl apply -f ./deployment.yaml

# 수신 컨트롤러가 배포될 때까지 대기합니다. 배포될 때까지 검사 유지합니다.
true이면 </&입니다. do aks_cluster_ip=$(kubectl get ingress -o=jsonpath='{.상태. loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; 그런 다음 에코 "AKS 수신 IP 주소는 다음과 같습니다: $aks_cluster_ip" break else echo "AKS 수신 IP 주소가 할당되기를 기다리는 중..." 수 면 150 대 fi 완료

# 문제 : 당신이 원본에 대한 Http를 넣어해야 바보. IP 주소로만 작업해야 합니다.
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  스토리지 계정에 CORS 추가  ##################################################
# 스토리지 계정에 허용되는 CORS 원본에 컨테이너 엔드포인트 추가
# 12.4040s P:7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS 수신 IP 주소: $aks_cluster_ip" echo "AKS 클러스터에 액세스하려면 다음 명령을 사용합니다." echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""