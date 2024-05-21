# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  Создание кластера AKS + реестра контейнеров (12 млн 52.863s)  ##################################################
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
  --subnets "[{'name':'$POSTGRES_SUBNET_NAME", "addressPrefix":'10.0.2.0/24'}]

# 2.3869s P:3
SubnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# Добавление Майкрософт. служба хранилища Конечная точка в подсеть, чтобы получить доступ к postgres позже 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Майкрософт. служба хранилища 

# Создание ACR для хранения приложения 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Имя образа для сборки и развертывания в ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# Создание AKS в подсети AKS с подключением к ACR 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Создание образа. TODO: Может потребоваться обновить это, чтобы удалить "buildx", так как это только для M1 Mac, на который я разрабатывается
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE. 

# Отправка изображения в ACR 
# 53.5264s P:1
Docker push $IMAGE 

##################################################  Создание хранилища BLOB-объектов  ##################################################
# Storage account 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Ключ учетной записи хранения 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Контейнер хранилища 
# 1.5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob 

# # 12.4040s P:7
# az storage cors add \
#   --services b \
#   --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  Создание базы данных PSQL  ##################################################
# База данных PSQL, созданная в виртуальной сети в подсети Postgres 
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

# Строка подключения базы данных PSQL
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Создание компьютерного зрения  ##################################################
# Требуется ручной шаг на портале сегодня
# Получите эту ошибку, если вы этого не сделали: 
# (ResourceKindRequireAcceptTerms) Эта подписка не может создать ComputerVision, пока вы не согласитесь с условиями ответственного ИИ для этого ресурса. Вы можете согласиться с условиями ответственного ИИ, создав ресурс на портале Azure, а затем повторите попытку. Дополнительные сведения см. в статье https://go.microsoft.com/fwlink/?linkid=2164911
# Код: ResourceKindRequireAcceptTerms
# Сообщение. Эта подписка не может создать ComputerVision, пока вы не согласитесь с условиями ответственного ИИ для этого ресурса. Вы можете согласиться с условиями ответственного ИИ, создав ресурс на портале Azure, а затем повторите попытку. Дополнительные сведения см. в статье https://go.microsoft.com/fwlink/?linkid=2164911

# Компьютерное зрение
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# Конечная точка компьютерного зрения
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Ключ компьютерного зрения
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account key list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Установка контроллера входящего трафика и развертывание приложения (1m 26.3481s)  ##################################################

# Установка контроллера входящего трафика Nginx: может потребоваться обновить шлюз приложений. 
# 0.2217s P:1
Helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations". service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Замена переменных среды в шаблоне развертывания переменными в скрипте и создание нового шаблона развертывания для развертывания в AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1.9233s + 5s для входящего трафика
kubectl apply -f ./deployment.yaml

# Ожидание развертывания контроллера входящего трафика. Будет продолжать проверка до его развертывания
значение true; do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; затем эхо "IP-адрес входящего трафика AKS: $aks_cluster_ip" прерывается еще эхо "Ожидание назначения IP-адреса входящего трафика AKS..." спящий 150-х фи готово

# Проблема: Глупый, который необходимо поместить http для источника. Должен работать только с IP-адресом
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  Добавление CORS в учетную запись хранения  ##################################################
# Добавление конечной точки контейнера в разрешенный источник CORS для учетной записи хранения
# 12.4040s P:7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "Чтобы получить доступ к кластеру AKS, используйте следующую команду:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""