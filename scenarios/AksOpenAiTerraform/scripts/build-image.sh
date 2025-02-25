ACR_NAME=$(terraform output resource_group_name)
IMAGE_NAME="magic8ball"
TAG="v1"
IMAGE="$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"

az acr login --name $ACR_NAME

# Build and push app image
ACR_URL=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
docker build -t $ACR_URL/$IMAGE ./app --push