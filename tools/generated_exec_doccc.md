---
title: Highly Available Kubernetes Cluster with AKS, Application Gateway, Monitor, and Key Vault
description: This Exec Doc demonstrates how to deploy a highly available Azure Kubernetes Service (AKS) cluster integrated with Azure Application Gateway for Ingress, Azure Monitor for observability, and Azure Key Vault for managing secrets.
ms.topic: quickstart
ms.date: 10/11/2023
author: azureuser
ms.author: azurealias
ms.custom: innovation-engine, azurecli, kubernetes, monitoring
---

# Highly Available Kubernetes Cluster with AKS, Application Gateway, Monitor, and Key Vault

This Exec Doc walks you through the deployment of a highly available AKS cluster integrated with an Azure Application Gateway used for Ingress, Azure Monitor for observability, and Azure Key Vault for securely managing secrets. Each section includes code blocks with environment variable declarations and inline explanations that automate the cloud infrastructure deployment and help you learn as you go.

## Overview of the Deployment

In this workflow, we perform the following steps:

1. Create a resource group.
2. Create a dedicated virtual network and subnet for the Application Gateway.
3. Deploy an Azure Application Gateway.
4. Update the Application Gateway routing rule to assign an explicit priority.
5. Create an Azure Key Vault to manage secrets.
6. Retrieve the Application Gateway resource ID for integration.
7. Deploy an AKS cluster with:
   - Ingress add-on integration with the Application Gateway.
   - Monitoring add-on for Azure Monitor.
8. Enable the Azure Key Vault secrets provider add-on on the AKS cluster.

For all resources that require unique names, a randomly generated suffix is appended. Code blocks are of type "bash" ensuring that they are executable via Innovation Engine.

## Step 1: Create a Resource Group

We start by defining our environment variables and creating a resource group to contain all the resources used in this deployment.

```bash
export REGION="WestUS2"
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export RG_NAME="MyAKSResourceGroup$RANDOM_SUFFIX"
az group create --name $RG_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx",
  "location": "westus2",
  "managedBy": null,
  "name": "MyAKSResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 2: Create a Virtual Network for the Application Gateway

Next, we create a virtual network and a dedicated subnet for our Application Gateway. This isolation ensures that the Application Gateway is deployed within its own network segment.

```bash
export VNET_NAME="MyVnet$RANDOM_SUFFIX"
export SUBNET_NAME="AppGwSubnet"
az network vnet create --resource-group $RG_NAME --name $VNET_NAME --address-prefix 10.0.0.0/16 --subnet-name $SUBNET_NAME --subnet-prefix 10.0.1.0/24
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "newVNet": true,
  "subnets": [
    {
      "addressPrefix": "10.0.1.0/24",
      "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/virtualNetworks/MyVnetxxxxxx/subnets/AppGwSubnet",
      "name": "AppGwSubnet"
    }
  ]
}
```

## Step 3: Deploy the Azure Application Gateway

We deploy the Application Gateway using the Standard_V2 SKU for high availability and scalability. The default request routing rule "rule1" is automatically created but without a priority, which must be rectified for newer API versions.

```bash
export AAGW_NAME="MyAppGateway$RANDOM_SUFFIX"
az network application-gateway create --name $AAGW_NAME --resource-group $RG_NAME --location $REGION --sku Standard_V2 --capacity 2 --vnet-name $VNET_NAME --subnet $SUBNET_NAME --http-settings-port 80
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "applicationGateway": {
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx",
    "location": "westus2",
    "name": "MyAppGatewayxxxxxx",
    "provisioningState": "Succeeded",
    "sku": {
      "capacity": 2,
      "name": "Standard_V2"
    },
    "type": "Microsoft.Network/applicationGateways"
  }
}
```

## Step 4: Update the Application Gateway Routing Rule Priority

Instead of deleting and recreating the default rule, we update the existing request routing rule "rule1" to assign it an explicit priority. This addresses the error regarding an empty priority field required by API versions starting from 2021-08-01.

```bash
# Wait until the Application Gateway is fully provisioned.
az network application-gateway wait --name $AAGW_NAME --resource-group $RG_NAME --created

