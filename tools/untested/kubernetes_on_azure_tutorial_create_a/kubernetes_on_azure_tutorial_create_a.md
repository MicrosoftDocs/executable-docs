---
title: Kubernetes on Azure tutorial - Create an Azure Kubernetes Service (AKS) cluster
description: In this Azure Kubernetes Service (AKS) tutorial, you learn how to create an AKS cluster and use kubectl to connect to the Kubernetes main node.
ms.topic: tutorial
ms.date: 03/05/2025
author: schaffererin
ms.author: schaffererin

ms.custom: mvc, devx-track-azurecli, devx-track-azurepowershell, devx-track-extended-azdevcli

#Customer intent: As a developer or IT pro, I want to learn how to create an Azure Kubernetes Service (AKS) cluster so that I can deploy and run my own applications.
---

# Tutorial - Create an Azure Kubernetes Service (AKS) cluster

Kubernetes provides a distributed platform for containerized applications. With Azure Kubernetes Service (AKS), you can quickly create a production ready Kubernetes cluster.

In this tutorial, you deploy a Kubernetes cluster in AKS. You learn how to:

> [!div class="checklist"]
>
> * Deploy an AKS cluster that can authenticate to an Azure Container Registry (ACR).
> * Install the Kubernetes CLI, `kubectl`.
> * Configure `kubectl` to connect to your AKS cluster.

## Before you begin

In previous tutorials, you created a container image and uploaded it to an ACR instance. Start with [Tutorial 1 - Prepare application for AKS][aks-tutorial-prepare-app] to follow along.

* If you're using Azure CLI, this tutorial requires that you're running the Azure CLI version 2.35.0 or later. Check your version with `az --version`. To install or upgrade, see [Install Azure CLI][azure-cli-install].
* If you're using Azure PowerShell, this tutorial requires that you're running Azure PowerShell version 5.9.0 or later. Check your version with `Get-InstalledModule -Name Az`. To install or upgrade, see [Install Azure PowerShell][azure-powershell-install].
* If you're using Azure Developer CLI, this tutorial requires that you're running the Azure Developer CLI version 1.5.1 or later. Check your version with `azd version`. To install or upgrade, see [Install Azure Developer CLI][azure-azd-install].

---

## Create a Kubernetes cluster

AKS clusters can use [Kubernetes role-based access control (Kubernetes RBAC)][k8s-rbac], which allows you to define access to resources based on roles assigned to users. If a user is assigned multiple roles, permissions are combined. Permissions can be scoped to either a single namespace or across the whole cluster.

To learn more about AKS and Kubernetes RBAC, see [Control access to cluster resources using Kubernetes RBAC and Microsoft Entra identities in AKS][aks-k8s-rbac].

### [Azure CLI](#tab/azure-cli)

This tutorial requires Azure CLI version 2.35.0 or later. Check your version with `az --version`. To install or upgrade, see [Install Azure CLI][azure-cli-install]. If you're using the Bash environment in Azure Cloud Shell, the latest version is already installed. 

### [Azure PowerShell](#tab/azure-powershell)

This tutorial requires Azure PowerShell version 5.9.0 or later. Check your version with `Get-InstalledModule -Name Az`. To install or upgrade, see [Install Azure PowerShell][azure-powershell-install]. If you're using Azure Cloud Shell, the latest version is already installed. 

### [Azure Developer CLI](#tab/azure-azd)

This tutorial requires Azure Developer CLI version 1.5.1 or later. Check your version with `azd version`. To install or upgrade, see [Install Azure Developer CLI][azure-azd-install].

---

## Install the Kubernetes CLI

You use the Kubernetes CLI, [`kubectl`][kubectl], to connect to your Kubernetes cluster. If you use the Azure Cloud Shell, `kubectl` is already installed. If you're running the commands locally, you can use the Azure CLI or Azure PowerShell to install `kubectl`.

### [Azure CLI](#tab/azure-cli)

* Install `kubectl` locally using the [`az aks install-cli`][az aks install-cli] command.

    ```azurecli-interactive
    az aks install-cli
    ```

### [Azure PowerShell](#tab/azure-powershell)

* Install `kubectl` locally using the [`Install-AzAksCliTool`][install-azaksclitool] cmdlet.

    ```azurepowershell-interactive
    Install-AzAksCliTool
    ```

### [Azure Developer CLI](#tab/azure-azd)

`azd` environments in a codespace automatically download all dependencies found in `./devcontainer/devcontainer.json`. This includes the Kubernetes CLI along with any Azure Container Registry (ACR) images.

* To install `kubectl` locally, use the [`az aks install-cli`][az aks install-cli] command.

    ```azurecli-interactive
    az aks install-cli
    ```

---

## Create an AKS cluster

