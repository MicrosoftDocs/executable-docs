---
title: Create a network isolated AKS cluster
titleSuffix: Azure Kubernetes Service
description: Learn how to configure an Azure Kubernetes Service (AKS) cluster with outbound and inbound network restrictions.
ms.subservice: aks-networking
author: shashankbarsin
ms.author: shasb
ms.topic: how-to
ms.date: 04/24/2025
zone_pivot_groups: network-isolated-acr-type
---

# Create a network isolated Azure Kubernetes Service (AKS) cluster 

Organizations typically have strict security and compliance requirements to regulate egress (outbound) network traffic from a cluster to eliminate risks of data exfiltration. By default, standard SKU Azure Kubernetes Service (AKS) clusters have unrestricted outbound internet access. This level of network access allows nodes and services you run to access external resources as needed. If you wish to restrict egress traffic, a limited number of ports and addresses must be accessible to maintain healthy cluster maintenance tasks. The conceptual document on [outbound network and FQDN rules for AKS clusters][outbound-rules] provides a list of required endpoints for the AKS cluster and its optional add-ons and features.

One common solution to restricting outbound traffic from the cluster is to use a [firewall device][aks-firewall] to restrict traffic based on firewall rules. Firewall is applicable when your application requires outbound access, but when outbound requests have to be inspected and secured. Configuring a firewall manually with required egress rules and *FQDNs* is a cumbersome process especially if your only requirement is to create an isolated AKS cluster with no outbound dependencies for the cluster bootstrapping.

To reduce risk of data exfiltration, network isolated cluster allows for bootstrapping the AKS cluster without any outbound network dependencies, even for fetching cluster components/images from Microsoft Artifact Registry (MAR). The cluster operator could incrementally set up allowed outbound traffic for each scenario they want to enable. This article walks you through the steps of creating a network isolated cluster.


## Before you begin

- Read the [conceptual overview of this feature][conceptual-network-isolated], which provides an explanation of how network isolated clusters work. The overview article also:
  - Explains two options for private Azure Container Registry (ACR) resource used for cluster bootstrapping - AKS-managed ACR or bring-your-own ACR.
  - Explains two private cluster modes for creating private access to API server - [private link-based][private-clusters] or [API Server Vnet Integration][api-server-vnet-integration].
  - Explains the two outbound types for cluster egress control - `none` or `block` (preview).
  - Describes the [current limitations of network isolated clusters][conceptual-network-isolated-limitations].

> [!NOTE]
> Outbound type `none` is generally available.
> Outbound type`block` is in preview.

[!INCLUDE [preview features callout](~/reusable-content/ce-skilling/azure/includes/aks/includes/preview/preview-callout.md)]

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]
 - This article requires version 2.71.0 or later of the Azure CLI. If you're using Azure Cloud Shell, the latest version is already installed there.
 - You should install the `aks-preview` Azure CLI extension version *9.0.0b2* or later if you are using outbound type `block` (preview).
    - If you don't already have the `aks-preview` extension, install it using the [`az extension add`][az-extension-add] command.
        ```azurecli-interactive
        az extension add --name aks-preview
        ```
    - If you already have the `aks-preview` extension, update it to make sure you have the latest version using the [`az extension update`][az-extension-update] command.
        ```azurecli-interactive
        az extension update --name aks-preview
       ```
- Network isolated clusters are supported on AKS clusters using Kubernetes version 1.30 or higher.
- If you're choosing to use the Bring your own (BYO) Azure Container Registry (ACR) option, you need to ensure the ACR is [Premium SKU service tier][container-registry-skus].
- If you are using a network isolated cluster configured with API Server VNet Integration, you should follow the prerequisites and guidance in this [document][api-server-vnet-integration].

::: zone pivot="aks-managed-acr"

## Deploy a network isolated cluster with AKS-managed ACR

AKS creates, manages, and reconciles an ACR resource in this option. You don't need to assign any permissions or manage the ACR. AKS manages the cache rules, private link, and private endpoint used in the network isolated cluster.

### Create a network isolated cluster

When creating a network isolated AKS cluster, you can choose one of the following private cluster modes - private link-based or API Server Vnet Integration.

Regardless of the mode you select, you should set `--bootstrap-artifact-source` and  `--outbound-type` parameters.

The `--bootstrap-artifact-source` can be set to either `Direct` or `Cache` corresponding to using direct MAR (NOT network isolated) and private ACR (network isolated) for image pulls respectively.

The `--outbound-type parameter` can be set to either `none` or `block` (preview). If the outbound type is set to `none`, then AKS doesn't set up any outbound connections for the cluster, allowing the user to configure them on their own. If the outbound type is set to `block`, then all outbound connections are blocked.

