# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  Erstellen von AKS Cluster + Containerregistrierung (12m 52.863s)  ##################################################
# 1.4264s S: 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362 s P:7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefix 10.0.0.0/16 \
  --subnetzname $AKS_SUBNET_NAME \
  --subnetzpräfix 10.0.1.0/24 \
  --Subnetzen "[{'name':'$POSTGRES_SUBNET_NAME', 'addressPrefix':'10.0.2.0/24'}]"

# 2.3869s P:3
subnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# Hinzufügen von Microsoft.Storage-Endpunkt zu Subnetz, damit es später auf Postgres zugreifen kann 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# Erstellen von ACR zur Aufnahme der Anwendung 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Name des Zu erstellenden und bereitstellenden Images für ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# Erstellen von AKS in AKS-Subnetz mit Verbindung mit ACR 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.10.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Erstellen des Bilds. TODO: Möglicherweise müssen Sie dies aktualisieren, um "Buildx" zu entfernen, da dies nur für M1 Mac ist, auf dem ich entwicklung
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE . 

# Pushing image to ACR 
# 53.5264s P:1
Docker-Push-$IMAGE 

##################################################  Erstellen eines Blobspeichers  ##################################################
# Speicherkonto 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Speicherkontoschlüssel 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Speichercontainer 
# 1.5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --public-access blob 

# # 12.4040s P:7
# az storage cors add \
#   --services b \
#   --Methods DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origins $CLUSTER_INGRESS_URL \
#   --allowed-headers '*' \
#   --max-age 3600 \
#   --account-name $MY_STORAGE_ACCOUNT_NAME \
#   --account-key $STORAGE_ACCOUNT_KEY 


##################################################  Erstellen einer PSQL-Datenbank  ##################################################
# PSQL-Datenbank, die in Vnet in Postgres Subnetz erstellt wurde 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABASE_SERVER_NAME \
  --database-name $MY_DATABASE_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --Version 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --vnet $MY_VNET_NAME \
  --Subnetz $POSTGRES_SUBNETZNAME \
  --yes 

# PSQL-Datenbank Verbindungszeichenfolge
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Erstellen einer Computervision  ##################################################
# Erfordert heute einen manuellen Schritt im Portal.
# Erhalten Sie diesen Fehler, wenn Sie nicht: 
# (ResourceKindRequireAcceptTerms) Dieses Abonnement kann ComputerVision erst erstellen, wenn Sie den Bedingungen für verantwortungsvolle KI für diese Ressource zustimmen. Sie können den Bedingungen für verantwortungsvolle KI zustimmen, indem Sie eine Ressource über das Azure-Portal erstellen und es dann erneut versuchen. Weitere Details finden Sie unter https://go.microsoft.com/fwlink/?linkid=2164911
# Code: ResourceKindRequireAcceptTerms
# Nachricht: Dieses Abonnement kann ComputerVision erst erstellen, wenn Sie den Bedingungen für verantwortungsvolle KI für diese Ressource zustimmen. Sie können den Bedingungen für verantwortungsvolle KI zustimmen, indem Sie eine Ressource über das Azure-Portal erstellen und es dann erneut versuchen. Weitere Details finden Sie unter https://go.microsoft.com/fwlink/?linkid=2164911

# Maschinelles Sehen
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --yes   

# Computer-Vision-Endpunkt
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Computer-Vision-Schlüssel
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Installieren des Ingress-Controllers und bereitstellen der Anwendung (1m 26.3481s)  ##################################################

# Installieren des Nginx-Eingangscontrollers TODO: Kann auf das App-Gateway aktualisieren 
# 0.2217s P:1
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21.0756 s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Ersetzen von Umgebungsvariablen in der Bereitstellungsvorlage durch Variablen im Skript und Erstellen einer neuen Bereitstellungsvorlage für die Bereitstellung auf AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1,9233s + 5s für Den Eingangs
kubectl apply -f ./deployment.yaml

# Warten auf die Bereitstellung des Eingangscontrollers. Überprüft weiterhin, bis sie bereitgestellt wird.
während wahr; do aks_cluster_ip=$(kubectl get ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; echo "AKS Ingress IP Address is: $aks_cluster_ip" break else echo "Waiting for AKS Ingress IP Address to be assigned..." Schlaf 150s fi fertig

# Problem: Dumb, dass Sie http für den Ursprung ablegen müssen. Sollte nur mit IP-Adresse funktionieren
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  Hinzufügen von CORS zum Speicherkonto  ##################################################
# Hinzufügen eines Containerendpunkts zum zulässigen CORS-Ursprung für Speicherkonto
# 12.4040 s P:7
az storage cors add \
  --services b \
  --Methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "To access the AKS cluster, use the following command:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""