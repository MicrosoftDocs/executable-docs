---
title: Linux VM Setup and SSH Access
description: This Exec Doc creates a Linux VM in Azure and demonstrates how to non-interactively retrieve its public IP address and SSH into it using predefined environment variables.
ms.topic: quickstart
ms.date: 10/12/2023
author: chatgpt
ms.author: chatgpt
ms.custom: innovation-engine, linux, azure-cli
---

# Linux VM Setup and SSH Access

This Exec Doc demonstrates how to create a Linux virtual machine in Azure using the Azure CLI, retrieve its public IP address, and then SSH into it. All input values are predefined and no user interaction is required.

## Step 1: Create a Resource Group

In this step, we create a resource group in a specified region. The resource group name is given a random suffix to ensure uniqueness between executions.

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

Now, we create a Linux VM with Ubuntu LTS. We set the administrator username and generate the SSH keys automatically. The VM name also includes a random suffix to ensure uniqueness.

```bash
export VM_NAME="MyLinuxVM$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image UbuntuLTS \
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

We retrieve the public IP address of the VM so we can SSH into it. The command outputs the public IP address in TSV format.

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

Finally, we SSH into the Linux VM using the retrieved public IP address and the administrator username. This command launches an interactive SSH session.

```bash
ssh $ADMIN_USERNAME@$PUBLIC_IP
```

Note: Running the SSH command will open an interactive session into your Linux VM. To exit the session, type "exit".

---

This Exec Doc automates the creation of cloud infrastructure non-interactively while showcasing each step needed to eventually access the Linux VM via SSH. Enjoy exploring your new virtual machine!