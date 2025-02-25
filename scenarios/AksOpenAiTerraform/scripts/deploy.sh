#!/bin/bash

SUBSCRIPTION_ID=$(az account show --query id --output tsv)
TENANT_ID=$(az account show --query tenantId --output tsv)
RESOURCE_GROUP=$(terraform output resource_group_name)
LOCATION="westus3"

# Build Image
ACR_NAME=$(terraform output acr_name)
az acr login --name $ACR_NAME
ACR_URL=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
docker build -t $ACR_URL/magic8ball:v1 ./app --push

az aks get-credentials \
  --admin \
  --name $clusterName \
  --resource-group $resourceGroupName \
  --subscription $subscriptionId \
  --only-show-errors

# Install NGINX ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --create-namespace \
  --namespace "ingress-basic" \
  --set controller.replicaCount=3 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --set controller.metrics.enabled=true \
  --set controller.metrics.serviceMonitor.enabled=true \
  --set controller.metrics.serviceMonitor.additionalLabels.release="prometheus" \

# Install Cert manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --create-namespace \
  --namespace "cert-manager" \
  --set installCRDs=true \
  --set nodeSelector."kubernetes\.io/os"=linux

# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
    --create-namespace \
    --namespace prometheus \
    --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

NAMESPACE="magic8ball"
kubectl create namespace $NAMESPACE
kubectl apply -f cluster-issuer.yml
kubectl apply -f service-account.yml
kubectl apply -n $NAMESPACE -f ingress.yml
kubectl apply -n $NAMESPACE -f config-map.yml
kubectl apply -n $NAMESPACE -f deployment.yml
kubectl apply -f "service.yml" -n $NAMESPACE

# Add DNS Record
ingressName="magic8ball-ingress"
publicIpAddress=$(kubectl get ingress $ingressName -n $namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -n $publicIpAddress ]; then
  echo "[$publicIpAddress] external IP address of the application gateway ingress controller successfully retrieved from the [$ingressName] ingress"
else
  echo "Failed to retrieve the external IP address of the application gateway ingress controller from the [$ingressName] ingress"
  exit
fi
az network dns record-set a add-record \
  --zone-name "contoso.com" \
  --resource-group $RESOURCE_GROUP \
  --record-set-name magic8ball \
  --ipv4-address $publicIpAddress