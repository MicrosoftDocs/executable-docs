# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  AKS-cluster en containerregister maken (12m 52.863s)  ##################################################
# 1.4264s P: 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362s P:7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --subnet-voorvoegsel 10.0.1.0/24 \
  --subnetten "[{'name':'$POSTGRES_SUBNET_NAME', 'addressPrefix':'10.0.2.0/24'}]

# 2.3869s P:3
subnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# Microsoft.Storage-eindpunt toevoegen aan subnet zodat het later toegang heeft tot postgres 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-eindpunten Microsoft.Storage 

# ACR maken om de toepassing te bevatten 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Naam van de installatiekopieën die moeten worden gebouwd en geïmplementeerd in ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# AKS maken in het AKS-subnet met verbinding met ACR 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# De installatiekopieën bouwen. TODO: Mogelijk moet u dit bijwerken om 'buildx' te verwijderen, omdat dat alleen voor M1 Mac's is waarop ik ontwikkel
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE . 

# Afbeelding naar ACR pushen 
# 53.5264s P:1
docker push $IMAGE 

##################################################  Blob-opslag maken  ##################################################
# Opslagaccount 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Opslagaccountsleutel 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Opslagcontainer 
# 1.5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob 

# # 12.4040s P:7
# az storage cors add \
#   --services b \
#   --methoden DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-leeftijd 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  PSQL-database maken  ##################################################
# PSQL-database gemaakt in Vnet in Postgres-subnet 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABASE_SERVER_NAME \
  --databasenaam $MY_DATABASE_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --opslaggrootte 32 \
  --versie 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --vnet $MY_VNET_NAME \
  --subnet $POSTGRES_SUBNET_NAME \
  --Ja 

# PSQL-database verbindingsreeks
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Computer Vision maken  ##################################################
# Vereist vandaag een handmatige stap in de portal
# Deze fout wordt weergegeven als u het volgende niet doet: 
# (ResourceKindRequireAcceptTerms) Dit abonnement kan geen ComputerVision maken totdat u akkoord gaat met de verantwoordelijke AI-voorwaarden voor deze resource. U kunt akkoord gaan met verantwoordelijke AI-termen door een resource te maken via Azure Portal en het vervolgens opnieuw te proberen. Ga voor meer informatie naar https://go.microsoft.com/fwlink/?linkid=2164911
# Code: ResourceKindRequireAcceptTerms
# Bericht: Dit abonnement kan ComputerVision pas maken als u akkoord gaat met de verantwoordelijke AI-voorwaarden voor deze resource. U kunt akkoord gaan met verantwoordelijke AI-termen door een resource te maken via Azure Portal en het vervolgens opnieuw te proberen. Ga voor meer informatie naar https://go.microsoft.com/fwlink/?linkid=2164911

# Computer Vision
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --Ja   

# Computer Vision-eindpunt
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Computer Vision-sleutel
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Ingangscontroller installeren en toepassing implementeren (1m 26.3481s)  ##################################################

# Nginx-controller voor inkomend verkeer installeren: Mogelijk wilt u bijwerken naar App Gateway 
# 0.2217s P:1
Helm-opslagplaats toevoegen ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
Helm installeer inkomend-nginx-inkomend-nginx/inkomend-nginx \
  --create-namespace \
  --naamruimte inkomend-basic \
  --set controller.service.annotaations.". service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Omgevingsvariabelen in de implementatiesjabloon vervangen door variabelen in het script en het maken van een nieuwe implementatiesjabloon voor implementatie op AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1,9233s + 5s voor inkomend verkeer
kubectl apply -f ./deployment.yaml

# Wacht tot de ingangscontroller is geïmplementeerd. Blijft controleren totdat deze is geïmplementeerd
terwijl waar; do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; echo 'AKS Inkomend IP-adres is: $aks_cluster_ip' breek anders echo 'Wachten op AKS Inkomend IP-adres wordt toegewezen...' slaap 150s fi klaar

# Probleem: Dom dat u de Http voor de oorsprong moet plaatsen. Werkt alleen met IP-adres
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  CORS toevoegen aan opslagaccount  ##################################################
# Containereindpunt toevoegen aan toegestane CORS-oorsprong voor opslagaccount
# 12.4040s P:7
az storage cors add \
  --services b \
  --methoden DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-leeftijd 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "To access the AKS cluster, use the following command:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""