#### Private link-based

Create a private link-based network isolated cluster by running the [az aks create][az-aks-create] command with `--bootstrap-artifact-source`, `--enable-private-cluster`, and `--outbound-type` parameters.

```azurecli-interactive
az aks create --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME}   --kubernetes-version 1.30.3 --bootstrap-artifact-source Cache --outbound-type none  --network-plugin azure --enable-private-cluster
```

#### API Server VNet integration

Create a network isolated cluster configured with API Server VNet Integration by running the [az aks create][az-aks-create] command with `--bootstrap-artifact-source`, `--enable-private-cluster`, `--enable-apiserver-vnet-integration` and `--outbound-type` parameters.

```azurecli
az aks create --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --kubernetes-version 1.30.3 --bootstrap-artifact-source Cache --outbound-type none --network-plugin azure --enable-private-cluster --enable-apiserver-vnet-integration
```

### Update an existing AKS cluster to network isolated type

If you'd rather enable network isolation on an existing AKS cluster instead of creating a new cluster, use the [az aks update][az-aks-update] command.

```azurecli-interactive
az aks update --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --bootstrap-artifact-source Cache --outbound-type none
```

After the feature is enabled, any newly added node can bootstrap successfully without egress. When you enable network isolation on an existing cluster, keep in mind that you need to manually reimage all existing node pools.

```azurecli-interactive
az aks upgrade --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --node-image-only
```

>[!IMPORTANT]
> Remember to reimage the cluster's node pools after you enable the network isolation mode for an existing cluster. Otherwise, the feature won't take effect for the cluster.

::: zone-end

::: zone pivot="byo-acr"

## Deploy a network isolated cluster with bring your own ACR

AKS supports bringing your own (BYO) ACR. To support the BYO ACR scenario, you have to configure an ACR private endpoint and a private DNS zone before you create the AKS cluster.

The following steps show how to prepare these resources:

* Custom virtual network and subnets for AKS and ACR.
* ACR, ACR cache rule, private endpoint, and private DNS zone.
* Custom control plane identity and kubelet identity.


### Step 1: Create the virtual network and subnets

```shell
az group create --name ${RESOURCE_GROUP} --location ${LOCATION}

az network vnet create  --resource-group ${RESOURCE_GROUP} --name ${VNET_NAME} --address-prefixes 192.168.0.0/16

az network vnet subnet create --name ${AKS_SUBNET_NAME} --vnet-name ${VNET_NAME} --resource-group ${RESOURCE_GROUP} --address-prefixes 192.168.1.0/24 

SUBNET_ID=$(az network vnet subnet show --name ${AKS_SUBNET_NAME} --vnet-name ${VNET_NAME} --resource-group ${RESOURCE_GROUP} --query 'id' --output tsv)

az network vnet subnet create --name ${ACR_SUBNET_NAME} --vnet-name ${VNET_NAME} --resource-group ${RESOURCE_GROUP} --address-prefixes 192.168.2.0/24 --private-endpoint-network-policies Disabled
```

### Step 2: Disable virtual network outbound connectivity (Optional)

There are multiple ways to [disable the virtual network outbound connectivity][vnet-disable-outbound-access].

### Step 3: Create the ACR and enable artifact cache

1. Create the ACR with the private link.

    ```shell
    az acr create --resource-group ${RESOURCE_GROUP} --name ${REGISTRY_NAME} --sku Premium --public-network-enabled false

    REGISTRY_ID=$(az acr show --name ${REGISTRY_NAME} -g ${RESOURCE_GROUP}  --query 'id' --output tsv)
    ```

2. Create an ACR cache rule following the below command to allow users to cache MAR container images and binaries in the new ACR, note the cache rule name and repo names must be strictly aligned with the guidance below.

    ```shell
    az acr cache create -n aks-managed-mcr -r ${REGISTRY_NAME} -g ${RESOURCE_GROUP} --source-repo "mcr.microsoft.com/*" --target-repo "aks-managed-repository/*"
    ```
> [!NOTE]
> With BYO ACR, it is your responsibility to ensure the ACR cache rule is created and maintained correctly as above. This step is critical to cluster creation, functioning and upgrading. This cache rule should NOT be modified.
    

### Step 4: Create a private endpoint for the ACR

