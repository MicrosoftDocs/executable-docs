---
title: 'Quickstart: Create a Linux VM and SSH into it using Azure CLI'
description: Learn how to create a Linux virtual machine in Azure using Azure CLI and test connectivity by running a non-interactive SSH command.
ms.topic: quickstart
ms.date: 10/12/2023
author: yourGitHubUsername
ms.author: yourGitHubUsername
ms.custom: innovation-engine,azurecli,linux
---

This Exec Doc demonstrates how to deploy a Linux virtual machine in Azure using the Azure CLI and then verify connectivity by running a non-interactive SSH command that echoes a greeting. In this walkthrough, we create a resource group with a random suffix to ensure uniqueness. Next, we deploy the VM and retrieve its public IP address. Finally, we SSH into the VM in a non-interactive manner by running a command remotely. This approach avoids any interactive prompts during execution.

## Step 1: Declare Environment Variables

We declare our environment variables that will be used throughout the document. Notice that we add a random suffix to the names that need to be unique, such as the resource group and VM name.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export MY_RESOURCE_GROUP="MyResourceGroup$RANDOM_SUFFIX"
export MY_VM_NAME="LinuxVM$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
```

## Step 2: Create the Resource Group

We create a resource group which will hold all the resources for our VM. The resource group name uses a random suffix so that it remains unique upon multiple deployments.

```bash
az group create --name $MY_RESOURCE_GROUP --location $REGION
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

## Step 3: Create the Linux Virtual Machine

We now deploy a Linux virtual machine using the Ubuntu 22.04 LTS image (represented by "Ubuntu2204"). The VM is created in the previously set resource group and location, and SSH keys are generated automatically. The VM name also includes the random suffix.

```bash
az vm create --resource-group $MY_RESOURCE_GROUP --name $MY_VM_NAME --image Ubuntu2204 --admin-username $ADMIN_USERNAME --generate-ssh-keys --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "",
  "password": null,
  "publicIpAddress": "xxx.xxx.xxx.xxx",
  "resourceGroup": "MyResourceGroupxxx",
  "sshKey": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDxxxxxxxx",
  "userName": "azureuser",
  "vmId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "zone": ""
}
```

## Step 4: Retrieve the Public IP Address of the VM

After the VM deployment, we retrieve its public IP address using the Azure CLI. This public IP address will be used for the SSH command.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP --name $MY_VM_NAME --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
```

Results:

<!-- expected_similarity=0.3 -->
```text
xxx.xxx.xxx.xxx
```

## Step 5: SSH into the Linux VM in a Non-Interactive Way

Instead of starting an interactive SSH session, we run a command on the VM over SSH to verify connectivity. The SSH command is run in batch mode (non-interactive) and echoes a greeting from the VM.

```bash
ssh -o BatchMode=yes $ADMIN_USERNAME@$PUBLIC_IP "echo 'Hello from the Linux VM!'"
```

Results:

<!-- expected_similarity=0.3 -->
```text
Hello from the Linux VM!
```

This completes the process of creating a Linux virtual machine in Azure and verifying SSH connectivity in a non-interactive manner using Azure CLI.