---
title: Quickstart: Create a Linux VM and SSH into it using Azure CLI
description: Learn to create an Azure Linux VM and connect via SSH using auto-generated keys. Follow this quick guide to deploy, retrieve the IP, and connect securely.
ms.topic: quickstart
ms.date: 10/07/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, azurecli, linux-vm
---

# Quickstart: Create a Linux VM and SSH into it using Azure CLI

This Exec Doc guides you through deploying a Linux virtual machine (Linux VM) on Azure using the Azure CLI. The VM is deployed in a new resource group with a random suffix to ensure uniqueness. After the VM is created, its public IP is retrieved and the SSH command is provided so you can connect securely.

## Step 1: Set Environment Variables and Create a Resource Group

In this step, we declare environment variables that will be used throughout the Exec Doc and generate random suffixes to ensure resource names remain unique.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export RESOURCE_GROUP="MyResourceGroup$RANDOM_SUFFIX"
export REGION="centralindia"
```

Next, we create a resource group in the specified region.

```bash
az group create --name $RESOURCE_GROUP --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx",
  "location": "centralindia",
  "managedBy": null,
  "name": "MyResourceGroupxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 2: Create the Linux Virtual Machine

Now that the resource group is ready, we create a Linux VM. In this example, the VM is deployed with an Ubuntu 22.04 image. A default administrator username is provided, and SSH keys are generated automatically if they do not already exist in your environment.

```bash
export VM_NAME="LinuxVm$RANDOM_SUFFIX"
az vm create --resource-group $RESOURCE_GROUP --name $VM_NAME --image Ubuntu2204 --admin-username azureuser --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxx/providers/Microsoft.Compute/virtualMachines/LinuxVmxxx",
  "location": "centralindia",
  "macAddress": "...",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "xx.xx.xx.xx",
  "resourceGroup": "MyResourceGroupxxx",
  "zones": ""
}
```

## Step 3: Retrieve the VM's Public IP Address

After the VM is created, we need its public IP address to connect via SSH. The following command queries the VM's network settings and stores the public IP address in an environment variable.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $RESOURCE_GROUP --name $VM_NAME --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
echo "The public IP of the VM is: $PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->
```text
The public IP of the VM is: xx.xx.xx.xx
```

## Step 4: SSH into the Linux VM

Now that you have the public IP address, use the following SSH command to open an interactive session into your Linux VM.

```bash
ssh azureuser@$PUBLIC_IP
```

This completes the Exec Doc for deploying a Linux VM and connecting to it via SSH using the Azure CLI.