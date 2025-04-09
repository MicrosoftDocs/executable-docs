---
title: 'Quickstart: Create and SSH into a Linux VM using Azure CLI'
description: Learn how to automate the deployment of a Linux virtual machine with a valid Ubuntu image and perform a non-interactive SSH test connection using Azure CLI.
ms.topic: quickstart
ms.date: 10/10/2023
author: your-github-username
ms.author: your-github-username
ms.custom: innovation-engine, azurecli, linux-related-content
---

# Quickstart: Create and SSH into a Linux VM using Azure CLI

This Exec Doc demonstrates how to create a Linux virtual machine (VM) on Azure using a valid Ubuntu image and perform a non-interactive SSH test to verify connectivity to the VM. This process is automated and does not require interactive user input during execution. Each step is explained in detail so you can learn while the commands execute.

In response to previous errors, the following changes have been made:
- The Ubuntu image reference has been corrected to use a valid image ("Ubuntu2204").
- The deployment region has been updated from "WestUS2" to "centralindia" to help avoid quota issues experienced in the WestUS2 region.

## Create a Resource Group

In this section, we declare the environment variables and create a new resource group for our deployment. We append a random suffix to the resource group name to ensure uniqueness for each run.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export MY_RESOURCE_GROUP_NAME="MyLinuxResourceGroup${RANDOM_SUFFIX}"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyLinuxResourceGroupabc123",
  "location": "centralindia",
  "managedBy": null,
  "name": "MyLinuxResourceGroupabc123",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

> The output above confirms that the resource group was created successfully in the centralindia region. Subscription identifiers and resource group names have been redacted for security.

## Create the Linux Virtual Machine

Next, we create a Linux virtual machine using the valid Ubuntu2204 image. We also generate SSH keys automatically with the --generate-ssh-keys flag if they do not already exist. A random suffix is added to the VM name to ensure uniqueness. Specifying the region as centralindia helps avoid potential core quota issues.

```bash
export ADMIN_USERNAME="azureuser"
export MY_VM_NAME="MyLinuxVM${RANDOM_SUFFIX}"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --image Ubuntu2204 --admin-username $ADMIN_USERNAME --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyLinuxResourceGroupabc123/providers/Microsoft.Compute/virtualMachines/MyLinuxVMabc123",
  "location": "centralindia",
  "name": "MyLinuxVMabc123",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.170.12.34"
}
```

> The output shows that the VM deployment was successful using the Ubuntu2204 image, and provides details including the public IP address.

## Obtain the VM's Public IP

After the VM is deployed, we retrieve its public IP address. This IP address will be used to test the SSH connection.

```bash
export VM_PUBLIC_IP=$(az vm list-ip-addresses --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --query "[].virtualMachine.network.publicIpAddresses[].ipAddress" -o tsv)
echo "The VM public IP address is: $VM_PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->

```text
The VM public IP address is: 52.170.12.34
```

> The command returns the public IP address of the virtual machine. Note that the actual IP address will vary with each deployment.

## Test SSH Connection to the VM

To ensure the VM is accessible via SSH without launching an interactive session, we run a non-interactive SSH command. This command executes a simple echo command on the VM and uses SSH options to disable strict host key checking and to operate in batch mode.

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=no $ADMIN_USERNAME@$VM_PUBLIC_IP echo "SSH connection successful"
```

Results:

<!-- expected_similarity=0.3 -->

```text
SSH connection successful
```

> The output confirms that the SSH connection to the VM is working as expected by printing the confirmation message.
