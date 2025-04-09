---
title: 'Quickstart: Create a Linux VM and Test SSH Connectivity Using Azure CLI'
description: Learn how to deploy a Linux virtual machine in Azure and test SSH connectivity to the VM using Azure CLI. This guide ensures that a valid image is used and explicitly selects a region that avoids quota issues.
ms.topic: quickstart
ms.date: 10/20/2023
author: yourGithubUsername
ms.author: yourGithubUsername
ms.custom: innovation-engine, azurecli, linux
---

# Quickstart: Create a Linux VM and Test SSH Connectivity Using Azure CLI

In this Exec Doc, we deploy a Linux virtual machine using the valid Ubuntu2204 image, obtain its public IP, and verify non-interactive SSH connectivity. All commands run without user input, and environment variables are declared with a random suffix for unique resource names to allow multiple executions without conflicts.

## Step 1: Declare Environment Variables

We start by declaring the environment variables that will be used throughout the Exec Doc. Note that a random suffix is appended to resource names so that each deployment is unique. We also set the region explicitly to one where capacity issues are less likely (centralindia).

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export MY_RESOURCE_GROUP_NAME="LinuxVMResourceGroup$RANDOM_SUFFIX"
export MY_VM_NAME="LinuxVM$RANDOM_SUFFIX"
export MY_VM_USER="azureuser"
```

## Step 2: Create a Resource Group

Next, we create a resource group in the specified region. This resource group will host the virtual machine and its related resources.

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

Now, we deploy a Linux virtual machine using the Ubuntu2204 image—a valid image per Azure's allowed list. This command specifies the admin username and instructs Azure to auto-generate SSH keys if none are available. We explicitly pass the region variable to avoid potential defaults to regions with quota issues.

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

Before testing SSH connectivity, we retrieve the public IP address of the deployed VM. This address is stored in the PUBLIC_IP environment variable for later use.

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

Finally, we verify SSH connectivity by executing a non-interactive SSH command. The SSH command uses the BatchMode option to avoid prompts and immediately echoes a success message if the connection is established.

```bash
ssh -o BatchMode=yes $MY_VM_USER@$PUBLIC_IP echo "SSH connection successful"
```

Results:

<!-- expected_similarity=0.3 -->
```console
SSH connection successful
```

In this Exec Doc, we've ensured that a valid image (Ubuntu2204) is used and explicitly set the deployment region to centralindia to help avoid regional quota issues. We've deployed a Linux VM, retrieved its public IP, and confirmed SSH connectivity—all without prompting for user input.