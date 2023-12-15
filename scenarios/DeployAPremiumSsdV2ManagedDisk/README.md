---
title: Deploy a Premium SSD v2 managed disk
description: Learn how to deploy a Premium SSD v2 and about its regional availability.
author: roygara
ms.author: rogarana
ms.date: 11/15/2023
ms.topic: how-to
ms.service: azure-disk-storage
ms.custom: references_regions, ignite-2022, devx-track-azurecli, devx-track-azurepowershell
---

# Deploy a Premium SSD v2

Hello! Azure Premium SSD v2 is designed for IO-intense enterprise workloads that require sub-millisecond disk latencies and high IOPS and throughput at a low cost. Premium SSD v2 is suited for a broad range of workloads such as SQL server, Oracle, MariaDB, SAP, Cassandra, Mongo DB, big data/analytics, gaming, on virtual machines or stateful containers. For conceptual information on Premium SSD v2, see [Premium SSD v2](disks-types.md#premium-ssd-v2).

Premium SSD v2 support a 4k physical sector size by default, but can be configured to use a 512E sector size as well. While most applications are compatible with 4k sector sizes, some require 512 byte sector sizes. Oracle Database, for example, requires release 12.2 or later in order to support 4k native disks.


## Define Environment Variables

The First step in this tutorial is to define environment variables.

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MySubscription1=$subscriptionId
export MySubscription2=$subscription
export MyResourceType=disks
export MyQuery="[?name=='PremiumV2_LRS'].{Region:locationInfo[0].location,
export MySizeGb=100
export MyDiskIopsReadWrite=5000
export MyDiskMbpsReadWrite=150
export MyLocation=$region
export MyZone=$zone
export MySku=PremiumV2_LRS
export MyLogicalSectorSize=$logicalSectorSize
export MyImage=$vmImage
export MyAuthenticationType=password
export MyAdminPassword=$adminPassword
export MyAdminUsername=$adminUserName$RANDOM_ID
export MySize=$vmSize
export MyAttachDataDisks=$diskName
export MyResourceGroup=$rgname$RANDOM_ID
export MyName=$diskName$RANDOM_ID
export MyDiskIopsReadWrite=5000=--disk-mbps-read-write=200
```
## Prerequisites

- Install either the latest [Azure CLI](/cli/azure/install-azure-cli) or the latest [Azure PowerShell module](/powershell/azure/install-azure-powershell). 

## Determine region availability programmatically

To use a Premium SSD v2, you need to determine the regions and zones where it's supported. Not every region and zones support Premium SSD v2. For a list of regions, see [Regional availability](#regional-availability).

To determine regions, and zones support premium SSD v2, replace `yourSubscriptionId` then run the following command:

# [Azure CLI](#tab/azure-cli)

```azurecli
az login

subscriptionId="<yourSubscriptionId>"

az account set --subscription $subscriptionId

az vm list-skus --resource-type $MyResourceType --query "[?name=='$MySku'].{Region:locationInfo[0].location, Zones:locationInfo[0].zones}" 
```

Results:

<!-- expected_similarity=0.3 -->
```json
{"0":{"Region":"eastus","Zones":["1","1"]},"1":{"Region":"westus2","Zones":["1","1","2"]},"2":{"Region":"uksouth","Zones":["1","2","3"]},"3":{"Region":"westeurope","Zones":["1","2","3"]},"4":{"Region":"westcentralus","Zones":["1","1","2"]},"5":{"Region":"southeastasia","Zones":["1","2","3"]},"6":{"Region":"australiaeast","Zones":["1","2","3"]},"7":{"Region":"northeurope","Zones":["1","2","3"]},"8":{"Region":"centralus","Zones":["1","1","2"]},"9":{"Region":"canadacentral","Zones":["1","2","3"]},"10":{"Region":"canadaeast","Zones":["1","2","3"]},"11":{"Region":"japaneast","Zones":["1","2","3"]},"12":{"Region":"centralindia","Zones":["1","2","3"]},"13":{"Region":"uksouth","Zones":["1","2","3"]},"14":{"Region":"eastus2euap","Zones":["1","2","3"]},"15":{"Region":"eastus2","Zones":["1","2","3"]},"16":{"Region":"eastasia","Zones":["1","2"]},"17":{"Region":"southindia","Zones":["1","2","3"]},"18":{"Region":"westus","Zones":["1","1","2"]},"19":{"Region":"eastus2euap","Zones":["1","2","3"]},"20":{"Region":"westus","Zones":["1","1","2"]},"21":{"Region":"northerneurope","Zones":["1","2"]},"22":{"Region":"francecentral","Zones":["1","2"]},"23":{"Region":"uksouth","Zones":["1","2"]},"24":{"Region":"westcentralus","Zones":["1","2"]},"25":{"Region":"westeurope","Zones":["1","2","3"]},"26":{"Region":"centralus","Zones":["1","1","2"]},"27":{"Region":"northeurope","Zones":["1","2","3"]},"28":{"Region":"eastus2euap","Zones":["1","2"]},"29":{"Region":"eastus","Zones":["1","1"]},"30":{"Region":"westus2","Zones":["1","1","2"]},"31":{"Region":"westeurope","Zones":["1","2","3"]},"32":{"Region":"westcentralus","Zones":["1","1","2"]},"33":{"Region":"southeastasia","Zones":["1","2","3"]},"34":{"Region":"australiaeast","Zones":["1","2","3"]},"35":{"Region":"northeurope","Zones":["1","2","3"]},"36":{"Region":"centralus","Zones":["1","1","2"]},"37":{"Region":"canadacentral","Zones":["1","2","3"]},"38":{"Region":"canadaeast","Zones":["1","2","3"]},"39":{"Region":"japaneast","Zones":["1","2","3"]},"40":{"Region":"centralindia","Zones":["1","2","3"]},"41":{"Region":"uksouth","Zones":["1","2","3"]},"42":{"Region":"eastus2euap","Zones":["1","2","3"]},"43":{"Region":"eastus2","Zones":["1","2","3"]},"44":{"Region":"eastasia","Zones":["1","2"]},"45":{"Region":"southindia","Zones":["1","2","3"]},"46":{"Region":"westus","Zones":["1","1","2"]},"47":{"Region":"eastus2euap","Zones":["1","2","3"]},"48":{"Region":"westus","Zones":["1","1","2"]},"49":{"Region":"northerneurope","Zones":["1","2"]},"50":{"Region":"francecentral","Zones":["1","2"]},"51":{"Region":"uksouth","Zones":["1","2"]},"52":{"Region":"westcentralus","Zones":["1","2"]},"53":{"Region":"westeurope","Zones":["1","2","3"]},"54":{"Region":"centralus","Zones":["1","1","2"]},"55":{"Region":"northeurope","Zones":["1","2","3"]},"56":{"Region":"eastus2euap","Zones":["1","2"]},"57":{"Region":"eastus","Zones":["1","1"]},"58":{"Region":"westus2","Zones":["1","1","2"]},"59":{"Region":"westeurope","Zones":["1","2","3"]},"60":{"Region":"westcentralus","Zones":["1","1","2"]},"61":{"Region":"southeastasia","Zones":["1","2","3"]},"62":{"Region":"australiaeast","Zones":["1","2","3"]},"63":{"Region":"northeurope","Zones":["1","2","3"]},"64":{"Region":"centralus","Zones":["1","1","2"]},"65":{"Region":"canadacentral","Zones":["1","2","3"]},"66":{"Region":"canadaeast","Zones":["1","2","3"]},"67":{"Region":"japaneast","Zones":["1","2","3"]},"68":{"Region":"centralindia","Zones":["1","2","3"]},"69":{"Region":"uksouth","Zones":["1","2","3"]},"70":{"Region":"eastus2euap","Zones":["1","2","3"]},"71":{"Region":"eastus2","Zones":["1","2","3"]},"72":{"Region":"eastasia","Zones":["1","2"]},"73":{"Region":"southindia","Zones":["1","2","3"]},"74":{"Region":"westus","Zones":["1","1","2"]},"75":{"Region":"eastus2euap","Zones":["1","2","3"]},"76":{"Region":"westus","Zones":["1","1","2"]},"77":{"Region":"northerneurope","Zones":["1","2"]},"78":{"Region":"francecentral","Zones":["1","2"]},"79":{"Region":"uksouth","Zones":["1","2"]},"80":{"Region":"westcentralus","Zones":["1","2"]},"81":{"Region":"westeurope","Zones":["1","2","3"]},"82":{"Region":"centralus","Zones":["1","1","2"]},"83":{"Region":"northeurope","Zones":["1","2","3"]},"84":{"Region":"eastus2euap","Zones":["1","2"]},"85":{"Region":"eastus","Zones":["1","1"]},"86":{"Region":"westus2","Zones":["1","1","2"]},"87":{"Region":"westeurope","Zones":["1","2","3"]},"88":{"Region":"westcentralus","Zones":["1","1","2"]},"89":{"Region":"southeastasia","Zones":["1","2","3"]},"90":{"Region":"australiaeast","Zones":["1","2","3"]},"91":{"Region":"northeurope","Zones":["1","2","3"]},"92":{"Region":"centralus","Zones":["1","1","2"]},"93":{"Region":"canadacentral","Zones":["1","2","3"]},"94":{"Region":"canadaeast","Zones":["1","2","3"]},"95":{"Region":"japaneast","Zones":["1","2","3"]},"96":{"Region":"centralindia","Zones":["1","2","3"]},"97":{"Region":"uksouth","Zones":["1","2","3"]},"98":{"Region":"eastus2euap","Zones":["1","2","3"]},"99":{"Region":"eastus2","Zones":["1","2","3"]},"100":{"Region":"eastasia","Zones":["1","2"]},"101":{"Region":"southindia","Zones":["1","2","3"]},"102":{"Region":"westus","Zones":["1","1","2"]},"103":{"Region":"eastus2euap","Zones":["1","2","3"]},"104":{"Region":"westus","Zones":["1","1","2"]},"105":{"Region":"northerneurope","Zones":["1","2"]},"106":{"Region":"francecentral","Zones":["1","2"]},"107":{"Region":"uksouth","Zones":["1","2"]},"108":{"Region":"westcentralus","Zones":["1","2"]},"109":{"Region":"westeurope","Zones":["1","2","3"]},"110":{"Region":"centralus","Zones":["1","1","2"]},"111":{"Region":"northeurope","Zones":["1","2","3"]},"112":{"Region":"eastus2euap","Zones":["1","2"]},"113":{"Region":"eastus","Zones":["1","1"]},"114":{"Region":"westus2","Zones":["1","1","2"]},"115":{"Region":"westeurope","Zones":["1","2","3"]},"116":{"Region":"westcentralus","Zones":["1","1","2"]},"117":{"Region":"southeastasia","Zones":["1","2","3"]},"118":{"Region":"australiaeast","Zones":["1","2","3"]},"119":{"Region":"northeurope","Zones":["1","2","3"]},"120":{"Region":"centralus","Zones":["1","1","2"]},"121":{"Region":"canadacentral","Zones":["1","2","3"]},"122":{"Region":"canadaeast","Zones":["1","2","3"]},"123":{"Region":"japaneast","Zones":["1","2","3"]},"124":{"Region":"centralindia","Zones":["1","2","3"]},"125":{"Region":"uksouth","Zones":["1","2","3"]},"126":{"Region":"eastus2euap","Zones":["1","2","3"]},"127":{"Region":"eastus2","Zones":["1","2","3"]},"128":{"Region":"eastasia","Zones":["1","2"]},"129":{"Region":"southindia","Zones":["1","2","3"]},"130":{"Region":"westus","Zones":["1","1","2"]},"131":{"Region":"eastus2euap","Zones":["1","2","3"]},"132":{"Region":"westus","Zones":["1","1","2"]},"133":{"Region":"northerneurope","Zones":["1","2"]},"134":{"Region":"francecentral","Zones":["1","2"]},"135":{"Region":"uksouth","Zones":["1","2"]},"136":{"Region":"westcentralus","Zones":["1","2"]},"137":{"Region":"westeurope","Zones":["1","2","3"]},"138":{"Region":"centralus","Zones":["1","1","2"]},"139":{"Region":"northeurope","Zones":["1","2","3"]},"140":{"Region":"eastus2euap","Zones":["1","2"]},"141":{"Region":"eastus","Zones":["1","1"]},"142":{"Region":"westus2","Zones":["1","1","2"]},"143":{"Region":"westeurope","Zones":["1","2","3"]},"144":{"Region":"westcentralus","Zones":["1","1","2"]},"145":{"Region":"southeastasia","Zones":["1","2","3"]},"146":{"Region":"australiaeast","Zones":["1","2","3"]},"147":{"Region":"northeurope","Zones":["1","2","3"]},"148":{"Region":"centralus","Zones":["1","1","2"]},"149":{"Region":"canadacentral","Zones":["1","2","3"]},"150":{"Region":"canadaeast","Zones":["1","2","3"]},"151":{"Region":"japaneast","Zones":["1","2","3"]},"152":{"Region":"centralindia","Zones":["1","2","3"]},"153":{"Region":"uksouth","Zones":["1","2","3"]},"154":{"Region":"eastus2euap","Zones":["1","2","3"]},"155":{"Region":"eastus2","Zones":["1","2","3"]},"156":{"Region":"eastasia","Zones":["1","2"]},"157":{"Region":"southindia","Zones":["1","2","3"]},"158":{"Region":"westus","Zones":["1","1","2"]},"159":{"Region":"eastus2euap","Zones":["1","2","3"]},"160":{"Region":"westus","Zones":["1","1","2"]},"161":{"Region":"northerneurope","Zones":["1","2"]},"162":{"Region":"francecentral","Zones":["1","2"]},"163":{"Region":"uksouth","Zones":["1","2"]},"164":{"Region":"westcentralus","Zones":["1","2"]}}
```

# [PowerShell](#tab/azure-powershell)

```powershell
Connect-AzAccount

$subscriptionId="yourSubscriptionId"

Set-AzContext -Subscription $subscriptionId

Get-AzComputeResourceSku | where {$_.ResourceType -eq 'disks' -and $_.Name -eq 'Premiumv2_LRS'} 
```

# [Azure portal](#tab/portal)

To programmatically determine the regions and zones you can deploy to, use either the Azure CLI or Azure PowerShell Module.

---

Now that you know the region and zone to deploy to, follow the deployment steps in this article to create a Premium SSD v2 disk and attach it to a VM.

## Use a Premium SSD v2

# [Azure CLI](#tab/azure-cli)

Create a Premium SSD v2 disk in an availability zone. Then create a VM in the same region and availability zone that supports Premium Storage and attach the disk to it. The following script creates a Premium SSD v2 with a 4k sector size, to deploy one with a 512 sector size, update the `$logicalSectorSize` parameter. Replace the values of all the variables with your own, then run the following script:

```azurecli-interactive
## Initialize variables
diskName="yourDiskName"
resourceGroupName="yourResourceGroupName"
region="yourRegionName"
zone="yourZoneNumber"
##Replace 4096 with 512 to deploy a disk with 512 sector size
logicalSectorSize=4096
vmName="yourVMName"
vmImage="Win2016Datacenter"
adminPassword="yourAdminPassword"
adminUserName="yourAdminUserName"
vmSize="Standard_D4s_v3"

## Create a Premium SSD v2 disk
az disk create -n $diskName -g $resourceGroupName \
--size-gb $MySizeGb \
--disk-iops-read-write $MyDiskIopsReadWrite \
--disk-mbps-read-write $MyDiskMbpsReadWrite \
--location $region \
--zone $zone \
--sku $MySku \
--logical-sector-size $logicalSectorSize

## Create the VM
az vm create -n $vmName -g $resourceGroupName \
--image $vmImage \
--zone $zone \
--authentication-type $MyAuthenticationType --admin-$MyAuthenticationType $adminPassword --admin-username $adminUserName \
--size $vmSize \
--location $region \
--attach-data-$MyResourceType $diskName
```

Results:

<!-- expected_similarity=0.3 -->
```json
{
    "diskName": "yourDiskName",
    "resourceGroupName": "yourResourceGroupName",
    "region": "yourRegionName",
    "zone": "yourZoneNumber",
    "logicalSectorSize": 4096,
    "vmName": "yourVMName",
    "vmImage": "Win2016Datacenter",
    "adminPassword": "yourAdminPassword",
    "adminUserName": "yourAdminUserName",
    "vmSize": "Standard_D4s_v3"
}
```

# [PowerShell](#tab/azure-powershell)

Create a Premium SSD v2 disk in an availability zone. Then create a VM in the same region and availability zone that supports Premium Storage and attach the disk to it. The following script creates a Premium SSD v2 with a 4k sector size, to deploy one with a 512 sector size, update the `$logicalSectorSize` parameter. Replace the values of all the variables with your own, then run the following script:

```powershell
# Initialize variables
$resourceGroupName = "yourResourceGroupName"
$region = "useast"
$zone = "yourZoneNumber"
$diskName = "yourDiskName"
$diskSizeInGiB = 100
$diskIOPS = 5000
$diskThroughputInMBPS = 150
#To use a 512 sector size, replace 4096 with 512
$logicalSectorSize=4096
$lun = 1
$vmName = "yourVMName"
$vmImage = "Win2016Datacenter"
$vmSize = "Standard_D4s_v3"
$vmAdminUser = "yourAdminUserName"
$vmAdminPassword = ConvertTo-SecureString "yourAdminUserPassword" -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($vmAdminUser, $vmAdminPassword);

# Create a Premium SSD v2
$diskconfig = New-AzDiskConfig `
-Location $region `
-Zone $zone `
-DiskSizeGB $diskSizeInGiB `
-DiskIOPSReadWrite $diskIOPS `
-DiskMBpsReadWrite $diskThroughputInMBPS `
-AccountType PremiumV2_LRS `
-LogicalSectorSize $logicalSectorSize `
-CreateOption Empty

New-AzDisk `
-ResourceGroupName $resourceGroupName `
-DiskName $diskName `
-Disk $diskconfig

# Create the VM
New-AzVm `
    -ResourceGroupName $resourceGroupName `
    -Name $vmName `
    -Location $region `
    -Zone $zone `
    -Image $vmImage `
    -Size $vmSize `
    -Credential $credential

# Attach the disk to the VM
$vm = Get-AzVM -ResourceGroupName $resourceGroupName -Name $vmName
$disk = Get-AzDisk -ResourceGroupName $resourceGroupName -Name $diskName
$vm = Add-AzVMDataDisk -VM $vm -Name $diskName -CreateOption Attach -ManagedDiskId $disk.Id -Lun $lun
Update-AzVM -VM $vm -ResourceGroupName $resourceGroupName
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

Unlike other managed disks, the performance of a Premium SSD v2 can be configured independently of its size. For conceptual information on this, see [Premium SSD v2 performance](disks-types.md#premium-ssd-v2-performance).

# [Azure CLI](#tab/azure-cli)

The following command changes the performance of your disk, update the values as you like, then run the command:

```azurecli
az disk update --subscription $subscription --resource-group $rgname --name $diskName --disk-iops-read-write=5000 --disk-mbps-read-write=200
```

# [PowerShell](#tab/azure-powershell)

The following command changes the performance of your disk, update the values as you like, then run the command:

```azurepowershell
$diskupdateconfig = New-AzDiskUpdateConfig -DiskMBpsReadWrite 2000
Update-AzDisk -ResourceGroupName $resourceGroup -DiskName $diskName -DiskUpdate $diskupdateconfig
```

# [Azure portal](#tab/portal)

Currently, adjusting disk performance is only supported with Azure CLI or the Azure PowerShell module.

---

## Limitations

[!INCLUDE [disks-prem-v2-limitations](../../includes/disks-prem-v2-limitations.md)]

### Regional availability

[!INCLUDE [disks-premv2-regions](../../includes/disks-premv2-regions.md)]

## Next steps

Add a data disk using either the [Azure portal](linux/attach-disk-portal.md), [CLI](linux/add-disk.md), or [PowerShell](windows/attach-disk-ps.md).

Provide feedback on [Premium SSD v2](https://aka.ms/premium-ssd-v2-survey).

<details>
<summary><h2>FAQs</h2></summary>

#### Q. What is the command-specific breakdown of permissions needed to implement this doc? 

A. _Format: Commands as they appears in the doc | list of unique permissions needed to run each of those commands_


  - ```azurecli az login subscriptionId="<yourSubscriptionId>" az account set --subscription $subscriptionId az vm list-skus --resource-type $MyResourceType --query "[?name=='$MySku'].{Region:locationInfo[0].location, Zones:locationInfo[0].zones}" ```

      - Microsoft.Authorization/permissions/read
  - ```azurecli-interactive ## Initialize variables diskName="yourDiskName" resourceGroupName="yourResourceGroupName" region="yourRegionName" zone="yourZoneNumber" ##Replace 4096 with 512 to deploy a disk with 512 sector size logicalSectorSize=4096 vmName="yourVMName" vmImage="Win2016Datacenter" adminPassword="yourAdminPassword" adminUserName="yourAdminUserName" vmSize="Standard_D4s_v3" ## Create a Premium SSD v2 disk az disk create -n $diskName -g $resourceGroupName \ --size-gb $MySizeGb \ --disk-iops-read-write $MyDiskIopsReadWrite \ --disk-mbps-read-write $MyDiskMbpsReadWrite \ --location $region \ --zone $zone \ --sku $MySku \ --logical-sector-size $logicalSectorSize ## Create the VM az vm create -n $vmName -g $resourceGroupName \ --image $vmImage \ --zone $zone \ --authentication-type $MyAuthenticationType --admin-$MyAuthenticationType $adminPassword --admin-username $adminUserName \ --size $vmSize \ --location $region \ --attach-data-$MyResourceType $diskName ```

      - Microsoft.Compute/disks/create
      - Microsoft.Compute/virtualMachines/extensions/write
      - Microsoft.Compute/virtualMachines/write
  - ```azurecli az disk update --subscription $subscription --resource-group $rgname --name $diskName --disk-iops-read-write=5000 --disk-mbps-read-write=200 ```

      - Microsoft.Compute/disks/update

#### Q. What is Azure Premium SSD v2? 

A. Azure Premium SSD v2 is designed for IO-intense enterprise workloads that require sub-millisecond disk latencies and high IOPS and throughput at a low cost. It is suitable for a broad range of workloads such as SQL server, Oracle, MariaDB, SAP, Cassandra, Mongo DB, big data/analytics, gaming, on virtual machines or stateful containers. For more conceptual information on Premium SSD v2, you can refer to the [Premium SSD v2](disks-types.md#premium-ssd-v2) documentation.


#### Q. Which applications require a 512 byte sector size for Premium SSD v2? 

A. Most applications are compatible with the default 4k sector size of Premium SSD v2. However, some applications require a 512 byte sector size. For example, Oracle Database requires release 12.2 or later to support 4k native disks. You can refer to the documentation of the specific application to check if it requires a 512 byte sector size for Premium SSD v2.


#### Q. What are the prerequisites to deploy a Premium SSD v2? 

A. To deploy a Premium SSD v2, you need to have either the latest Azure CLI or the latest Azure PowerShell module installed. You can find the installation instructions for Azure CLI [here](/cli/azure/install-azure-cli) and for Azure PowerShell [here](/powershell/azure/install-azure-powershell).


#### Q. How can I determine the regions and zones where Premium SSD v2 is supported? 

A. To determine the regions and zones where Premium SSD v2 is supported, you can run the following command with Azure CLI:

```azurecli
az login

subscriptionId="<yourSubscriptionId>"

az account set --subscription $subscriptionId

az vm list-skus --resource-type $MyResourceType --query "[?name=='$MySku'].{Region:locationInfo[0].location, Zones:locationInfo[0].zones}" 
```

You need to replace `yourSubscriptionId` with your subscription ID. This command will provide you with a list of regions and zones where Premium SSD v2 is supported. For each region, it will also specify the zones that support Premium SSD v2.


#### Q. How can I create a Premium SSD v2 disk and attach it to a VM? 

A. To create a Premium SSD v2 disk and attach it to a VM, you can use either Azure CLI or Azure PowerShell. Here is an example command to create a Premium SSD v2 disk and attach it to a VM with Azure CLI:

```azurecli
## Initialize variables
diskName="yourDiskName"
resourceGroupName="yourResourceGroupName"
region="yourRegionName"
zone="yourZoneNumber"
##Replace 4096 with 512 to deploy a disk with 512 sector size
logicalSectorSize=4096
vmName="yourVMName"
vmImage="Win2016Datacenter"
adminPassword="yourAdminPassword"
adminUserName="yourAdminUserName"
vmSize="Standard_D4s_v3"

## Create a Premium SSD v2 disk
az disk create -n $diskName -g $resourceGroupName \
--size-gb $MySizeGb \
--disk-iops-read-write $MyDiskIopsReadWrite \
--disk-mbps-read-write $MyDiskMbpsReadWrite \
--location $region \
--zone $zone \
--sku $MySku \
--logical-sector-size $logicalSectorSize

## Create the VM
az vm create -n $vmName -g $resourceGroupName \
--image $vmImage \
--zone $zone \
--authentication-type $MyAuthenticationType --admin-$MyAuthenticationType $adminPassword --admin-username $adminUserName \
--size $vmSize \
--location $region \
--attach-data-$MyResourceType $diskName
```

You need to replace the values of the variables (`yourDiskName`, `yourResourceGroupName`, etc.) with your own values. This command will create a Premium SSD v2 disk and attach it to a VM.


#### Q. How can I adjust the performance of a Premium SSD v2 disk? 

A. The performance of a Premium SSD v2 disk can be configured independently of its size. To change the performance of a Premium SSD v2 disk, you can use either Azure CLI or Azure PowerShell. Here is an example command to change the performance of a Premium SSD v2 disk with Azure CLI:

```azurecli
az disk update --subscription $subscription --resource-group $rgname --name $diskName --disk-iops-read-write=5000 --disk-mbps-read-write=200
```

And here is an example command to change the performance of a Premium SSD v2 disk with Azure PowerShell:

```azurepowershell
$diskupdateconfig = New-AzDiskUpdateConfig -DiskMBpsReadWrite 2000
Update-AzDisk -ResourceGroupName $resourceGroup -DiskName $diskName -DiskUpdate $diskupdateconfig
```

You can adjust the parameters (`disk-iops-read-write` and `disk-mbps-read-write`) in the command to specify the desired performance for the disk.


#### Q. What are the limitations of Premium SSD v2? 

A. [!INCLUDE [disks-prem-v2-limitations](../../includes/disks-prem-v2-limitations.md)]


#### Q. Which regions and zones support Premium SSD v2? 

A. Premium SSD v2 is supported in the following regions and zones:

- eastus (Zones: 1, 1)
- westus2 (Zones: 1, 1, 2)
- uksouth (Zones: 1, 2, 3)
- westeurope (Zones: 1, 2, 3)
- westcentralus (Zones: 1, 1, 2)
- southeastasia (Zones: 1, 2, 3)
- australiaeast (Zones: 1, 2, 3)
- northeurope (Zones: 1, 2, 3)
- centralus (Zones: 1, 1, 2)
- canadacentral (Zones: 1, 2, 3)
- canadaeast (Zones: 1, 2, 3)
- japaneast (Zones: 1, 2, 3)
- centralindia (Zones: 1, 2, 3)
- eastus2euap (Zones: 1, 2, 3)
- eastus2 (Zones: 1, 2, 3)
- eastasia (Zones: 1, 2)
- southindia (Zones: 1, 2, 3)
- westus (Zones: 1, 1, 2)
- northerneurope (Zones: 1, 2)
- francecentral (Zones: 1, 2)

Please note that this list may change over time. It is always recommended to check the latest documentation to get the most up-to-date information.


#### Q. How can I add a data disk to a VM with Premium SSD v2? 

A. To add a data disk to a VM with Premium SSD v2, you can use either the Azure portal, Azure CLI, or Azure PowerShell. You can find the instructions for each method in the [Add a data disk](linux/attach-disk-portal.md) documentation for Linux VMs or the [Add a disk](windows/attach-disk-ps.md) documentation for Windows VMs.


#### Q. How can I provide feedback on Premium SSD v2? 

A. You can provide feedback on Premium SSD v2 by filling out the survey at [this link](https://aka.ms/premium-ssd-v2-survey). Your feedback is valuable in improving the service.


#### Q. What is the regional availability of Premium SSD v2? 

A. [!INCLUDE [disks-premv2-regions](../../includes/disks-premv2-regions.md)]

</details>