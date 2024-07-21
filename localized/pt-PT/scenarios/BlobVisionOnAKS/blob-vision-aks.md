# Vars Env
export MY_RESOURCE_GROUP_NAME=dasha-vision-test export MY_LOCATION=westus export MY_STORAGE_ACCOUNT_NAME=dashastoragevision export MY_DATABASE_SERVER_NAME=dasha-server-vision2 export MY_DATABASE_NAME=demo export MY_DATABASE_USERNAME=postgres export MY_DATABASE_PASSWORD=Sup3rS3cr3t!
export MY_COMPUTER_VISION_NAME=dasha-vision-test export MY_CONTAINER_APP_NAME=dasha-container-vision export MY_CONTAINER_APP_ENV_NAME=dasha-environment-vision export AKS_SUBNET_NAME=AKSSubnet export POSTGRES_SUBNET_NAME=PostgreSQLSubnet export MY_VNET_NAME=vision-vnet export MY_CONTAINER_REGISTRY=dashavisionacr export MY_CLUSTER_NAME=vision-cluster export DIR="$(dirname "$0")"

##################################################  Criar AKS Cluster + registo de contentor (12m 52.863s)  ##################################################
# 1,4264s P: 2 
az group create --name $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION 

# 17,7362s P:7
az rede vnet criar \
  --resource-group $MY_NOME_GRUPO_DE_RECURSOS \
  --localização $MY_LOCALIZAÇÃO \
  --name $MY_VNET_NAME \
  --endereço-prefixo 10.0.0.0/16 \
  --subnet-name $AKS_SUBNET_NAME \
  --sub-rede-prefixo 10.0.1.0/24 \
  --sub-redes "[{'name':'$POSTGRES_SUBNET_NAME', 'addressPrefix':'10.0.2.0/24'}]"

# 2,3869s P:3
subnetId=$(az network vnet subnet show --name $AKS_SUBNET_NAME --resource-group $MY_RESOURCE_GROUP_NAME --vnet-name $MY_VNET_NAME --query "id" -o tsv)  

# Adicionando o Microsoft.Storage Endpoint à sub-rede para que ele possa acessar o postgres mais tarde 
# 13,3114s P:4
Atualização da sub-rede VNet da rede AZ \
  --name $AKS_SUBNET_NAME \
  --resource-group $MY_NOME_GRUPO_DE_RECURSOS \
  --vnet-name $MY_VNET_NAME \
  --pontos de extremidade de serviço Microsoft.Storage 

# Criar ACR para conter o aplicativo 
# 37,7627s P:3
az acr create -n $MY_CONTAINER_REGISTRY -g $MY_RESOURCE_GROUP_NAME --sku basic 

#4,7910s P:1
az acr login --name $MY_CONTAINER_REGISTRY   

# Nome da imagem a ser criada e implantada no ACR
export IMAGE=$MY_CONTAINER_REGISTRY.azurecr.io/vision-demo:v1

# Criar AKS na sub-rede AKS com ligação ao ACR 
# 224,9959s P: 8
az aks create -n $MY_CLUSTER_NAME -g $MY_RESOURCE_GROUP_NAME --generate-ssh-keys --attach-acr $MY_CONTAINER_REGISTRY --vnet-subnet-id $subnetId --network-plugin azure --service-cidr 10.1.0.0/16 --dns-service-ip 10.1.0.10  

# 2.3341s 2
az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n $MY_CLUSTER_NAME 

# Construindo a imagem. TODO: Você pode precisar atualizar isso para remover "buildx", já que isso é apenas para M1 Mac que estou desenvolvendo em
# 133,4897s P:2
Docker buildx build --platform=linux/amd64 -t $IMAGE . 

# Enviar imagem para ACR 
# 53,5264s P:1
Empurrar $IMAGE do Docker 

##################################################  Criar armazenamento de blob  ##################################################
# Conta de armazenamento 
# 27,3420s P:7
az storage account create --name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --location $MY_LOCATION --sku Standard_LRS --vnet-name $MY_VNET_NAME --subnet $AKS_SUBNET_NAME --allow-blob-public-access true

# Chave da conta de armazenamento 
# 1,9883s P:2
export STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name $MY_STORAGE_ACCOUNT_NAME --resource-group $MY_RESOURCE_GROUP_NAME --consulta "[0].value" --output tsv) 

# Contentor de armazenamento 
# 1,5613s P:4
az storage container create --name images --account-name $MY_STORAGE_ACCOUNT_NAME --account-key $STORAGE_ACCOUNT_KEY --blob de acesso público 

# # 12.4040s P:7
# az armazenamento cors adicionar \
#   --serviços b \
#   --métodos DELETE GET HEAD MERGE OPTIONS POST PUT \
#   --origens $CLUSTER_INGRESS_URL \
#   --cabeçalhos permitidos '*' \
#   --idade máxima 3600 \
#   --nome-conta $MY_NOME_DA_CONTA_DO_ARMAZENAMENTO \
#   --chave-conta $STORAGE_CHAVE_CONTA_CHAVE 


