---
title: 'Quickstart: Use the Azure CLI to create an Ubuntu Virtual Machine and attach an Azure Data Disk'
description: In this quickstart, you learn how to use the Azure CLI to create an Ubuntu Linux virtual machine
author: ajoian
ms.service: virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/10/2024
ms.author: ajoian
ms.custom: mvc, devx-track-azurecli, mode-api, innovation-engine, linux-related-content
---

# Quickstart: Use the Azure CLI to create an Ubuntu Virtual Machine and attach an Azure Data Disk

This quickstart shows you how to use the Azure CLI to deploy an Ubuntu Linux virtual machine (VM) in Azure and attach an Azure Data Disk to the virtual machine. The Azure CLI is used to create and manage Azure resources via either the command line or scripts.

If you don't have an Azure subscription, create a [free account](https://azure.microsoft.com/free/?WT.mc_id=A261C142F) before you begin.

## Launch Azure Cloud Shell

The Azure Cloud Shell is a free interactive shell that you can use to run the steps in this article. It has common Azure tools preinstalled and configured to use with your account.

To open the Cloud Shell, just select **Try it** from the upper right corner of a code block. You can also open Cloud Shell in a separate browser tab by going to [https://shell.azure.com/bash](https://shell.azure.com/bash). Select **Copy** to copy the blocks of code, paste it into the Cloud Shell, and select **Enter** to run it.

If you prefer to install and use the CLI locally, this quickstart requires Azure CLI version 2.0.30 or later. Run `az --version` to find the version. If you need to install or upgrade, see [Install Azure CLI]( /cli/azure/install-azure-cli).

## Define environment variables

The first step is to define the environment variables. Environment variables are commonly used in Linux to centralize configuration data to improve consistency and maintainability of the system. Create the following environment variables to specify the names of resources that you create later in this tutorial:

```bash
export RANDOM_ID="$(openssl rand -hex 3)"
export MY_RESOURCE_GROUP_NAME="LinuxRG-$RANDOM_ID"
export REGION="westus3"
export ZONE="1"
export MY_VM_NAME="myVM$RANDOM_ID"
export MY_VM_USERNAME="azureadmin"
export MY_VM_SIZE='Standard_D4s_v3'
export MY_VM_IMAGE='Canonical:ubuntu-24_04-lts:server:latest'
export MY_DNS_LABEL="mydnslabel$RANDOM_ID"
export MY_AZURE_USER=$(az account show --query user.name --output tsv)
export FQDN="${MY_DNS_LABEL}.${REGION}.cloudapp.azure.com"
export LUN1_NAME="ZRS-$RANDOM_ID"
export LUN2_NAME="PSSDV2-$RANDOM_ID"
```

## Log in to Azure using the CLI

In order to run commands in Azure using the CLI, you need to log in first. Log in using the `az login` command.

## Create a resource group

A resource group is a container for related resources. All resources must be placed in a resource group. The [az group create](/cli/azure/group) command creates a resource group with the previously defined $MY_RESOURCE_GROUP_NAME and $REGION parameters.

```bash
az group create \
    --name $MY_RESOURCE_GROUP_NAME \
    --location $REGION -o JSON
```

Results:

<!-- expected_similarity=0.3 -->
```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-d161e6",
  "location": "westus3",
  "managedBy": null,
  "name": "LinuxRG-d161e6",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Create an Azure Linux Virtual Machine with a data disk

The following first example creates a VM named `$MY_VM_NAME` and creates SSH keys if they don't already exist in a default key location and creates a data disk as LUN0.

To improve the security of Linux virtual machines in Azure, you can integrate with Azure Active Directory authentication. Now you can use Azure AD as a core authentication platform. You can also SSH into the Linux VM by using Azure AD and OpenSSH certificate-based authentication. This functionality allows organizations to manage access to VMs with Azure role-based access control and Conditional Access policies.

Create a VM with the [az vm create](/cli/azure/vm#az-vm-create) command.

```bash
az vm create \
    --name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --admin-username $MY_VM_USERNAME \
    --authentication-type ssh \
    --assign-identity \
    --image $MY_VM_IMAGE \
    --nsg-rule SSH \
    --public-ip-address-allocation static \
    --public-ip-address-dns-name $MY_DNS_LABEL \
    --public-ip-sku Standard \
    --nic-delete-option Delete \
    --accelerated-networking true \
    --storage-sku os=Premium_LRS 0=Premium_LRS \
    --os-disk-caching ReadWrite \
    --os-disk-delete-option Delete \
    --os-disk-size-gb 30 \
    --data-disk-caching ReadOnly \
    --data-disk-sizes-gb 128 \
    --data-disk-delete-option Detach \
    --size $MY_VM_SIZE \
    --generate-ssh-keys \
    --zone $ZONE -o JSON
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "mydnslabelxxxxxx.westus3.cloudapp.azure.com",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-a36f5d/providers/Microsoft.Compute/virtualMachines/myVMa36f5d",
  "identity": {
    "systemAssignedIdentity": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "userAssignedIdentities": {}
  },
  "location": "westus3",
  "macAddress": "7C-1E-52-22-D8-72",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "xx.xx.xx.xx",
  "resourceGroup": "LinuxRG-a36f5d",
  "zones": ""
}
```

## Enable Azure AD Login for a Linux virtual machine in Azure

The following code example deploys a Linux VM and then installs the extension to enable an Azure AD Login for a Linux VM. VM extensions are small applications that provide post-deployment configuration and automation tasks on Azure virtual machines.

```bash
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --vm-name $MY_VM_NAME -o JSON
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "autoUpgradeMinorVersion": true,
  "enableAutomaticUpgrade": null,
  "forceUpdateTag": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-a36f5d/providers/Microsoft.Compute/virtualMachines/myVMa36f5d/extensions/AADSSHLoginForLinux",
  "instanceView": null,
  "location": "westus3",
  "name": "AADSSHLoginForLinux",
  "protectedSettings": null,
  "protectedSettingsFromKeyVault": null,
  "provisionAfterExtensions": null,
  "provisioningState": "Succeeded",
  "publisher": "Microsoft.Azure.ActiveDirectory",
  "resourceGroup": "LinuxRG-a36f5d",
  "settings": null,
  "suppressFailures": null,
  "tags": null,
  "type": "Microsoft.Compute/virtualMachines/extensions",
  "typeHandlerVersion": "1.0",
  "typePropertiesType": "AADSSHLoginForLinux"
}
```

In this scenario the LUN0 our first data disk is going to be formatted and mounted using the command below:

```bash
ssh $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun0 mklabel gpt mkpart primary ext4 0% 100%"
ssh $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun0"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mkfs.ext4 /dev/disk/azure/scsi1/lun0-part1"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /srv/LUN0"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun0-part1 /srv/LUN0"
```

Results:

<!-- expected_similarity=0.3 -->
```text
/dev/sdc: gpt partitions 1
mke2fs 1.47.0 (5-Feb-2023)
Discarding device blocks: done
Creating filesystem with 33553920 4k blocks and 8388608 inodes
Filesystem UUID: 1095e29c-07db-47ec-8b19-1ffcaf4f5628
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424, 20480000, 23887872

