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
# DELETE
export EMAIL="ariaamini@microsoft.com"
export SUBSCRIPTION_ID="b7684763-6bf2-4be5-8fdd-f9fadb0f27a1"

# Define input vars
export LOCATION="westus3"
export KUBERNETES_VERSION="1.30.7"
export AZURE_OPENAI_MODEL="gpt-4o-mini"
export AZURE_OPENAI_VERSION="2024-07-18"

# Run Terraform
export TF_VAR_location=$LOCATION  # $TF_VAR_example_name will be read as var example_name by terraform.
export TF_VAR_kubernetes_version=$KUBERNETES_VERSION
export TF_VAR_model_name=$AZURE_OPENAI_MODEL
export TF_VAR_model_version=$AZURE_OPENAI_VERSION
export ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID  # Used by terraform to find sub.
terraform -chdir=infra init
terraform -chdir=infra apply

# Save outputs
export RESOURCE_GROUP=$(terraform -chdir=infra output -raw resource_group_name)
export WORKLOAD_IDENTITY_CLIENT_ID=$(terraform -chdir=infra output -raw workload_identity_client_id)
export AZURE_OPENAI_ENDPOINT=$(terraform -chdir=infra output -raw openai_endpoint)
export ACR_LOGIN_URL=$(terraform -chdir=infra output -raw acr_login_url)
export IMAGE="$ACR_LOGIN_URL/magic8ball:v1"
```

# Login to AKS
```bash
az aks get-credentials --admin --name AksCluster --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID
```

## Build Dockerfile
```bash
az acr login --name $ACR_LOGIN_URL
docker build -t $IMAGE ./magic8ball --push
```

# Deploy App
```bash
envsubst < quickstart-app.yml | kubectl apply -f -
```

# Wait for public IP
```bash
kubectl wait --for=jsonpath="{.status.loadBalancer.ingress[0].ip}" service/magic8ball-service
PUBLIC_IP=$(kubectl get service/magic8ball-service -o=jsonpath="{.status.loadBalancer.ingress[0].ip}")
echo "Connect to app: $PUBLIC_IP"
```