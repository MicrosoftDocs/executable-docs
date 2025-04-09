---
title: 'Quickstart: Create a Linux VM and Test SSH Connectivity Using Azure CLI'
description: Learn how to deploy a Linux virtual machine in Azure using a valid Ubuntu2204 image, retrieve its public IP, and test SSH connectivity without manual intervention. This guide uses the centralindia region to avoid quota issues and configures SSH options to bypass host key verification.
ms.topic: quickstart
ms.date: 10/20/2023
author: yourGithubUsername
ms.author: yourGithubUsername
ms.custom: innovation-engine, azurecli, linux
---

# Quickstart: Create a Linux VM and Test SSH Connectivity Using Azure CLI

In this Exec Doc, we deploy a Linux virtual machine using the valid Ubuntu2204 image, obtain its public IP, and verify non-interactive SSH connectivity. We explicitly select the "centralindia" region to avoid core quota issues and modify the SSH command to bypass host key verification errors. All commands run without user input, and unique resource names are generated using a random suffix.

## Step 1: Declare Environment Variables

We start by declaring the environment variables that will be used throughout the Exec Doc. A random suffix is appended to resource names so that each deployment is unique. The region is explicitly set to centralindia to help avoid regional core quota issues.

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

Now, we deploy a Linux virtual machine using the Ubuntu2204 image—a valid image from the approved list. This command specifies the admin username, auto-generates SSH keys if none exist, and explicitly sets the location to centralindia. This helps to avoid quota issues seen in other regions.

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

Finally, we verify SSH connectivity by executing a non-interactive SSH command. We add the options -o StrictHostKeyChecking=no and -o UserKnownHostsFile=/dev/null to bypass host key verification, ensuring the command runs without manual intervention.

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $MY_VM_USER@$PUBLIC_IP echo "SSH connection successful"
```

Results:

<!-- expected_similarity=0.3 -->
```console
SSH connection successful
```

In this Exec Doc, we've addressed previous errors by using a valid image (Ubuntu2204), explicitly setting the deployment region to centralindia to avoid quota issues, and enhancing the SSH command to bypass host key verification errors. This ensures a reliable, non-interactive deployment and connectivity test.