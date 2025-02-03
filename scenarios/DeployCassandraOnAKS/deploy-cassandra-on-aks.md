---
title: "Deploy a Cassandra Cluster on AKS"
description: Learn how to deploy a Cassandra cluster on an Azure Kubernetes Service (AKS) cluster using Azure CLI and Kubernetes manifests.
ms.topic: tutorial
ms.date: 10/12/2023
author: execdocwriter
ms.author: execdocwriter
ms.custom: aks, cassandra, azurecli, kubernetes, innovation-engine
---

# Deploy a Cassandra Cluster on AKS

In this tutorial, you'll deploy an open-source Apache Cassandra cluster on Azure Kubernetes Service (AKS) and manage it using Kubernetes. This tutorial demonstrates creating an AKS cluster, deploying Cassandra, and verifying the deployment.

## Prerequisites

1. Install Azure CLI. You can follow [Install the Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) for instructions.
2. Install `kubectl`. You can use the `az aks install-cli` command to install it if you are using Azure Cloud Shell.

---

## Step 1: Create an AKS Cluster

Create an AKS cluster with a specified resource group.

```bash
export RANDOM_SUFFIX="$(openssl rand -hex 3)"
export REGION="westus2"
export MY_RESOURCE_GROUP_NAME="MyAKSResourceGroup$RANDOM_SUFFIX"

# Create a resource group in the specified region
az group create \
  --name $MY_RESOURCE_GROUP_NAME \
  --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
    "id": "/subscriptions/xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/CassandraClusterRGxxx",
    "location": "centralindia",
    "managedBy": null,
    "name": "CassandraClusterRGxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

```bash
export MY_AKS_CLUSTER_NAME="MyAKSCluster$RANDOM_SUFFIX"

# Create the AKS cluster
az aks create \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys
```

---

## Step 2: Connect to the AKS Cluster

Retrieve the AKS cluster credentials and configure `kubectl`.

```bash
az aks get-credentials \
  --resource-group $MY_RESOURCE_GROUP_NAME \
  --name $MY_AKS_CLUSTER_NAME
```

After running the command, your `kubectl` context will be set to the newly created AKS cluster. Verify the connection:

```bash
kubectl get nodes
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME                                STATUS   ROLES   AGE     VERSION
aks-nodepool1-xxxxx-vmss000000      Ready    agent   3m56s   v1.26.0
aks-nodepool1-xxxxx-vmss000001      Ready    agent   3m52s   v1.26.0
aks-nodepool1-xxxxx-vmss000002      Ready    agent   3m48s   v1.26.0
```

---

## Step 3: Deploy the Cassandra Cluster

Create a Kubernetes manifest file in Cloud Shell to define the Cassandra deployment. Use a name like `cassandra-deployment.yaml`.

```bash
cat <<EOF > cassandra-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cassandra
spec:
  selector:
    matchLabels:
      app: cassandra
  serviceName: "cassandra"
  replicas: 3
  template:
    metadata:
      labels:
        app: cassandra
    spec:
      containers:
      - name: cassandra
        image: cassandra:latest
        ports:
        - containerPort: 9042
          name: cql
        volumeMounts:
        - mountPath: /var/lib/cassandra
          name: cassandra-data
      volumes:
      - name: cassandra-data
EOF

# Apply the manifest to the cluster
kubectl apply -f cassandra-deployment.yaml
```

Results:

<!-- expected_similarity=0.3 -->

```text
statefulset.apps/cassandra created
```

---

## Step 4: Create a Headless Service for Cassandra

Create a Kubernetes manifest file in Cloud Shell to define the Cassandra headless service. Use a name like `cassandra-service.yaml`.

```bash
cat <<EOF > cassandra-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: cassandra
  namespace: default
spec:
  clusterIP: None
  selector:
    app: cassandra
  ports:
  - name: cql
    port: 9042
    targetPort: 9042
EOF

# Apply the service manifest to the cluster
kubectl apply -f cassandra-service.yaml
```


## Step 4: Verify Cassandra Deployment

Check the status of the Cassandra pods to ensure deployment is successful.

```bash
while true; do
  POD_STATUSES=$(kubectl get pods -l app=cassandra -o jsonpath='{.items[*].status.phase}')
  ALL_RUNNING=true
  for STATUS in $POD_STATUSES; do
    if [ "$STATUS" != "Running" ]; then
      ALL_RUNNING=false
      break
    fi
  done

  if [ "$ALL_RUNNING" = true ]; then
    kubectl get pods -l app=cassandra
    break
  else
    sleep 10
  fi
done
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME           READY   STATUS    RESTARTS   AGE
cassandra-0    1/1     Running   0          3m
cassandra-1    1/1     Running   0          2m
cassandra-2    1/1     Running   0          1m
```

Verify the Cassandra StatefulSet.

```bash
kubectl get statefulset cassandra
```

Results:

<!-- expected_similarity=0.3 -->

```text
NAME         READY   AGE
cassandra    3/3     3m
```

---

## Step 5: Access Cassandra Cluster

Create a temporary Pod to access the Cassandra cluster using `cqlsh`, the Cassandra query tool.

```bash
kubectl run cassandra-client --rm -it --image=cassandra:latest -- /bin/bash
```

Once you are inside the Pod, connect to the Cassandra cluster using `cqlsh`.

```bash
# Within the Pod, run:
cqlsh cassandra-0.cassandra
```

You should now be connected to the Cassandra database.

> **Note:** When you're done testing, exit the shell and delete the Pod automatically.

Results:

<!-- expected_similarity=0.3 -->

```text
Connected to Test Cluster at cassandra-0.cassandra:9042.
[cqlsh 5.0.1 | Cassandra 4.0.0 | CQL spec 3.4.0 | Native protocol v4]
Use HELP for help.
```

---

This tutorial deployed an Apache Cassandra cluster on AKS. You managed the cluster using Kubernetes manifests and verified its deployment.

> **IMPORTANT:** Do not forget to clean up unnecessary resources like the AKS cluster if you no longer need them.