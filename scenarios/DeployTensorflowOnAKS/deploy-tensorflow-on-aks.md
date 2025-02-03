---
title: 'Setup: Deploy a Tensorflow Cluster on Azure Kubernetes Service (AKS)'
description: Learn how to deploy a Tensorflow cluster on Azure Kubernetes Service (AKS) using Azure CLI.
ms.topic: how-to
ms.date: 10/31/2023
author: azureexecdocs
ms.author: azureexecdocs
ms.custom: devx-track-azurecli, mode-api, innovation-engine, machine-learning, kubernetes
---

# Setup: Deploy a Tensorflow Cluster on Azure Kubernetes Service (AKS)

This guide demonstrates how to deploy a Tensorflow cluster on AKS using the Azure CLI. The setup includes provisioning an AKS cluster, configuring a Kubernetes namespace, and deploying a TensorFlow cluster.

---

## Prerequisites

- Azure CLI (version 2.40.0 or later)
- Kubernetes CLI (kubectl) installed and configured with the Azure AKS cluster
- Bash shell with OpenSSL for generating random suffixes

> **Note:** Please make sure you are logged into Azure and have set your subscription in advance.

---

## Step 1: Create a Resource Group

Create a new resource group to hold your AKS cluster.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export RESOURCE_GROUP_NAME="AKS-TF-ResourceGroup-$RANDOM_SUFFIX"
az group create --name $RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/AKS-TF-ResourceGroup-xxx",
    "location": "westus2",
    "managedBy": null,
    "name": "AKS-TF-ResourceGroup-xxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

---

## Step 2: Create an AKS Cluster

Provision an AKS cluster in the resource group.

```bash
export AKS_CLUSTER_NAME="AKS-TF-Cluster-$RANDOM_SUFFIX"
az aks create --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP_NAME --node-count 3 --enable-addons monitoring --generate-ssh-keys
```

---

## Step 3: Connect to the AKS Cluster

Obtain the cluster credentials and configure `kubectl` to use the newly created AKS cluster.

```bash
az aks get-credentials --name $AKS_CLUSTER_NAME --resource-group $RESOURCE_GROUP_NAME
```

Results:

<!-- expected_similarity=0.3 -->

```text
Merged "AKS-TF-Cluster-xxx" as current context in /home/username/.kube/config
```

---

## Step 4: Create a Kubernetes Namespace for TensorFlow

Create a namespace to organize resources related to TensorFlow.

```bash
export NAMESPACE="tensorflow-cluster"
kubectl create namespace $NAMESPACE
```

Results:

<!-- expected_similarity=0.3 -->

```text
namespace/tensorflow-cluster created
```

---

## Step 5: Prepare TensorFlow Deployment Configuration

Create the TensorFlow deployment configuration file.

```bash
cat <<EOF > tensorflow-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tensorflow-deployment
  namespace: $NAMESPACE
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tensorflow
  template:
    metadata:
      labels:
        app: tensorflow
    spec:
      containers:
      - name: tensorflow-container
        image: tensorflow/tensorflow:latest
        ports:
        - containerPort: 8501
EOF
```

---

## Step 6: Deploy the TensorFlow Cluster

Deploy the TensorFlow cluster by applying the configuration file.

```bash
kubectl apply -f tensorflow-deployment.yaml
```

Results:

<!-- expected_similarity=0.3 -->

```text
deployment.apps/tensorflow-deployment created
```

---

## Step 7: Create a LoadBalancer Service for TensorFlow

Expose the TensorFlow deployment using a LoadBalancer service to make it accessible externally.

```bash
cat <<EOF > tensorflow-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: tensorflow-service
  namespace: $NAMESPACE
spec:
  selector:
    app: tensorflow
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8501
  type: LoadBalancer
EOF

kubectl apply -f tensorflow-service.yaml
```

Results:

<!-- expected_similarity=0.3 -->

```text
service/tensorflow-service created
```

---

## Step 8: Check Service External IP

Retrieve the external IP address of the TensorFlow service.

```bash
while true; do
  ENDPOINTS=$(kubectl get endpoints tensorflow-service --namespace $NAMESPACE -o jsonpath='{.subsets[*].addresses[*].ip}')
  if [ -n "$ENDPOINTS" ]; then
    echo "Service endpoints: $ENDPOINTS"
    break
  else
    echo "Waiting for service endpoints..."
    sleep 10
  fi
done
```

Results:

<!-- expected_similarity=0.3 -->

```text
Service endpoints: 10.244.1.5 10.244.1.6
```

This confirms that the service is routing correctly to its backend pods.