```shell
az network private-endpoint create --name myPrivateEndpoint --resource-group ${RESOURCE_GROUP} --vnet-name ${VNET_NAME} --subnet ${ACR_SUBNET_NAME} --private-connection-resource-id ${REGISTRY_ID} --group-id registry --connection-name myConnection

NETWORK_INTERFACE_ID=$(az network private-endpoint show --name myPrivateEndpoint --resource-group ${RESOURCE_GROUP} --query 'networkInterfaces[0].id' --output tsv)

REGISTRY_PRIVATE_IP=$(az network nic show --ids ${NETWORK_INTERFACE_ID} --query "ipConfigurations[?privateLinkConnectionProperties.requiredMemberName=='registry'].privateIPAddress" --output tsv)

DATA_ENDPOINT_PRIVATE_IP=$(az network nic show --ids ${NETWORK_INTERFACE_ID} --query "ipConfigurations[?privateLinkConnectionProperties.requiredMemberName=='registry_data_$LOCATION'].privateIPAddress" --output tsv)
```

### Step 5: Create a private DNS zone and add records

Create a private DNS zone named `privatelink.azurecr.io`. Add the records for the registry REST endpoint `{REGISTRY_NAME}.azurecr.io`, and the registry data endpoint `{REGISTRY_NAME}.{REGISTRY_LOCATION}.data.azurecr.io`.

```shell
az network private-dns zone create --resource-group ${RESOURCE_GROUP} --name "privatelink.azurecr.io"

az network private-dns link vnet create --resource-group ${RESOURCE_GROUP} --zone-name "privatelink.azurecr.io" --name MyDNSLink --virtual-network ${VNET_NAME} --registration-enabled false

az network private-dns record-set a create --name ${REGISTRY_NAME} --zone-name "privatelink.azurecr.io" --resource-group ${RESOURCE_GROUP}

az network private-dns record-set a add-record --record-set-name ${REGISTRY_NAME} --zone-name "privatelink.azurecr.io" --resource-group ${RESOURCE_GROUP} --ipv4-address ${REGISTRY_PRIVATE_IP}

az network private-dns record-set a create --name ${REGISTRY_NAME}.${LOCATION}.data --zone-name "privatelink.azurecr.io" --resource-group ${RESOURCE_GROUP}

az network private-dns record-set a add-record --record-set-name ${REGISTRY_NAME}.${LOCATION}.data --zone-name "privatelink.azurecr.io" --resource-group ${RESOURCE_GROUP} --ipv4-address ${DATA_ENDPOINT_PRIVATE_IP}
```

### Step 6: Create control plane and kubelet identities

#### Control plane identity

```shell
az identity create --name ${CLUSTER_IDENTITY_NAME} --resource-group ${RESOURCE_GROUP}

CLUSTER_IDENTITY_RESOURCE_ID=$(az identity show --name ${CLUSTER_IDENTITY_NAME} --resource-group ${RESOURCE_GROUP} --query 'id' -o tsv)

CLUSTER_IDENTITY_PRINCIPAL_ID=$(az identity show --name ${CLUSTER_IDENTITY_NAME} --resource-group ${RESOURCE_GROUP} --query 'principalId' -o tsv)
```

#### Kubelet identity

```shell
az identity create --name ${KUBELET_IDENTITY_NAME} --resource-group ${RESOURCE_GROUP}

KUBELET_IDENTITY_RESOURCE_ID=$(az identity show --name ${KUBELET_IDENTITY_NAME} --resource-group ${RESOURCE_GROUP} --query 'id' -o tsv)

KUBELET_IDENTITY_PRINCIPAL_ID=$(az identity show --name ${KUBELET_IDENTITY_NAME} --resource-group ${RESOURCE_GROUP} --query 'principalId' -o tsv)
```

#### Grant AcrPull permissions for the Kubelet identity

```shell
az role assignment create --role AcrPull --scope ${REGISTRY_ID} --assignee-object-id ${KUBELET_IDENTITY_PRINCIPAL_ID} --assignee-principal-type ServicePrincipal
```

After you configure these resources, you can proceed to create the network isolated AKS cluster with BYO ACR.

### Step 7: Create network isolated cluster using BYO ACR

When creating a network isolated cluster, you can choose one of the following private cluster modes - private link-based or API Server Vnet Integration.

Regardless of the mode you select, you should set `--bootstrap-artifact-source` and  `--outbound-type` parameters.

The `--bootstrap-artifact-source` can be set to either `Direct` or `Cache` corresponding to using direct Microsoft Artifact Registry (MAR) (NOT network isolated) and private ACR (network isolated) for image pulls respectively.

The `--outbound-type parameter` can be set to either `none` or `block` (preview). If the outbound type is set to `none`, then AKS doesn't set up any outbound connections for the cluster, allowing the user to configure them on their own. If the outbound type is set to `block`, then all outbound connections are blocked.

