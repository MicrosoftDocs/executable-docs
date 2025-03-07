---
title: Deploy a Highly Available PostgreSQL Database on AKS using CloudNativePG Operator
description: This Exec Doc demonstrates how to deploy a highly available PostgreSQL database on an Azure Kubernetes Service (AKS) cluster using the CloudNativePG operator. It covers creating the necessary Azure resources, installing the operator via Helm, and deploying a multi-instance PostgreSQL cluster.
ms.topic: quickstart
ms.date: 10/12/2023
author: yourgithubusername
ms.author: youralias
ms.custom: innovation-engine, akshighavailability, cloudnativepg
---

# Deploy a Highly Available PostgreSQL Database on AKS using CloudNativePG Operator

This document guides you through deploying a highly available PostgreSQL database on an AKS cluster using the CloudNativePG operator. You will create an Azure resource group and an AKS cluster with a random suffix for uniqueness, install the CloudNativePG operator using Helm, and then deploy a PostgreSQL cluster configured for high availability.

The following steps include environment variable declarations, Azure CLI commands, and Kubernetes commands executed via bash code blocks. Each code block includes an accompanying result block to verify that the commands execute with the expected output.

---

## Step 1: Create an Azure Resource Group

In this section, we declare environment variables for the deployment. The resource group name will have a random suffix appended to ensure uniqueness. We then create the resource group in the designated region (WestUS2).

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export RESOURCE_GROUP="cnpg-rg$RANDOM_SUFFIX"
az group create --name $RESOURCE_GROUP --location $REGION
```

Results: 

<!-- expected_similarity=0.3 --> 

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/cnpg-rgxxxxxxxxx",
  "location": "WestUS2",
  "name": "cnpg-rgxxxxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": {}
}
```

---

## Step 2: Create an AKS Cluster

Now we create an AKS cluster in the resource group. The cluster name is also appended with a random suffix. This cluster will have 3 nodes to support deployment of a highly available PostgreSQL database.

```bash
export AKS_CLUSTER="cnpg-aks$RANDOM_SUFFIX"
az aks create --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER --node-count 3 --enable-addons monitoring --generate-ssh-keys --location $REGION
```

Results: 

<!-- expected_similarity=0.3 --> 

```JSON
{
  "fqdn": "cnpg-aksxxxxxxxxx.hcp.westus2.azmk8s.io",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/cnpg-rgxxxxxxxxx/providers/Microsoft.ContainerService/managedClusters/cnpg-aksxxxxxxxxx",
  "location": "WestUS2",
  "name": "cnpg-aksxxxxxxxxx",
  "provisioningState": "Succeeded",
  "tags": {}
}
```

After creating the cluster, download its credentials so that kubectl can interact with it:

```bash
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER
```

Results:

<!-- expected_similarity=0.3 --> 

```console
Merged "cnpg-aksxxxxxxxxx" as current context in /home/xxxxx/.kube/config
```

---

## Step 3: Install the CloudNativePG Operator

The CloudNativePG operator is installed via Helm. This section adds the CloudNativePG Helm repository and deploys the operator into its own namespace (cnpg-system).

```bash
helm repo add cloudnative-pg https://cloudnative-pg.io/charts
helm repo update
helm install cnpg cloudnative-pg/cnpg --namespace cnpg-system --create-namespace
```

Results:

<!-- expected_similarity=0.3 --> 

```console
NAME: cnpg
LAST DEPLOYED: Wed Oct 11 2023 12:34:56 PM
NAMESPACE: cnpg-system
STATUS: deployed
REVISION: 1
```

---

## Step 4: Deploy a Highly Available PostgreSQL Cluster

In this step, you'll deploy a PostgreSQL cluster using CloudNativePG. The configuration specifies three instances to achieve high availability, and a minimal storage allocation is used for demonstration purposes.

First, create the PostgreSQL cluster manifest file named "ha-postgresql.yaml". This file should reside in the same folder as this Exec Doc.

```bash
cat << 'EOF' > ha-postgresql.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: ha-postgres
spec:
  instances: 3
  storage:
    size: 1Gi
  postgresVersion: 14
EOF
```

Results:

<!-- expected_similarity=0.3 --> 

```console
ha-postgresql.yaml created
```

Now, apply the YAML file to deploy the PostgreSQL cluster.

```bash
kubectl apply -f ha-postgresql.yaml
```

Results:

<!-- expected_similarity=0.3 --> 

```console
cluster.postgresql.cnpg.io/ha-postgres created
```

---

In this Exec Doc, you've created an Azure resource group and an AKS cluster, installed the CloudNativePG operator using Helm, and deployed a highly available PostgreSQL database on the cluster using a custom YAML manifest. This automated, one-click deployment is repeatable and ensures that the resources are unique for every run.