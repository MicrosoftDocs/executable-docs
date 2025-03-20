---
title: Tutorial - Create and manage Linux VMs with the Azure CLI
description: In this tutorial, you learn how to use the Azure CLI to create and manage Linux VMs in Azure
author: ju-shim
ms.service: azure-virtual-machines
ms.collection: linux
ms.topic: tutorial
ms.date: 03/23/2023
ms.author: jushiman
ms.custom: mvc, devx-track-azurecli, linux-related-content, innovation-engine
#Customer intent: As an IT administrator, I want to learn about common maintenance tasks so that I can create and manage Linux VMs in Azure
---

# Tutorial: Create and Manage Linux VMs with the Azure CLI

**Applies to:** :heavy_check_mark: Linux VMs :heavy_check_mark: Flexible scale sets

Azure virtual machines provide a fully configurable and flexible computing environment. This tutorial covers basic Azure virtual machine deployment items such as selecting a VM size, selecting a VM image, and deploying a VM. You learn how to:

> [!div class="checklist"]
> * Create and connect to a VM
> * Select and use VM images
> * View and use specific VM sizes
> * Resize a VM
> * View and understand VM state

This tutorial uses the CLI within the [Azure Cloud Shell](/azure/cloud-shell/overview), which is constantly updated to the latest version.

If you choose to install and use the CLI locally, this tutorial requires that you are running the Azure CLI version 2.0.30 or later. Run `az --version` to find the version. If you need to install or upgrade, see [Install Azure CLI]( /cli/azure/install-azure-cli).

## Create resource group

Below, we declare environment variables. A random suffix is appended to resource names that need to be unique for each deployment.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="eastus2"
export MY_RESOURCE_GROUP_NAME="myResourceGroupVM$RANDOM_SUFFIX"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/myResourceGroupVMxxx",
  "location": "eastus2",
  "name": "myResourceGroupVMxxx",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

An Azure resource group is a logical container into which Azure resources are deployed and managed. A resource group must be created before a virtual machine. In this example, a resource group named *myResourceGroupVM* is created in the *eastus2* region.

The resource group is specified when creating or modifying a VM, which can be seen throughout this tutorial.

## Create virtual machine

When you create a virtual machine, several options are available such as operating system image, disk sizing, and administrative credentials. The following example creates a VM named *myVM* that runs SUSE Linux Enterprise Server (SLES). A user account named *azureuser* is created on the VM, and SSH keys are generated if they do not exist in the default key location (*~/.ssh*).

```bash
export MY_VM_NAME="myVM$RANDOM_SUFFIX"
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM_NAME \
    --image SuseSles15SP5 \
    --public-ip-sku Standard \
    --admin-username azureuser \
    --generate-ssh-keys
```

