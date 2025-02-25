#!/bin/bash

cd terraform
SUBSCRIPTION_ID=$(az account show --query id --output tsv)
RESOURCE_GROUP=$(terraform output -raw resource_group_name)
CLUSTER_NAME=$(terraform output -raw cluster_name)
ACR_NAME="$(terraform output -raw acr_name)"
# EMAIL="$(terraform output -raw email)"
EMAIL=ariaamini@microsoft.com
cd ..

# Build Image
az acr login --name $ACR_NAME
ACR_URL=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
IMAGE=$ACR_URL/magic8ball:v1
docker build -t $IMAGE ./app --push

# Login
az aks get-credentials --admin --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --subscription $SUBSCRIPTION_ID

# Install Deps
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add jetstack https://charts.jetstack.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
# NGINX ingress controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace "ingress-basic" \
  --set controller.replicaCount=2 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --set controller.metrics.enabled=true \
  --set controller.metrics.serviceMonitor.enabled=true \
  --set controller.metrics.serviceMonitor.additionalLabels.release="prometheus"
# Cert manager
helm install cert-manager jetstack/cert-manager \
  --create-namespace \
  --namespace cert-manager \
  --set crds.enabled=true \
  --set nodeSelector."kubernetes\.io/os"=linux
# Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
    --create-namespace \
    --namespace prometheus \
    --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

export IMAGE
export EMAIL
echo $IMAGE
kubectl create namespace magic8ball
envsubst < quickstart-app.yml | kubectl apply -f -

# Add DNS Record
publicIpAddress=$(kubectl get ingress magic8ball-ingress -n magic8ball -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
az network dns record-set a add-record \
  --zone-name "contoso.com" \
  --resource-group $RESOURCE_GROUP \
  --record-set-name magic8ball \
  --ipv4-address $publicIpAddress