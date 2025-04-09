---
title: 'Quickstart: Create a Linux VM and SSH into it using Azure CLI'
description: Learn how to quickly create a Linux Virtual Machine in Azure and retrieve its public IP address to SSH into the VM using Azure CLI.
ms.topic: quickstart
ms.date: 10/12/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, linux, azurecli
---

# Quickstart: Create a Linux VM and SSH into it using Azure CLI

This Exec Doc demonstrates how to create a new resource group, deploy a Linux Virtual Machine (VM) with Ubuntu2204 image, retrieve its public IP address, and then show the command to SSH into the VM. All environment variables such as resource group name and VM name include a random suffix to avoid conflicts with existing resources on subsequent executions.

## Step 1: Create a Resource Group

In this section, we create a resource group in the "WestUS2" region. A random suffix is appended to the resource group name to ensure uniqueness.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export MY_RESOURCE_GROUP_NAME="MyResourceGroup$RANDOM_SUFFIX"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 --> 

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxxx",
  "location": "WestUS2",
  "managedBy": null,
  "name": "MyResourceGroupxxxxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 2: Create a Linux Virtual Machine

This step deploys a Linux VM using the Ubuntu2204 image. The admin username is set to "azureuser" and SSH keys are automatically generated. A unique VM name is created using the same random suffix.

```bash
export VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $VM_NAME --image Ubuntu2204 --admin-username azureuser --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 --> 

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachines/MyLinuxVMxxxxxx",
  "location": "WestUS2",
  "name": "MyLinuxVMxxxxxx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "xx.xx.xx.xx"
}
```

## Step 3: Retrieve the Public IP Address of the VM

After the VM is created, this command retrieves the public IP address assigned to the VM. This IP is used to connect via SSH later.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $VM_NAME --query "[].virtualMachine.network.publicIpAddresses[*].ipAddress" -o tsv)
echo $PUBLIC_IP
```

Results:

<!-- expected_similarity=0.3 --> 

```text
xx.xx.xx.xx
```

## Step 4: SSH into the Linux VM

Finally, use the public IP address obtained in the previous step to SSH into your Linux VM. The following command displays the SSH command you can run in your terminal.

```bash
echo "You can now SSH into your VM using:"
echo "ssh azureuser@$PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 --> 

```text
You can now SSH into your VM using:
ssh azureuser@xx.xx.xx.xx
```

In this Exec Doc, you have learned how to create a resource group, deploy a Linux VM with Ubuntu2204, retrieve the VM's public IP address, and display the SSH command to connect to your new Linux Virtual Machine.