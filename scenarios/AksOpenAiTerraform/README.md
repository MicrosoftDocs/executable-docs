---
title: Deploy and run an Azure OpenAI ChatGPT application on AKS via Terraform
description: This article shows how to deploy an AKS cluster and Azure OpenAI Service via Terraform and how to deploy a ChatGPT-like application in Python.
ms.topic: quickstart 
ms.date: 09/06/2024 
author: aamini7
ms.author: ariaamini
ms.custom: innovation-engine, linux-related-content 
---

## Install AKS extension

Run commands below to set up AKS extensions for Azure.

```bash
az extension add --name aks-preview
az aks install-cli
```

## Provision Resources

Provision all infrastructure using terraform.

```bash
export SUBSCRIPTION_ID="b7684763-6bf2-4be5-8fdd-f9fadb0f27a1"
export EMAIL="amini5454@gmail.com"

export ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
terraform -chdir=infra init
terraform -chdir=infra apply

# Save outputs
export RESOURCE_GROUP=$(terraform -chdir=infra output -raw resource_group_name)
export CLUSTER_NAME=$(terraform -chdir=infra output -raw cluster_name)
export WORKLOAD_IDENTITY_CLIENT_ID=$(terraform -chdir=infra output -raw workload_identity_client_id)
export ACR_NAME=$(terraform -chdir=infra output -raw acr_name)
```

# Login

Login to AKS cluster

```bash
az aks get-credentials --admin --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID
```

## Build Dockerfile

Build app's container image

```bash
export IMAGE="$ACR_NAME.azurecr.io/magic8ball:v1"
az acr login --name $ACR_NAME
docker build -t $IMAGE ./magic8ball --push
```

# Deploy App

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --set controller.replicaCount=2 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --set controller.metrics.enabled=true \
  --set controller.metrics.serviceMonitor.enabled=true \
  --set controller.metrics.serviceMonitor.additionalLabels.release="prometheus"
helm install cert-manager jetstack/cert-manager \
  --set crds.enabled=true \
  --set nodeSelector."kubernetes\.io/os"=linux
helm install prometheus prometheus-community/kube-prometheus-stack \
    --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

envsubst < quickstart-app.yml | kubectl apply -f -
```

# Wait for App to Finish

Wait for public IP

```bash
kubectl wait --for=jsonpath='{.status.loadBalancer.ingress[0].ip}' ingress/magic8ball-ingress
```

# Add DNS Record

Have DNS point to app

```bash
PUBLIC_IP=$(kubectl get ingress magic8ball-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
az network dns record-set a add-record \
  --zone-name "contoso.com" \
  --resource-group $RESOURCE_GROUP \
  --record-set-name magic8ball \
  --ipv4-address $PUBLIC_IP
```