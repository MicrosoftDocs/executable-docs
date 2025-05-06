---
title: 'Quickstart: Create a private Azure Kubernetes Service (AKS) Automatic cluster (preview) in a custom virtual network'
description: Learn how to quickly deploy a private Kubernetes cluster and deploy an application in Azure Kubernetes Service (AKS) Automatic (preview) in a custom virtual network.
ms.topic: quickstart
ms.date: 03/03/2025
author: sabbour
ms.author: asabbour
zone_pivot_groups: bicep-azure-cli
---

# Quickstart: Create a private Azure Kubernetes Service (AKS) Automatic cluster (preview) in a custom virtual network

**Applies to:** :heavy_check_mark: AKS Automatic (preview)

[Azure Kubernetes Service (AKS) Automatic (preview)][what-is-aks-automatic] provides the easiest managed Kubernetes experience for developers, DevOps engineers, and platform engineers. Ideal for modern and AI applications, AKS Automatic automates AKS cluster setup and operations and embeds best practice configurations. Users of any skill level can benefit from the security, performance, and dependability of AKS Automatic for their applications. 

In this quickstart, you learn to:

- Create a virtual network.
- Create a managed identity with permissions over the virtual network.
- Deploy a private AKS Automatic cluster in the virtual network.
- Connect to the private cluster.
- Run a sample multi-container application with a group of microservices and web front ends simulating a retail scenario.

## Before you begin

This quickstart assumes a basic understanding of Kubernetes concepts. For more information, see [Kubernetes core concepts for Azure Kubernetes Service (AKS)][kubernetes-concepts].

[!INCLUDE [azure-cli-prepare-your-environment-no-header.md](~/reusable-content/azure-cli/azure-cli-prepare-your-environment-no-header.md)]

