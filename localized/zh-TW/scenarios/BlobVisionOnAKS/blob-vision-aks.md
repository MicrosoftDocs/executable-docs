# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t！
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR=“$（dirname ”$0“）”

##################################################  建立 AKS 叢集 + 容器登錄 （12m 52.863s）  ##################################################
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

# 將 Microsoft.Storage Endpoint 新增至子網，以便稍後存取 postgres 
# 13.3114s P：4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# 建立 ACR 以包含應用程式 
# 37.7627s P：3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P：1
az acr login --name $MY_CONTAINER_REGISTRY   

# 要建置並部署至 ACR 的映像名稱
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo：v1

# 在具有 ACR 連線的 AKS 子網中建立 AKS 
# 224.9959s P： 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# 建置映像。 TODO：您可能需要更新此專案以移除 “buildx”，因為這是 M1 Mac 的唯一一個我正在開發的專案
# 133.4897s P：2
docker buildx build --platform=linux/amd64 -t $IMAGE 。 

# 將映像推送至 ACR 
# 53.5264s P：1
docker push $IMAGE 

##################################################  建立 Blob 儲存體  ##################################################
# 儲存體帳戶 
# 27.3420s P：7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# 儲存體帳戶金鑰 
# 1.9883s P：2
export STORAGE_ACCOUNT_KEY=$（az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query “[0].value” --output tsv） 

# 儲存體容器 
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


##################################################  建立 PSQL 資料庫  ##################################################
# 在 Postgres 子網的 Vnet 中建立的 PSQL 資料庫 
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

# PSQL 資料庫 連接字串
export DATABASE_URL=“postgres：//$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME” 


##################################################  建立電腦視覺  ##################################################
# 目前需要入口網站中的手動步驟
# 如果您未執行下列錯誤，請取得此錯誤： 
# （ResourceKindRequireAcceptTerms）除非您同意此資源的負責任 AI 條款，否則此訂用帳戶無法建立 ComputerVision。 您可以透過 Azure 入口網站建立資源，然後再試一次，以同意負責任 AI 條款。 如需詳細資訊，請移至 https://go.microsoft.com/fwlink/?linkid=2164911
# 程序代碼：ResourceKindRequireAcceptTerms
# 訊息：除非您同意此資源的負責任 AI 條款，否則此訂用帳戶無法建立 ComputerVision。 您可以透過 Azure 入口網站建立資源，然後再試一次，以同意負責任 AI 條款。 如需詳細資訊，請移至 https://go.microsoft.com/fwlink/?linkid=2164911

# 電腦視覺
# 1.8069s P：6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# 計算機視覺端點
# 1.2103s P：2
export COMPUTER_VISION_ENDPOINT=$（az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query “properties.endpoint” --output tsv） 

# 計算機視覺金鑰
# 1.3998s P：2
export COMPUTER_VISION_KEY=$（az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query “key1” --output tsv）

##################################################  安裝輸入控制器和部署應用程式 （1m 26.3481s）  ##################################################

# 安裝 Nginx 輸入控制器 TODO：可能想要更新至應用程式閘道 
# 0.2217s P：1
helm 存放庫新增輸入-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P：3
helm 安裝 ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations。」service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path“=/healthz 

# 以腳本中的變數取代部署範本中的環境變數，並建立新的部署範本以在AKS上部署
sed -e “s|<IMAGE_NAME>|${IMAGE}|g” \
  -e “s|<DATABASE_URL>|${DATABASE_URL}|g” \
  -e “s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g” \
  -e “s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g” \
  -e “s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g” \
  -e “s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g” deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1.9233s + 5s 用於輸入
kubectl apply -f ./deployment.yaml

# 等候輸入控制器部署。 會持續檢查，直到部署為止
為 true;do aks_cluster_ip=$（kubectl get ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}'） if [[ -n “$aks_cluster_ip” ]];然後回應 “AKS 輸入IP位址為：$aks_cluster_ip” 中斷，否則會回應「正在等候指派 AKS 輸入IP位址...」睡眠 150s fi 完成

# 問題：您必須為來源放置 Http 的啞巴。 應該只使用IP位址
export CLUSTER_INGRESS_URL=“http：//$aks_cluster_ip” 

##################################################  將 CORS 新增至記憶體帳戶  ##################################################
# 將容器端點新增至記憶體帳戶允許的 CORS 來源
# 12.4040s P：7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo “---------- Deployment Complete ----------” echo “AKS Ingress IP Address： $aks_cluster_ip” echo “To access the AKS cluster， use the following command：” echo “az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster” echo “”