---
title: 'Deploy ClickHouse Cluster on AKS'
description: Learn how to deploy a ClickHouse Cluster on Azure Kubernetes Service (AKS) using Azure CLI and Kubernetes manifests.
ms.topic: quickstart
ms.date: 10/05/2023
author: azure-execdocwriter
ms.author: azureexecdocwriter
ms.custom: devx-track-azurecli, mode-api, innovation-engine, aks-related-content
---

# Deploy ClickHouse Cluster on AKS

This Exec Doc demonstrates how to deploy a ClickHouse Cluster on Azure Kubernetes Service (AKS). ClickHouse is an open-source column-oriented database management system. By following this guide, you'll create an AKS cluster, deploy a ClickHouse cluster on it using a Kubernetes manifest, and verify the deployment.

## Prerequisites

Ensure that you have the following:

1. An Azure subscription.
2. The Azure CLI installed (v2.30.0 or later). 
3. Access to `kubectl` CLI to manage your Kubernetes cluster.
4. Azure CLI extensions enabled for AKS (`az extension add --name aks`).

---

## Step 1: Create a Resource Group

Create a new Azure resource group to contain all resources related to the deployment.

```bash
export RANDOM_SUFFIX="$(openssl rand -hex 3)"
export REGION="westus2"
export MY_RESOURCE_GROUP="MyAKSResourceGroup$RANDOM_SUFFIX"
az group create --name $MY_RESOURCE_GROUP --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxx",
    "location": "centralindia",
    "managedBy": null,
    "name": "MyAKSResourceGroupxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

---

## Step 2: Create an AKS Cluster

Create an Azure Kubernetes Service (AKS) cluster in the resource group.

```bash
export MY_AKS_CLUSTER="MyAKSCluster$RANDOM_SUFFIX"
az aks create --resource-group $MY_RESOURCE_GROUP --name $MY_AKS_CLUSTER --node-count 3 --generate-ssh-keys
```

---

## Step 3: Connect to the AKS Cluster

Obtain the Kubernetes credentials to connect to your AKS cluster.

```bash
az aks get-credentials --resource-group $MY_RESOURCE_GROUP --name $MY_AKS_CLUSTER
```

Results:

<!-- expected_similarity=0.3 -->

```text
Merged "MyAKSClusterxxx" as current context in /home/user/.kube/config
```

---

## Step 4: Create a Namespace for ClickHouse

Create a Kubernetes namespace to host the ClickHouse deployment.

```bash
kubectl create namespace clickhouse
```

Results:

<!-- expected_similarity=0.3 -->

```text
namespace/clickhouse created
```

---

## Step 5: Deploy ClickHouse on AKS

Use the following Kubernetes manifest to deploy ClickHouse. Save this manifest into a file named **clickhouse-deployment.yaml**.

```bash
cat <<EOF > clickhouse-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: clickhouse
  namespace: clickhouse
spec:
  serviceName: "clickhouse"
  replicas: 3
  selector:
    matchLabels:
      app: clickhouse
  template:
    metadata:
      labels:
        app: clickhouse
    spec:
      containers:
      - name: clickhouse
        image: yandex/clickhouse-server:latest
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
        ports:
        - containerPort: 8123
          name: http
        - containerPort: 9000
          name: native
        volumeMounts:
        - name: clickhouse-data
          mountPath: /var/lib/clickhouse
  volumeClaimTemplates:
  - metadata:
      name: clickhouse-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
EOF
```

Apply the configuration to deploy ClickHouse.

```bash
kubectl apply -f clickhouse-deployment.yaml
```

Results:

<!-- expected_similarity=0.3 -->

```text
statefulset.apps/clickhouse created
persistentvolumeclaim/clickhouse-pvc created
```

---

## Step 6: Verify the Deployment

Check if the ClickHouse pods are running correctly:

```bash
while true; do
  POD_STATUSES=$(kubectl get pods -n clickhouse -o jsonpath='{.items[*].status.phase}')
  ALL_RUNNING=true
  for STATUS in $POD_STATUSES; do
    if [ "$STATUS" != "Running" ]; then
      ALL_RUNNING=false
      break
    fi
  done

  if [ "$ALL_RUNNING" = true ]; then
    kubectl get pods -n clickhouse
    break
  else
    sleep 10
  fi
done
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME                READY   STATUS    RESTARTS   AGE
clickhouse-0        1/1     Running   0          2m
clickhouse-1        1/1     Running   0          2m
clickhouse-2        1/1     Running   0          2m
```

---

## Summary

You have successfully deployed a ClickHouse cluster on AKS. You can now connect to the ClickHouse service using the appropriate service endpoint or Kubernetes port forwarding.