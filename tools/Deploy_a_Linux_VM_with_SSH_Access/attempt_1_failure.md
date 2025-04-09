---
title: Quickstart: Create a Linux VM and SSH into it using Azure CLI
description: Learn how to create a Linux virtual machine on Azure and connect to it using SSH with pre-generated SSH keys. This Exec Doc demonstrates deploying the VM in a uniquely named resource group, retrieving its public IP address, and providing the SSH command to connect.
ms.topic: quickstart
ms.date: 10/07/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, azurecli, linux-vm
---

# Quickstart: Create a Linux VM and SSH into it using Azure CLI

This Exec Doc walks you through deploying a Linux virtual machine (VM) on Azure using the Azure CLI. The VM is deployed in a new resource group with a random suffix to ensure uniqueness. Once the VM is created, the public IP is retrieved and an SSH command is provided so you can connect to the VM.

## Step 1: Set Environment Variables and Create a Resource Group

In this step, we declare environment variables that will be used throughout the Exec Doc. We generate random suffixes to ensure that resource names are unique between successive runs.

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

Now that the resource group is ready, we create a Linux VM. The VM is created with an Ubuntu 22.04 image, a default administrator username, and SSH keys are generated automatically if they do not exist in your environment.

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

After the VM is created, we need its public IP address in order to connect via SSH. The following command queries the public IP address from the VM's network settings and stores it in an environment variable.

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

Now that you have the public IP, you can SSH into the Linux VM. Use the following command to establish an SSH session. Note that this command is provided for informational purposes; executing it will open an interactive SSH session.

```bash
ssh azureuser@$PUBLIC_IP
```

After running the SSH command, you will be connected to your Linux VM. Use this connection to manage and run commands on the VM.

This completes the Exec Doc for deploying a Linux VM and connecting to it via SSH using the Azure CLI.