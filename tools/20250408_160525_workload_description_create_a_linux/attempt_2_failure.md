---
title: Linux VM Setup and SSH Access
description: This Exec Doc creates a Linux virtual machine in Azure using a valid Ubuntu image and demonstrates how to non-interactively retrieve its public IP address and SSH into it using predefined environment variables.
ms.topic: quickstart
ms.date: 04/08/2025
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, linux, azure-cli
---

# Linux VM Setup and SSH Access

This Exec Doc demonstrates how to create a Linux virtual machine in Azure using the Azure CLI with a valid Ubuntu image, retrieve its public IP address, and then SSH into it. All input values are predefined and no user interaction is required during the deployment process. Note that the SSH command will launch an interactive session into the Linux VM.

## Step 1: Create a Resource Group

In this step, we create a resource group in the specified region. The resource group name is appended with a random suffix to ensure uniqueness between executions.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export RESOURCE_GROUP="MyResourceGroup$RANDOM_SUFFIX"
az group create --name $RESOURCE_GROUP --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "id": "/subscriptions/xxxxx/resourceGroups/MyResourceGroupxxxxxx",
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

Now, we create a Linux VM with the Ubuntu 22.04 LTS image. We set the administrator username and generate SSH keys automatically. The VM name also includes a random suffix to ensure uniqueness.

```bash
export VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image Ubuntu2204 \
  --admin-username $ADMIN_USERNAME \
  --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->

```json
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx/resourceGroups/MyResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachines/MyLinuxVMxxxxxx",
  "location": "WestUS2",
  "macAddress": "xx:xx:xx:xx:xx:xx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.x.x",
  "publicIpAddress": "20.30.x.x",
  "resourceGroup": "MyResourceGroupxxxxxx",
  "zones": ""
}
```

## Step 3: Retrieve the Virtual Machine's Public IP Address

We retrieve the public IP address of the VM so we can use it to SSH into the machine. The command outputs the public IP address in TSV format.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $RESOURCE_GROUP --name $VM_NAME --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
echo "Public IP Address:" $PUBLIC_IP
```

Results:

<!-- expected_similarity=0.3 -->

```text
Public IP Address: 20.30.x.x
```

## Step 4: SSH into the Linux Virtual Machine

Finally, we SSH into the Linux VM using the retrieved public IP address and the administrator username. This command initiates an interactive SSH session. To exit the session, type "exit".

```bash
ssh $ADMIN_USERNAME@$PUBLIC_IP
```