---
title: Quickstart: Create a Linux VM and SSH into it using Azure CLI
description: This guide demonstrates how to create a Linux virtual machine in Azure using the Azure CLI with the Ubuntu 22.04 image, and then execute a non-interactive SSH command to verify connectivity with the VM.
ms.topic: quickstart
ms.date: 10/16/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, azure-cli
---

# Quickstart: Create a Linux VM and SSH into it using Azure CLI

This Exec Doc walks you through creating an Azure resource group, deploying a Linux VM using the Ubuntu 22.04 image, and verifying connectivity by SSHing into the VM via a non-interactive command. All necessary environment variables are declared and suffixed where needed to ensure that repeated runs do not cause naming conflicts.

## Step 1: Create a Resource Group

In this section, we declare our environment variables, generate a random suffix, and create a resource group. The random suffix ensures that the resource group name is unique during each execution.

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
  "id": "/subscriptions/xxxxx/resourceGroups/MyResourceGroupxxxxx",
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

## Step 2: Create a Linux Virtual Machine

Now, we create a Linux VM using the Ubuntu 22.04 image. An SSH key will automatically be generated if one does not exist. The VM name is suffixed with the same random value to ensure uniqueness.

```bash
export MY_VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --image ubuntu2204 --admin-username azureuser --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx/resourceGroups/MyResourceGroupxxxxx/providers/Microsoft.Compute/virtualMachines/MyLinuxVMxxxxx",
  "location": "WestUS2",
  "macAddress": "xx:xx:xx:xx:xx:xx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.123.45.67",
  "resourceGroup": "MyResourceGroupxxxxx",
  "zones": ""
}
```

## Step 3: Retrieve the Public IP Address

Here we retrieve the public IP address of the newly created virtual machine. We store the IP in an environment variable and display it. This IP is then used to SSH into the VM.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
echo $PUBLIC_IP
```

Results:

<!-- expected_similarity=0.3 -->
```text
52.123.45.67
```

## Step 4: SSH into the Linux VM

Finally, we use SSH in a non-interactive mode to execute a simple command on the remote VM. This command will echo a message confirming that the SSH connection is working. Note that the SSH command uses the option to bypass host key checking for automation purposes.

```bash
ssh -o StrictHostKeyChecking=no azureuser@$PUBLIC_IP "echo 'Hello from VM'"
```

Results:

<!-- expected_similarity=0.3 -->
```text
Hello from VM
```