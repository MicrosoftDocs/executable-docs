---
title: Deploy a Premium SSD v2 managed disk
description: Learn how to deploy a Premium SSD v2 and about its regional availability.
author: roygara
ms.author: rogarana
ms.date: 08/12/2024
ms.topic: how-to
ms.service: azure-disk-storage
ms.custom: references_regions, devx-track-azurecli, devx-track-azurepowershell
---

# Deploy a Premium SSD v2

Azure Premium SSD v2 is designed for IO-intense enterprise workloads that require sub-millisecond disk latencies and high IOPS and throughput at a low cost. Premium SSD v2 is suited for a broad range of workloads such as SQL server, Oracle, MariaDB, SAP, Cassandra, Mongo DB, big data/analytics, gaming, on virtual machines or stateful containers. For conceptual information on Premium SSD v2, see [Premium SSD v2](disks-types.md#premium-ssd-v2).

Premium SSD v2 support a 4k physical sector size by default, but can be configured to use a 512E sector size as well. While most applications are compatible with 4k sector sizes, some require 512 byte sector sizes. Oracle Database, for example, requires release 12.2 or later in order to support 4k native disks.

## Limitations

[!INCLUDE [disks-prem-v2-limitations](./includes/disks-prem-v2-limitations.md)]

### Regional availability

[!INCLUDE [disks-premv2-regions](./includes/disks-premv2-regions.md)]

## Prerequisites

- Install either the latest [Azure CLI](/cli/azure/install-azure-cli) or the latest [Azure PowerShell module](/powershell/azure/install-azure-powershell). 

## Determine region availability programmatically

Since not every region and zone supports Premium SSD v2, you can use the Azure CLI or PowerShell to determine region and zone supportability.

# [Azure CLI](#tab/azure-cli)

To determine the regions and zones that support Premium SSD v2, replace `yourSubscriptionId` with your subscription, and then run the [az vm list-skus](/cli/azure/vm#az-vm-list-skus) command:

```markdown
az login

subscriptionId="<yourSubscriptionId>"

az account set --subscription $subscriptionId

az vm list-skus --resource-type disks --query "[?name=='PremiumV2_LRS'].{Region:locationInfo[0].location, Zones:locationInfo[0].zones}" 
```

# [PowerShell](#tab/azure-powershell)

To determine the regions and zones that support Premium SSD v2, replace `yourSubscriptionId` with your subscription, and then run the [Get-AzComputeResourceSku](/powershell/module/az.compute/get-azcomputeresourcesku) command:

```powershell
Connect-AzAccount

$subscriptionId="yourSubscriptionId"

Set-AzContext -Subscription $subscriptionId

Get-AzComputeResourceSku | where {$_.ResourceType -eq 'disks' -and $_.Name -eq 'Premiumv2_LRS'} 
```

# [Azure portal](#tab/portal)

To programmatically determine the regions and zones you can deploy to, use either the Azure CLI, Azure PowerShell Module. 

---

## Create a resource group

An [Azure resource group][azure-resource-group] is a logical group in which Azure resources are deployed and managed. When you create a resource group, you're prompted to specify a location. This location is the storage location of your resource group metadata and where your resources run in Azure if you don't specify another region during resource creation

Create a resource group using the [`az group create`][az-group-create] command.

```azurecli-interactive
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_ID"
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

Now that you know the region and zone to deploy to, follow the deployment steps in this article to create a Premium SSD v2 disk and attach it to a VM.

## Use a Premium SSD v2

Create a Premium SSD v2 disk in an availability zone by using the [az disk create](/cli/azure/disk#az-disk-create) command. 

The following script creates a Premium SSD v2 with a 4k sector size, to deploy one with a 512 sector size, update the `$LOGICAL_SECTOR_SIZE` parameter. Replace the values of all the variables with your own, then run the following script:

```azurecli-interactive
## Create a Premium SSD v2 disk
export MY_DISK_NAME="myDisk$RANDOM_ID"
##Replace 4096 with 512 to deploy a disk with 512 sector size
export LOGICAL_SECTOR_SIZE=4096
az disk create -n $MY_DISK_NAME -g $MY_RESOURCE_GROUP_NAME \
--size-gb 100 \
--disk-iops-read-write 5000 \
--disk-mbps-read-write 150 \
--location $REGION \
--sku PremiumV2_LRS \
--zone "1" \
--logical-sector-size $LOGICAL_SECTOR_SIZE
```

## Create the VM

Then create a VM in the same region and availability zone that supports Premium Storage and attach the disk to it by using the [az vm create](/cli/azure/vm#az-vm-create) command. 

```azurecli-interactive
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_VM_IMAGE="Win2016Datacenter"
export MY_VM_SIZE="Standard_D4s_v3"
export AZURE_USERNAME=azureuser
export AZURE_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9@#%^&*()-_=+[]{}|;:,.<>?')
az vm create -n $MY_VM_NAME -g $MY_RESOURCE_GROUP_NAME \
--image $MY_VM_IMAGE \
--authentication-type password --admin-password $AZURE_PASSWORD --admin-username $AZURE_USERNAME \
--size $MY_VM_SIZE \
--location $REGION \
--zone "1" \
--attach-data-disks $MY_DISK_NAME 
```

# [PowerShell](#tab/azure-powershell)

Create a Premium SSD v2 disk in an availability zone by using the [New-AzDiskConfig](/powershell/module/az.compute/new-azdiskconfig) to define the configuration of your disk and the [New-AzDisk](/powershell/module/az.compute/new-azdisk) command to create your disk. Next, create a VM in the same region and availability zone that supports Premium Storage by using the [az vm create](/cli/azure/vm#az-vm-create). Finally, attach the disk to it by using the [Get-AzVM](/powershell/module/az.compute/get-azvm) command to identify variables for the virtual machine, the [Get-AzDisk](/powershell/module/az.compute/get-azdisk) command to identify variables for the disk, the [Add-AzVMDataDisk](/powershell/module/az.compute/add-azvmdatadisk) command to add the disk, and the [Update-AzVM](/powershell/module/az.compute/update-azvm) command to attach the new disk to the virtual machine. 

The following script creates a Premium SSD v2 with a 4k sector size, to deploy one with a 512 sector size, update the `$LOGICAL_SECTOR_SIZE` parameter. Replace the values of all the variables with your own, then run the following script:

```powershell
# Initialize variables
$MY_RESOURCE_GROUP_NAME = "yourResourceGroupName"
$REGION = "useast"
$zone = "yourZoneNumber"
$MY_DISK_NAME = "yourMY_DISK_NAME"
$diskSizeInGiB = 100
$diskIOPS = 5000
$diskThroughputInMBPS = 150
#To use a 512 sector size, replace 4096 with 512
$LOGICAL_SECTOR_SIZE=4096
$lun = 1
$MY_VM_NAME = "yourMY_VM_NAME"
$MY_VM_IMAGE = "Win2016Datacenter"
$MY_VM_SIZE = "Standard_D4s_v3"
$vmAdminUser = "yourAdminUserName"
$vmAdminPassword = ConvertTo-SecureString "yourAdminUserPassword" -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($vmAdminUser, $vmAdminPassword);

# Create a Premium SSD v2
$diskconfig = New-AzDiskConfig `
-Location $REGION `
-Zone $zone `
-DiskSizeGB $diskSizeInGiB `
-DiskIOPSReadWrite $diskIOPS `
-DiskMBpsReadWrite $diskThroughputInMBPS `
-AccountType PremiumV2_LRS `
-LOGICAL_SECTOR_SIZE $LOGICAL_SECTOR_SIZE `
-CreateOption Empty

New-AzDisk `
-ResourceGroupName $MY_RESOURCE_GROUP_NAME `
-MY_DISK_NAME $MY_DISK_NAME `
-Disk $diskconfig

# Create the VM
New-AzVm `
    -ResourceGroupName $MY_RESOURCE_GROUP_NAME `
    -Name $MY_VM_NAME `
    -Location $REGION `
    -Zone $zone `
    -Image $MY_VM_IMAGE `
    -Size $MY_VM_SIZE `
    -Credential $credential

# Attach the disk to the VM
$vm = Get-AzVM -ResourceGroupName $MY_RESOURCE_GROUP_NAME -Name $MY_VM_NAME
$disk = Get-AzDisk -ResourceGroupName $MY_RESOURCE_GROUP_NAME -Name $MY_DISK_NAME
$vm = Add-AzVMDataDisk -VM $vm -Name $MY_DISK_NAME -CreateOption Attach -ManagedDiskId $disk.Id -Lun $lun
Update-AzVM -VM $vm -ResourceGroupName $MY_RESOURCE_GROUP_NAME
```

# [Azure portal](#tab/portal)

1. Sign in to the [Azure portal](https://portal.azure.com/).
1. Navigate to **Virtual machines** and follow the normal VM creation process.
1. On the **Basics** page, select a [supported region](#regional-availability) and set **Availability options** to **Availability zone**.
1. Select one of the zones.
1. Fill in the rest of the values on the page as you like.

    :::image type="content" source="media/disks-deploy-premium-v2/premv2-portal-deploy.png" alt-text="Screenshot of the basics page, region and availability options and zones highlighted." lightbox="media/disks-deploy-premium-v2/premv2-portal-deploy.png":::

1. Proceed to the **Disks** page.
1. Under **Data disks** select **Create and attach a new disk**.

    :::image type="content" source="media/disks-deploy-premium-v2/premv2-create-data-disk.png" alt-text="Screenshot highlighting create and attach a new disk on the disk page." lightbox="media/disks-deploy-premium-v2/premv2-create-data-disk.png":::

1. Select the **Disk SKU** and select **Premium SSD v2**.

    :::image type="content" source="media/disks-deploy-premium-v2/premv2-select.png" alt-text="Screenshot selecting Premium SSD v2 SKU." lightbox="media/disks-deploy-premium-v2/premv2-select.png":::

1. Select whether you'd like to deploy a 4k or 512 logical sector size.

    :::image type="content" source="media/disks-deploy-premium-v2/premv2-sector-size.png" alt-text="Screenshot of deployment logical sector size deployment options." lightbox="media/disks-deploy-premium-v2/premv2-sector-size.png":::

1. Proceed through the rest of the VM deployment, making any choices that you desire.

You've now deployed a VM with a premium SSD v2.

---

## Adjust disk performance

You can adjust the performance of a Premium SSD v2 disk four times within a 24 hour period. Creating a disk counts as one of these times, so for the first 24 hours after creating a premium SSD v2 disk you can only adjust its performance up to three times.

For conceptual information on adjusting disk performance, see [Premium SSD v2 performance](disks-types.md#premium-ssd-v2-performance).

# [Azure CLI](#tab/azure-cli)

Use the [az disk update](/cli/azure/disk#az-disk-update) command to change the performance configuration of your Premium SSD v2 disk. For example, you can use the `disk-iops-read-write` parameter to adjust the max IOPS limit, and the `disk-mbps-read-write` parameter to adjust the max throughput limit of your Premium SSD v2 disk.  

The following command adjusts the performance of your disk. Update the values in the command, and then run it:

```azurecli
az disk update --subscription $subscription --resource-group $rgname --name $MY_DISK_NAME --disk-iops-read-write=5000 --disk-mbps-read-write=200
```

# [PowerShell](#tab/azure-powershell)

Use the [New-AzDiskUpdateConfig](/powershell/module/az.compute/new-azdiskupdateconfig) command to define your new performance configuration values for your Premium SSD v2 disks, and then use the [Update-AzDisk](/powershell/module/az.compute/update-azdisk) command to apply your configuration changes to your disk. For example, you can use the `DiskIOPSReadWrite` parameter to adjust the max IOPS limit, and the `DiskMBpsReadWrite` parameter to adjust the max throughput limit of your Premium SSD v2 disk.  

The following command adjusts the performance of your disk. Update the values in the command, and then run it:

```azurepowershell
$diskupdateconfig = New-AzDiskUpdateConfig -DiskIOPSReadWrite 5000 -DiskMBpsReadWrite 200
Update-AzDisk -ResourceGroupName $resourceGroup -MY_DISK_NAME $MY_DISK_NAME -DiskUpdate $diskupdateconfig
```

# [Azure portal](#tab/portal)

1. Navigate to the disk you'd like to modify in the [Azure portal](https://portal.azure.com/).
1. Select **Size + Performance**
1. Set the values for **Disk IOPS** or **Disk throughput (MB/s)** or both, to meet your needs, then select **Save**.

---

## Next steps

Add a data disk by using either the [Azure portal](linux/attach-disk-portal.yml), [Azure CLI](linux/add-disk.md), or [PowerShell](windows/attach-disk-ps.md).

Provide feedback on [Premium SSD v2](https://aka.ms/premium-ssd-v2-survey).