Allocating group tables: done
Writing inode tables: done
Creating journal (131072 blocks): done
Writing superblocks and filesystem accounting information: done

mkdir: created directory '/srv/LUN0'
mount: /dev/sdc1 mounted on /srv/LUN0.
```

In oder to update the /etc/fstab file, you can use the following command, and mount the LUN1 using it's unique identifier (UUID) together with the discard mount option:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun0-part1) /srv/LUN0 ext4 defaults,discard 0 0 | sudo tee -a /etc/fstab'
```

Results:

<!-- expected_similarity=0.3 -->
```text
UUID=1095e29c-07db-47ec-8b19-1ffcaf4f5628 /srv/LUN0 ext4 defaults,discard 0 0
```

## Attach a new disk to a VM

If you want to add a new, empty data disk on your VM, use the [az vm disk attach](/cli/azure/vm/disk) command with the `--new` parameter. If your VM is in an Availability Zone, the disk is automatically created in the same zone as the VM. For more information, see [Overview of Availability Zones](../../availability-zones/az-overview.md). The following example creates a disk named *$LUN2_NAME* that is 50 Gb in size:

```bash
az vm disk attach \
    --new \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --name $LUN1_NAME \
    --sku Premium_ZRS \
    --caching None \
    --lun 1 \
    --size-gb 50
```

In this second possible scenario the LUN1 is going to be our data disk, the following example shows how to format and mount the data disk.

```bash
ssh $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun1 mklabel gpt mkpart primary ext4 0% 100%"
ssh $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun1"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mkfs.ext4 /dev/disk/azure/scsi1/lun1-part1"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /srv/LUN1"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun1-part1 /srv/LUN1"
```

Results:

<!-- expected_similarity=0.3 -->
```text
/dev/sdd: gpt partitions 1
mke2fs 1.47.0 (5-Feb-2023)
Discarding device blocks: done
Creating filesystem with 13106688 4k blocks and 3276800 inodes
Filesystem UUID: 6e8ad233-5664-4f75-8ec6-3aa34f228868
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424

Allocating group tables: done
Writing inode tables: done
Creating journal (65536 blocks): done
Writing superblocks and filesystem accounting information: done

mkdir: created directory '/srv/LUN1'
mount: /dev/sdd1 mounted on /srv/LUN1.
```

In oder to update the /etc/fstab file, you can use the following command, and mount the LUN1 using it's unique identifier (UUID) together with the discard mount option:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun1-part1) /srv/LUN1 ext4 defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Results:

<!-- expected_similarity=0.3 -->
```text
UUID=0b1629d5-0cd5-41fd-9050-b2ed7e3f1028 /srv/LUN1 ext4 defaults,discard 0 0
```

## Attach an existing data disk to a VM

