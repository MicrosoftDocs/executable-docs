---
title: 'Quickstart: Create a Linux VM and SSH into it using Azure CLI'
description: Learn how to quickly create a Linux Virtual Machine in Azure using the Ubuntu2204 image, retrieve its public IP address, and display the SSH command to connect to the VM.
ms.topic: quickstart
ms.date: 10/12/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, linux, azurecli
---

# Quickstart: Create a Linux VM and SSH into it using Azure CLI

This Exec Doc demonstrates how to create a new resource group, deploy a Linux Virtual Machine (VM) with the Ubuntu2204 image, retrieve its public IP address, and then display the SSH command you can use to connect to the VM. Environment variables such as the resource group name and VM name include a random suffix to ensure uniqueness across deployments while reducing quota impact by using a lean VM size. All resources will be deployed into the "centralindia" region to avoid regional quota issues.

## Step 1: Create a Resource Group

In this step, we create a resource group in the "centralindia" region. A random suffix is appended to the resource group name so that there are no conflicts with previously created resources.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export MY_RESOURCE_GROUP_NAME="MyResourceGroup$RANDOM_SUFFIX"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxxx",
  "location": "centralindia",
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

In this section, we deploy a Linux VM using the validated image "Ubuntu2204". To reduce quota impact and ensure the deployment succeeds, we explicitly set the location to use the resource group's region ("centralindia") and select a lean VM size (--size Standard_B1s). The admin username is set to "azureuser" and SSH keys are generated automatically. The VM name also includes the random suffix to ensure uniqueness.

```bash
export VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $VM_NAME --image Ubuntu2204 --admin-username azureuser --generate-ssh-keys --location $REGION --size Standard_B1s
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachines/MyLinuxVMxxxxxx",
  "location": "centralindia",
  "name": "MyLinuxVMxxxxxx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "xx.xx.xx.xx"
}
```

## Step 3: Retrieve the Public IP Address of the VM

After the VM is created, this command fetches the public IP address assigned to it from the same resource group and VM name. The public IP is required for establishing an SSH connection to the VM.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $VM_NAME --query "[].virtualMachine.network.publicIpAddresses[*].ipAddress" -o tsv)
echo $PUBLIC_IP
```

Results:

<!-- expected_similarity=0.3 -->

```text
xx.xx.xx.xx
```

## Step 4: Display the SSH Command

Finally, this section displays the SSH command that you can use to connect to your Linux VM. Copy and run the command in your terminal to establish an SSH session.

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