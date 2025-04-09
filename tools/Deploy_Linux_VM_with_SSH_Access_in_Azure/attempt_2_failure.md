---
title: 'Quickstart: Create a Linux VM and Test SSH Connectivity Using Azure CLI'
description: Learn how to deploy a Linux virtual machine in Azure and test SSH connectivity to the VM using Azure CLI.
ms.topic: quickstart
ms.date: 10/20/2023
author: yourGithubUsername
ms.author: yourGithubUsername
ms.custom: innovation-engine, azurecli, linux
---

# Quickstart: Create a Linux VM and Test SSH Connectivity Using Azure CLI

In this Exec Doc, we will deploy a Linux virtual machine in Azure, obtain its public IP, and then test SSH connectivity with a non-interactive command. All commands are designed to run without prompting for user input and include environment variable declarations to ensure uniqueness across deployments.

## Step 1: Declare Environment Variables

We start by declaring the environment variables that will be used throughout the Exec Doc. Note that a random suffix is appended to resource names that need to be unique in order to support multiple executions without conflicts.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export MY_RESOURCE_GROUP_NAME="LinuxVMResourceGroup$RANDOM_SUFFIX"
export MY_VM_NAME="LinuxVM$RANDOM_SUFFIX"
export MY_VM_USER="azureuser"
```

## Step 2: Create a Resource Group

Next, we create a resource group where the VM and associated resources will be deployed. The resource group name includes a random suffix to ensure uniqueness during multiple deployments.

```bash
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/LinuxVMResourceGroupxxx",
  "location": "centralindia",
  "managedBy": null,
  "name": "LinuxVMResourceGroupxxx",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 3: Create a Linux Virtual Machine

Now, we deploy a Linux virtual machine using the Ubuntu2204 image, which is a valid image from Azure. This command automatically generates SSH keys if none exist. The administrator username is set using the MY_VM_USER environment variable.

```bash
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --image Ubuntu2204 --admin-username $MY_VM_USER --generate-ssh-keys --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/LinuxVMResourceGroupxxx/providers/Microsoft.Compute/virtualMachines/LinuxVMxxx",
  "location": "centralindia",
  "macAddress": "xx:xx:xx:xx:xx:xx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "xxx.xxx.xxx.xxx",
  "resourceGroup": "LinuxVMResourceGroupxxx",
  "zones": ""
}
```

## Step 4: Retrieve the Public IP Address of the VM

Before testing SSH connectivity, we retrieve the VM's public IP address. This command extracts the public IP address from the deployed VM and stores it in the PUBLIC_IP environment variable.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
echo "The public IP is: $PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->
```console
The public IP is: xxx.xxx.xxx.xxx
```

## Step 5: Test SSH Connectivity to the Linux VM

Finally, we test SSH connectivity by executing a non-interactive SSH command. The SSH command uses the BatchMode option to avoid prompts and immediately echoes a success message if the connection is established.

```bash
ssh -o BatchMode=yes $MY_VM_USER@$PUBLIC_IP echo "SSH connection successful"
```

Results:

<!-- expected_similarity=0.3 -->
```console
SSH connection successful
```

In this Exec Doc, we've deployed a Linux virtual machine using the Ubuntu2204 image (a valid image per Azure's allowed list), retrieved its public IP, and verified SSH connectivity using Azure CLI commands. This example demonstrates effective use of environment variables for unique resource naming and ensures that execution is non-interactive, making it suitable for automated CI/CD pipelines.