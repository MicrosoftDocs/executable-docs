---
title: 'Quickstart: Create a Linux VM and SSH into it'
description: 'This Exec Doc demonstrates how to create a Linux Virtual Machine in Azure using Azure CLI with the Ubuntu 22.04 LTS image and then provides instructions to SSH into it. The process uses environment variables and appends a random suffix to ensure resource uniqueness.'
ms.topic: quickstart
ms.date: 10/12/2023
author: developerUser
ms.author: developerUser
ms.custom: innovation-engine, azurecli, linux-automation
---

# Quickstart: Create a Linux VM and SSH into it

In this Exec Doc, you will create a Linux Virtual Machine in Azure using the Ubuntu 22.04 LTS image (specified as Ubuntu2204) and get the connection details to SSH into the newly created VM. The process includes creating a resource group, deploying the VM, retrieving its public IP address, and outputting the SSH command. Note that explicit region parameters are provided to avoid defaulting to a region with heavy quota usage.

## Step 1: Set Environment Variables

In this section, we declare environment variables that will be used throughout the Exec Doc. A random suffix is appended to resource group and VM names to ensure they are unique on each run.

```bash
export VM_RANDOM_SUFFIX=$(openssl rand -hex 3)
export RESOURCE_GROUP_NAME="LinuxVMResourceGroup$VM_RANDOM_SUFFIX"
export REGION="centralindia"
export VM_NAME="LinuxVM$VM_RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
```

## Step 2: Create a Resource Group

In this step, a resource group is created in the specified region. The resource group serves as a container that holds related resources for the solution.

```bash
az group create --name $RESOURCE_GROUP_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx/resourceGroups/LinuxVMResourceGroupxxx",
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

This section deploys a Linux Virtual Machine using the Ubuntu 22.04 LTS image. The --location parameter is explicitly provided to ensure the VM is created in the same region as the resource group, avoiding default settings that might lead to quota issues. The command also generates SSH keys if they do not exist.

```bash
az vm create \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $VM_NAME \
  --location $REGION \
  --image Ubuntu2204 \
  --admin-username $ADMIN_USERNAME \
  --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "computerName": "LinuxVMxxx",
  "id": "/subscriptions/xxxxx/resourceGroups/LinuxVMResourceGroupxxx/providers/Microsoft.Compute/virtualMachines/LinuxVMxxx",
  "location": "centralindia",
  "macAddress": "xx:xx:xx:xx:xx:xx",
  "powerState": "VM running",
  "privateIpAddress": "10.xx.xx.xx",
  "provisioningState": "Succeeded",
  "publicIpAddress": "xx.xx.xx.xx"
}
```

## Step 4: Retrieve the Public IP Address

After the VM is created, retrieve its public IP address. This IP is required to connect to the VM using SSH.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $VM_NAME \
  --query "[].virtualMachine.network.publicIpAddresses[*].ipAddress" \
  --output tsv)
echo "Public IP for VM: $PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->

```text
Public IP for VM: xx.xx.xx.xx
```

## Step 5: SSH into the Linux VM

To SSH into the Linux VM, use the following command. This prints out the SSH command that you can copy and run in your local terminal. Note that executing the SSH command directly within this Exec Doc may lead to an interactive session; hence, it is recommended to run this command in your local or external terminal.

```bash
echo "To connect to your Linux VM, run the following SSH command:"
echo "ssh $ADMIN_USERNAME@$PUBLIC_IP"
```

This will display the SSH command similar to:

ssh azureuser@xx.xx.xx.xx

You should copy this command into your terminal to establish an SSH connection to your newly created Linux VM.

---

This completes the Exec Doc for creating a Linux VM using the Ubuntu 22.04 LTS (Ubuntu2204) image and obtaining the SSH connection details. Enjoy exploring your Linux environment in Azure!