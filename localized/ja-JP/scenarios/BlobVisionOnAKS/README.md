# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABA Standard Edition_Standard Edition RVER_NAME=dasha-server-vision2 export MY_DATABA Standard Edition_NAME=demo export MY_DATABA Standard Edition_U Standard EditionRNAME=postgres export MY_DATABA Standard Edition_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  AKS クラスターとコンテナー レジストリの作成 (12m 52.863s)  ##################################################
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

# 後で postgres にアクセスできるように Microsoft.Storage エンドポイントをサブネットに追加する 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# アプリケーションを格納する ACR を作成する 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# ビルドして ACR にデプロイするイメージの名前
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# ACR への接続を使用して AKS サブネットに AKS を作成する 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# イメージのビルド。 TODO:それは私が開発しているM1 Macののみであるため、これを更新して"buildx"を削除する必要がある場合があります
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE . 

# イメージを ACR にプッシュする 
# 53.5264s P:1
docker push $IMAGE 

##################################################  BLOB ストレージを作成する  ##################################################
# ストレージ アカウント 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# ストレージ アカウント キー 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# ストレージ コンテナー 
# 1.5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access BLOB 

# # 12.4040s P:7
# az storage cors add \
#   --services b \
#   --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  PSQL データベースを作成する  ##################################################
# Postgres サブネットの Vnet に作成された PSQL データベース 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABA Standard Edition_Standard Edition RVER_NAME \
  --database-name $MY_DATABA Standard Edition_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 15 \
  --admin-user $MY_DATABA Standard Edition_U Standard Edition RNAME \
  --admin-password $MY_DATABA Standard Edition_PASSWORD \
  --vnet $MY_VNET_NAME \
  --subnet $POSTGRES_SUBNET_NAME \
  --yes 

# PSQL データベース 接続文字列
export DATABA Standard Edition_URL="postgres://$MY_DATABA Standard Edition_U Standard Edition RNAME:$MY_DATABA Standard Edition_PASSWORD@$MY_DATABA Standard Edition_Standard Edition RVER_NAME.postgres.database.azure.com/$MY_DATABAStandard Edition_NAME" 


##################################################  コンピューター ビジョンを作成する  ##################################################
# 今すぐポータルで手動で手順を実行する必要がある
# 次の操作を行わない場合は、このエラーが発生します。 
# (ResourceKindRequireAcceptTerms)このサブスクリプションは、このリソースの責任ある AI 条件に同意するまで ComputerVision を作成できません。 責任ある AI の用語に同意するには、Azure Portal を使用してリソースを作成してから、もう一度試します。 詳細については、以下を参照してください。 https://go.microsoft.com/fwlink/?linkid=2164911
# コード: ResourceKindRequireAcceptTerms
# メッセージ: このサブスクリプションでは、このリソースの責任ある AI 条件に同意するまで ComputerVision を作成できません。 責任ある AI の用語に同意するには、Azure Portal を使用してリソースを作成してから、もう一度試します。 詳細については、以下を参照してください。 https://go.microsoft.com/fwlink/?linkid=2164911

# Computer Vision
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# Computer Vision エンドポイント
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Computer Vision キー
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  イングレス コントローラーのインストールとアプリケーションのデプロイ (1m 26.3481s)  ##################################################

# Nginx イングレス コントローラー TODO のインストール: App Gateway に更新したい場合があります 
# 0.2217s P:1
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations。service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# デプロイ テンプレート内の環境変数をスクリプト内の変数に置き換え、AKS にデプロイする新しいデプロイ テンプレートを作成する
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABA Standard Edition_URL>|${DATABA Standard Edition_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1.9233s + 5s for ingress
kubectl apply -f ./deployment.yaml

# イングレス コントローラーがデプロイされるのを待機しています。 デプロイされるまでチェックを続けます
一方、true。do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [- n "$aks_cluster_ip" ];次に、"AKS イングレス IP アドレスは:$aks_cluster_ip" break else echo "Waiting for AKS Ingress IP Address to be assigned..." (AKS イングレス IP アドレスが割り当てられるのを待機しています。) をエコーします。スリープ 150s fi done

# 問題: 配信元に Http を配置する必要がある呆呆。 IP アドレスを使用する必要がある
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  ストレージ アカウントへの CORS の追加  ##################################################
# ストレージ アカウントの許可された CORS 配信元にコンテナー エンドポイントを追加する
# 12.4040s P:7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "AKS クラスターにアクセスするには、次のコマンドを使用します:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""