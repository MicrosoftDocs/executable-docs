---
title: Explanation: AKS Cluster Creation Script
description: This Exec Doc explains a shell script that creates an AKS cluster using Azure CLI. The document walks you through each functional block to help you understand the purpose of the script and how each section contributes to the overall process.
ms.topic: article
ms.date: 2023-10-12
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, ms-learn, azure, cluster-creation
---

# Explanation: AKS Cluster Creation Script

In this Exec Doc, we examine a shell script that automates the process of creating an Azure Kubernetes Service (AKS) cluster. The script covers several key tasks: setting safe execution options, defining configuration variables, creating a resource group, deploying the AKS cluster, retrieving credentials, and finally verifying the cluster connectivity. Read on to understand the purpose and function of each block.

---

## Script Header and Safety Settings

Below the shebang line, the script uses `set -e` to ensure that the script exits immediately upon encountering any error. This helps prevent cascading failures during the deployment process.

```bash
#!/bin/bash
# This script creates an AKS cluster using Azure CLI

# Exit on error
set -e
```

The above code ensures that any failure in subsequent commands stops the script, thereby protecting against unintended side effects.

---

## Configuration Variables

This section defines the necessary configuration variables for the deployment. These variables include the resource group name, location, cluster name, node count, node VM size, and the Kubernetes version. The comments also guide you on how to check for available Kubernetes versions using the Azure CLI.

```bash
# Configuration variables
RESOURCE_GROUP="myAKSResourceGroup"
LOCATION="eastus"
CLUSTER_NAME="myAKSCluster"
NODE_COUNT=3
NODE_VM_SIZE="Standard_DS2_v2"
KUBERNETES_VERSION="1.26.3"  # Check available versions with: az aks get-versions --location $LOCATION --output table
```

Each variable is critical for the subsequent commands that create and configure the AKS cluster. Note that these values are hardcoded; changing them will adjust the deployment accordingly.

---

## (Optional) Azure Login Comment

The script includes a commented-out Azure login command. This serves as a reminder to log in if you aren’t already authenticated. Since the Exec Doc guidelines do not allow login commands, the line remains commented out.

```bash
# Login to Azure (uncomment if not already logged in)
# az login
```

This block is informational and does not affect the execution when the script is run in a pre-authenticated session.

---

## Creating the Resource Group

Before deploying the AKS cluster, the script creates a resource group in the specified location. This resource group will contain all the resources associated with the AKS cluster.

```bash
# Create resource group
echo "Creating resource group $RESOURCE_GROUP in $LOCATION..."
az group create --name $RESOURCE_GROUP --location $LOCATION
```

The echo statement provides user feedback, while the `az group create` command creates the resource group if it does not already exist.

---

## Deploying the AKS Cluster

The next functional block involves the creation of the AKS cluster. The script uses several parameters to customize the deployment, such as node count, VM size, Kubernetes version, SSH key generation, managed identity, and autoscaling settings.

```bash
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
```

This block deploys the AKS cluster with the defined specifications. It also enables cluster autoscaling between 1 and 5 nodes to adapt to workload demands.

---

## Retrieving Cluster Credentials

Once the AKS cluster is deployed, the script retrieves the cluster's credentials. This allows you to manage the Kubernetes cluster using the `kubectl` command-line tool.

```bash
# Get credentials for the Kubernetes cluster
echo "Getting credentials for cluster $CLUSTER_NAME..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME
```

The credentials command updates your local kubeconfig file, enabling seamless interaction with your cluster.

---

## Final Confirmation and Cluster Verification

After the credentials are fetched, the script prints success messages and then verifies the cluster connection by listing the cluster nodes using `kubectl`.

```bash
echo "AKS cluster $CLUSTER_NAME has been created successfully!"
echo "You can now use kubectl to manage your cluster"

# Verify connection to the cluster
echo "Verifying connection to the cluster..."
kubectl get nodes
```

This verification confirms that the cluster is operational and that the kubectl context is correctly set up.

Results: 

<!-- expected_similarity=0.3 -->

```console
NAME                                STATUS   ROLES   AGE   VERSION
aks-nodepool1-abcdef12-vmss000000     Ready    agent   5m    v1.26.3
```

The above result block illustrates a typical output from `kubectl get nodes`, indicating that at least one node in the AKS cluster is ready and connected.

---

This Exec Doc provides a short and sweet explanation of every major functional block in the AKS cluster creation script. By following the annotated steps, you gain a clearer understanding of how cloud resources are provisioned in a streamlined, automated manner.