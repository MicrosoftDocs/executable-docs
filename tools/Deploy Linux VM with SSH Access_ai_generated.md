---
title: 'Quickstart: Create a Linux VM and SSH into it'
description: Learn how to create a Linux virtual machine in Azure using Azure CLI and then SSH into it.
ms.topic: quickstart
ms.date: 10/12/2023
author: yourgithubusername
ms.author: yourgithubusername
ms.custom: innovation-engine, azurecli, linux-related-content
---

# Quickstart: Create a Linux VM and SSH into it

This Exec Doc demonstrates how to create a resource group, deploy a Linux VM using a supported Ubuntu image, retrieve its public IP address, and then SSH into the VM. The process uses environment variables to manage configuration details and appends a random suffix to resource names to ensure uniqueness.

The following sections walk through each step with code blocks. Remember that you must already be logged in to Azure and have your subscription set.

## Step 1: Create a Resource Group

In this section, we declare environment variables necessary for the deployment and create a resource group in the "centralindia" region. A random suffix is appended to the resource group name to guarantee uniqueness.

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export REGION="centralindia"
export RG_NAME="LinuxRG$RANDOM_SUFFIX"
az group create --name $RG_NAME --location $REGION
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "id": "/subscriptions/xxxxx/resourceGroups/LinuxRGabc123",
  "location": "centralindia",
  "managedBy": null,
  "name": "LinuxRGabc123",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```

## Step 2: Create a Linux Virtual Machine

Now we create a Linux VM using a supported Ubuntu image ('Ubuntu2204'). In this example, we use a Standard_B1s VM size. We also set an administrator username and let Azure generate SSH key pairs automatically. A random suffix is used in the VM name for uniqueness.

```bash
export VM_NAME="LinuxVM$RANDOM_SUFFIX"
export ADMIN_USERNAME="azureuser"
az vm create \
  --resource-group $RG_NAME \
  --name $VM_NAME \
  --image Ubuntu2204 \
  --size Standard_B1s \
  --admin-username $ADMIN_USERNAME \
  --generate-ssh-keys
```

Results:

<!-- expected_similarity=0.3 -->
```JSON
{
  "fqdns": "",
  "id": "/subscriptions/xxxxx/resourceGroups/LinuxRGabc123/providers/Microsoft.Compute/virtualMachines/LinuxVMabc123",
  "location": "centralindia",
  "macAddress": "00-0X-0X-0X-0X-0X",
  "machineId": "xxxxx",
  "name": "LinuxVMabc123",
  "powerState": "VM running",
  "privateIpAddress": "10.0.0.4",
  "publicIpAddress": "13.92.xxx.xxx",
  "resourceGroup": "LinuxRGabc123",
  "zones": ""
}
```

## Step 3: Retrieve the VM Public IP Address

This step retrieves the public IP address of the newly created VM. The public IP is stored in an environment variable to be used in the SSH step.

```bash
export VM_PUBLIC_IP=$(az vm list-ip-addresses --resource-group $RG_NAME --name $VM_NAME --query "[].virtualMachine.network.publicIpAddresses[0].ipAddress" --output tsv)
echo "The public IP address of the VM is: $VM_PUBLIC_IP"
```

Results:

<!-- expected_similarity=0.3 -->
```text
The public IP address of the VM is: 13.92.xxx.xxx
```

## Step 4: SSH into the Linux VM

Finally, once you have retrieved the public IP address, you can SSH into your Linux VM using the generated SSH key pair. This command establishes an SSH connection without prompting for host key verification.

```bash
ssh -o StrictHostKeyChecking=no $ADMIN_USERNAME@$VM_PUBLIC_IP
```

When executed, this command initiates an SSH session with your Linux VM. After connecting, you will have full access to manage and configure the VM as needed.

---

This Exec Doc has successfully deployed a Linux VM in Azure using a supported Ubuntu image and shown how to connect to it using SSH, all accomplished with a series of Azure CLI commands executed via the Innovation Engine.