AKS clusters can use [Kubernetes role-based access control (Kubernetes RBAC)][k8s-rbac], which allows you to define access to resources based on roles assigned to users. Permissions are combined when users are assigned multiple roles. Permissions can be scoped to either a single namespace or across the whole cluster. For more information, see [Control access to cluster resources using Kubernetes RBAC and Microsoft Entra ID in AKS][aks-k8s-rbac].

For information about AKS resource limits and region availability, see [Quotas, virtual machine size restrictions, and region availability in AKS][quotas-skus-regions].

> [!IMPORTANT]
> This tutorial creates a three-node cluster. To ensure your cluster operates reliably, you should run at least two nodes. A minimum of three nodes is required to use Azure Container Storage. If you get an error message when trying to create the cluster, then you might need to request a quota increase for your Azure subscription or try a different Azure region. Alternatively, you can omit the node VM size parameter to use the default VM size.

### [Azure CLI](#tab/azure-cli)

To allow an AKS cluster to interact with other Azure resources, the Azure platform automatically creates a cluster identity. In this example, the cluster identity is [granted the right to pull images][container-registry-integration] from the ACR instance you created in the previous tutorial. To execute the command successfully, you must have an **Owner** or **Azure account administrator** role in your Azure subscription.

* Create an AKS cluster using the [`az aks create`][az aks create] command. The following example creates a cluster named *myAKSCluster* in the resource group named *myResourceGroup*. This resource group was created in the [previous tutorial][aks-tutorial-prepare-acr] in the *westus2* region. We'll continue to use the environment variable, `$ACRNAME`, that we set in the [previous tutorial][aks-tutorial-prepare-acr]. If you don't have this environment variable set, set it now to the same value you used previously.

    ```azurecli-interactive
    az aks create \
        --resource-group myResourceGroup \
        --name myAKSCluster \
        --node-count 3 \
        --node-vm-size standard_l8s_v3 \
        --generate-ssh-keys \
        --attach-acr $ACRNAME
    ```

    > [!NOTE]
    > If you already generated SSH keys, you might encounter an error similar to `linuxProfile.ssh.publicKeys.keyData is invalid`. To proceed, retry the command without the `--generate-ssh-keys` parameter.

To avoid needing an **Owner** or **Azure account administrator** role, you can also manually configure a service principal to pull images from ACR. For more information, see [ACR authentication with service principals](/azure/container-registry/container-registry-auth-service-principal) or [Authenticate from Kubernetes with a pull secret](/azure/container-registry/container-registry-auth-kubernetes). Alternatively, you can use a [managed identity](use-managed-identity.md) instead of a service principal for easier management.

### [Azure PowerShell](#tab/azure-powershell)

To allow an AKS cluster to interact with other Azure resources, the Azure platform automatically creates a cluster identity. In this example, the cluster identity is [granted the right to pull images][container-registry-integration] from the ACR instance you created in the previous tutorial. To execute the command successfully, you need to have an **Owner** or **Azure account administrator** role in your Azure subscription.

* Create an AKS cluster using the [`New-AzAksCluster`][new-azakscluster] cmdlet. The following example creates a cluster named *myAKSCluster* in the resource group named *myResourceGroup*. This resource group was created in the [previous tutorial][aks-tutorial-prepare-acr] in the *westus2* region.

    ```azurepowershell-interactive
    New-AzAksCluster -ResourceGroupName myResourceGroup -Name myAKSCluster -NodeCount 3 -NodeVmSize standard_l8s_v3 -GenerateSshKey -AcrNameToAttach $ACRNAME
    ```

    > [!NOTE]
    > If you already generated SSH keys, you might encounter an error similar to `linuxProfile.ssh.publicKeys.keyData is invalid`. To proceed, retry the command without the `-GenerateSshKey` parameter.

To avoid needing an **Owner** or **Azure account administrator** role, you can also manually configure a service principal to pull images from ACR. For more information, see [ACR authentication with service principals](/azure/container-registry/container-registry-auth-service-principal) or [Authenticate from Kubernetes with a pull secret](/azure/container-registry/container-registry-auth-kubernetes). Alternatively, you can use a [managed identity](use-managed-identity.md) instead of a service principal for easier management.

### [Azure Developer CLI](#tab/azure-azd)

`azd` packages the deployment of clusters with the application itself using the `azd up` command. This command is covered in the [Deploy containerized application](tutorial-kubernetes-deploy-application.md) tutorial.

---

## Connect to cluster using kubectl

### [Azure CLI](#tab/azure-cli)

1. Configure `kubectl` to connect to your Kubernetes cluster using the [`az aks get-credentials`][az aks get-credentials] command. The following example gets credentials for the AKS cluster named *myAKSCluster* in *myResourceGroup*.

    ```azurecli-interactive
    az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
    ```