- This article requires version **2.68** or later of the Azure CLI. If you're using Azure Cloud Shell, the latest version is already installed there.
- This article requires the `aks-preview` Azure CLI extension version **13.0.0b3** or later.
- If you have multiple Azure subscriptions, select the appropriate subscription ID in which the resources should be billed using the [az account set](/cli/azure/account#az-account-set) command.
- Register the `AutomaticSKUPreview` feature in your Azure subscription.
- The identity creating the cluster should also have the [following permissions on the resource group][Azure-Policy-RBAC-permissions]:
    - `Microsoft.Authorization/policyAssignments/write`
    - `Microsoft.Authorization/policyAssignments/read`
- AKS Automatic clusters with custom virtual networks only support user assigned managed identity.
- AKS Automatic clusters with custom virtual networks don't support the Managed NAT Gateway outbound type.
- AKS Automatic clusters require deployment in Azure regions that support at least three [availability zones][availability-zones].
:::zone target="docs" pivot="bicep"
- To deploy a Bicep file, you need to write access on the resources you create and access to all operations on the `Microsoft.Resources/deployments` resource type. For example, to create a virtual machine, you need `Microsoft.Compute/virtualMachines/write` and `Microsoft.Resources/deployments/*` permissions. For a list of roles and permissions, see [Azure built-in roles](/azure/role-based-access-control/built-in-roles).
:::zone-end

When using a custom virtual network with AKS Automatic, you must create and delegate an API server subnet to `Microsoft.ContainerService/managedClusters`, which grants the AKS service permissions to inject the API server pods and internal load balancer into that subnet. You can't use the subnet for any other workloads, but you can use it for multiple AKS clusters located in the same virtual network. The minimum supported API server subnet size is a */28*.

The cluster identity needs **Network Contributor** permissions on the virtual network. Lack of permissions at the API server subnet can cause a provisioning failure. Lack of permissions at the virtual network can cause Node Auto Provisioning scaling failure.

> [!WARNING]
> An AKS cluster reserves at least 9 IPs in the subnet address space. Running out of IP addresses may prevent API server scaling and cause an API server outage.

> [!IMPORTANT]
> AKS Automatic tries to dynamically select a virtual machine size for the `system` node pool based on the capacity available in the subscription. Make sure your subscription has quota for 16 vCPUs of any of the following sizes in the region you're deploying the cluster to: [Standard_D4pds_v5](/azure/virtual-machines/sizes/general-purpose/dpsv5-series), [Standard_D4lds_v5](/azure/virtual-machines/sizes/general-purpose/dldsv5-series), [Standard_D4ads_v5](/azure/virtual-machines/sizes/general-purpose/dadsv5-series), [Standard_D4ds_v5](/azure/virtual-machines/sizes/general-purpose/ddsv5-series), [Standard_D4d_v5](/azure/virtual-machines/sizes/general-purpose/ddv5-series), [Standard_D4d_v4](/azure/virtual-machines/sizes/general-purpose/ddv4-series), [Standard_DS3_v2](/azure/virtual-machines/sizes/general-purpose/dsv3-series), [Standard_DS12_v2](/azure/virtual-machines/sizes/memory-optimized/dv2-dsv2-series-memory). You can [view quotas for specific VM-families and submit quota increase requests](/azure/quotas/per-vm-quota-requests) through the Azure portal.

### Install the aks-preview Azure CLI extension

[!INCLUDE [preview features callout](~/reusable-content/ce-skilling/azure/includes/aks/includes/preview/preview-callout.md)]

To install the aks-preview extension, run the following command:

```azurecli-interactive
az extension add --name aks-preview
```

Run the following command to update to the latest version of the extension released:

```azurecli-interactive
az extension update --name aks-preview
```

### Register the feature flags

To use AKS Automatic in preview, register the following flag using the [az feature register][az-feature-register] command.

```azurecli-interactive
az feature register --namespace Microsoft.ContainerService --name AutomaticSKUPreview
```

Verify the registration status by using the [az feature show][az-feature-show] command. It takes a few minutes for the status to show *Registered*:

```azurecli-interactive
az feature show --namespace Microsoft.ContainerService --name AutomaticSKUPreview
```

When the status reflects *Registered*, refresh the registration of the *Microsoft.ContainerService* resource provider by using the [az provider register][az-provider-register] command:

```azurecli-interactive
az provider register --namespace Microsoft.ContainerService
```

:::zone target="docs" pivot="azure-cli"

## Define variables

Define the following variables that will be used in the subsequent steps.

:::code language="azurecli" source="~/aks-samples/automatic/custom-network/private/sh/define-vars.sh" interactive="cloudshell-bash":::

## Create a resource group

An [Azure resource group][azure-resource-group] is a logical group in which Azure resources are deployed and managed.

Create a resource group using the [az group create][az-group-create] command.

:::code language="azurecli" source="~/aks-samples/automatic/custom-network/private/sh/create-rg.sh" interactive="cloudshell-bash":::

The following sample output resembles successful creation of the resource group:

```output
{
  "id": "/subscriptions/<guid>/resourceGroups/automatic-rg",
  "location": "eastus",
  "managedBy": null,
  "name": "automatic-rg",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null
}
```

## Create a virtual network

Create a virtual network using the [`az network vnet create`][az-network-vnet-create] command. Create an API server subnet and cluster subnet using the [`az network vnet subnet create`][az-network-vnet-subnet-create] command. The API subnet needs a delegation to `Microsoft.ContainerService/managedClusters`.

:::code language="azurecli" source="~/aks-samples/automatic/custom-network/private/sh/create-vnet.sh" interactive="cloudshell-bash":::

All traffic within the virtual network is allowed by default. But if you  added Network Security Group (NSG) rules to restrict traffic between different subnets, ensure that the NSG security rules permit the following types of communication:

| Destination | Source | Protocol | Port | Use |
|--- |--- |--- |--- |--- |
| APIServer Subnet CIDR   | Cluster Subnet | TCP           | 443 and 4443      | Required to enable communication between Nodes and the API server.|
| APIServer Subnet CIDR   | Azure Load Balancer |  TCP           | 9988      | Required to enable communication between Azure Load Balancer and the API server. You can also enable all communication between the Azure Load Balancer and the API Server Subnet CIDR. |

## Create a managed identity and give it permissions on the virtual network

Create a managed identity using the [`az identity create`][az-identity-create] command and retrieve the principal ID. Assign the **Network Contributor** role on virtual network to the managed identity using the [`az role assignment create`][az-role-assignment-create] command.

:::code language="azurecli" source="~/aks-samples/automatic/custom-network/private/sh/create-uami.sh" interactive="cloudshell-bash":::

## Create a private AKS Automatic cluster in a custom virtual network

To create a private AKS Automatic cluster, use the [az aks create][az-aks-create] command. Note the use of the `--enable-private-cluster` flag.

:::code language="azurecli" source="~/aks-samples/automatic/custom-network/private/sh/create-aks.sh" highlight="5,6,7,9" interactive="cloudshell-bash":::

After a few minutes, the command completes and returns JSON-formatted information about the cluster.

## Connect to the cluster

When an AKS Automatic cluster is created as a private cluster, the API server endpoint has no public IP address. To manage the API server, for example via `kubectl`, you need to connect through a machine that has access to the  cluster's Azure virtual network. There are several options for establishing network connectivity to the private cluster. Refer to [Options for connecting to the private cluster][connect-private-cluster] for more information.

To manage a Kubernetes cluster, use the Kubernetes command-line client, [kubectl][kubectl]. `kubectl` is already installed if you use Azure Cloud Shell. To install `kubectl` locally, run the [az aks install-cli][az-aks-install-cli] command. AKS Automatic clusters are configured with [Microsoft Entra ID for Kubernetes role-based access control (RBAC)][aks-entra-rbac].

When you create a cluster using the Azure CLI, your user is [assigned built-in roles][aks-entra-rbac-builtin-roles] for `Azure Kubernetes Service RBAC Cluster Admin`.

Configure `kubectl` to connect to your Kubernetes cluster using the [az aks get-credentials][az-aks-get-credentials] command. This command downloads credentials and configures the Kubernetes CLI to use them.

```azurecli-interactive
az aks get-credentials --resource-group ${RG_NAME} --name ${CLUSTER_NAME}
```

Verify the connection to your cluster using the [kubectl get][kubectl-get] command. This command returns a list of the cluster nodes.

```bash
kubectl get nodes
```

The following sample output shows how you're asked to log in.

```output
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code AAAAAAAAA to authenticate.
```

After you log in, the following sample output shows the managed system node pools. Make sure the node status is *Ready*.

```output
NAME                                STATUS   ROLES   AGE     VERSION
aks-nodepool1-13213685-vmss000000   Ready    agent   2m26s   v1.28.5
aks-nodepool1-13213685-vmss000001   Ready    agent   2m26s   v1.28.5
aks-nodepool1-13213685-vmss000002   Ready    agent   2m26s   v1.28.5
```

:::zone-end

:::zone target="docs" pivot="bicep"

## Create a resource group

An [Azure resource group][azure-resource-group] is a logical group in which Azure resources are deployed and managed. When you create a resource group, you're prompted to specify a location. This location is the storage location of your resource group metadata and where your resources run in Azure if you don't specify another region during resource creation.

Create a resource group using the [az group create][az-group-create] command.

```azurecli-interactive
az group create --name <resource-group> --location <location>
```

The following sample output resembles successful creation of the resource group:

```output
{
  "id": "/subscriptions/<guid>/resourceGroups/myResourceGroup",
  "location": "eastus",
  "managedBy": null,
  "name": "myResourceGroup",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null
}
```

## Create a virtual network

This Bicep file defines a virtual network.

:::code language="bicep" source="~/aks-samples/automatic/custom-network/private/bicep/virtualNetwork.bicep":::

Save the Bicep file **virtualNetwork.bicep** to your local computer.

> [!IMPORTANT]
> The Bicep file sets the `vnetName` param to  *aksAutomaticVnet*, the `addressPrefix` param to *172.19.0.0/16*, the `apiServerSubnetPrefix` param to *172.19.0.0/28*, and the `apiServerSubnetPrefix` param to *172.19.1.0/24*. If you want to use different values, make sure to update the strings to your preferred values.

Deploy the Bicep file using the Azure CLI.

```azurecli-interactive
az deployment group create --resource-group <resource-group> --template-file virtualNetwork.bicep
```

All traffic within the virtual network is allowed by default. But if you added Network Security Group (NSG) rules to restrict traffic between different subnets, ensure that the NSG security rules permit the following types of communication:

| Destination | Source | Protocol | Port | Use |
|--- |--- |--- |--- |--- |
| APIServer Subnet CIDR   | Cluster Subnet | TCP           | 443 and 4443      | Required to enable communication between Nodes and the API server.|
| APIServer Subnet CIDR   | Azure Load Balancer |  TCP           | 9988      | Required to enable communication between Azure Load Balancer and the API server. You can also enable all communication between the Azure Load Balancer and the API Server Subnet CIDR. |

## Create a managed identity

This Bicep file defines a user assigned managed identity.

:::code language="bicep" source="~/aks-samples/automatic/custom-network/private/bicep/uami.bicep":::

Save the Bicep file **uami.bicep** to your local computer.

> [!IMPORTANT]
> The Bicep file sets the `uamiName` param to the *aksAutomaticUAMI*. If you want to use a different identity name, make sure to update the string to your preferred name.

Deploy the Bicep file using the Azure CLI.

```azurecli-interactive
az deployment group create --resource-group <resource-group> --template-file uami.bicep
```

## Assign the Network Contributor role over the virtual network

This Bicep file defines role assignments over the virtual network.

:::code language="bicep" source="~/aks-samples/automatic/custom-network/private/bicep/roleAssignments.bicep":::

Save the Bicep file **roleAssignments.bicep** to your local computer.

> [!IMPORTANT]
> The Bicep file sets the `vnetName` param to *aksAutomaticVnet*. If you used a different virtual network name, make sure to update the string to your preferred virtual network name.

Deploy the Bicep file using the Azure CLI. You need to provide the user assigned identity principal ID.

```azurecli-interactive
az deployment group create --resource-group <resource-group> --template-file roleAssignments.bicep \
--parameters uamiPrincipalId=<user assigned identity prinicipal id>
```

## Create a private AKS Automatic cluster in a custom virtual network

This Bicep file defines the AKS Automatic cluster.

:::code language="bicep" source="~/aks-samples/automatic/custom-network/private/bicep/aks.bicep" highlight="29,33,34,36,37,38,40,41,42,43,44,45":::

Save the Bicep file **aks.bicep** to your local computer.

> [!IMPORTANT]
> The Bicep file sets the `clusterName` param to *aksAutomaticCluster*. If you want a different cluster name, make sure to update the string to your preferred cluster name.

Deploy the Bicep file using the Azure CLI. You need to provide the API server subnet resource ID, the cluster subnet resource ID, and user assigned identity principal ID.

```azurecli-interactive
az deployment group create --resource-group <resource-group> --template-file aks.bicep \
--parameters apiServerSubnetId=<API server subnet resource id> \
--parameters clusterSubnetId=<cluster subnet resource id> \
--parameters uamiPrincipalId=<user assigned identity prinicipal id>
```

## Connect to the cluster

When an AKS Automatic cluster is created as a private cluster, the API server endpoint has no public IP address. To manage the API server, for example via `kubectl`, you need to connect through a machine that has access to the  cluster's Azure virtual network. There are several options for establishing network connectivity to the private cluster. Refer to [Options for connecting to the private cluster][connect-private-cluster] for more information.

To manage a Kubernetes cluster, use the Kubernetes command-line client, [kubectl][kubectl]. `kubectl` is already installed if you use Azure Cloud Shell. To install `kubectl` locally, run the [az aks install-cli][az-aks-install-cli] command. AKS Automatic clusters are configured with [Microsoft Entra ID for Kubernetes role-based access control (RBAC)][aks-entra-rbac].

> [!IMPORTANT]
> When you create a cluster using Bicep, you need to [assign one of the built-in roles][aks-entra-rbac-builtin-roles] such as `Azure Kubernetes Service RBAC Reader`, `Azure Kubernetes Service RBAC Writer`, `Azure Kubernetes Service RBAC Admin`, or `Azure Kubernetes Service RBAC Cluster Admin` to your users, scoped to the cluster or a specific namespace, example using `az role assignment create --role "Azure Kubernetes Service RBAC Cluster Admin" --scope <AKS cluster resource id> --assignee user@contoso.com`. Also make sure your users have the `Azure Kubernetes Service Cluster User` built-in role to be able to do run `az aks get-credentials`, and then get the kubeconfig of your AKS cluster using the `az aks get-credentials` command.

Configure `kubectl` to connect to your Kubernetes cluster using the [az aks get-credentials][az-aks-get-credentials] command. This command downloads credentials and configures the Kubernetes CLI to use them.

```azurecli-interactive
az aks get-credentials --resource-group <resource-group> --name <cluster-name>
```

Verify the connection to your cluster using the [kubectl get][kubectl-get] command. This command returns a list of the cluster nodes.

```bash
kubectl get nodes
```

The following sample output shows how you're asked to log in.

```output
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code AAAAAAAAA to authenticate.
```

After you log in, the following sample output shows the managed system node pools. Make sure the node status is *Ready*.

```output
NAME                                STATUS   ROLES   AGE     VERSION
aks-nodepool1-13213685-vmss000000   Ready    agent   2m26s   v1.28.5
aks-nodepool1-13213685-vmss000001   Ready    agent   2m26s   v1.28.5
aks-nodepool1-13213685-vmss000002   Ready    agent   2m26s   v1.28.5
```

:::zone-end


## Deploy the application

To deploy the application, you use a manifest file to create all the objects required to run the [AKS Store application](https://github.com/Azure-Samples/aks-store-demo). A [Kubernetes manifest file][kubernetes-deployment] defines a cluster's desired state, such as which container images to run. The manifest includes the following Kubernetes deployments and services:

:::image type="content" source="../learn/media/quick-kubernetes-deploy-portal/aks-store-architecture.png" alt-text="Screenshot of Azure Store sample architecture." lightbox="../learn/media/quick-kubernetes-deploy-portal/aks-store-architecture.png":::

- **Store front**: Web application for customers to view products and place orders.
- **Product service**: Shows product information.
- **Order service**: Places orders.
- **Rabbit MQ**: Message queue for an order queue.

> [!NOTE]
> We don't recommend running stateful containers, such as Rabbit MQ, without persistent storage for production. These containers are used here for simplicity, but we recommend using managed services, such as Azure Cosmos DB or Azure Service Bus.

1. Create a namespace `aks-store-demo` to deploy the Kubernetes resources into.

    ```bash
    kubectl create ns aks-store-demo
    ```

1. Deploy the application using the [kubectl apply][kubectl-apply] command into the `aks-store-demo` namespace. The YAML file defining the deployment is on [GitHub](https://github.com/Azure-Samples/aks-store-demo).

    ```bash
    kubectl apply -n aks-store-demo -f https://raw.githubusercontent.com/Azure-Samples/aks-store-demo/main/aks-store-ingress-quickstart.yaml
    ```

    The following sample output shows the deployments and services:

    ```output
    statefulset.apps/rabbitmq created
    configmap/rabbitmq-enabled-plugins created
    service/rabbitmq created
    deployment.apps/order-service created
    service/order-service created
    deployment.apps/product-service created
    service/product-service created
    deployment.apps/store-front created
    service/store-front created
    ingress/store-front created
    ```

## Test the application

When the application runs, a Kubernetes service exposes the application front end to the internet. This process can take a few minutes to complete.

1. Check the status of the deployed pods using the [kubectl get pods][kubectl-get] command. Make sure all pods are `Running` before proceeding. If this is the first workload you deploy, it may take a few minutes for [node auto provisioning][node-auto-provisioning] to create a node pool to run the pods.

    ```bash
    kubectl get pods -n aks-store-demo
    ```

1. Check for a public IP address for the store-front application. Monitor progress using the [kubectl get service][kubectl-get] command with the `--watch` argument.

    ```bash
    kubectl get ingress store-front -n aks-store-demo --watch
    ```

    The **ADDRESS** output for the `store-front` service initially shows empty:

    ```output
    NAME          CLASS                                HOSTS   ADDRESS        PORTS   AGE
    store-front   webapprouting.kubernetes.azure.com   *                      80      12m
    ```

1. Once the **ADDRESS** changes from blank to an actual public IP address, use `CTRL-C` to stop the `kubectl` watch process.

    The following sample output shows a valid public IP address assigned to the service:

    ```output
    NAME          CLASS                                HOSTS   ADDRESS        PORTS   AGE
    store-front   webapprouting.kubernetes.azure.com   *       4.255.22.196   80      12m
    ```

1. Open a web browser to the external IP address of your ingress to see the Azure Store app in action.

    :::image type="content" source="../learn/media/quick-kubernetes-deploy-cli/aks-store-application.png" alt-text="Screenshot of AKS Store sample application." lightbox="../learn/media/quick-kubernetes-deploy-cli/aks-store-application.png":::

## Delete the cluster

If you don't plan on going through the [AKS tutorial][aks-tutorial], clean up unnecessary resources to avoid Azure charges. Run the [az group delete][az-group-delete] command to remove the resource group, container service, and all related resources.

```azurecli-interactive
az group delete --name <resource-group> --yes --no-wait
```
> [!NOTE]
> The AKS cluster was created with a user-assigned managed identity. If you don't need that identity anymore, you can manually remove it.

## Next steps

In this quickstart, you deployed a private Kubernetes cluster using [AKS Automatic][what-is-aks-automatic] in a custom virtual network and then deployed a simple multi-container application to it. This sample application is for demo purposes only and doesn't represent all the best practices for Kubernetes applications. For guidance on creating full solutions with AKS for production, see [AKS solution guidance][aks-solution-guidance].

To learn more about AKS Automatic, continue to the introduction.

> [!div class="nextstepaction"]
> [Introduction to Azure Kubernetes Service (AKS) Automatic (preview)][what-is-aks-automatic]


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
[node-auto-provisioning]: ../node-autoprovision.md
[kubernetes-deployment]: ../concepts-clusters-workloads.md#deployments-and-yaml-manifests
[aks-solution-guidance]: /azure/architecture/reference-architectures/containers/aks-start-here?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json
[baseline-reference-architecture]: /azure/architecture/reference-architectures/containers/aks/baseline-aks?toc=/azure/aks/toc.json&bc=/azure/aks/breadcrumb/toc.json
[az-feature-register]: /cli/azure/feature#az_feature_register
[az-feature-show]: /cli/azure/feature#az_feature_show
[az-provider-register]: /cli/azure/provider#az_provider_register
[what-is-aks-automatic]: ../intro-aks-automatic.md
[Azure-Policy-RBAC-permissions]: /azure/governance/policy/overview#azure-rbac-permissions-in-azure-policy
[aks-entra-rbac]: /azure/aks/manage-azure-rbac
[aks-entra-rbac-builtin-roles]: /azure/aks/manage-azure-rbac#create-role-assignments-for-users-to-access-the-cluster
[availability-zones]: /azure/reliability/availability-zones-region-support
[az-network-vnet-create]: /cli/azure/network/vnet#az-network-vnet-create
[az-network-vnet-subnet-create]: /cli/azure/network/vnet/subnet#az-network-vnet-subnet-create
[az-identity-create]: /cli/azure/identity#az-identity-create
[az-role-assignment-create]: /cli/azure/role/assignment#az-role-assignment-create
[connect-private-cluster]: ../private-clusters.md#options-for-connecting-to-the-private-cluster
