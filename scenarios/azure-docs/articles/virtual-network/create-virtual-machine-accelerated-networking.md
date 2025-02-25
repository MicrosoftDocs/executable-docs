---
title: Create an Azure Virtual Machine with Accelerated Networking
description: Use Azure portal, Azure CLI, or PowerShell to create Linux or Windows virtual machines with Accelerated Networking enabled for improved network performance.
author: asudbring
ms.author: allensu
ms.service: azure-virtual-network
ms.topic: how-to
ms.date: 01/07/2025
ms.custom: fasttrack-edit, devx-track-azurecli, linux-related-content, innovation-engine
---

# Create an Azure Virtual Machine with Accelerated Networking

This article describes how to create a Linux or Windows virtual machine (VM) with Accelerated Networking (AccelNet) enabled by using the Azure CLI command-line interface. 

## Configure AZ CLI extensions

First, configure your Azure CLI settings to allow preview extensions:

```bash
az config set extension.dynamic_install_allow_preview=true
```

## Create Resource Group

Use [az group create](/cli/azure/group#az-group-create) to create a resource group that contains the resources. Be sure to select a supported Windows or Linux region as listed in [Windows and Linux Accelerated Networking](https://azure.microsoft.com/updates/accelerated-networking-in-expanded-preview).

```bash
export RANDOM_SUFFIX=$(openssl rand -hex 3)
export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
export REGION="eastus2"

az group create \
    --name $RESOURCE_GROUP_NAME \
    --location $REGION
```

Results:

<!-- expected_similarity=0.3 --> 

```json
{
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367",
  "location": "eastus2",
  "managedBy": null,
  "name": "test-rg69e367",
  "properties": {
    "provisioningState": "Succeeded"
  },
  "tags": null,
  "type": "Microsoft.Resources/resourceGroups"
}
```
    
## Create VNET

Use [az network vnet create](/cli/azure/network/vnet#az-network-vnet-create) to create a virtual network with one subnet in the resource group:

```bash
export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
export VNET_NAME="vnet-1$RANDOM_SUFFIX"
export SUBNET_NAME="subnet-1$RANDOM_SUFFIX"
export VNET_ADDRESS_PREFIX="10.0.0.0/16"
export SUBNET_ADDRESS_PREFIX="10.0.0.0/24"

az network vnet create \
    --resource-group $RESOURCE_GROUP_NAME \
    --name $VNET_NAME \
    --address-prefix $VNET_ADDRESS_PREFIX \
    --subnet-name $SUBNET_NAME \
    --subnet-prefix $SUBNET_ADDRESS_PREFIX
```

Results:

<!-- expected_similarity=0.3 --> 

```json
{
  "newVNet": {
    "addressSpace": {
      "addressPrefixes": [
        "10.0.0.0/16"
      ]
    },
    "enableDdosProtection": false,
    "etag": "W/\"300c6da1-ee4a-47ee-af6e-662d3a0230a1\"",
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/virtualNetworks/vnet-169e367",
    "location": "eastus2",
    "name": "vnet-169e367",
    "provisioningState": "Succeeded",
    "resourceGroup": "test-rg69e367",
    "resourceGuid": "3d64254d-70d4-47e3-a129-473d70ea2ab8",
    "subnets": [
      {
        "addressPrefix": "10.0.0.0/24",
        "delegations": [],
        "etag": "W/\"300c6da1-ee4a-47ee-af6e-662d3a0230a1\"",
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/virtualNetworks/vnet-169e367/subnets/subnet-169e367",
        "name": "subnet-169e367",
        "privateEndpointNetworkPolicies": "Disabled",
        "privateLinkServiceNetworkPolicies": "Enabled",
        "provisioningState": "Succeeded",
        "resourceGroup": "test-rg69e367",
        "type": "Microsoft.Network/virtualNetworks/subnets"
      }
    ],
    "type": "Microsoft.Network/virtualNetworks",
    "virtualNetworkPeerings": []
  }
}
```

## Create Bastion Subnet

Create the Bastion subnet with [az network vnet subnet create](/cli/azure/network/vnet/subnet).

```bash
export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
export VNET_NAME="vnet-1$RANDOM_SUFFIX"
export SUBNET_NAME="AzureBastionSubnet"
export SUBNET_ADDRESS_PREFIX="10.0.1.0/24"

az network vnet subnet create \
    --vnet-name $VNET_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --name AzureBastionSubnet \
    --address-prefix $SUBNET_ADDRESS_PREFIX
```

Results:

<!-- expected_similarity=0.3 --> 

```json
{
  "addressPrefix": "10.0.1.0/24",
  "delegations": [],
  "etag": "W/\"a2863964-0276-453f-a104-b37391e8088b\"",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/virtualNetworks/vnet-169e367/subnets/AzureBastionSubnet",
  "name": "AzureBastionSubnet",
  "privateEndpointNetworkPolicies": "Disabled",
  "privateLinkServiceNetworkPolicies": "Enabled",
  "provisioningState": "Succeeded",
  "resourceGroup": "test-rg69e367",
  "type": "Microsoft.Network/virtualNetworks/subnets"
}
```

### Create Azure Bastion

1. Create a public IP address for the Azure Bastion host with [az network public-ip create](/cli/azure/network/public-ip).

```bash
export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
export PUBLIC_IP_NAME="public-ip-bastion$RANDOM_SUFFIX"
export REGION="eastus2"
export ALLOCATION_METHOD="Static"
export SKU="Standard"

az network public-ip create \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $PUBLIC_IP_NAME \
  --location $REGION \
  --allocation-method $ALLOCATION_METHOD \
  --sku $SKU
```

Results:

<!-- expected_similarity=0.3 --> 

```json
{
  "publicIp": {
    "ddosSettings": {
      "protectionMode": "VirtualNetworkInherited"
    },
    "etag": "W/\"efa750bf-63f9-4c02-9ace-a747fc405d0f\"",
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/publicIPAddresses/public-ip-bastion69e367",
    "idleTimeoutInMinutes": 4,
    "ipAddress": "203.0.113.173",
    "ipTags": [],
    "location": "eastus2",
    "name": "public-ip-bastion69e367",
    "provisioningState": "Succeeded",
    "publicIPAddressVersion": "IPv4",
    "publicIPAllocationMethod": "Static",
    "resourceGroup": "test-rg69e367",
    "resourceGuid": "fc809493-80c8-482c-9f5a-9d6442472a99",
    "sku": {
      "name": "Standard",
      "tier": "Regional"
    },
    "type": "Microsoft.Network/publicIPAddresses"
  }
}
```

## Create Azure Bastion Host

Create an Azure Bastion host with [az network bastion create](/cli/azure/network/bastion). Azure Bastion is used to securely connect Azure virtual machines without exposing them to the public internet.

```bash
export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
export BASTION_NAME="bastion$RANDOM_SUFFIX"
export VNET_NAME="vnet-1$RANDOM_SUFFIX"
export PUBLIC_IP_NAME="public-ip-bastion$RANDOM_SUFFIX"
export REGION="eastus2"

az network bastion create \
  --resource-group $RESOURCE_GROUP_NAME \
  --name $BASTION_NAME \
  --vnet-name $VNET_NAME \
  --public-ip-address $PUBLIC_IP_NAME \
  --location $REGION
```

Results:

<!-- expected_similarity=0.3 --> 

```json
{
  "disableCopyPaste": false,
  "dnsName": "bst-cc1d5c1d-9496-44fa-a8b3-3b2130efa306.bastion.azure.com",
  "enableFileCopy": false,
  "enableIpConnect": false,
  "enableKerberos": false,
  "enableSessionRecording": false,
  "enableShareableLink": false,
  "enableTunneling": false,
  "etag": "W/\"229bd068-160b-4935-b23d-eddce4bb31ed\"",
  "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/bastionHosts/bastion69e367",
  "ipConfigurations": [
    {
      "etag": "W/\"229bd068-160b-4935-b23d-eddce4bb31ed\"",
      "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/bastionHosts/bastion69e367/bastionHostIpConfigurations/bastion_ip_config",
      "name": "bastion_ip_config",
      "privateIPAllocationMethod": "Dynamic",
      "provisioningState": "Succeeded",
      "publicIPAddress": {
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/publicIPAddresses/public-ip-bastion69e367",
        "resourceGroup": "test-rg69e367"
      },
      "resourceGroup": "test-rg69e367",
      "subnet": {
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/virtualNetworks/vnet-169e367/subnets/AzureBastionSubnet",
        "resourceGroup": "test-rg69e367"
      },
      "type": "Microsoft.Network/bastionHosts/bastionHostIpConfigurations"
    }
  ],
  "location": "eastus2",
  "name": "bastion69e367",
  "provisioningState": "Succeeded",
  "resourceGroup": "test-rg69e367",
  "scaleUnits": 2,
  "sku": {
    "name": "Standard"
  },
  "type": "Microsoft.Network/bastionHosts"
}
```

## Create a network interface with Accelerated Networking

1. Use [az network nic create](/cli/azure/network/nic#az-network-nic-create) to create a network interface (NIC) with Accelerated Networking enabled. The following example creates a NIC in the subnet of the virtual network.

   ```bash
    export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
    export NIC_NAME="nic-1$RANDOM_SUFFIX"
    export VNET_NAME="vnet-1$RANDOM_SUFFIX"
    export SUBNET_NAME="subnet-1$RANDOM_SUFFIX"

    az network nic create \
        --resource-group $RESOURCE_GROUP_NAME \
        --name $NIC_NAME \
        --vnet-name $VNET_NAME \
        --subnet $SUBNET_NAME \
        --accelerated-networking true
   ```

    Results:
    
    <!-- expected_similarity=0.3 --> 

    ```json
   {
      "NewNIC": {
        "auxiliaryMode": "None",
        "auxiliarySku": "None",
        "disableTcpStateTracking": false,
        "dnsSettings": {
          "appliedDnsServers": [],
          "dnsServers": [],
          "internalDomainNameSuffix": "juswipouodrupijji24xb0rkxa.cx.internal.cloudapp.net"
        },
        "enableAcceleratedNetworking": true,
        "enableIPForwarding": false,
        "etag": "W/\"0e24b553-769b-4350-b1aa-ab4cd04100bf\"",
        "hostedWorkloads": [],
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/networkInterfaces/nic-169e367",
        "ipConfigurations": [
          {
            "etag": "W/\"0e24b553-769b-4350-b1aa-ab4cd04100bf\"",
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/networkInterfaces/nic-169e367/ipConfigurations/ipconfig1",
            "name": "ipconfig1",
            "primary": true,
            "privateIPAddress": "10.0.0.4",
            "privateIPAddressVersion": "IPv4",
            "privateIPAllocationMethod": "Dynamic",
            "provisioningState": "Succeeded",
            "resourceGroup": "test-rg69e367",
            "subnet": {
              "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Network/virtualNetworks/vnet-169e367/subnets/subnet-169e367",
              "resourceGroup": "test-rg69e367"
            },
            "type": "Microsoft.Network/networkInterfaces/ipConfigurations"
          }
        ],
        "location": "eastus2",
        "name": "nic-169e367",
        "nicType": "Standard",
        "provisioningState": "Succeeded",
        "resourceGroup": "test-rg69e367",
        "resourceGuid": "6798a335-bd66-42cc-a92a-bb678d4d146e",
        "tapConfigurations": [],
        "type": "Microsoft.Network/networkInterfaces",
        "vnetEncryptionSupported": false
      }
    }
    ```

---

## Create a VM and attach the NIC

Use [az vm create](/cli/azure/vm#az-vm-create) to create the VM, and use the `--nics` option to attach the NIC you created. Ensure you select a VM size and distribution listed in [Windows and Linux Accelerated Networking](https://azure.microsoft.com/updates/accelerated-networking-in-expanded-preview). For a list of all VM sizes and characteristics, see [Sizes for virtual machines in Azure](/azure/virtual-machines/sizes). The following example creates a VM with a size that supports Accelerated Networking, Standard_DS4_v2. The command will generate SSH keys for the virtual machine for login. Make note of the location of the private key. The private key is needed in later steps for connecting to the virtual machine with Azure Bastion.

```bash
export RESOURCE_GROUP_NAME="test-rg$RANDOM_SUFFIX"
export VM_NAME="vm-1$RANDOM_SUFFIX"
export IMAGE="Ubuntu2204"
export SIZE="Standard_DS4_v2"
export ADMIN_USER="azureuser"
export NIC_NAME="nic-1$RANDOM_SUFFIX"

az vm create \
   --resource-group $RESOURCE_GROUP_NAME \
   --name $VM_NAME \
   --image $IMAGE \
   --size $SIZE \
   --admin-username $ADMIN_USER \
   --generate-ssh-keys \
   --nics $NIC_NAME
```

Results:
    
<!-- expected_similarity=0.3 --> 

```json
{
    "fqdns": "",
    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/test-rg69e367/providers/Microsoft.Compute/virtualMachines/vm-169e367",
    "location": "eastus2",
    "macAddress": "60-45-BD-84-F0-D5",
    "powerState": "VM running",
    "privateIpAddress": "10.0.0.4",
    "publicIpAddress": "",
    "resourceGroup": "test-rg69e367",
    "zones": ""
}
```

## Next steps

- [How Accelerated Networking works in Linux and FreeBSD VMs](./accelerated-networking-how-it-works.md)

- [Proximity placement groups](/azure/virtual-machines/co-location)