2. Verify connection to your cluster using the [`kubectl get nodes`][kubectl-get] command, which returns a list of cluster nodes.

    ```azurecli-interactive
    kubectl get nodes
    ```

    The following example output shows a list of the cluster nodes:

    ```output
    NAME                                STATUS   ROLES   AGE   VERSION
    aks-nodepool1-19366578-vmss000000   Ready    agent   47h   v1.30.9
    aks-nodepool1-19366578-vmss000001   Ready    agent   47h   v1.30.9
    aks-nodepool1-19366578-vmss000002   Ready    agent   47h   v1.30.9
    ```

### [Azure PowerShell](#tab/azure-powershell)

1. Configure `kubectl` to connect to your Kubernetes cluster using the [`Import-AzAksCredential`][import-azakscredential] cmdlet. The following example gets credentials for the AKS cluster named *myAKSCluster* in *myResourceGroup*.

    ```azurepowershell-interactive
    Import-AzAksCredential -ResourceGroupName myResourceGroup -Name myAKSCluster
    ```

2. Verify connection to your cluster using the [`kubectl get nodes`][kubectl-get] command, which returns a list of cluster nodes.

    ```azurepowershell-interactive
    kubectl get nodes
    ```

    The following example output shows a list of the cluster nodes.

    ```output
    NAME                                STATUS   ROLES   AGE   VERSION
    aks-nodepool1-19366578-vmss000000   Ready    agent   47h   v1.30.9
    aks-nodepool1-19366578-vmss000001   Ready    agent   47h   v1.30.9
    aks-nodepool1-19366578-vmss000002   Ready    agent   47h   v1.30.9
    ```

### [Azure Developer CLI](#tab/azure-azd)

1. Configure authentication to your cluster using the [`azd auth login`][azd-auth-login] command.

    ```azdeveloper
    azd auth login 
    ```

2. Follow the directions for your auth method.

3. Verify the connection to your cluster using the [`kubectl get nodes`][kubectl-get] command.

    ```azurecli-interactive
    kubectl get nodes
    ```

    The following example output shows a list of the cluster nodes:

    ```output
    NAME                                STATUS   ROLES   AGE   VERSION
    aks-nodepool1-19366578-vmss000000   Ready    agent   47h   v1.30.9
    aks-nodepool1-19366578-vmss000001   Ready    agent   47h   v1.30.9
    aks-nodepool1-19366578-vmss000002   Ready    agent   47h   v1.30.9
    ```

[!INCLUDE [azd-login-ts](./includes/azd/azd-login-ts.md)]

---

## Next step

In this tutorial, you deployed a Kubernetes cluster in AKS and configured `kubectl` to connect to the cluster. You learned how to:

> [!div class="checklist"]
>
> * Deploy an AKS cluster that can authenticate to an ACR.
> * Install the Kubernetes CLI, `kubectl`.
> * Configure `kubectl` to connect to your AKS cluster.

In the next tutorial, you learn how to deploy Azure Container Storage on your cluster and create a generic ephemeral volume. If you're using Azure Developer CLI, or if you weren't able to use a storage optimized VM type due to quota issues, proceed directly to the [Deploy containerized application](tutorial-kubernetes-deploy-application.md) tutorial.

> [!div class="nextstepaction"]
> [Deploy Azure Container Storage][aks-tutorial-acstor]

<!-- LINKS - external -->
[kubectl]: https://kubernetes.io/docs/reference/kubectl/
[kubectl-get]: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#get
[k8s-rbac]: https://kubernetes.io/docs/reference/access-authn-authz/rbac/

<!-- LINKS - internal -->
[aks-tutorial-deploy-app]: ./tutorial-kubernetes-deploy-application.md
[aks-tutorial-prepare-acr]: ./tutorial-kubernetes-prepare-acr.md
[aks-tutorial-prepare-app]: ./tutorial-kubernetes-prepare-app.md
[aks-tutorial-acstor]: ./tutorial-kubernetes-deploy-azure-container-storage.md
[az aks create]: /cli/azure/aks#az_aks_create
[az aks install-cli]: /cli/azure/aks#az_aks_install_cli
[az aks get-credentials]: /cli/azure/aks#az_aks_get_credentials
[azure-azd-install]: /azure/developer/azure-developer-cli/install-azd
[azure-cli-install]: /cli/azure/install-azure-cli
[container-registry-integration]: ./cluster-container-registry-integration.md
[quotas-skus-regions]: quotas-skus-regions.md
[azure-powershell-install]: /powershell/azure/install-az-ps
[new-azakscluster]: /powershell/module/az.aks/new-azakscluster
[install-azaksclitool]: /powershell/module/az.aks/install-azaksclitool
[import-azakscredential]: /powershell/module/az.aks/import-azakscredential
[aks-k8s-rbac]: azure-ad-rbac.md
[azd-auth-login]: /azure/developer/azure-developer-cli/reference#azd-auth-login

