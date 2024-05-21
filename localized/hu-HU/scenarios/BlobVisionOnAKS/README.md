# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABA Standard kiadás_Standard kiadás RVER_NAME=dasha-server-vision2 export MY_DATABA Standard kiadás_NAME=demo export MY_DATABA Standard kiadás_UStandard kiadás RNAME=postgres export MY_DATABA Standard kiadás_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  AKS-fürt + tárolóregisztrációs adatbázis létrehozása (12m 52.863s)  ##################################################
# 1.4264s P: 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362s P:7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --alhálózat-előtag 10.0.1.0/24 \
  --alhálózatok "[{'name':'$POSTGRES_SUBNET_NAME', 'addressPrefix':'10.0.2.0/24'}]"

# 2.3869s P:3
subnetId=$(az network vnet subnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# Microsoft.Storage-végpont hozzáadása az alhálózathoz, hogy később hozzáférhessen a postgreshez 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# ACR létrehozása az alkalmazás használatához 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Az ACR-ben létrehozandó és üzembe helyezendő rendszerkép neve
image=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# AKS létrehozása az AKS-alhálózatban az ACR-hez való kapcsolattal 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# A kép létrehozása. TODO: Lehet, hogy frissítenie kell ezt a "buildx" eltávolításához, mivel ez az M1 Mac csak az, amelyen fejlesztek
# 133.4897s P:2
docker build --platform=linux/amd64 -t $IMAGE . 

# Kép küldése az ACR-be 
# 53.5264s P:1
docker push $IMAGE 

##################################################  Blob storage létrehozása  ##################################################
# Tárfiók 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Tárfiók kulcsa 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Tároló 
# 1.5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob 

# # 12.4040s P:7
# az storage cors add \
#   --services b \
#   --metódusok TÖRLÉS GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  PSQL-adatbázis létrehozása  ##################################################
# A Postgres alhálózat virtuális hálózatában létrehozott PSQL-adatbázis 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABA Standard kiadás_Standard kiadás RVER_NAME \
  --database-name $MY_DATABA Standard kiadás_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --15-ös verzió \
  --admin-user $MY_DATABA Standard kiadás_U Standard kiadás RNAME \
  --admin-password $MY_DATABA Standard kiadás_PASSWORD \
  --vnet $MY_VNET_NAME \
  --subnet $POSTGRES_SUBNET_NAME \
  --igen 

# PSQL-adatbázis kapcsolati sztring
databa Standard kiadás_URL="postgres://$MY_DATABA Standard kiadás_U Standard kiadás RNAME:$MY_DATABA Standard kiadás_PASSWORD@$MY_DATABA Standard kiadás_Standard kiadás RVER_NAME.postgres.database.azure.com/$MY_DATABAStandard kiadás_NAME" 


##################################################  Számítógépes látás létrehozása  ##################################################
# Manuális lépésre van szükség a portálon
# A következő hibaüzenet jelenik meg, ha nem: 
# (ResourceKindRequireAcceptTerms) Ez az előfizetés mindaddig nem tudja létrehozni a ComputerVisiont, amíg ön nem fogadja el az erőforrás felelős AI-feltételeit. A felelős AI-feltételek elfogadásához hozzon létre egy erőforrást az Azure Portalon, majd próbálkozzon újra. További részletekért látogasson el a https://go.microsoft.com/fwlink/?linkid=2164911
# Kód: ResourceKindRequireAcceptTerms
# Üzenet: Ez az előfizetés mindaddig nem tudja létrehozni a ComputerVisiont, amíg ön nem fogadja el az erőforrás felelős AI-feltételeit. A felelős AI-feltételek elfogadásához hozzon létre egy erőforrást az Azure Portalon, majd próbálkozzon újra. További részletekért látogasson el a https://go.microsoft.com/fwlink/?linkid=2164911

# Számítógépes látástechnológia
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --igen   

# Számítógépes látásvégpont
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Számítógépes látáskulcs
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Bejövőforgalom-vezérlő telepítése és alkalmazás telepítése (1m 26.3481s)  ##################################################

# Nginx bejövőforgalom-vezérlő TODO telepítése: Előfordulhat, hogy frissíteni szeretne az App Gatewayre 
# 0.2217s P:1
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Az üzembehelyezési sablon környezeti változóinak lecserélése a szkript változóira, és új üzembehelyezési sablon létrehozása az AKS-en való üzembe helyezéshez
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABA Standard kiadás_URL>|${DATABA Standard kiadás_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1,9233s + 5s bejövő forgalomhoz
kubectl apply -f ./deployment.yaml

# Várakozás a bejövőforgalom-vezérlő üzembe helyezésére. Továbbra is ellenőrzi, amíg üzembe nem helyezi
míg igaz; do aks_cluster_ip=$(kubectl get ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; majd echo "AKS bejövő IP-cím: $aks_cluster_ip" break else echo "Várakozás az AKS bejövő IP-cím hozzárendelésére..." alvó 150s fi kész

# Probléma: Buta, hogy meg kell tenni a Http a forrás. Csak az IP-címmel kell dolgoznia
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  CORS hozzáadása tárfiókhoz  ##################################################
# Tárolóvégpont hozzáadása a tárfiók engedélyezett CORS-forrásához
# 12.4040s P:7
az storage cors add \
  --services b \
  --metódusok TÖRLÉS GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Bejövő IP-cím: $aks_cluster_ip" echo "Az AKS-fürt eléréséhez használja a következő parancsot:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""