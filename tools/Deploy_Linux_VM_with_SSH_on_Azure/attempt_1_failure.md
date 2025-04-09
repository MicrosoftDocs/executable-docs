---
title: 'Quickstart: Create and SSH into a Linux VM using Azure CLI'
description: Learn how to automate the deployment of a Linux virtual machine and perform a non-interactive SSH test connection using Azure CLI.
ms.topic: quickstart
ms.date: 10/10/2023
author: your-github-username
ms.author: your-github-username
ms.custom: innovation-engine, azurecli, linux-related-content
---

# Quickstart: Create and SSH into a Linux VM using Azure CLI

This Exec Doc demonstrates how to create a Linux virtual machine (VM) on Azure and perform a non-interactive SSH test to verify connectivity to the VM. This process is automated and does not require interactive user input during execution. Each step is explained in detail so you can learn while the commands execute.

## Create a Resource Group

In this section, we declare the environment variables and create a new resource group for our deployment. We append a random suffix to the resource group name to ensure uniqueness for each run.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="WestUS2"
export MY_RESOURCE_GROUP_NAME="MyLinuxResourceGroup${RANDOM_SUFFIX}"
az group create --name $MY_RESOURCE_GROUP_NAME --location $REGION
```

Results: 

<!-- expected_similarity=0.3 -->

```JSON
{
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyLinuxResourceGroupabc123",
  "location": "WestUS2",
  "managedBy": null,
  "name": "MyLinuxResourceGroupabc123",
  "properties": {
      "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

> In the result above, the resource group creation is successful. The subscription ID and resource group name have been redacted for security.

## Create the Linux Virtual Machine

Next, we create a Linux virtual machine using the Ubuntu LTS image. We also generate SSH keys on the fly using the --generate-ssh-keys flag if they do not already exist. A random suffix is used in the VM name for uniqueness.

```bash
export ADMIN_USERNAME="azureuser"
export MY_VM_NAME="MyLinuxVM${RANDOM_SUFFIX}"
az vm create --resource-group $MY_RESOURCE_GROUP_NAME --name $MY_VM_NAME --image UbuntuLTS --admin-username $ADMIN_USERNAME --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->

```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx-xxxxx-xxxxx-xxxxx/resourceGroups/MyLinuxResourceGroupabc123/providers/Microsoft.Compute/virtualMachines/MyLinuxVMabc123",
  "location": "WestUS2",
  "name": "MyLinuxVMabc123",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "52.170.12.34"
}
```

> The output shows that the VM deployment is successful and provides details such as the VM's public IP address.

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

> The command returns the public IP address of the virtual machine. Note that the actual IP will vary.

## Test SSH Connection to the VM

To ensure the VM is accessible via SSH without launching an interactive session, we run a non-interactive SSH command. The command is set to execute a simple echo command on the VM. It uses SSH options to disable strict host key checking and run in batch mode.

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=no $ADMIN_USERNAME@$VM_PUBLIC_IP echo "SSH connection successful"
```

Results:

<!-- expected_similarity=0.3 -->

```text
SSH connection successful
```

> The output confirms that the SSH connection to the VM is working as expected by printing the confirmation message.
