---
title: 'Tutorial: Create & manage a Virtual Machine Scale Set – Azure CLI'
description: Learn how to use the Azure CLI to create a Virtual Machine Scale Set, along with some common management tasks such as how to start and stop an instance, or change the scale set capacity.
author: ju-shim
ms.author: jushiman
ms.topic: tutorial
ms.service: azure-virtual-machine-scale-sets
ms.date: 10/05/2023
ms.reviewer: mimckitt
ms.custom: mimckitt, devx-track-azurecli, innovation-engine
---

# Tutorial: Create and manage a Virtual Machine Scale Set with Azure CLI

A Virtual Machine Scale Set allows you to deploy and manage a set of virtual machines. Throughout the lifecycle of a Virtual Machine Scale Set, you may need to run one or more management tasks. In this tutorial, you will learn how to:

- Create a resource group.
- Create a Virtual Machine Scale Set.
- Scale out and in.
- Stop, start, and restart VM instances.

> [!div class="checklist"]
> * Create a resource group.
> * Create a Virtual Machine Scale Set.
> * Scale out and in.
> * Stop, Start, and restart VM instances.

This article requires Azure CLI version 2.0.29 or later. If using Azure Cloud Shell, the latest version is already installed.

---

## Create a resource group

An Azure resource group is a container that holds related resources. A resource group must be created before a Virtual Machine Scale Set. This example uses a unique random suffix for the resource group name to avoid conflicts. Replace `<RANDOM_SUFFIX>` with a unique value.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="westus2"
export RESOURCE_GROUP_NAME="myResourceGroup$RANDOM_SUFFIX"

az group create --name $RESOURCE_GROUP_NAME --location $REGION
```

The resource group name is used when you create or modify a scale set throughout this tutorial.

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx/resourceGroups/myResourceGroupxxx",
  "location": "westus2",
  "managedBy": null,
  "name": "myResourceGroupxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

---

## Create a Virtual Machine Scale Set

> [!IMPORTANT]
> Starting November 2023, VM scale sets created using PowerShell and Azure CLI will default to Flexible Orchestration Mode if no orchestration mode is specified. For more information about this change and what actions you should take, go to [Breaking Change for VMSS PowerShell/CLI Customers - Microsoft Community Hub](https://techcommunity.microsoft.com/t5/azure-compute-blog/breaking-change-for-vmss-powershell-cli-customers/ba-p/3818295).

A Virtual Machine Scale Set is created using the `az vmss create` command. Replace `<VALID_IMAGE>` with a supported image such as `Ubuntu2204`. The VM SKU size is set to `Standard_B1s`. SSH keys are generated if they don’t exist.

```bash
export SCALE_SET_NAME="myScaleSet$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
export VALID_IMAGE="Ubuntu2204" # Use a valid image from the supported list

az vmss create \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $SCALE_SET_NAME \
  --orchestration-mode flexible \
  --image $VALID_IMAGE \
  --vm-sku "Standard_B1s" \
  --admin-username $ADMIN_USERNAME \
  --generate-ssh-keys
```

It takes a few minutes to create and configure the scale set resources and VM instances. A load balancer is also created to distribute traffic.

Verify the scale set creation:

```bash
az vmss list --resource-group $RESOURCE_GROUP_NAME --output table
```

---

## View information about VM instances

To view a list of VM instances in your scale set, use the `az vmss list-instances` command. Flexible orchestration mode assigns dynamically generated instance names.

```bash
az vmss list-instances \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $SCALE_SET_NAME \
  --output table
```

Results (example):

<!-- expected_similarity=0.3 -->

```text
InstanceId  ResourceGroup          VmId                                  ProvisioningState  Location
----------- ----------------------- ------------------------------------ -----------------  ----------
1           myResourceGroupxxx     e768fb62-0d58-4173-978d-1f564e4a925a Succeeded          westus2       
0           myResourceGroupxxx     5a2b34bd-1123-abcd-abcd-1623e0caf234 Succeeded          westus2
```

To see additional information about a specific VM instance, use the `az vm show` command:

```bash
export INSTANCE_NAME=$(az vmss list-instances --resource-group $RESOURCE_GROUP_NAME --name $SCALE_SET_NAME --query "[0].name" -o tsv)

az vm show --resource-group $RESOURCE_GROUP_NAME --name $INSTANCE_NAME
```

---

## Change the capacity of a scale set

By default, two VM instances are created in the scale set. To increase or decrease instances, use the `az vmss scale` command. For example, scale to 3 instances:

```bash
az vmss scale \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $SCALE_SET_NAME \
  --new-capacity 3
```

Verify the updated instance count:

```bash
az vmss list-instances \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $SCALE_SET_NAME \
  --output table
```

Results:

<!-- expected_similarity=0.3 -->

```text
InstanceId  ResourceGroup          VmId                                  ProvisioningState  Location
----------- ----------------------- ------------------------------------ -----------------  ----------
2           myResourceGroupxxx     54f68ce0-f123-abcd-abcd-4e6820cabccd Succeeded          westus2
1           myResourceGroupxxx     e768fb62-0d58-4173-978d-1f564e4a925a Succeeded          westus2       
0           myResourceGroupxxx     5a2b34bd-1123-abcd-abcd-1623e0caf234 Succeeded          westus2
```

---

## Stop instances in a scale set

To stop individual VMs in Flexible orchestration mode, retrieve their unique names:

```bash
export INSTANCE_NAME=$(az vmss list-instances --resource-group $RESOURCE_GROUP_NAME --name $SCALE_SET_NAME --query "[0].name" -o tsv)

az vm stop \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $INSTANCE_NAME
```

For all instances, use:

```bash
az vmss stop --resource-group $RESOURCE_GROUP_NAME --name $SCALE_SET_NAME
```

---

## Start instances in a scale set

To start individual stopped VMs, use:

```bash
az vm start \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $INSTANCE_NAME
```

To start all instances:

```bash
az vmss start \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $SCALE_SET_NAME
```

---

## Restart instances in a scale set

Restart specific instances:

```bash
az vm restart \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $INSTANCE_NAME
```

Or restart all instances:

```bash
az vmss restart \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $SCALE_SET_NAME
```

---

## Clean up resources

When you delete a resource group, all associated resources are deleted:

```bash
az group delete --name $RESOURCE_GROUP_NAME --no-wait --yes
```

---

## Next steps

In this tutorial, you learned how to perform common Virtual Machine Scale Set management tasks with Azure CLI:

> [!div class="checklist"]
> * Create a resource group.
> * Create a scale set.
> * View and use specific VM sizes.
> * Manually scale a scale set.
> * Perform common management tasks such as stopping, starting, and restarting instances.

Advance to the next tutorial to learn how to connect to scale set instances:

> [!div class="nextstepaction"]
> [Use data disks with scale sets](tutorial-connect-to-instances-cli.md)