It may take a few minutes to create the VM. Once the VM has been created, the Azure CLI outputs information about the VM. Take note of the `publicIpAddress`; this address can be used to access the virtual machine.

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/myResourceGroupVMxxx/providers/Microsoft.Compute/virtualMachines/myVMxxx",
  "location": "eastus2",
  "macAddress": "00-0D-3A-23-9A-49",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.174.34.95",
  "resourceGroup": "myResourceGroupVMxxx"
}
```

## Connect to VM

You can now connect to the VM with SSH in the Azure Cloud Shell or from your local computer. Replace the example IP address with the `publicIpAddress` noted in the previous step.

To connect to the VM, first retrieve the public IP address using the Azure CLI. Execute the following command to store the IP address in a variable: 
```export IP_ADDRESS=$(az vm show --show-details --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps --output tsv)```

Once you have the IP address, use SSH to connect to the VM. The following command connects to the VM using the `azureuser` account and the retrieved IP address: 
```ssh -o StrictHostKeyChecking=no azureuser@$IP_ADDRESS```

## Understand VM images

The Azure Marketplace includes many images that can be used to create VMs. In the previous steps, a virtual machine was created using a SUSE image. In this step, the Azure CLI is used to search the marketplace for an Ubuntu image, which is then used to deploy a second virtual machine.

To see a list of the most commonly used images, use the [az vm image list](/cli/azure/vm/image) command.

```bash
az vm image list --output table
```

The command output returns the most popular VM images on Azure.

```output
Architecture    Offer                         Publisher               Sku                                 Urn                                                                             UrnAlias                 Version
--------------  ----------------------------  ----------------------  ----------------------------------  ------------------------------------------------------------------------------  -----------------------  ---------
x64             debian-10                     Debian                  10                                  Debian:debian-10:10:latest                                                      Debian                   latest
x64             flatcar-container-linux-free  kinvolk                 stable                              kinvolk:flatcar-container-linux-free:stable:latest                              Flatcar                  latest
x64             opensuse-leap-15-3            SUSE                    gen2                                SUSE:opensuse-leap-15-3:gen2:latest                                             openSUSE-Leap            latest
x64             RHEL                          RedHat                  7-LVM                               RedHat:RHEL:7-LVM:latest                                                        RHEL                     latest
x64             sles-15-sp3                   SUSE                    gen2                                SUSE:sles-15-sp3:gen2:latest                                                    SLES                     latest
x64             0001-com-ubuntu-server-jammy  Canonical               18.04-LTS                           Canonical:UbuntuServer:18.04-LTS:latest                                         UbuntuLTS                latest
x64             WindowsServer                 MicrosoftWindowsServer  2022-Datacenter                     MicrosoftWindowsServer:WindowsServer:2022-Datacenter:latest                     Win2022Datacenter        latest
x64             WindowsServer                 MicrosoftWindowsServer  2022-datacenter-azure-edition-core  MicrosoftWindowsServer:WindowsServer:2022-datacenter-azure-edition-core:latest  Win2022AzureEditionCore  latest
x64             WindowsServer                 MicrosoftWindowsServer  2019-Datacenter                     MicrosoftWindowsServer:WindowsServer:2019-Datacenter:latest                     Win2019Datacenter        latest
x64             WindowsServer                 MicrosoftWindowsServer  2016-Datacenter                     MicrosoftWindowsServer:WindowsServer:2016-Datacenter:latest                     Win2016Datacenter        latest
x64             WindowsServer                 MicrosoftWindowsServer  2012-R2-Datacenter                  MicrosoftWindowsServer:WindowsServer:2012-R2-Datacenter:latest                  Win2012R2Datacenter      latest
x64             WindowsServer                 MicrosoftWindowsServer  2012-Datacenter                     MicrosoftWindowsServer:WindowsServer:2012-Datacenter:latest                     Win2012Datacenter        latest
x64             WindowsServer                 MicrosoftWindowsServer  2008-R2-SP1                         MicrosoftWindowsServer:WindowsServer:2008-R2-SP1:latest                         Win2008R2SP1             latest
```

A full list can be seen by adding the `--all` parameter. The image list can also be filtered by `--publisher` or `–-offer`. In this example, the list is filtered for all images, published by OpenLogic, with an offer that matches *0001-com-ubuntu-server-jammy*.

```bash
az vm image list --offer 0001-com-ubuntu-server-jammy --publisher Canonical --all --output table
```

Example partial output:

```output
Architecture    Offer                              Publisher    Sku              Urn                                                                       Version
--------------  ---------------------------------  -----------  ---------------  ------------------------------------------------------------------------  ---------------
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202204200          22.04.202204200
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202205060          22.04.202205060
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202205280          22.04.202205280
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202206040          22.04.202206040
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202206090          22.04.202206090
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202206160          22.04.202206160
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202206220          22.04.202206220
x64             0001-com-ubuntu-server-jammy       Canonical    22_04-lts        Canonical:0001-com-ubuntu-server-jammy:22_04-lts:22.04.202207060          22.04.202207060
```

> [!NOTE]
> Canonical has changed the **Offer** names they use for the most recent versions. Before Ubuntu 20.04, the **Offer** name is UbuntuServer. For Ubuntu 20.04 the **Offer** name is `0001-com-ubuntu-server-focal` and for Ubuntu 22.04 it's `0001-com-ubuntu-server-jammy`.

To deploy a VM using a specific image, take note of the value in the *Urn* column, which consists of the publisher, offer, SKU, and optionally a version number to [identify](cli-ps-findimage.md#terminology) the image. When specifying the image, the image version number can be replaced with `latest`, which selects the latest version of the distribution. In this example, the `--image` parameter is used to specify the latest version of a Ubuntu 22.04.

```bash
export MY_VM2_NAME="myVM2$RANDOM_SUFFIX"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM2_NAME --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts:latest --generate-ssh-keys
```

## Understand VM sizes

A virtual machine size determines the amount of compute resources such as CPU, GPU, and memory that are made available to the virtual machine. Virtual machines need to be sized appropriately for the expected work load. If workload increases, an existing virtual machine can be resized.

### VM Sizes

The following table categorizes sizes into use cases.

| Type                      |    Description       |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| [General purpose](../sizes-general.md)         | Balanced CPU-to-memory. Ideal for dev / test and small to medium applications and data solutions.  |
| [Compute optimized](../sizes-compute.md)    | High CPU-to-memory. Good for medium traffic applications, network appliances, and batch processes.        |
| [Memory optimized](../sizes-memory.md)     | High memory-to-core. Great for relational databases, medium to large caches, and in-memory analytics.                 |
| [Storage optimized](../sizes-storage.md)      | High disk throughput and IO. Ideal for Big Data, SQL, and NoSQL databases. |
| [GPU](../sizes-gpu.md)          | Specialized VMs targeted for heavy graphic rendering and video editing.       |
| [High performance](../sizes-hpc.md) | Our most powerful CPU VMs with optional high-throughput network interfaces (RDMA). |

### Find available VM sizes

To see a list of VM sizes available in a particular region, use the [az vm list-sizes](/cli/azure/vm) command.

```bash
az vm list-sizes --location $REGION --output table
```

Example partial output:

```output
  MaxDataDiskCount    MemoryInMb  Name                      NumberOfCores    OsDiskSizeInMb    ResourceDiskSizeInMb
