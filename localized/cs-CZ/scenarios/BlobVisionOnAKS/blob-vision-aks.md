# Env vars
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  Vytvoření clusteru AKS + registru kontejneru (12 min. 52.863s)  ##################################################
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

# Přidání koncového bodu Microsoft.Storage do podsítě, aby mohl později přistupovat k postgresi 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# Vytvoření služby ACR, která bude obsahovat aplikaci 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Název image pro sestavení a nasazení do ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# Vytvoření AKS v podsíti AKS s připojením k ACR 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Sestavení image TODO: Možná budete muset aktualizovat, aby se odebral "buildx", protože to je pro M1 Mac pouze to, že vyvíjím na
# 133.4897s P:2
docker buildx --platform=linux/amd64 -t $IMAGE . 

# Nahrání image do ACR 
# 53.5264s P:1
docker push $IMAGE 

##################################################  Vytvoření úložiště objektů blob  ##################################################
# Účet úložiště 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Klíč účtu úložiště 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Kontejner úložiště 
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


##################################################  Vytvoření databáze PSQL  ##################################################
# Databáze PSQL vytvořená ve virtuální síti v podsíti Postgres 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABASE_SERVER_NAME \
  --database-name $MY_DATABASE_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --velikost úložiště 32 \
  --version 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --vnet $MY_VNET_NAME \
  --subnet $POSTGRES_SUBNET_NAME \
  --Ano 

# Připojovací řetězec databáze PSQL
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Vytvoření počítačového zpracování obrazu  ##################################################
# Vyžaduje dnes ruční krok na portálu.
# Pokud ne, zobrazí se tato chyba: 
# (ResourceKindRequireAcceptTerms) Toto předplatné nemůže vytvořit ComputerVision, dokud nebudete souhlasit s podmínkami zodpovědné umělé inteligence pro tento prostředek. Pokud chcete souhlasit s podmínkami zodpovědné umělé inteligence, vytvořte prostředek prostřednictvím webu Azure Portal a zkuste to znovu. Další podrobnosti najdete na https://go.microsoft.com/fwlink/?linkid=2164911
# Kód: ResourceKindRequireAcceptTerms
# Zpráva: Toto předplatné nemůže vytvořit ComputerVision, dokud nebudete souhlasit s podmínkami zodpovědné umělé inteligence pro tento prostředek. Pokud chcete souhlasit s podmínkami zodpovědné umělé inteligence, vytvořte prostředek prostřednictvím webu Azure Portal a zkuste to znovu. Další podrobnosti najdete na https://go.microsoft.com/fwlink/?linkid=2164911

# Počítačové zpracování obrazu
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --Ano   

# Koncový bod počítačového zpracování obrazu
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Klíč počítačového zpracování obrazu
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Instalace kontroleru příchozího přenosu dat a nasazení aplikace (1m 26.3481s)  ##################################################

# Instalace toDO kontroleru příchozího přenosu dat Nginx: Může se přát aktualizovat na App Gateway 
# 0.2217s P:1
Přidání ingress-nginx úložiště helm https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
Helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." \.kubernetes\.\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Nahrazení proměnných prostředí v šabloně nasazení proměnnými ve skriptu a vytvoření nové šablony nasazení pro nasazení v AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" nasazení/scripts/deployment-template.yaml > ./deployment.yaml

# 1,9233s + 5s pro příchozí přenos dat
kubectl apply -f ./deployment.yaml

# Čeká se na nasazení kontroleru příchozího přenosu dat. Bude pokračovat v kontrole, dokud se nenasadí.
zatímco true; do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; pak ozvěna "IP adresa příchozího přenosu dat AKS je: $aks_cluster_ip" break else echo "Čeká se na přiřazení IP adresy příchozího přenosu dat AKS..." spánek 150s fi hotovo

# Problém: Dumb that you have put the Http for the origin. Měla by fungovat jenom s IP adresou.
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  Přidání CORS do účtu úložiště  ##################################################
# Přidání koncového bodu kontejneru do povoleného zdroje CORS pro účet úložiště
# 12.4040s P:7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "To access the AKS cluster, use the AKS cluster, use the following command: echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""