---
title: 'Quickstart: Deploy an Azure Kubernetes Service (AKS) cluster and Apache Airflow using Azure CLI'
description: Learn how to quickly deploy a Kubernetes cluster and deploy Apache Airflow in Azure Kubernetes Service (AKS) using Azure CLI.
ms.topic: quickstart
ms.date: 04/09/2024
author: tamram
ms.author: tamram
ms.custom: H1Hack27Feb2017, mvc, devcenter, devx-track-azurecli, mode-api, innovation-engine, linux-related-content
#Customer intent: As a developer or cluster operator, I want to deploy an AKS cluster and deploy Apache Airflow, so I can see how to run applications using the managed Kubernetes service in Azure.
---

# Quickstart: Deploy an Azure Kubernetes Service (AKS) cluster and Apache Airflow using Azure CLI

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://go.microsoft.com/fwlink/?linkid=2262758)

Azure Kubernetes Service (AKS) is a managed Kubernetes service that lets you quickly deploy and manage clusters. In this quickstart, you learn how to:

- Deploy an AKS cluster using the Azure CLI.
- Deploy Apache Airflow to your AKS cluster.

> [!NOTE]
> To get started with quickly provisioning an AKS cluster, this article includes steps to deploy a cluster with default settings for evaluation purposes only. Before deploying a production-ready cluster, we recommend that you familiarize yourself with our [baseline reference architecture][baseline-reference-architecture] to consider how it aligns with your business requirements.

## Before you begin

This quickstart assumes a basic understanding of Kubernetes concepts. For more information, see [Kubernetes core concepts for Azure Kubernetes Service (AKS)][kubernetes-concepts].