#### Private link-based

Create a private link-based network isolated cluster that accesses your ACR by running the [az aks create][az-aks-create] command with the required parameters.

```shell
az aks create --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --kubernetes-version 1.30.3 --vnet-subnet-id ${SUBNET_ID} --assign-identity ${CLUSTER_IDENTITY_RESOURCE_ID} --assign-kubelet-identity ${KUBELET_IDENTITY_RESOURCE_ID} --bootstrap-artifact-source Cache --bootstrap-container-registry-resource-id ${REGISTRY_ID} --outbound-type none --network-plugin azure --enable-private-cluster
```

#### API Server VNet integration

For a network isolated cluster configured with API server VNet integration, first create a subnet and assign the correct role with the following commands:

```shell
az network vnet subnet create --name ${APISERVER_SUBNET_NAME} --vnet-name ${VNET_NAME} --resource-group ${RESOURCE_GROUP} --address-prefixes 192.168.3.0/24

export APISERVER_SUBNET_ID=$(az network vnet subnet show --resource-group ${RESOURCE_GROUP} --vnet-name ${VNET_NAME} --name ${APISERVER_SUBNET_NAME} --query id -o tsv)
```

```shell
az role assignment create --scope ${APISERVER_SUBNET_ID} --role "Network Contributor" --assignee-object-id ${CLUSTER_IDENTITY_PRINCIPAL_ID} --assignee-principal-type ServicePrincipal
```

Create a network isolated cluster configured with API Server VNet Integration and access your ACR by running the [az aks create][az-aks-create] command with the required parameters.

```shell
az aks create --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --kubernetes-version 1.30.3 --vnet-subnet-id ${SUBNET_ID} --assign-identity ${CLUSTER_IDENTITY_RESOURCE_ID} --assign-kubelet-identity ${KUBELET_IDENTITY_RESOURCE_ID} --bootstrap-artifact-source Cache --bootstrap-container-registry-resource-id ${REGISTRY_ID} --outbound-type none --network-plugin azure --enable-apiserver-vnet-integration --apiserver-subnet-id ${APISERVER_SUBNET_ID}
```

### Update an existing AKS cluster

If you'd rather enable network isolation on an existing AKS cluster instead of creating a new cluster, use the [az aks update][az-aks-update] command.

When creating the private endpoint and private DNS zone for the BYO ACR, use the existing virtual network and subnets of the existing AKS cluster. When you assign the **AcrPull** permission to the kubelet identity, use the existing kubelet identity of the existing AKS cluster.

To enable the network isolated feature on an existing AKS cluster, use the following command:

```shell
az aks update --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --bootstrap-artifact-source Cache --bootstrap-container-registry-resource-id ${REGISTRY_ID} --outbound-type none
```

After the network isolated cluster feature is enabled, nodes in the newly added node pool can bootstrap successfully without egress. You must reimage existing node pools so that newly scaled node can bootstrap successfully. When you enable the feature on an existing cluster, you need to manually reimage all existing node pools.

```shell
az aks upgrade --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --node-image-only
```

>[!IMPORTANT]
> Remember to reimage the cluster's node pools after you enable the network isolated cluster feature. Otherwise, the feature won't take effect for the cluster.


### Update your ACR ID

It's possible to update the private ACR used with a network isolated cluster. To identify the ACR resource ID, use the `az aks show` command.

```shell
az aks show --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME}
```

Updating the ACR ID is performed by running the `az aks update` command with the `--bootstrap-artifact-source` and `--bootstrap-container-registry-resource-id` parameters.

```shell
az aks update --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --bootstrap-artifact-source Cache --bootstrap-container-registry-resource-id <New BYO ACR resource ID>
```

When you update the ACR ID on an existing cluster, you need to manually reimage all existing nodes.

```shell
az aks upgrade --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --node-image-only
```

>[!IMPORTANT]
> Remember to reimage the cluster's node pools after you enable the network isolated cluster feature. Otherwise, the feature won't take effect for the cluster.

::: zone-end

## Validate that network isolated cluster is enabled