------------------  ------------  ----------------------  ---------------  ----------------  ----------------------
4                   8192          Standard_D2ds_v4           2                1047552           76800
8                   16384         Standard_D4ds_v4           4                1047552           153600
16                  32768         Standard_D8ds_v4           8                1047552           307200
32                  65536         Standard_D16ds_v4          16               1047552           614400
32                  131072        Standard_D32ds_v4          32               1047552           1228800
32                  196608        Standard_D48ds_v4          48               1047552           1843200
32                  262144        Standard_D64ds_v4          64               1047552           2457600
4                   8192          Standard_D2ds_v5           2                1047552           76800
8                   16384         Standard_D4ds_v5           4                1047552           153600
16                  32768         Standard_D8ds_v5           8                1047552           307200
32                  65536         Standard_D16ds_v5          16               1047552           614400
32                  131072        Standard_D32ds_v5          32               1047552           1228800
32                  196608        Standard_D48ds_v5          48               1047552           1843200
32                  262144        Standard_D64ds_v5          64               1047552           2457600
32                  393216        Standard_D96ds_v5          96               1047552           3686400
```

### Create VM with specific size

In the previous VM creation example, a size was not provided, which results in a default size. A VM size can be selected at creation time using [az vm create](/cli/azure/vm) and the `--size` parameter.

```bash
export MY_VM3_NAME="myVM3$RANDOM_SUFFIX"
az vm create \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $MY_VM3_NAME \
    --image SuseSles15SP5 \
    --size Standard_D2ds_v4  \
    --generate-ssh-keys