# Update the default request routing rule (rule1) with an explicit priority.
az network application-gateway rule update --resource-group $RG_NAME --gateway-name $AAGW_NAME --name rule1 --priority 1
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "name": "rule1",
  "priority": 1,
  "ruleType": "Basic",
  "httpListener": {
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx/httpListeners/appGatewayHttpListener"
  },
  "backendAddressPool": {
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx/backendAddressPools/BackendAddressPool_1"
  },
  "backendHttpSettings": {
    "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx/backendHttpSettingsCollection/appGatewayBackendHttpSettings"
  }
}
```

## Step 5: Create an Azure Key Vault

Create an Azure Key Vault to securely store and manage application secrets and certificates. The Key Vault integration with AKS allows your cluster to securely retrieve secrets when needed.

```bash
export KEYVAULT_NAME="myKeyVault$RANDOM_SUFFIX"
az keyvault create --name $KEYVAULT_NAME --resource-group $RG_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceVaults/myKeyVaultxxxxxx",
  "location": "westus2",
  "name": "myKeyVaultxxxxxx",
  "properties": {
    "sku": {
      "family": "A",
      "name": "standard"
    },
    "tenantId": "xxxxx-xxxxx-xxxxx-xxxxx",
    "accessPolicies": []
  },
  "type": "Microsoft.KeyVault/vaults"
}
```

## Step 6: Retrieve Application Gateway Resource ID

Before deploying the AKS cluster, retrieve the Application Gateway resource ID. This ID is required for integrating the Application Gateway Ingress add-on with AKS.

```bash
export AAGW_ID=$(az network application-gateway show --name $AAGW_NAME --resource-group $RG_NAME --query id -o tsv)
echo $AAGW_ID
```

Results:

<!-- expected_similarity=0.3 -->
```text
/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx
```

## Step 7: Deploy the AKS Cluster with Ingress and Monitoring Add-ons

Deploy the AKS cluster using three nodes. The cluster is integrated with the Application Gateway Ingress add-on using the Application Gateway resource ID obtained in the previous step. Additionally, the monitoring add-on is enabled for integration with Azure Monitor.

```bash
export AKS_CLUSTER_NAME="MyAKSCluster$RANDOM_SUFFIX"
az aks create --resource-group $RG_NAME --name $AKS_CLUSTER_NAME --node-count 3 --enable-addons ingress-appgw,monitoring --appgw-id $AAGW_ID --network-plugin azure --location $REGION --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "aadProfile": null,
  "addonProfiles": {
    "ingressApplicationGateway": {
      "config": {
        "appgwId": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx"
      },
      "enabled": true,
      "identity": {}
    },
    "omsagent": {
      "config": {
        "logAnalyticsWorkspaceResourceID": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourcegroups/MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus/providers/Microsoft.OperationalInsights/workspaces/MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus"
      },
      "enabled": true
    }
  },
  "dnsPrefix": "myaksclustercxxxxxx",
  "enableRBAC": true,
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourcegroups/MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus/providers/Microsoft.ContainerService/managedClusters/MyAKSClusterxxxxxx",
  "location": "westus2",
  "name": "MyAKSClusterxxxxxx",
  "provisioningState": "Succeeded",
  "resourceGroup": "MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus",
  "type": "Microsoft.ContainerService/managedClusters"
}
```

## Step 8: Enable Azure Key Vault Secrets Provider Add-on on AKS

Integrate the AKS cluster with Azure Key Vault by enabling the Azure Key Vault secrets provider add-on. This add-on securely mounts secrets stored in Azure Key Vault as volumes within your pods.

```bash
az aks enable-addons --addons azure-keyvault-secrets-provider --name $AKS_CLUSTER_NAME --resource-group $RG_NAME
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "addonProfiles": {
    "azureKeyvaultSecretsProvider": {
      "config": {},
      "enabled": true
    },
    "ingressApplicationGateway": {
      "config": {
        "appgwId": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyAKSResourceGroupxxxxxx/providers/Microsoft.Network/applicationGateways/MyAppGatewayxxxxxx"
      },
      "enabled": true
    },
    "omsagent": {
      "config": {
        "logAnalyticsWorkspaceResourceID": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourcegroups/MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus/providers/Microsoft.OperationalInsights/workspaces/MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus"
      },
      "enabled": true
    }
  },
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourcegroups/MC_MyAKSResourceGroupxxxxxx_myaksclustercxxxxxx_eastus/providers/Microsoft.ContainerService/managedClusters/MyAKSClusterxxxxxx",
  "name": "MyAKSClusterxxxxxx"
}
```

## Summary

In this Exec Doc, you deployed a highly available AKS cluster integrated with an Application Gateway used for Ingress, Azure Monitor for observability, and Azure Key Vault for secure secret management. A dedicated virtual network was created for the Application Gateway, and after the gateway was provisioned, the default Application Gateway routing rule was updated to include a defined priority—thereby addressing the API validation requirement. With clearly defined environment variables and inline explanations, you can now deploy this production-grade infrastructure using the Innovation Engine without encountering deployment errors.

Feel free to execute these commands step-by-step in your preferred Azure CLI environment.