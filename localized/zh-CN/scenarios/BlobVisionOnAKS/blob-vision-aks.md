# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t！
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR=“$（dirname ”$0“）

##################################################  创建 AKS 群集 + 容器注册表（12m 52.863s）  ##################################################
# 1.4264s P： 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362s P：7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --subnet-prefix 10.0.1.0/24 \
  --subnets “[{'name'：'$POSTGRES_SUBNET_NAME'， 'addressPrefix'：'10.0.2.0/24'}]”

# 2.3869s P：3
subnetId=$（az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query “id” -o tsv）  

# 将 Microsoft.Storage Endpoint 添加到子网，以便稍后可以访问 postgres 
# 13.3114s P：4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# 创建 ACR 以包含应用程序 
# 37.7627s P：3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P：1
az acr login --name $MY_CONTAINER_REGISTRY   

# 要生成并部署到 ACR 的映像的名称
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo：v1

# 在 AKS 子网中创建 AKS 并连接到 ACR 
# 224.9959s P： 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# 生成映像。 TODO：可能需要更新此项以删除“buildx”，因为这是 M1 Mac 仅针对我正在开发的
# 133.4897s P：2
docker buildx build --platform=linux/amd64 -t $IMAGE。 

# 将映像推送到 ACR 
# 53.5264s P：1
docker push $IMAGE 

##################################################  创建 Blob 存储  ##################################################
# 存储帐户 
# 27.3420s P：7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# 存储帐户密钥 
# 1.9883s P：2
export STORAGE_ACCOUNT_KEY=$（az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query “[0].value” --output tsv） 

# 存储容器 
# 1.5613s P：4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob 

# # 12.4040s P：7
# az storage cors add \
#   --services b \
#   --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  创建 PSQL 数据库  ##################################################
# 在 Postgres 子网中的 Vnet 中创建的 PSQL 数据库 
# 330.8194s P：13
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

# PSQL 数据库连接字符串
export DATABASE_URL=“postgres：//$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME” 


##################################################  创建计算机视觉  ##################################################
# 现在需要门户中的手动步骤
# 如果不这样做，请获取此错误： 
# （ResourceKindRequireAcceptTerms）在同意此资源的“负责任的 AI 条款”之前，此订阅无法创建 ComputerVision。 可以通过 Azure 门户创建资源，然后重试，从而同意负责任的 AI 条款。 有关更多详细信息，请转到 https://go.microsoft.com/fwlink/?linkid=2164911
# 代码：ResourceKindRequireAcceptTerms
# 消息：只有在你同意此资源的负责任的 AI 条款后，此订阅才能创建 ComputerVision。 可以通过 Azure 门户创建资源，然后重试，从而同意负责任的 AI 条款。 有关更多详细信息，请转到 https://go.microsoft.com/fwlink/?linkid=2164911

# 计算机视觉
# 1.8069s P：6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# 计算机视觉终结点
# 1.2103s P：2
export COMPUTER_VISION_ENDPOINT=$（az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query “properties.endpoint” --output tsv） 

# 计算机视觉密钥
# 1.3998s P：2
export COMPUTER_VISION_KEY=$（az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query “key1” --output tsv）

##################################################  安装入口控制器和部署应用程序（1m 26.3481s）  ##################################################

# 安装 Nginx 入口控制器 TODO：可能需要更新到应用网关 
# 0.2217s P：1
helm 存储库添加 ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P：3
helm 安装 ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations.”service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path“=/healthz 

# 将部署模板中的环境变量替换为脚本中的变量，并创建新的部署模板以在 AKS 上部署
sed -e “s|<IMAGE_NAME>|${IMAGE}|g” \
  -e “s|<DATABASE_URL>|${DATABASE_URL}|g” \
  -e “s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g” \
  -e “s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g” \
  -e “s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g” \
  -e “s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g” deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1.9233s + 5s 用于入口
kubectl apply -f ./deployment.yaml

# 等待部署入口控制器。 将一直检查，直到部署
while true;do aks_cluster_ip=$（kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}'） if [[ -n “$aks_cluster_ip” ]];然后回显“AKS 入口 IP 地址为：$aks_cluster_ip”中断，否则回显“正在等待分配 AKS 入口 IP 地址...”睡眠 150s fi 完成

# 问题：必须为源放置 Http 的哑巴。 应仅使用 IP 地址
export CLUSTER_INGRESS_URL=“http：//$aks_cluster_ip” 

##################################################  将 CORS 添加到存储帐户  ##################################################
# 将容器终结点添加到存储帐户允许的 CORS 源
# 12.4040s P：7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo “----------部署完成----------” 回显 “AKS 入口 IP 地址： $aks_cluster_ip” 回显 “若要访问 AKS 群集，请使用以下命令：” echo “az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster” echo “”