To validate the network isolated cluster feature is enabled, use the `[az aks show][az-aks-show] command

```azurecli-interactive
az aks show --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME}
```

The following output shows that the feature is enabled, based on the values of the `outboundType` property (none or blocked) and `artifactSource` property (Cached).

```
"kubernetesVersion": "1.30.3",
"name": "myAKSCluster"
"type": "Microsoft.ContainerService/ManagedClusters"
"properties": {
  ...
  "networkProfile": {
    ...
    "outboundType": "none",
    ...
  },
  ...
  "bootstrapProfile": {
    "artifactSource": "Cache",
    "containerRegistryId": "/subscriptions/my-subscription-id/my-node-resource-group-name/providers/Microsoft.ContainerRegistry/registries/my-registry-name"
  },
  ...
}
```

## Disable network isolated cluster

Disable the network isolated cluster feature by running the `az aks update` command with the `--bootstrap-artifact-source` and `--outbound-type` parameters.

```azurecli-interactive
az aks update --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --bootstrap-artifact-source Direct --outbound-type LoadBalancer
```

When you disable the feature on an existing cluster, you need to manually reimage all existing nodes.

```azurecli-interactive
az aks upgrade --resource-group ${RESOURCE_GROUP} --name ${AKS_NAME} --node-image-only
```

>[!IMPORTANT]
> Remember to reimage the cluster's node pools after you disable the network isolated cluster feature. Otherwise, the feature won't take effect for the cluster.

## Troubleshooting

If you're experiencing issues, such as image pull fails, see [Troubleshoot network isolated Azure Kubernetes Service (AKS) clusters issues][ni-troubleshoot].

## Next steps

If you want to set up outbound restriction configuration using Azure Firewall, visit [Control egress traffic using Azure Firewall in AKS][aks-firewall].

If you want to restrict how pods communicate between themselves and East-West traffic restrictions within cluster, see [Secure traffic between pods using network policies in AKS][use-network-policies].


<!-- LINKS - External -->
[microsoft-artifact-registry]: https://mcr.microsoft.com
[microsoft-packages-repository]: https://packages.microsoft.com
[ubuntu-security-repository]: https://security.ubuntu.com
[register-feature-flag]: /azure/azure-resource-manager/management/preview-features?tabs=azure-cli#register-preview-feature
[container-registry-skus]: /azure/container-registry/container-registry-skus
[akv-privatelink]: /azure/key-vault/general/private-link-service?tabs=portal
[azuremonitoring]: /azure/azure-monitor/logs/private-link-configure#connect-to-a-private-endpoint
[az-extension-add]: /cli/azure/extension#az-extension-add
[az-extension-update]: /cli/azure/extension#az-extension-update
[az-feature-register]: /cli/azure/feature#az_feature_register
[az-feature-show]: /cli/azure/feature#az_feature_show
[az-provider-register]: /cli/azure/provider#az_provider_register
[azure-acr-rbac-contributor]: /azure/container-registry/container-registry-roles
[container-registry-private-link]: /azure/container-registry/container-registry-private-link
[az-aks-create]: /cli/azure/aks#az-aks-create
[az-aks-update]: /cli/azure/aks#az-aks-update
[az-aks-show]: /cli/azure/aks#az-aks-show
[gitops-overview]: /azure/azure-arc/kubernetes/conceptual-gitops-flux2
[azure-container-storage]: /azure/storage/container-storage/container-storage-introduction
[azure-backup-aks]: /azure/backup/azure-kubernetes-service-backup-overview
[vnet-disable-outbound-access]: /azure/virtual-network/ip-services/default-outbound-access#how-can-i-transition-to-an-explicit-method-of-public-connectivity-and-disable-default-outbound-access
[azmontoring-private-link]: /azure/azure-monitor/containers/kubernetes-monitoring-private-link
[ni-troubleshoot]: /troubleshoot/azure/azure-kubernetes/extensions/troubleshoot-network-isolated-cluster

<!-- LINKS - Internal -->
[aks-firewall]: ./limit-egress-traffic.md
[conceptual-network-isolated]: ./concepts-network-isolated.md
[conceptual-network-isolated-limitations]: ./concepts-network-isolated.md#limitations
[aks-control-plane-identity]: ./use-managed-identity.md
[aks-private-link]: ./private-clusters.md
[azure-cni-overlay]: ./azure-cni-overlay.md
[outbound-rules-control-egress]: ./outbound-rules-control-egress.md
[private-clusters]: ./private-clusters.md
[api-server-vnet-integration]: ./api-server-vnet-integration.md
[use-network-policies]: ./use-network-policies.md
[workload-identity]: ./workload-identity-deploy-cluster.md
[csi-akv-wi]: ./csi-secrets-store-identity-access.md?pivots=access-with-a-microsoft-entra-workload-identity
[app-config-overview]: ./azure-app-configuration.md
[azure-ml-overview]: /azure/machine-learning/how-to-attach-kubernetes-anywhere
[dapr-overview]: ./dapr.md
[outbound-rules]: ./outbound-rules-control-egress.md
[aks-firewall]: ./limit-egress-traffic.md