- [!INCLUDE [quickstarts-free-trial-note](~/reusable-content/ce-skilling/azure/includes/quickstarts-free-trial-note.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- This article requires version 2.0.64 or later of the Azure CLI. If you're using Azure Cloud Shell, the latest version is already installed there.
- Make sure that the identity you're using to create your cluster has the appropriate minimum permissions. For more details on access and identity for AKS, see [Access and identity options for Azure Kubernetes Service (AKS)](../concepts-identity.md).
- If you have multiple Azure subscriptions, select the appropriate subscription ID in which the resources should be billed using the [az account set](/cli/azure/account#az-account-set) command. For more information, see [How to manage Azure subscriptions – Azure CLI](/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-subscription).

## Create a resource group

An [Azure resource group][azure-resource-group] is a logical group in which Azure resources are deployed and managed. When you create a resource group, you're prompted to specify a location. This location is the storage location of your resource group metadata and where your resources run in Azure if you don't specify another region during resource creation.

Create a resource group using the [`az group create`][az-group-create] command.

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myAKSResourceGroup$RANDOM_ID"
export REGION="eastus2"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:
<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/myAKSResourceGroupxxxxxx",
  "location": "eastus",
  "managedBy": null,
  "name": "testResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create an AKS cluster

Create an AKS cluster using the [`az aks create`][az-aks-create] command. The following example creates a cluster with one node and enables a system-assigned managed identity.

```azurecli-interactive
export MY_AKS_CLUSTER_NAME="myAKSCluster$RANDOM_ID"
az aks create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_AKS_CLUSTER_NAME \
    --node-count 1 \
    --generate-ssh-keys
```

Results:
<!-- expected_similarity=0.3 -->
```json
{
  "aadProfile": null,
  "addonProfiles": {
    "httpApplicationRouting": {
      "config": null,
      "enabled": false
    }
  },
  "agentPoolProfiles": [
    {
      "availabilityZones": null,
      "count": 1,
      "enableAutoScaling": false,
      "enableEncryptionAtHost": false,
      "enableFIPS": false,
      "enableNodePublicIP": false,
      "maxCount": null,
      "maxPods": 110,
      "minCount": null,
      "mode": "System",
      "name": "nodepool1",
      "nodeImageVersion": "AKSUbuntu-xxxx.x.x.x",
      "nodeLabels": null,
      "nodeTaints": null,
      "orchestratorVersion": "x.x.x",
      "osDiskSizeGb": 128,
      "osDiskType": "Managed",
      "osSku": "Ubuntu",
      "osType": "Linux",
      "provisioningState": "Succeeded",
      "scaleSetEvictionPolicy": null,
      "scaleSetPriority": "Regular",
      "spotMaxPrice": null,
      "tags": null,
      "type": "VirtualMachineScaleSets",
      "upgradeSettings": {
        "maxSurge": null
      },
      "vmSize": "Standard_DS2_v2",
      "vnetSubnetID": null
    }
  ],
  "apiServerAccessProfile": null,
  "autoScalerProfile": null,
  "autoUpgradeProfile": null,
  "azurePortalFQDN": "myAKSClusterxxxxxxxx-xxxxxxxx.hcp.eastus.azmk8s.io",
  "azurePortalURL": "https://myAKSClusterxxxxxxxx-xxxxxxxx.hcp.eastus.azmk8s.io",
  "dnsPrefix": "myAKSClusterxxxxxxxx",
  "enablePodSecurityPolicy": null,
  "enableRBAC": true,
  "extendedLocation": null,
  "fqdn": "myAKSClusterxxxxxxxx-xxxxxxxx.hcp.eastus.azmk8s.io",
  "fqdnSubdomain": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourcegroups/myResourceGroup/providers/Microsoft.ContainerService/managedClusters/myAKSClusterxxxxxxxx",
  "identity": null,
  "identityProfile": null,
  "kubernetesVersion": "x.x.x",
  "linuxProfile": {
    "adminUsername": "azureuser",
    "ssh": {
      "publicKeys": [
        {
          "keyData": "ssh-rsa xxxxxxxx...xxxxxx"
        }
      ]
    }
  },
  "location": "eastus",
  "maxAgentPools": 10,
  "name": "myAKSClusterxxxxxxxx",
  "networkProfile": {
    "dnsServiceIP": "10.0.0.10",
    "dockerBridgeCidr": "172.17.0.1/16",
    "loadBalancerProfile": {
      "allocatedOutboundPorts": null,
      "effectiveOutboundIPs": [
        {
          "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/MC_myResourceGroup_myAKSClusterxxxxxxxx_eastus/providers/Microsoft.Network/publicIPAddresses/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
          "resourceGroup": "MC_myResourceGroup_myAKSClusterxxxxxxxx_eastus"
        }
      ],
      "idleTimeoutInMinutes": null,
      "managedOutboundIPs": {
        "count": 1
      },
      "outboundIPPrefixes": null,
      "outboundIPs": null
    },
    "loadBalancerSku": "Standard",
    "networkMode": null,
    "networkPlugin": "kubenet",
    "networkPolicy": null,
    "outboundType": "loadBalancer",
    "podCidr": null,
    "serviceCidr": "10.0.0.0/16"
  },
  "nodeResourceGroup": "MC_myResourceGroup_myAKSClusterxxxxxxxx_eastus",
  "powerState": {
    "code": "Running"
  },
  "privateFQDN": null,
  "provisioningState": "Succeeded",
  "resourceGroup": "myResourceGroup",
  "servicePrincipalProfile": {
    "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "secret": null
  },
  "sku": {
    "name": "Basic",
    "tier": "Free"
  },
  "tags": null,
  "type": "Microsoft.ContainerService/ManagedClusters",
  "windowsProfile": null
}
```

> [!NOTE]
> When you create a new cluster, AKS automatically creates a second resource group to store the AKS resources. For more information, see [Why are two resource groups created with AKS?](../faq.md#why-are-two-resource-groups-created-with-aks)

## Connect to the cluster

To manage a Kubernetes cluster, use the Kubernetes command-line client, [kubectl][kubectl]. `kubectl` is already installed if you use Azure Cloud Shell. To install `kubectl` locally, use the [`az aks install-cli`][az-aks-install-cli] command.

1. Configure `kubectl` to connect to your Kubernetes cluster using the [az aks get-credentials][az-aks-get-credentials] command. This command downloads credentials and configures the Kubernetes CLI to use them.

    ```azurecli-interactive
    az aks get-credentials --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_AKS_CLUSTER_NAME
    ```

1. Verify the connection to your cluster using the [kubectl get][kubectl-get] command. This command returns a list of the cluster nodes.

    ```azurecli-interactive
    kubectl get nodes
    ```

## Deploy Apache Airflow

To deploy Apache Airflow to your AKS cluster, follow these steps:

1. **Add the Apache Airflow Helm repository**: Add the official Apache Airflow Helm repository.

    ```azurecli-interactive
    helm repo add apache-airflow https://airflow.apache.org
    helm repo update
    ```

2. **Install Apache Airflow**: Create a namespace for Airflow and install Airflow using Helm.

    ```azurecli-interactive
    kubectl create namespace airflow
    helm install airflow apache-airflow/airflow --namespace airflow
    ```

By following these steps, you will have Apache Airflow running on your AKS cluster.

## Test the Apache Airflow Deployment

You can validate that Apache Airflow is running by checking the status of the Airflow pods.

### **Check the Status of Airflow Pods**:
    ```bash
    #!/bin/bash

    NAMESPACE="airflow"
    POD_STATUS=$(kubectl get pods --namespace $NAMESPACE -o jsonpath='{.items[*].status.phase}')

    if [[ $POD_STATUS == *"Running"* ]]; then
        echo "All Airflow pods are running."
    else
        echo "Some Airflow pods are not running."
        exit 1
    fi
    ```

### Example Output

After running the script, you should see output similar to this:

```OUTPUT
All Airflow pods are running.
```

If any of the pods are not running, the script will output:

```OUTPUT
Some Airflow pods are not running.
```

## Delete the cluster

If you don't plan on going through the [AKS tutorial][aks-tutorial], clean up unnecessary resources to avoid Azure charges. You can remove the resource group, container service, and all related resources using the [`az group delete`][az-group-delete] command.

> [!NOTE]
> The AKS cluster was created with a system-assigned managed identity, which is the default identity option used in this quickstart. The platform manages this identity so you don't need to manually remove it.

## Next steps

In this quickstart, you deployed a Kubernetes cluster and then deployed a simple multi-container application to it. This sample application is for demo purposes only and doesn't represent all the best practices for Kubernetes applications. For guidance on creating full solutions with AKS for production, see [AKS solution guidance][aks-solution-guidance].

To learn more about AKS and walk through a complete code-to-deployment example, continue to the Kubernetes cluster tutorial.

> [!div class="nextstepaction"]
> [AKS tutorial][aks-tutorial]

<!-- LINKS - external -->
[kubectl]: https://kubernetes.io/docs/reference/kubectl/
[kubectl-apply]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#apply
[kubectl-get]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get

<!-- LINKS - internal -->
[kubernetes-concepts]: ../concepts-clusters-workloads.md
[aks-tutorial]: ../tutorial-kubernetes-prepare-app.md
[azure-resource-group]: /azure/azure-resource-manager/management/overview
[az-aks-create]: /cli/azure/aks#az-aks-create
[az-aks-get-credentials]: /cli/azure/aks#az-aks-get-credentials
[az-aks-install-cli]: /cli/azure/aks#az-aks-install-cli
[az-group-create]: /cli/azure/group#az-group-create
[az-group-delete]: /cli/azure/group#az-group-delete
[kubernetes-deployment]: ../concepts-clusters-workloads.md#deployments-and-yaml-manifests
[aks-solution-guidance]: /azure/architecture/reference-architectures/containers/aks-start-here?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json
[baseline-reference-architecture]: /azure/architecture/reference-architectures/containers/aks/baseline-aks?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json