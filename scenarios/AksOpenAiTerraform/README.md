---
title: Deploy and run an Azure OpenAI ChatGPT application on AKS via Terraform
description: This article shows how to deploy an AKS cluster and Azure OpenAI Service via Terraform and how to deploy a ChatGPT-like application in Python.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Provision Resources with Terraform (~5 minutes)
Run terraform to provision all the Azure resources required to setup your new OpenAI website.
```bash
# Authenticate
export ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
az ad sp create-for-rbac --name "ExecutableDocs" --role="Contributor" --scopes="/subscriptions/$ARM_SUBSCRIPTION_ID"
export ARM_CLIENT_ID=$(jq .appId <<< "$SP")
export ARM_CLIENT_SECRET=$(jq .password <<< "$SP")
export ARM_TENANT_ID=$(jq .tenant <<< "$SP")

# Terraform parses TF_VAR_* as vars (Ex: TF_VAR_name -> name)
export TF_VAR_location=$REGION
export TF_VAR_kubernetes_version="1.30.9"
export TF_VAR_model_name="gpt-4o-mini"
export TF_VAR_model_version="2024-07-18"
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

# Install Helm Charts
Install nginx and cert-manager through Helm
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo update

STATIC_IP=$(terraform -chdir=terraform output -raw static_ip)
DNS_LABEL=$(terraform -chdir=terraform output -raw dns_label)
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --set controller.replicaCount=2 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"=$DNS_LABEL \
  --set controller.service.loadBalancerIP=$STATIC_IP \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
helm upgrade --install cert-manager jetstack/cert-manager \
  --set crds.enabled=true \
  --set nodeSelector."kubernetes\.io/os"=linux
```

## Deploy
Apply/Deploy Manifest File 
```bash
export IMAGE="aamini8/magic8ball:latest"
# Uncomment below to manually build docker image yourself instead of using pre-built image.
# docker build -t <YOUR IMAGE NAME> ./magic8ball --push
export HOSTNAME=$(terraform -chdir=terraform output -raw hostname)
export WORKLOAD_IDENTITY_CLIENT_ID=$(terraform -chdir=terraform output -raw workload_identity_client_id)
export AZURE_OPENAI_DEPLOYMENT=$(terraform -chdir=terraform output -raw openai_deployment)
export AZURE_OPENAI_ENDPOINT=$(terraform -chdir=terraform output -raw openai_endpoint)
envsubst < quickstart-app.yml | kubectl apply -f -
```

## Wait for host to be ready
```bash
kubectl wait --for=condition=Ready certificate/tls-secret
echo "Visit: https://$HOSTNAME"
```