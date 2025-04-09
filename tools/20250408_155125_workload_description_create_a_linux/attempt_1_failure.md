---
title: 'Quickstart: Create a Linux VM and SSH into It'
description: This document demonstrates how to quickly create a Linux virtual machine (VM) in Azure and retrieve the SSH command needed to connect to it.
ms.topic: quickstart
ms.date: 10/06/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, cloud, azurecli
---

This Exec Doc will guide you through creating an Azure resource group, deploying a Linux virtual machine with Ubuntu LTS, retrieving its public IP address, and displaying the SSH command to connect to the VM. All commands are executed non-interactively with necessary environment variables declared on the fly. A random suffix is appended to resource names to ensure uniqueness across multiple executions.

### Step 1: Create a Resource Group

We first declare the required environment variables and create a new resource group. The variable RANDOM_SUFFIX ensures the resource group name is unique.

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

### Step 2: Create the Linux Virtual Machine

Next, we create a Linux VM using the Ubuntu LTS image. The VM name is generated using a random suffix for uniqueness. The admin username is set to "azureuser" and SSH keys are automatically generated.

```bash
export VM_NAME="linuxvm$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $VM_NAME --image UbuntuLTS --admin-username $ADMIN_USERNAME --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyResourceGroupxxxxxx/providers/Microsoft.Compute/virtualMachines/linuxvmxxxxxx",
  "location": "centralindia",
  "macAddress": "xx-xx-xx-xx-xx-xx",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "20.30.40.50",
  "resourceGroup": "MyResourceGroupxxxxxx",
  "zones": ""
}
```

### Step 3: Retrieve the VM's Public IP Address

We extract the public IP address of the newly created VM. This value will be used for connecting to the VM via SSH.

```bash
export PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $VM_NAME --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
echo "Public IP: $PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->

```text
Public IP: 20.30.40.50
```

### Step 4: Display SSH Command to Connect to the VM

Finally, we output the SSH command that you can use to connect to the Linux VM. Simply copy and run the displayed command in your terminal to access the VM. Note that this command is for demonstration purposes; running it will initiate an interactive SSH session.

```bash
echo "To SSH into the VM, run the following command:"
echo "ssh $ADMIN_USERNAME@$PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->

```text
To SSH into the VM, run the following command:
ssh azureuser@20.30.40.50
```

You have now successfully created a Linux VM in Azure and retrieved the information required to SSH into it. Enjoy exploring your new VM!