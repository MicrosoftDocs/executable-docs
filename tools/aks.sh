#!/bin/bash
# This script creates an AKS cluster using Azure CLI

# Exit on error
set -e

# Configuration variables
RESOURCE_GROUP="myAKSResourceGroup"
LOCATION="eastus"
CLUSTER_NAME="myAKSCluster"
NODE_COUNT=3
NODE_VM_SIZE="Standard_DS2_v2"
KUBERNETES_VERSION="1.26.3"  # Check available versions with: az aks get-versions --location $LOCATION --output table

# Login to Azure (uncomment if not already logged in)
# az login

# Create resource group
echo "Creating resource group $RESOURCE_GROUP in $LOCATION..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create AKS cluster
echo "Creating AKS cluster $CLUSTER_NAME..."
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --node-count $NODE_COUNT \
    --node-vm-size $NODE_VM_SIZE \
    --kubernetes-version $KUBERNETES_VERSION \
    --generate-ssh-keys \
    --enable-managed-identity \
    --enable-cluster-autoscaler \
    --min-count 1 \
    --max-count 5

# Get credentials for the Kubernetes cluster
echo "Getting credentials for cluster $CLUSTER_NAME..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME

echo "AKS cluster $CLUSTER_NAME has been created successfully!"
echo "You can now use kubectl to manage your cluster"

# Verify connection to the cluster
echo "Verifying connection to the cluster..."
kubectl get nodes