Lastly the third scenario is to attach an existing disk to a VM. You can use the [az vm disk attach](/cli/azure/vm/disk) command with the `--disk` parameter to attach an existing disk to a VM. The following example attaches an existing disk named *myDataDisk* to a VM named *myVM*:

First lets start by creating a new disk:

```bash
az disk create \
    --name $LUN2_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --location $REGION \
    --size-gb 128 \
    --disk-iops-read-write 3000 \
    --disk-mbps-read-write 125 \
    --sku PremiumV2_LRS \
    --zone $ZONE \
    --performance-plus false \
    --public-network-access Disabled -o JSON
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "encryptionSettingsCollection": null,
  "extendedLocation": null,
  "hyperVGeneration": null,
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/LinuxRG-e4c4b4/providers/Microsoft.Compute/disks/LUN2-e4c4b4",
  "lastOwnershipUpdateTime": null,
  "location": "westus3",
  "managedBy": null,
  "managedByExtended": null,
  "maxShares": 1,
  "name": "LUN2-e4c4b4",
  "networkAccessPolicy": "AllowAll",
  "optimizedForFrequentAttach": null,
  "osType": null,
  "propertyUpdatesInProgress": null,
  "provisioningState": "Succeeded",
  "publicNetworkAccess": "Disabled",
  "purchasePlan": null,
  "resourceGroup": "LinuxRG-e4c4b4",
  "securityProfile": null,
  "shareInfo": null,
  "sku": {
    "name": "PremiumV2_LRS",
    "tier": "Premium"
}
```

Then you can attach the disk to the VM:

```bash
LUN2_ID=$(az disk show --resource-group $MY_RESOURCE_GROUP_NAME --name $LUN2_NAME --query 'id' -o tsv)

az vm disk attach \
    --vm-name $MY_VM_NAME \
    --resource-group $MY_RESOURCE_GROUP_NAME \
    --disks $LUN2_ID \
    --sku PremiumV2_LRS \
    --lun 2
```

In this third scenario the LUN2 is going to be our data disk, the following example shows how to format and mount the data disk.

```bash
ssh $MY_VM_USERNAME@$FQDN -- "sudo parted -s -a optimal -- /dev/disk/azure/scsi1/lun2 mklabel gpt mkpart primary ext4 0% 100%"
ssh $MY_VM_USERNAME@$FQDN -- "sudo partprobe -s /dev/disk/azure/scsi1/lun2"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mkfs.ext4 /dev/disk/azure/scsi1/lun2-part1"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mkdir -v /srv/LUN2"
ssh $MY_VM_USERNAME@$FQDN -- "sudo mount -v /dev/disk/azure/scsi1/lun2-part1 /srv/LUN2"
```

Results:

<!-- expected_similarity=0.3 -->
```text
/dev/sde: gpt partitions 1
mke2fs 1.47.0 (5-Feb-2023)
Creating filesystem with 33553920 4k blocks and 8388608 inodes
Filesystem UUID: 0e0a110e-7d30-4235-ac4d-8ee59641e7c7
Superblock backups stored on blocks:
        32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
        4096000, 7962624, 11239424, 20480000, 23887872

Allocating group tables: done
Writing inode tables: done
Creating journal (131072 blocks): done
Writing superblocks and filesystem accounting information: done

mkdir: created directory '/srv/LUN2'
mount: /dev/sde1 mounted on /srv/LUN2.
```

In oder to update the /etc/fstab file, you can use the following command, and mount the LUN1 using it's unique identifier (UUID) together with the discard mount option:

```bash
ssh $MY_VM_USERNAME@$FQDN -- \
    'echo "UUID=$(sudo blkid -s UUID -o value /dev/disk/azure/scsi1/lun2-part1) /srv/LUN2 ext4 defaults,discard 0 0" | sudo tee -a /etc/fstab'
```

Results:

<!-- expected_similarity=0.3 -->
```text
UUID=4b54ed3b-2f5e-4fe7-b0e5-c40da6e3b8a8 /srv/LUN2 ext4 defaults,discard 0 0
```

## Check all mounted LUNs

To verify the mount points, you can use the following command:

```bash
ssh $MY_VM_USERNAME@$FQDN -- mount | egrep '(LUN0|LUN1|LUN2)'
```

Results:

<!-- expected_similarity=0.3 -->
```text
/dev/sdc1 on /srv/LUN0 type ext4 (rw,relatime)
/dev/sdd1 on /srv/LUN1 type ext4 (rw,relatime)
/dev/sde1 on /srv/LUN2 type ext4 (rw,relatime)
```

## SSH into the VM

You can now SSH into the VM by running the following command in your ssh client of choice:

```bash
ssh $MY_VM_USERNAME@$FQDN
```

## Next Steps

* [Learn about virtual machines](../index.yml)
* [Use Cloud-Init to initialize a Linux VM on first boot](tutorial-automate-vm-deployment.md)
* [Create custom VM images](tutorial-custom-images.md)
* [Load Balance VMs](../../load-balancer/quickstart-load-balancer-standard-public-cli.md)
