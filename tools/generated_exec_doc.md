---
title: 'Quickstart: Create a Linux VM and SSH into it using Azure CLI'
description: Learn how to create a Linux virtual machine (VM) in Azure and SSH into it using Azure CLI.
ms.topic: quickstart
ms.date: 10/10/2023
author: your-github-username
ms.author: your-alias
ms.custom: devx-track-azurecli, mode-api, innovation-engine
---

# Quickstart: Create a Linux VM and SSH into it using Azure CLI

This Exec Doc will guide you through the steps to create a Linux virtual machine (VM) in Azure using Azure CLI and then SSH into it. By the end of this guide, you will have your Linux VM provisioned and accessible via SSH.

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed and configured on your system.
- The user is expected to have already logged in to Azure and set their subscription.
- An SSH key pair (`id_rsa` and `id_rsa.pub`) present on your system, or Azure CLI can generate one for you during VM creation.

## Steps to Create a Linux VM

### Step 1: Set Environment Variables

We will begin by setting up the necessary environment variables for the resource group, VM name, region, and admin username to create the Linux VM.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export RESOURCE_GROUP="MyResourceGroup$RANDOM_SUFFIX"
export VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
```

### Step 2: Create a Resource Group

A resource group is a logical container for Azure resources.

```bash
az group create --name $RESOURCE_GROUP --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/MyResourceGroupxxx",
    "location": "westus2",
    "managedBy": null,
    "name": "MyResourceGroupxxx",
    "properties": {
        "provisioningState": "Succeeded"
    },
    "tags": null,
    "type": "Microsoft.Resources/resourceGroups"
}
```

### Step 3: Create a Linux VM

We will create a Linux virtual machine using the `az vm create` command. If you do not already have an SSH key pair, the `--generate-ssh-keys` flag allows the Azure CLI to generate one for you automatically. Ensure that a valid image is used.

In this example, we will use the `Ubuntu2204` image.

```bash
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name $VM_NAME \
    --image Ubuntu2204 \
    --admin-username $ADMIN_USERNAME \
    --generate-ssh-keys \
    --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
    "fqdns": "",
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/MyResourceGroupxxx/providers/Microsoft.Compute/virtualMachines/MyLinuxVMxxx",
    "location": "westus2",
    "macAddress": "xx-xx-xx-xx-xx-xx",
    "powerState": "VM running",
    "privateIpAddress": "10.0.0.4",
    "publicIpAddress": "xx.xx.xx.xx",
    "resourceGroup": "MyResourceGroupxxx",
    "zones": ""
}
```

From the output above, copy the `publicIpAddress`. This is the IP address you will use to SSH into the VM.

### Step 4: SSH into the Linux VM

Use the `ssh` command to connect to the Linux VM using the public IP address and the admin username. Update your SSH known hosts file before proceeding to securely establish the connection.

```bash
export PUBLIC_IP=$(az vm show --resource-group $RESOURCE_GROUP --name $VM_NAME --show-details --query publicIps -o tsv)
ssh-keyscan -H $PUBLIC_IP >> ~/.ssh/known_hosts
ssh $ADMIN_USERNAME@$PUBLIC_IP
```

If successful, you will have access to the terminal of your Linux VM.

---

You have now created a Linux VM and successfully connected to it via SSH.