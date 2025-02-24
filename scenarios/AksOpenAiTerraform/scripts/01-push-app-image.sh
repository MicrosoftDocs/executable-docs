#!/bin/bash

cd terraform

ACR_NAME=$(terraform output acr_url)

# Login
az acr login --name $ACR_NAME
ACR_URL=$(az acr show --name $ACR_NAME --query loginServer --output tsv)

# Build + Push
docker build -t $ACR_URL/$IMAGE ./app --push
