---
title: Azure App Configuration extension for Azure Kubernetes Service
description: Install and configure Azure App Configuration extension on your Azure Kubernetes Service (AKS).
author: RichardChen820
ms.author: junbchen
ms.service: azure-kubernetes-service
ms.topic: concept-article
ms.date: 10/10/2024
ms.subservice: aks-developer
ms.custom: devx-track-azurecli, references_regions
---

# Install Azure App Configuration AKS extension

[Azure App Configuration](/azure/azure-app-configuration/overview) provides a service to centrally manage application settings and feature flags. [Azure App Configuration Kubernetes Provider](https://mcr.microsoft.com/en-us/product/azure-app-configuration/kubernetes-provider/about) is a Kubernetes operator that gets key-values, Key Vault references and feature flags from Azure App Configuration and builds them into Kubernetes ConfigMaps and Secrets. Azure App Configuration extension for Azure Kubernetes Service (AKS) allows you to install and manage Azure App Configuration Kubernetes Provider on your AKS cluster via Azure Resource Manager (ARM).

## Prerequisites 

- An Azure subscription. [Create a free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- The latest version of the [Azure CLI](/cli/azure/install-azure-cli).
- An Azure Kubernetes Service (AKS) cluster. [Create an AKS cluster](/azure/aks/tutorial-kubernetes-deploy-cluster#create-a-kubernetes-cluster).
- Permission with the [Azure Kubernetes Service RBAC Admin](/azure/role-based-access-control/built-in-roles#azure-kubernetes-service-rbac-admin) role.

### Set up the Azure CLI extension for cluster extensions

Install the `k8s-extension` Azure CLI extension by running the following commands:

```azurecli
az extension add --name k8s-extension
```

If the `k8s-extension` extension is already installed, you can update it to the latest version using the following command:

```azurecli
az extension update --name k8s-extension
```

### Register the `KubernetesConfiguration` resource provider

If you haven't previously used cluster extensions, you may need to register the resource provider with your subscription. You can check the status of the provider registration using the [az provider list](/cli/azure/provider#az-provider-list) command, as shown in the following example:

```azurecli
az provider list --query "[?namespace=='Microsoft.KubernetesConfiguration']" -o table
```

The *Microsoft.KubernetesConfiguration* provider should report as *Registered*, as shown in the following example output:

```output
Namespace                          RegistrationState    RegistrationPolicy
---------------------------------  -------------------  --------------------
Microsoft.KubernetesConfiguration  Registered           RegistrationRequired
```

If the provider shows as *NotRegistered*, register the provider using the [az provider register](/cli/azure/provider#az-provider-register) as shown in the following example:

```azurecli
az provider register --namespace Microsoft.KubernetesConfiguration
```

## Install the extension on your AKS cluster

Create the Azure App Configuration extension, which installs Azure App Configuration Kubernetes Provider on your AKS.

For example, install the latest version of Azure App Configuration Kubernetes Provider via the Azure App Configuration extension on your AKS cluster:

### [Azure CLI](#tab/cli)

```azurecli
az k8s-extension create --cluster-type managedClusters \
    --cluster-name myAKSCluster \
    --resource-group myResourceGroup \
    --name appconfigurationkubernetesprovider \
    --extension-type Microsoft.AppConfiguration
```

### [Bicep](#tab/bicep)

Create a Bicep template using the following example. 

```bicep
@description('The name of the Managed Cluster resource.')
param clusterName string

resource existingManagedCluster 'Microsoft.ContainerService/managedClusters@2024-02-01' existing = {
  name: clusterName
}

resource appConfigExtension 'Microsoft.KubernetesConfiguration/extensions@2022-11-01' = {
  name: 'appconfigurationkubernetesprovider'
  scope: existingManagedCluster
  properties: {
    autoUpgradeMinorVersion: true
    configurationSettings: {
      'global.clusterType': 'managedclusters'
    }
    extensionType: 'microsoft.appconfiguration'
  }
}
```

Deploy the Bicep template using the `az deployment group` command.

```azurecli
az deployment group create \
  --resource-group myResourceGroup \
  --template-file ./my-bicep-file-path.bicep \
  --parameters clusterName=myAKSCluster
```

---

### Configure automatic updates

If you create Azure App Configuration extension without specifying a version, `--auto-upgrade-minor-version` *is automatically enabled*, configuring the Azure App Configuration extension to automatically update its minor version on new releases.

You can disable auto update by specifying the `--auto-upgrade-minor-version` parameter and setting the value to `false`. 

#### [Azure CLI](#tab/cli)

```azurecli
--auto-upgrade-minor-version false
```

#### [Bicep](#tab/bicep)

```bicep
properties {
  autoUpgradeMinorVersion: false
}
```

---

### Targeting a specific version

The same command-line argument is used for installing a specific version of Azure App Configuration Kubernetes Provider or rolling back to a previous version. Set `--auto-upgrade-minor-version` to `false` and `--version` to the version of Azure App Configuration Kubernetes Provider you wish to install. If the `version` parameter is omitted, the extension installs the latest version.

#### [Azure CLI](#tab/cli)

```azurecli
az k8s-extension create --cluster-type managedClusters \
    --cluster-name myAKSCluster \
    --resource-group myResourceGroup \
    --name appconfigurationkubernetesprovider \
    --extension-type Microsoft.AppConfiguration \
    --auto-upgrade-minor-version false
    --version 2.1.0
```

#### [Bicep](#tab/bicep)

Create a Bicep template using the following example. 

```bicep
@description('The name of the Managed Cluster resource.')
param clusterName string

resource existingManagedCluster 'Microsoft.ContainerService/managedClusters@2024-02-01' existing = {
  name: clusterName
}

resource appConfigExtension 'Microsoft.KubernetesConfiguration/extensions@2022-11-01' = {
  name: 'appconfigurationkubernetesprovider'
  scope: existingManagedCluster
  properties: {
    autoUpgradeMinorVersion: false
    configurationSettings: {
      'global.clusterType': 'managedclusters'
    }
    extensionType: 'microsoft.appconfiguration'
    version: '2.1.0'
  }
}
```

Deploy the Bicep template using the `az deployment group` command.

```azurecli
az deployment group create \
  --resource-group myResourceGroup \
  --template-file ./my-bicep-file-path.bicep \
  --parameters clusterName=myAKSCluster
```

---

## Extension versions

The Azure App Configuration extension supports the following version of Azure App Configuration Kubernetes Provider:
- `2.1.0`
- `2.0.0`

## Troubleshoot extension installation errors

If the extension fails to create or update, try suggestions and solutions in the [Azure App Configuration extension troubleshooting guide](/troubleshoot/azure/azure-kubernetes/extensions/troubleshoot-app-configuration-extension-installation-errors).

## Troubleshoot Azure App Configuration Kubernetes Provider

Troubleshoot Azure App Configuration Kubernetes Provider errors via the [troubleshooting guide](/azure/azure-app-configuration/quickstart-azure-kubernetes-service#troubleshooting).

## Delete the extension

If you need to delete the extension and remove Azure App Configuration Kubernetes Provider from your AKS cluster, you can use the following command: 

```azurecli
az k8s-extension delete --resource-group myResourceGroup --cluster-name myAKSCluster --cluster-type managedClusters --name appconfigurationkubernetesprovider
```

## Next Steps

- Learn more about [extra settings and preferences you can set on the Azure App Configuration extension](./azure-app-configuration-settings.md).
- Once you successfully install Azure App Configuration extension in your AKS cluster, try [quickstart](/azure/azure-app-configuration/quickstart-azure-kubernetes-service) to learn how to use it.
- See all the supported features of [Azure App Configuration Kubernetes Provider](/azure/azure-app-configuration/reference-kubernetes-provider).
