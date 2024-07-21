# Wariancja env
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  Tworzenie klastra AKS i rejestru kontenerów (12m 52.863s)  ##################################################
# 1.4264s P: 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17.7362s P:7
az network vnet create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --name $MY_VNET_NAME \
  --address-prefiks 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --subnet-prefix 10.0.1.0/24 \
  --subnets "[{'name':'$POSTGRES_SUBNET_NAME', 'addressPrefix':'10.0.2.0/24'}]"

# 2.3869s P:3
subnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# Dodawanie punktu końcowego usługi Microsoft.Storage do podsieci w celu uzyskania dostępu do bazy danych Postgres później 
# 13.3114s P:4
az network vnet subnet update \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --vnet-name $MY_VNET_NAME \
  --service-endpoints Microsoft.Storage 

# Tworzenie usługi ACR zawierającej aplikację 
# 37.7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4.7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Nazwa obrazu do kompilowania i wdrażania w usłudze ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# Tworzenie usługi AKS w podsieci usługi AKS z połączeniem z usługą ACR 
# 224.9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Kompilowanie obrazu. TODO: Może być konieczne zaktualizowanie tego, aby usunąć "buildx", ponieważ jest to tylko dla M1 Mac, że rozwijam się
# 133.4897s P:2
docker buildx build --platform=linux/amd64 -t $IMAGE . 

# Wypychanie obrazu do usługi ACR 
# 53.5264s P:1
$IMAGE wypychania platformy Docker 

##################################################  Tworzenie magazynu obiektów blob  ##################################################
# Konto magazynu 
# 27.3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Klucz konta magazynu 
# 1.9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "[0].value" --output tsv) 

# Kontener magazynu 
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


##################################################  Tworzenie bazy danych PSQL  ##################################################
# Baza danych PSQL utworzona w sieci wirtualnej w podsieci Postgres 
# 330.8194s P:13
az postgres flexible-server create \
  --name $MY_DATABASE_SERVER_NAME \
  --database-name $MY_DATABASE_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --location $MY_LOCATION \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --wersja 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --vnet $MY_VNET_NAME \
  --subnet $POSTGRES_SUBNET_NAME \
  --tak 

# parametry połączenia bazy danych PSQL
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Tworzenie przetwarzania obrazów  ##################################################
# Wymaga ręcznego kroku w portalu dzisiaj
# Jeśli nie: 
# (ResourceKindRequireAcceptTerms) Ta subskrypcja nie może utworzyć usługi ComputerVision, dopóki nie wyrazisz zgody na warunki odpowiedzialnego używania sztucznej inteligencji dla tego zasobu. Warunki odpowiedzialnego używania sztucznej inteligencji można zaakceptować, tworząc zasób za pośrednictwem witryny Azure Portal, a następnie spróbuj ponownie. Aby uzyskać więcej szczegółów, przejdź do https://go.microsoft.com/fwlink/?linkid=2164911
# Kod: ResourceKindRequireAcceptTerms
# Komunikat: Ta subskrypcja nie może utworzyć usługi ComputerVision, dopóki nie wyrazisz zgody na warunki odpowiedzialnego używania sztucznej inteligencji dla tego zasobu. Warunki odpowiedzialnego używania sztucznej inteligencji można zaakceptować, tworząc zasób za pośrednictwem witryny Azure Portal, a następnie spróbuj ponownie. Aby uzyskać więcej szczegółów, przejdź do https://go.microsoft.com/fwlink/?linkid=2164911

# Przetwarzanie obrazów
# 1.8069s P:6
az cognitiveservices account create \
  --name $MY_COMPUTER_VISION_NAME \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --kind ComputerVision \
  --sku S1 \
  --location $MY_LOCATION \
  --tak   

# Punkt końcowy przetwarzania obrazów
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "properties.endpoint" --output tsv) 

# Klucz przetwarzania obrazów
# 1.3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Instalowanie kontrolera ruchu przychodzącego i wdrażanie aplikacji (1m 26.3481s)  ##################################################

# Zainstaluj kontroler ruchu przychodzącego Nginx TODO: może chcieć zaktualizować usługę App Gateway 
# 0.2217s P:1
dodatek ingress-nginx repozytorium helm https://kubernetes.github.io/ingress-nginx 
# 21.0756s P:3
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations". usługa\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Zastępowanie zmiennych środowiskowych w szablonie wdrożenia zmiennymi w skrypcie i tworzenie nowego szablonu wdrożenia do wdrożenia w usłudze AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1,9233s + 5s dla ruchu przychodzącego
kubectl apply -f ./deployment.yaml

# Oczekiwanie na wdrożenie kontrolera ruchu przychodzącego. Będzie sprawdzać, dopóki nie zostanie wdrożona
wartość true; do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}'), jeśli [[ -n "$aks_cluster_ip" ]]; następnie echo "AKS Ingress IP Address is: $aks_cluster_ip" break else echo "Oczekiwanie na przypisanie adresu IP ruchu przychodzącego usługi AKS..." spać 150s fi gotowe

# Problem: Głupie, że musisz umieścić Http dla źródła. Powinna po prostu pracować z adresem IP
export CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  Dodawanie mechanizmu CORS do konta magazynu  ##################################################
# Dodawanie punktu końcowego kontenera do dozwolonego źródła mechanizmu CORS dla konta magazynu
# 12.4040s P:7
az storage cors add \
  --services b \
  --methods DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origins $CLUSTER_INGRESS_URL \
  --allowed-headers '*' \
  --max-age 3600 \
  --account-name $MY_STORAGE_ACCOUNT_NAME \
  --account-key $STORAGE_ACCOUNT_KEY 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "Aby uzyskać dostęp do klastra AKS, użyj następującego polecenia:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""