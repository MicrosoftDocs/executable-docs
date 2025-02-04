---
title: "Deploy a Trino Cluster on Azure Kubernetes Service (AKS)"
description: Learn how to deploy a Trino Cluster on AKS using Azure CLI for scalable and distributed SQL query processing.
ms.topic: article
ms.date: 10/10/2023
author: azure-author
ms.author: azurealias
ms.custom: devx-track-azurecli, mode-api, innovation-engine, aks, trino, distributed-sql, data-analytics
---

# Deploy a Trino Cluster on Azure Kubernetes Service (AKS)

In this Exec Doc, you will learn how to deploy a Trino (formerly PrestoSQL) cluster on Azure Kubernetes Service (AKS). Trino is a distributed SQL query engine, ideal for large-scale data analytics.

## Prerequisites

1. Ensure you have Azure CLI installed in your environment or use [Azure Cloud Shell](https://shell.azure.com/).  
2. Ensure a Kubernetes cluster is already deployed on AKS. You can create one using [this guide](https://learn.microsoft.com/azure/aks/).


## Step 2: Create Azure Resource Group

A resource group is a container that holds related resources for the Trino deployment.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export RESOURCE_GROUP_NAME="TrinoResourceGroup$RANDOM_SUFFIX"
export REGION="westus2"

az group create --name $RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/TrinoResourceGroupxxx",
    "location": "westus2",
    "managedBy": null,
    "name": "TrinoResourceGroupxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 3: Create AKS Cluster

We will deploy an AKS cluster to host the Trino cluster.

```bash
export AKS_CLUSTER_NAME="TrinoAKSCluster$RANDOM_SUFFIX"
export CLUSTER_NODES=3

az aks create \
    --resource-group $RESOURCE_GROUP_NAME \
    --name $AKS_CLUSTER_NAME \
    --node-count $CLUSTER_NODES \
    --generate-ssh-keys
```

## Step 4: Configure `kubectl` Access

We will configure `kubectl` to connect to the newly created AKS cluster.

```bash
az aks get-credentials --resource-group $RESOURCE_GROUP_NAME --name $AKS_CLUSTER_NAME
```

## Step 5: Create Namespace for Trino

Namespaces help organize your Kubernetes resources.

```bash
export NAMESPACE="trino$RANDOM_SUFFIX"
kubectl create namespace $NAMESPACE
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "kind": "Namespace",
    "apiVersion": "v1",
    "metadata": {
        "name": "trino",
        "selfLink": "/api/v1/namespaces/trino",
        "uid": "xxxxx-xxxxx-xxxxx-xxxxx",
        "resourceVersion": "xxxx",
        "creationTimestamp": "xxxx-xx-xxTxx:xx:xxZ"
    }
}
```

## Step 6: Deploy Trino on AKS

We will use a Kubernetes manifest to deploy the Trino cluster.

### Create `trino-deployment.yaml`

```bash
cat <<EOF > trino-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trino
  namespace: $NAMESPACE
spec:
  replicas: 2
  selector:
    matchLabels:
      app: trino
  template:
    metadata:
      labels:
        app: trino
    spec:
      containers:
        - name: trino
          image: trinodb/trino:latest
          ports:
            - containerPort: 8080
EOF
```

### Apply the Deployment

```bash
kubectl apply -f trino-deployment.yaml
```

Results:

<!-- expected_similarity=0.3 -->

```text
deployment.apps/trino created
```

## Step 7: Expose Trino Service

Expose the Trino deployment via a Kubernetes service for external access.

```bash
kubectl expose deployment trino \
    --type=LoadBalancer \
    --name=trino-service \
    --namespace=$NAMESPACE \
    --port=8080 \
    --target-port=8080
```

Results:

<!-- expected_similarity=0.3 -->

```output
service/trino-service exposed
```


## Step 8: Verify Deployment

Ensure that all Trino pods are running.

```bash
while true; do
  POD_STATUSES=$(kubectl get pods --namespace=$NAMESPACE -o jsonpath='{.items[*].status.phase}')
  ALL_RUNNING=true
  for STATUS in $POD_STATUSES; do
    if [ "$STATUS" != "Running" ]; then
      ALL_RUNNING=false
      break
    fi
  done

  if [ "$ALL_RUNNING" = true ]; then
    kubectl get pods --namespace=$NAMESPACE
    break
  else
    sleep 10
  fi
done
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME                     READY   STATUS    RESTARTS   AGE
trino-xxxxx-xxxxx        1/1     Running   0          5m
trino-xxxxx-xxxxx        1/1     Running   0          5m
```

## Step 9: Fetch Service Public IP

Retrieve the external IP address of the Trino service.

```bash
EXTERNAL_IP=$(kubectl get service trino-service --namespace=$NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "External IP: $EXTERNAL_IP"
```

Results:

<!-- expected_similarity=0.3 -->

```text
External IP: xx.xx.xx.xx
```

The `EXTERNAL-IP` field contains the Trino service's public IP. Visit `http://<EXTERNAL-IP>:8080` to access the Trino cluster.


You have successfully deployed a Trino cluster on Azure Kubernetes Service! 🎉