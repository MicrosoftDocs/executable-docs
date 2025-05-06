---
title: Enable Federal Information Process Standard (FIPS) for Azure Kubernetes Service (AKS) node pools
description: Learn how to enable Federal Information Process Standard (FIPS) for Azure Kubernetes Service (AKS) node pools.
author: nickomang
ms.author: nickoman
ms.topic: how-to 
ms.date: 02/29/2024
ms.custom: template-how-to, linux-related-content
---

# Enable Federal Information Process Standard (FIPS) for Azure Kubernetes Service (AKS) node pools

The Federal Information Processing Standard (FIPS) 140-2 is a US government standard that defines minimum security requirements for cryptographic modules in information technology products and systems. Azure Kubernetes Service (AKS) allows you to create Linux and Windows node pools with FIPS 140-2 enabled. Deployments running on FIPS-enabled node pools can use those cryptographic modules to provide increased security and help meet security controls as part of FedRAMP compliance. For more information on FIPS 140-2, see [Federal Information Processing Standard (FIPS) 140][fips].

> [!CAUTION]
> In this article, there are references to a feature that may be using Ubuntu OS versions that are being deprecated for AKS.
>- Starting on 17 June 2025, AKS will no longer support Ubuntu 18.04. Existing node images will be deleted and AKS will no longer provide security updates. You'll no longer be able to scale your node pools. [Upgrade your node pools](./upgrade-aks-cluster.md) to a supported kubernetes version to migrate to a supported Ubuntu version.
>- Starting on 17 March 2027, AKS will no longer support Ubuntu 20.04. Existing node images will be deleted and AKS will no longer provide security updates. You'll no longer be able to scale your node pools. [Upgrade your node pools](./upgrade-aks-cluster.md) to kubernetes version 1.34+ to migrate to a supported Ubuntu version.
>For more information on this retirement, see [AKS GitHub Issues](https://github.com/Azure/AKS/issues)

## Prerequisites

* Azure CLI version 2.32.0 or later installed and configured. To find the version, run `az --version`. For more information about installing or upgrading the Azure CLI, see [Install Azure CLI][install-azure-cli].

> [!NOTE]
>   AKS Monitoring Addon supports FIPS enabled node pools with Ubuntu, Azure Linux, and Windows starting with Agent version 3.1.17 (Linux) and Win-3.1.17 (Windows).

## Limitations

* FIPS-enabled node pools have the following limitations:
  * FIPS-enabled node pools require Kubernetes version 1.19 and greater.
  * To update the underlying packages or modules used for FIPS, you must use [Node Image Upgrade][node-image-upgrade].
  * Container images on the FIPS nodes aren't assessed for FIPS compliance.
  * Mounting of a CIFS share fails because FIPS disables some authentication modules. To work around this issue, see [Errors when mounting a file share on a FIPS-enabled node pool][errors-mount-file-share-fips].
  * FIPS-enabled node pools with [Arm64 VMs](./use-arm64-vms.md) are only supported with Azure Linux 3.0+.


> [!IMPORTANT]
> The FIPS-enabled Linux image is a different image than the default Linux image used for Linux-based node pools.
>
> FIPS-enabled node images can have different version numbers, such as kernel version, than images that aren't FIPS-enabled. The update cycle for FIPS-enabled node pools and node images can differ from node pools and images that aren't FIPS-enabled.

## Supported OS Versions
You can create FIPS-enabled node pools on all supported OS types (Linux and Windows). However, not all OS versions support FIPS-enabled node pools. After a new OS version is released, there's typically a waiting period before it's FIPS compliant.

This table includes the supported OS versions:

|OS Type|OS SKU|FIPS Compliance|
|--|--|--|
|Linux|Ubuntu|Supported|
|Linux|Azure Linux| Supported|
|Windows|Windows Server 2019| Supported|
|Windows| Windows Server 2022| Supported|

When requesting FIPS enabled Ubuntu, if the default Ubuntu version doesn't support FIPS, AKS defaults to the most recent FIPS-supported version of Ubuntu. For example, Ubuntu 22.04 is default for Linux node pools. Since 22.04 doesn't currently support FIPS, AKS defaults to Ubuntu 20.04 for Linux FIPS-enabled node pools.

> [!NOTE]
 > Previously, you could use the GetOSOptions API to determine whether a given OS supported FIPS. The GetOSOptions API is now deprecated and it will no longer be included in new AKS API versions starting with 2024-05-01. 

## Create a FIPS-enabled Linux node pool

1. Create a FIPS-enabled Linux node pool using the [`az aks nodepool add`][az-aks-nodepool-add] command with the `--enable-fips-image` parameter.

    ```azurecli-interactive
    az aks nodepool add \
        --resource-group myResourceGroup \
        --cluster-name myAKSCluster \
        --name fipsnp \
        --enable-fips-image
    ```

    > [!NOTE]
    > You can also use the `--enable-fips-image` parameter with the [`az aks create`][az-aks-create] command when creating a cluster to enable FIPS on the default node pool. When adding node pools to a cluster created in this way, you still must use the `--enable-fips-image` parameter when adding node pools to create a FIPS-enabled node pool.

2. Verify your node pool is FIPS-enabled using the [`az aks show`][az-aks-show] command and query for the *enableFIPS* value in *agentPoolProfiles*.

    ```azurecli-interactive
    az aks show \
        --resource-group myResourceGroup \
        --name myAKSCluster \
        --query="agentPoolProfiles[].{Name:name enableFips:enableFips}" \
        -o table
    ```

    The following example output shows the *fipsnp* node pool is FIPS-enabled:

    ```output
    Name       enableFips
    ---------  ------------
    fipsnp     True
    nodepool1  False  
    ```

3. List the nodes using the `kubectl get nodes` command.

    ```azurecli-interactive
    kubectl get nodes
    ```

    The following example output shows a list of the nodes in the cluster. The nodes starting with `aks-fipsnp` are part of the FIPS-enabled node pool.

    ```output
    NAME                                STATUS   ROLES   AGE     VERSION
    aks-fipsnp-12345678-vmss000000      Ready    agent   6m4s    v1.19.9
    aks-fipsnp-12345678-vmss000001      Ready    agent   5m21s   v1.19.9
    aks-fipsnp-12345678-vmss000002      Ready    agent   6m8s    v1.19.9
    aks-nodepool1-12345678-vmss000000   Ready    agent   34m     v1.19.9
    ```

4. Run a deployment with an interactive session on one of the nodes in the FIPS-enabled node pool using the `kubectl debug` command.

    ```azurecli-interactive
    kubectl debug node/aks-fipsnp-12345678-vmss000000 -it --image=mcr.microsoft.com/dotnet/runtime-deps:6.0
    ```

5. From the interactive session output, verify the FIPS cryptographic libraries are enabled. Your output should look similar to the following example output:

    ```output
    root@aks-fipsnp-12345678-vmss000000:/# cat /proc/sys/crypto/fips_enabled
    1
    ```

FIPS-enabled node pools also have a *kubernetes.azure.com/fips_enabled=true* label, which deployments can use to target those node pools.

## Create a FIPS-enabled Windows node pool

1. Create a FIPS-enabled Windows node pool using the [`az aks nodepool add`][az-aks-nodepool-add] command with the `--enable-fips-image` parameter. Unlike Linux-based node pools, Windows node pools share the same image set.

    ```azurecli-interactive
    az aks nodepool add \
        --resource-group myResourceGroup \
        --cluster-name myAKSCluster \
        --name fipsnp \
        --enable-fips-image \
        --os-type Windows
    ```

2. Verify your node pool is FIPS-enabled using the [`az aks show`][az-aks-show] command and query for the *enableFIPS* value in *agentPoolProfiles*.

    ```azurecli-interactive
    az aks show \
        --resource-group myResourceGroup \
        --name myAKSCluster \
        --query="agentPoolProfiles[].{Name:name enableFips:enableFips}" \
        -o table
    ```

3. Verify Windows node pools have access to the FIPS cryptographic libraries by [creating an RDP connection to a Windows node][aks-rdp] in a FIPS-enabled node pool and check the registry. From the **Run** application, enter `regedit`.
4. Look for `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Lsa\FIPSAlgorithmPolicy` in the registry.
5. If `Enabled` is set to *1*, then FIPS is enabled.

:::image type="content" source="./media/enable-fips-nodes/enable-fips-nodes-windows.png" alt-text="Screenshot shows a picture of the registry editor to the FIPS Algorithm Policy, and it being enabled.":::

FIPS-enabled node pools also have a *kubernetes.azure.com/fips_enabled=true* label, which deployments can use to target those node pools.

## Update an existing node pool to enable or disable FIPS

Existing Linux node pools can be updated to enable or disable FIPS. If you're planning to migrate your node pools from non-FIPS to FIPS, first validate that your application is working properly in a test environment before migrating it to a production environment. Validating your application in a test environment should prevent issues caused by the FIPS kernel blocking some weak cipher or encryption algorithm, such as an MD4 algorithm that isn't FIPS compliant.

> [!NOTE]
>   When updating an existing Linux node pool to enable or disable FIPS, the node pool update moves between the fips and non-fips image. This node pool update triggers a reimage to complete the update. This can cause the node pool update to take a few minutes to complete.

### Prerequisites

* Azure CLI version 2.64.0 or later. To find the version, run `az --version`. If you need to install or upgrade, see [Install Azure CLI][install-azure-cli].

### Enable FIPS on an existing node pool
Existing Linux node pools can be updated to enable FIPS. When you update an existing node pool, the node image changes from the current image to the recommended FIPS image of the same OS SKU. 

1. Update a node pool using the [`az aks nodepool update`][az-aks-nodepool-update] command with the `--enable-fips-image` parameter.

    ```azurecli-interactive
    az aks nodepool update \
        --resource-group myResourceGroup \
        --cluster-name myAKSCluster \
        --name np \
        --enable-fips-image
    ```

This command triggers a reimage of the node pool immediately to deploy the FIPS compliant Operating System. This reimage occurs during the node pool update. No extra steps are required.

2. Verify that your node pool is FIPS-enabled using the [`az aks show`][az-aks-show] command and query for the *enableFIPS* value in *agentPoolProfiles*.

    ```azurecli-interactive
    az aks show \
        --resource-group myResourceGroup \
        --name myAKSCluster \
        --query="agentPoolProfiles[].{Name:name enableFips:enableFips}" \
        -o table
    ```

    The following example output shows that the *np* node pool is FIPS-enabled:

    ```output
    Name       enableFips
    ---------  ------------
    np         True
    nodepool1  False  
    ```

3. List the nodes using the `kubectl get nodes` command.

    ```azurecli-interactive
    kubectl get nodes
    ```

    The following example output shows a list of the nodes in the cluster. The nodes starting with `aks-np` are part of the FIPS-enabled node pool.

    ```output
    NAME                                STATUS   ROLES   AGE     VERSION
    aks-np-12345678-vmss000000          Ready    agent   6m4s    v1.19.9
    aks-np-12345678-vmss000001          Ready    agent   5m21s   v1.19.9
    aks-np-12345678-vmss000002          Ready    agent   6m8s    v1.19.9
    aks-nodepool1-12345678-vmss000000   Ready    agent   34m     v1.19.9
    ```

4. Run a deployment with an interactive session on one of the nodes in the FIPS-enabled node pool using the `kubectl debug` command.

    ```azurecli-interactive
    kubectl debug node/aks-np-12345678-vmss000000 -it --image=mcr.microsoft.com/dotnet/runtime-deps:6.0
    ```

5. From the interactive session output, verify the FIPS cryptographic libraries are enabled. Your output should look similar to the following example output:

    ```output
    root@aks-np-12345678-vmss000000:/# cat /proc/sys/crypto/fips_enabled
    1
    ```

FIPS-enabled node pools also have a *kubernetes.azure.com/fips_enabled=true* label, which deployments can use to target those node pools.

## Disable FIPS on an existing node pool
Existing Linux node pools can be updated to disable FIPS. When updating an existing node pool, the node image changes from the current FIPS image to the recommended non-FIPS image of the same OS SKU. The node image change will occur after a reimage.

1. Update a Linux node pool using the [`az aks nodepool update`][az-aks-nodepool-update] command with the `--disable-fips-image` parameter.

    ```azurecli-interactive
    az aks nodepool update \
        --resource-group myResourceGroup \
        --cluster-name myAKSCluster \
        --name np \
        --disable-fips-image
    ```

This command triggers a reimage of the node pool immediately to deploy the FIPS compliant Operating System. This reimage occurs during the node pool update. No extra steps are required.

2. Verify that your node pool isn't FIPS-enabled using the [`az aks show`][az-aks-show] command and query for the *enableFIPS* value in *agentPoolProfiles*.

    ```azurecli-interactive
    az aks show \
        --resource-group myResourceGroup \
        --name myAKSCluster \
        --query="agentPoolProfiles[].{Name:name enableFips:enableFips}" \
        -o table
    ```

    The following example output shows that the *np* node pool isn't FIPS-enabled:

    ```output
    Name       enableFips
    ---------  ------------
    np         False
    nodepool1  False  
    ```
## Message of the Day

Pass the ```--message-of-the-day``` flag with the location of the file to replace the Message of the Day on Linux nodes at cluster creation or node pool creation.

Create a cluster with message of the day using the [`az aks create`][az-aks-create] command.

```azurecli
az aks create --cluster-name myAKSCluster --resource-group myResourceGroup --message-of-the-day ./newMOTD.txt
```

Add a node pool with message of the day using the [`az aks nodepool add`][az-aks-nodepool-add] command.

```azurecli
az aks nodepool add --name mynodepool1 --cluster-name myAKSCluster --resource-group myResourceGroup --message-of-the-day ./newMOTD.txt
```

## Next steps

To learn more about AKS security, see [Best practices for cluster security and upgrades in Azure Kubernetes Service (AKS)][aks-best-practices-security].

<!-- LINKS - Internal -->
[az-aks-nodepool-add]: /cli/azure/aks/nodepool#az-aks-nodepool-add
[az-aks-show]: /cli/azure/aks#az_aks_show
[az-aks-create]: /cli/azure/aks#az_aks_create
[aks-best-practices-security]: operator-best-practices-cluster-security.md
[aks-rdp]: rdp.md
[fips]: /azure/compliance/offerings/offering-fips-140-2
[install-azure-cli]: /cli/azure/install-azure-cli
[node-image-upgrade]: node-image-upgrade.md
[errors-mount-file-share-fips]: /troubleshoot/azure/azure-kubernetes/fail-to-mount-azure-file-share#fipsnodepool