##################################################  Criar banco de dados PSQL  ##################################################
# Banco de dados PSQL criado em Vnet na Sub-rede Postgres 
# 330,8194s P:13
az postgres flexible-server criar \
  --name $MY_NOME_DO_SERVIDOR_DO_BANCO DE DADOS \
  --database-name $MY_DATABASE_NAME \
  --resource-group $MY_NOME_GRUPO_DE_RECURSOS \
  --localização $MY_LOCALIZAÇÃO \
  --camada Burstable \
  --sku-name Standard_B1ms \
  --tamanho de armazenamento 32 \
  --versão 15 \
  --admin-user $MY_DATABASE_USERNAME \
  --admin-password $MY_DATABASE_PASSWORD \
  --vnet $MY_VNET_NAME \
  --sub-rede $POSTGRES_SUBNET_NAME \
  --Sim 

# Cadeia de conexão do banco de dados PSQL
export DATABASE_URL="postgres://$MY_DATABASE_USERNAME:$MY_DATABASE_PASSWORD@$MY_DATABASE_SERVER_NAME.postgres.database.azure.com/$MY_DATABASE_NAME" 


##################################################  Criar visão computacional  ##################################################
# Requer uma etapa manual no portal hoje
# Obtenha este erro se não o fizer: 
# (ResourceKindRequireAcceptTerms) Esta assinatura não pode criar o ComputerVision até que você concorde com os termos de IA Responsável para este recurso. Você pode concordar com os termos de IA responsável criando um recurso por meio do Portal do Azure e tentando novamente. Para mais detalhes, vá para https://go.microsoft.com/fwlink/?linkid=2164911
# Código: ResourceKindRequireAcceptTerms
# Mensagem: Esta assinatura não pode criar o ComputerVision até que você concorde com os termos de IA responsável para este recurso. Você pode concordar com os termos de IA responsável criando um recurso por meio do Portal do Azure e tentando novamente. Para mais detalhes, vá para https://go.microsoft.com/fwlink/?linkid=2164911

# Imagem digitalizada
# 1,8069s P:6
az cognitiveservices criar conta \
  --name $MY_NOME_VISÃO_DO_COMPUTADOR \
  --resource-group $MY_NOME_GRUPO_DE_RECURSOS \
  --tipo ComputerVision \
  --sku S1 \
  --localização $MY_LOCALIZAÇÃO \
  --Sim   

# Ponto final de visão computacional
# 1.2103s P:2
export COMPUTER_VISION_ENDPOINT=$(az cognitiveservices account show --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --consulta "properties.endpoint" --output tsv) 

# Chave de visão computacional
# 1,3998s P:2
export COMPUTER_VISION_KEY=$(az cognitiveservices account keys list --name $MY_COMPUTER_VISION_NAME --resource-group $MY_RESOURCE_GROUP_NAME --query "key1" --output tsv)

##################################################  Instalação do controlador Ingress e implantação do aplicativo (1m 26.3481s)  ##################################################

# Instale o controlador de ingresso Nginx TODO: Pode querer atualizar para o App Gateway 
# 0,2217s P:1
helm repo adicionar ingress-nginx https://kubernetes.github.io/ingress-nginx 
# 21,0756s P:3
helm instalar ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace ingress-basic \
  --set controller.service.annotations." serviço\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz 

# Substituindo variáveis de ambiente no modelo de implantação por variáveis em script e criando novo modelo de implantação para implantar no AKS
sed -e "s|<IMAGE_NAME>|${IMAGE}|g" \
  -e "s|<DATABASE_URL>|${DATABASE_URL}|g" \
  -e "s|<COMPUTER_VISION_KEY>|${COMPUTER_VISION_KEY}|g" \
  -e "s|<COMPUTER_VISION_ENDPOINT>|${COMPUTER_VISION_ENDPOINT}|g" \
  -e "s|<MY_STORAGE_ACCOUNT_NAME>|${MY_STORAGE_ACCOUNT_NAME}|g" \
  -e "s|<STORAGE_ACCOUNT_KEY>|${STORAGE_ACCOUNT_KEY}|g" deployment/scripts/deployment-template.yaml > ./deployment.yaml

# 1,9233s + 5s para ingresso
kubectl apply -f ./deployment.yaml

# Aguardando a implantação do controlador de ingresso. Continuará verificando até que seja implantado
enquanto verdadeiro; do aks_cluster_ip=$(kubectl get ingress ingress -o=jsonpath='{.status.loadBalancer.ingress[0].ip}') if [[ -n "$aks_cluster_ip" ]]; então echo "AKS Ingress IP Address is: $aks_cluster_ip" break else echo "Aguardando que o AKS Ingress IP Address seja atribuído..." dormir 150s fi feito

# Problema: que você tem que colocar o Http para a origem. Deve apenas trabalhar com endereço IP
exportar CLUSTER_INGRESS_URL="http://$aks_cluster_ip" 

##################################################  Adicionar CORS à conta de armazenamento  ##################################################
# Adicionar ponto de extremidade de contêiner à origem CORS permitida para a conta de armazenamento
# 12,4040s P:7
az armazenamento cors adicionar \
  --serviços b \
  --métodos DELETE GET HEAD MERGE OPTIONS POST PUT \
  --origens $CLUSTER_INGRESS_URL \
  --cabeçalhos permitidos '*' \
  --idade máxima 3600 \
  --nome-conta $MY_NOME_DA_CONTA_DO_ARMAZENAMENTO \
  --chave-conta $STORAGE_CHAVE_CONTA_CHAVE 


echo "---------- Deployment Complete ----------" echo "AKS Ingress IP Address: $aks_cluster_ip" echo "Para acessar o cluster AKS, use o seguinte comando:" echo "az aks get-credentials -g $MY_RESOURCE_GROUP_NAME -n aks-terraform-cluster" echo ""