```

### Resize a VM

After a VM has been deployed, it can be resized to increase or decrease resource allocation. You can view the current size of a VM with [az vm show](/cli/azure/vm):

```bash
az vm show --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query hardwareProfile.vmSize
```

Before resizing a VM, check if the desired size is available on the current Azure cluster. The [az vm list-vm-resize-options](/cli/azure/vm) command returns the list of sizes.

```bash
az vm list-vm-resize-options --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query [].name
```

If the desired size is available, the VM can be resized from a powered-on state, although it will be rebooted during the operation. Use the [az vm resize]( /cli/azure/vm) command to perform the resize.

```bash
az vm resize --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --size Standard_D4s_v3
```

If the desired size is not available on the current cluster, the VM needs to be deallocated before the resize operation can occur. Use the [az vm deallocate]( /cli/azure/vm) command to stop and deallocate the VM. Note that when the VM is powered back on, any data on the temporary disk may be removed. The public IP address also changes unless a static IP address is being used. Once deallocated, the resize can occur.

After the resize, the VM can be started.

```bash
az vm start --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME
```

## VM power states

An Azure VM can have one of many power states. This state represents the current state of the VM from the standpoint of the hypervisor.

### Power states

| Power State | Description |
|-------------|-------------|
| Starting    | Indicates the virtual machine is being started. |
| Running     | Indicates that the virtual machine is running. |
| Stopping    | Indicates that the virtual machine is being stopped. |
| Stopped     | Indicates that the virtual machine is stopped. Virtual machines in the stopped state still incur compute charges. |
| Deallocating| Indicates that the virtual machine is being deallocated. |
| Deallocated | Indicates that the virtual machine is removed from the hypervisor but still available in the control plane. Virtual machines in the Deallocated state do not incur compute charges. |
| -           | Indicates that the power state of the virtual machine is unknown. |

### Find the power state

To retrieve the state of a particular VM, use the [az vm get-instance-view](/cli/azure/vm) command. Be sure to specify a valid name for a virtual machine and resource group.

```bash
az vm get-instance-view \
    --name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --query instanceView.statuses[1] --output table
```

Output:

```output
Code                Level    DisplayStatus
------------------  -------  ---------------
PowerState/running  Info     VM running
```

To retrieve the power state of all the VMs in your subscription, use the [Virtual Machines - List All API](/rest/api/compute/virtualmachines/listall) with parameter **statusOnly** set to *true*.

## Management tasks

During the life-cycle of a virtual machine, you may want to run management tasks such as starting, stopping, or deleting a virtual machine. Additionally, you may want to create scripts to automate repetitive or complex tasks. Using the Azure CLI, many common management tasks can be run from the command line or in scripts.

### Get IP address

This command returns the private and public IP addresses of a virtual machine.

```bash
az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --output table
```

### Stop virtual machine

```bash
az vm stop --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME
```

### Start virtual machine

```bash
az vm start --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME
```

### Deleting VM resources

Depending on how you delete a VM, it may only delete the VM resource, not the networking and disk resources. You can change the default behavior to delete other resources when you delete the VM. For more information, see [Delete a VM and attached resources](../delete.md).

Deleting a resource group also deletes all resources in the resource group, like the VM, virtual network, and disk. The `--no-wait` parameter returns control to the prompt without waiting for the operation to complete. The `--yes` parameter confirms that you wish to delete the resources without an additional prompt to do so.

## Next steps

In this tutorial, you learned about basic VM creation and management such as how to:

> [!div class="checklist"]
> * Create and connect to a VM
> * Select and use VM images
> * View and use specific VM sizes
> * Resize a VM
> * View and understand VM state

Advance to the next tutorial to learn about VM disks.

> [!div class="nextstepaction"]
> [Create and Manage VM disks](./tutorial-manage-disks.md)