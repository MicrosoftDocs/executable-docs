# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME==Ekspor PostgreSQLSubnet MY_VNET_NAME=ekspor vision-vnet MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  Membuat Kluster AKS + registri kontainer (12m 52.863s)  ##################################################
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

# Menambahkan Titik Akhir Microsoft.Storage ke Subnet sehingga dapat mengakses postgres nanti 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# Membuat ACR untuk memuat aplikasi 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Nama gambar untuk membangun dan menyebarkan ke ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# Membuat AKS di subnet AKS dengan koneksi ke ACR 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Membangun gambar. TODO: Anda mungkin perlu memperbarui ini untuk menghapus "buildx" karena hanya untuk M1 Mac yang saya kembangkan
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE . 

# Mendorong gambar ke ACR 
# 53.5264s P:1
docker mendorong $IMAGE 

##################################################  Membuat penyimpanan blob  ##################################################
# Akun Penyimpanan 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Kunci akun penyimpanan 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Wadah penyimpanan 
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


##################################################  Membuat database PSQL  ##################################################
# Database PSQL dibuat di Vnet di Subnet Postgres 
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
  --Ya 

# string koneksi database PSQL
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Membuat visi komputer  ##################################################
# Memerlukan langkah manual di portal hari ini
# Dapatkan kesalahan ini jika Anda tidak: 
# (ResourceKindRequireAcceptTerms) Langganan ini tidak dapat membuat ComputerVision sampai Anda menyetujui persyaratan AI yang bertanggung jawab untuk sumber daya ini. Anda dapat menyetujui persyaratan AI yang bertanggung jawab dengan membuat sumber daya melalui Portal Microsoft Azure lalu mencoba lagi. Untuk detail selengkapnya, buka https://go.microsoft.com/fwlink/?linkid=2164911
# Kode: ResourceKindRequireAcceptTerms
# Pesan: Langganan ini tidak dapat membuat ComputerVision sampai Anda menyetujui persyaratan AI yang bertanggung jawab untuk sumber daya ini. Anda dapat menyetujui persyaratan AI yang bertanggung jawab dengan membuat sumber daya melalui Portal Microsoft Azure lalu mencoba lagi. Untuk detail selengkapnya, buka https://go.microsoft.com/fwlink/?linkid=2164911

# Computer Vision
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --Ya   

# Titik akhir visi komputer
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Kunci visi komputer
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Menginstal pengontrol Ingress dan menyebarkan aplikasi (1m 26.3481s)  ##################################################

# Instal Nginx ingress controller TODO: Mungkin ingin memperbarui ke App Gateway 
# 0.2217s P:1
helm repo tambahkan ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Mengganti variabel lingkungan dalam templat penyebaran dengan variabel dalam skrip dan membuat templat penyebaran baru untuk disebarkan di AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1.9233s + 5s untuk masuk
kubectl apply -f ./deployment.yaml

# Menunggu pengontrol ingress disebarkan. Akan terus memeriksa sampai disebarkan
sementara benar; do aks_cluster_ip=$(kubectl get ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') jika [[ -n "$aks_cluster_ip" ]]; kemudian gema "AKS Ingress IP Address is: $aks_cluster_ip" break else echo "Waiting for AKS Ingress IP Address to be assigned..." tidur 150s fi selesai

# Masalah: Bodoh bahwa Anda harus menempatkan Http untuk asal. Seharusnya hanya bekerja dengan Alamat IP
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  Menambahkan CORS ke akun penyimpanan  ##################################################
# Menambahkan titik akhir kontainer ke asal CORS yang diizinkan untuk akun penyimpanan
# 12.4040s P:7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "Untuk mengakses kluster AKS, gunakan perintah berikut:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""