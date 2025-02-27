---
title: Deploy and run an Azure OpenAI ChatGPT application on AKS via Terraform
description: This article shows how to deploy an AKS cluster and Azure OpenAI Service via Terraform and how to deploy a ChatGPT-like application in Python.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Provision Resources
Run terraform to provision all the required Azure resources
```bash
# Terraform parses TF_VAR_* (Ex: TF_VAR_xname -> xname)
export TF_VAR_location="westus3"  
export TF_VAR_kubernetes_version="1.30.7"
export TF_VAR_model_name="gpt-4o-mini"
export TF_VAR_model_version="2024-07-18"

terraform -chdir=infra init
terraform -chdir=infra apply -auto-approve
```

## Login to Cluster
```bash
RESOURCE_GROUP=$(terraform -chdir=infra output -raw resource_group_name)
az aks get-credentials --admin --name AksCluster --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID
```

## Deploy
```bash
## Build Dockerfile
ACR_LOGIN_URL=$(terraform -chdir=infra output -raw acr_login_url)
IMAGE="$ACR_LOGIN_URL/magic8ball:v1"
az acr login --name $ACR_LOGIN_URL
docker build -t $IMAGE ./magic8ball --push

# Apply Manifest File
export IMAGE
export WORKLOAD_IDENTITY_CLIENT_ID=$(terraform -chdir=infra output -raw workload_identity_client_id)
export AZURE_OPENAI_DEPLOYMENT=$(terraform -chdir=infra output -raw openai_deployment)
export AZURE_OPENAI_ENDPOINT=$(terraform -chdir=infra output -raw openai_endpoint)
envsubst < quickstart-app.yml | kubectl apply -f -```
```

## Wait for public IP
```bash
kubectl wait --for=jsonpath="{.status.loadBalancer.ingress[0].ip}" service/magic8ball-service
PUBLIC_IP=$(kubectl get service/magic8ball-service -o=jsonpath="{.status.loadBalancer.ingress[0].ip}")
echo "Connect to app: $PUBLIC_IP"
```