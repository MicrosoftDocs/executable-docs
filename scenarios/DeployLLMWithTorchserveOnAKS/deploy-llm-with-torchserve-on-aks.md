---
title: 'Quickstart: Deploy a Large Language Model with TorchServe on Azure Kubernetes Service (AKS)'
description: Learn how to deploy a large language model using TorchServe on AKS.
ms.topic: quickstart
ms.date: 10/18/2023
author: placeholder
ms.author: placeholder
ms.custom: devx-track-azurecli, mode-api, innovation-engine, linux-related-content
---

# Quickstart: Deploy a Large Language Model with TorchServe on Azure Kubernetes Service (AKS)

In this quickstart, you will learn how to deploy a large language model (LLM) using TorchServe on Azure Kubernetes Service (AKS). TorchServe is a flexible and easy-to-use tool for serving PyTorch models at scale.

## Prerequisites

- An Azure subscription. If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/).
- Azure CLI installed. To install, see [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli).
- Kubernetes CLI (`kubectl`) installed. To install, see [Install kubectl](https://kubernetes.io/docs/tasks/tools/).
- Docker installed. To install, see [Install Docker](https://docs.docker.com/get-docker/).
- Basic knowledge of Docker, Kubernetes, and AKS.

## Create a Resource Group

Create a resource group with the `az group create` command.

```bash
export RANDOM_ID=1f659d
export RESOURCE_GROUP="LLMResourceGroup$RANDOM_ID"
export LOCATION="westus2"
az group create --name $RESOURCE_GROUP --location $LOCATION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LLMResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "LLMResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create an Azure Container Registry

Create an Azure Container Registry (ACR) to store your Docker images.

```bash
export ACR_NAME="llmacr$RANDOM_ID"
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "adminUserEnabled": false,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LLMResourceGroupxxxxxx/providers/Microsoft.ContainerRegistry/registries/llmacrxxxxxx",
  "location": "eastus",
  "loginServer": "llmacrxxxxxx.azurecr.io",
  "name": "llmacrxxxxxx",
  "provisioningState": "Succeeded",
  "resourceGroup": "LLMResourceGroupxxxxxx",
  "sku": {
    "name": "Basic",
    "tier": "Basic"
  },
  "type": "Microsoft.ContainerRegistry/registries"
}
```

## Create an AKS Cluster

Create an AKS cluster and attach the ACR.

```bash
export AKS_CLUSTER="LLMAKSCluster$RANDOM_ID"
```

This command may take several minutes to complete.

## Connect to the Cluster

Configure `kubectl` to connect to your Kubernetes cluster.

```bash
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER
```

Verify the connection by listing the cluster nodes.

```bash
kubectl get nodes
```

## Build and Push the Docker Image

### Prepare Model Artifacts

Place your model artifacts in the same directory as this markdown file. Ensure the following files are present:

- `model.py`: Your PyTorch model definition.
- `model.pt`: Your trained model weights.
- `handler.py`: A custom handler for TorchServe.
- `requirements.txt`: Any additional Python dependencies.

### Create a Model Archive

Generate a TorchServe model archive (`.mar` file).

```bash
torch-model-archiver \
    --model-name llm_model \
    --version 1.0 \
    --model-file model.py \
    --serialized-file model.pt \
    --handler handler.py \
    --extra-files requirements.txt
```

### Create a Dockerfile

Create a file named `Dockerfile` in the same directory with the following content:

```dockerfile
FROM pytorch/torchserve:latest

# Copy the model archive into the model store
COPY llm_model.mar /home/model-server/model-store/

# Expose TorchServe ports
EXPOSE 8080 8081

# Start TorchServe
CMD ["torchserve", "--start", "--model-store", "/home/model-server/model-store", "--models", "llm_model.mar"]
```

### Build the Docker Image

Build the Docker image and tag it with your ACR login server.

```bash
export ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
export IMAGE_TAG="$ACR_LOGIN_SERVER/llm-torchserve:latest"
docker build -t $IMAGE_TAG .
```

### Push the Image to ACR

Log in to ACR and push the image.

```bash
az acr login --name $ACR_NAME
docker push $IMAGE_TAG
```

## Deploy the Docker Image to AKS

### Assign the `AcrPull` Role to the AKS Cluster's Managed Identity

```bash
AKS_RESOURCE_GROUP=$RESOURCE_GROUP
AKS_CLUSTER_NAME=$AKS_CLUSTER

# Get the managed identity's object ID
OBJECT_ID=$(az aks show \
  --resource-group $AKS_RESOURCE_GROUP \
  --name $AKS_CLUSTER_NAME \
  --query "identityProfile.kubeletidentity.objectId" \
  --output tsv)

# Assign the AcrPull role using the object ID
az role assignment create \
  --assignee-object-id $OBJECT_ID \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull \
  --scope $(az acr show --name $ACR_NAME --query id --output tsv)
```

### Create a Kubernetes Deployment

Create a Kubernetes deployment file named `torchserve-deployment.yaml` in the same directory and add the following content:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: torchserve-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: torchserve
  template:
    metadata:
      labels:
        app: torchserve
    spec:
      containers:
      - name: torchserve-container
        image: $IMAGE_TAG
        ports:
        - containerPort: 8080
```

Apply the deployment:

```bash
kubectl apply -f torchserve-deployment.yaml
```

## Expose the Service

Create a service file named `torchserve-service.yaml` in the same directory with the following content:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: torchserve-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: torchserve
```

Apply the service:

```bash
kubectl apply -f torchserve-service.yaml
```

## Test the Deployment

Wait for the external IP to become available:

```bash
kubectl get service torchserve-service 
```

Once the `EXTERNAL-IP` is assigned, you can test the deployment:

```bash
export SERVICE_IP=$(kubectl get service torchserve-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
kubectl get service torchserve-service --watch
curl http://$SERVICE_IP/ping
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "status": "Healthy"
}
```

Invoke the model inference endpoint:

```bash
curl -X POST http://$SERVICE_IP/predictions/llm_model -T input.json
```

Replace `input.json` with your input data file.

## Next Steps

In this quickstart, you deployed a large language model using TorchServe on AKS. You can now scale your deployment, monitor performance, and integrate with other Azure services.