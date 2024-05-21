# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t !
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname « $0 ») »

##################################################  Créer un cluster AKS + registre de conteneurs (12m 52.863s)  ##################################################
# 1.4264s P : 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362s P :7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --subnet-prefix 10.0.1.0/24 \
  --subnets « [{'name' :'$POSTGRES_SUBNET_NAME', 'addressPrefix' :'10.0.2.0/24'}] »

# 2.3869s P :3
subnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query « id » -o tsv)  

# Ajout de Microsoft. Stockage point de terminaison vers le sous-réseau afin qu’il puisse accéder ultérieurement à postgres 
# 13.3114s P :4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft. Stockage 

# Créer ACR pour contenir l’application 
# 37.7627s P :3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P :1
az acr login --name $MY_CONTAINER_REGISTRY   

# Nom de l’image à générer et déployer sur ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo :v1

# Créer AKS dans un sous-réseau AKS avec connexion à ACR 
# 224.9959s P : 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Création de l’image. TODO : Vous devrez peut-être mettre à jour cette opération pour supprimer « buildx », car c’est pour M1 Mac que je développe sur
# 133.4897s P :2
docker buildx build --platform=linux/amd64 -t $IMAGE . 

# Envoi d’une image vers ACR 
# 53.5264s P :1
$IMAGE docker Push 

##################################################  Créer un stockage d’objets blob  ##################################################
# Compte de stockage 
# 27.3420s P :7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Clé du compte de stockage 
# 1.9883s P :2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query « [0].value » --output tsv) 

# Conteneur de stockage 
# 1.5613s P :4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob 

# # 12.4040s P :7
# az storage cors add \
#   --services b \
#   --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  Créer une base de données PSQL  ##################################################
# Base de données PSQL créée dans un réseau virtuel dans le sous-réseau Postgres 
# 330.8194s P :13
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

# Base de données PSQL chaîne de connexion
export DATABASE_URL="postgres ://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME » 


##################################################  Créer une vision par ordinateur  ##################################################
# Nécessite une étape manuelle dans le portail aujourd’hui
# Obtenez cette erreur si vous ne procédez pas comme suit : 
# (ResourceKindRequireAcceptTerms) Cet abonnement ne peut pas créer ComputerVision tant que vous n’êtes pas d’accord avec les termes de l’IA responsable pour cette ressource. Vous pouvez accepter les termes de l’IA responsable en créant une ressource via le portail Azure, puis réessayer. Pour plus de détails, consultez https://go.microsoft.com/fwlink/?linkid=2164911
# Code : ResourceKindRequireAcceptTerms
# Message : cet abonnement ne peut pas créer ComputerVision tant que vous n’êtes pas d’accord avec les termes de l’IA responsable pour cette ressource. Vous pouvez accepter les termes de l’IA responsable en créant une ressource via le portail Azure, puis réessayer. Pour plus de détails, consultez https://go.microsoft.com/fwlink/?linkid=2164911

# Vision par ordinateur
# 1.8069s P :6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# Point de terminaison de vision par ordinateur
# 1.2103s P :2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query « properties.endpoint » --output tsv) 

# Clé de vision par ordinateur
# 1.3998s P :2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query « key1 » --output tsv)

##################################################  Installation du contrôleur d’entrée et déploiement de l’application (1m 26.3481s)  ##################################################

# Installer nginx ingress controller TODO : May want to update to App Gateway 
# 0.2217s P :1
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756s P :3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Remplacement des variables d’environnement dans le modèle de déploiement par des variables dans le script et création d’un modèle de déploiement à déployer sur AKS
sed -e « s|<IMAGE_NAME>|${IMAGE}|g » \
  -e « s|<DATABASE_URL>|${DATABASE_URL}|g » \
  -e « s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g » \
  -e « s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g » \
  -e « s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g » \
  -e " s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g » deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1.9233s + 5s pour l’entrée
kubectl apply -f ./deployment.yaml

# En attente du déploiement du contrôleur d’entrée. Conservera le case activée jusqu’à ce qu’il soit déployé
alors que true ; do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n « $aks_cluster_ip » ]] ; puis écho « AkS Ingress IP Address is : $aks_cluster_ip » break else echo " Waiting for AKS Ingress IP Address to be assigned... » veillez 150s fi terminé

# Problème : Dumb que vous devez placer le http pour l’origine. Doit simplement fonctionner avec l’adresse IP
export CLUSTER_INGRESS_URL="http ://$aks_cluster_ip » 

##################################################  Ajout de CORS au compte de stockage  ##################################################
# Ajouter un point de terminaison de conteneur à l’origine CORS autorisée pour le compte de stockage
# 12.4040s P :7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo « ---------- Deployment Complete ---------- » echo « AKS Ingress IP Address : $aks_cluster_ip » echo « To access the AKS cluster, use the following command : » echo « az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster » echo «  »