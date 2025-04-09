---
title: 'Quickstart: Create a Linux VM and SSH into it'
description: Learn how to create a Linux virtual machine in Azure and SSH into it using Azure CLI commands within an Exec Doc.
ms.topic: quickstart
ms.date: 10/12/2023
author: azureuser123
ms.author: azureuser123
ms.custom: innovation-engine, azurecli, linux-related-content
---

In this Exec Doc, you will learn how to create a Linux virtual machine (VM) in Azure using the Azure CLI and then SSH into the newly created VM. All commands have been configured to run non-interactively. Remember to update any variables if necessary and note that resources are appended with a random suffix to avoid naming conflicts in subsequent runs.

## Step 1: Set Environment Variables

In this step, we declare the environment variables that will be used throughout the Exec Doc. A random suffix is appended to the resource group and VM names to ensure uniqueness.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export MY_RESOURCE_GROUP_NAME="MyResourceGroup$RANDOM_SUFFIX"
export MY_VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
```

## Step 2: Create a Resource Group

This step creates a new resource group in the specified region.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxx",
  "location": "WestUS2",
  "managedBy": null,
  "name": "MyResourceGroupxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 3: Create a Linux Virtual Machine

Now you will create a Linux VM using the Ubuntu LTS image. The command includes the generation of SSH keys if they do not already exist. The default administrator username is set to "azureuser".

```bash
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --image UbuntuLTS --admin-username azureuser --generate-ssh-keys
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxx/providers/Microsoft.Compute/virtualMachines/MyLinuxVMxxxxx",
  "location": "WestUS2",
  "name": "MyLinuxVMxxxxx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.xxx.xxx.xxx"
}
```

## Step 4: Retrieve the VM's Public IP Address

Next, you retrieve the public IP address of the newly created VM. This value is stored in an environment variable for later use in the SSH command.

```bash
export PUBLIC_IP=$(az vm show -d --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query publicIps -o tsv)
```

## Step 5: SSH into the VM

Finally, use the SSH command to connect to your Linux VM. The SSH command includes the option to disable strict host key checking to avoid interactive prompts during the first connection.

```bash
ssh -o StrictHostKeyChecking=no azureuser@$PUBLIC_IP
```

This SSH command connects you to the VM using the default administrator account "azureuser". Once connected, you can start managing your Linux environment directly.

Happy learning and exploring your new Linux VM in Azure!