---
title: Deploy and run an Azure OpenAI ChatGPT application on AKS via Terraform
description: This article shows how to deploy an AKS cluster and Azure OpenAI Service via Terraform and how to deploy a ChatGPT-like application in Python.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Provision Resources with Terraform (~8 minutes)
Run terraform to provision all the Azure resources required to setup your new OpenAI website.
```bash
# Terraform parses TF_VAR_* as vars (Ex: TF_VAR_name -> name)
export TF_VAR_location="westus3"  
export TF_VAR_kubernetes_version="1.30.7"
export TF_VAR_model_name="gpt-4o-mini"
export TF_VAR_model_version="2024-07-18"
# Terraform consumes sub id as $ARM_SUBSCRIPTION_ID
export ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
# Run Terraform
terraform -chdir=terraform init
terraform -chdir=terraform apply -auto-approve
```

## Login to Cluster
In order to use the kubectl to run commands on the newly created cluster, you must first login.
```bash
RESOURCE_GROUP=$(terraform -chdir=terraform output -raw resource_group_name)
az aks get-credentials --admin --name AksCluster --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID
```

## Deploy
Apply/Deploy Manifest File 
```bash
export IMAGE="aamini8/magic8ball:v1"
export WORKLOAD_IDENTITY_CLIENT_ID=$(terraform -chdir=terraform output -raw workload_identity_client_id)
export AZURE_OPENAI_DEPLOYMENT=$(terraform -chdir=terraform output -raw openai_deployment)
export AZURE_OPENAI_ENDPOINT=$(terraform -chdir=terraform output -raw openai_endpoint)
envsubst < quickstart-app.yml | kubectl apply -f -
```

## Wait for public IP
```bash
kubectl wait --for=jsonpath="{.status.loadBalancer.ingress[0].ip}" service/magic8ball
PUBLIC_IP=$(kubectl get service/magic8ball -o=jsonpath="{.status.loadBalancer.ingress[0].ip}")
echo "Connect to app: $PUBLIC_IP"
```