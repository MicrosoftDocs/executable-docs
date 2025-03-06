---
title: 'Quickstart: Use Terraform to create a Linux VM'
description: In this quickstart, you learn how to use Terraform to create a Linux virtual machine
author: tomarchermsft
ms.service: azure-virtual-machines
ms.collection: linux
ms.topic: quickstart
ms.date: 07/24/2023
ms.author: tarcher
ms.custom: devx-track-terraform, linux-related-content
content_well_notification: 
  - AI-contribution
ai-usage: ai-assisted
---

# Quickstart: Use Terraform to create a Linux VM

**Applies to:** :heavy_check_mark: Linux VMs 

Article tested with the following Terraform and Terraform provider versions:

This article shows you how to create a complete Linux environment and supporting resources with Terraform. Those resources include a virtual network, subnet, public IP address, and more.

[!INCLUDE [Terraform abstract](~/azure-dev-docs-pr/articles/terraform/includes/abstract.md)]

In this article, you learn how to:
> [!div class="checklist"]
> * Create a random value for the Azure resource group name using [random_pet](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/pet).
> * Create an Azure resource group using [azurerm_resource_group](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group).
> * Create a virtual network (VNET) using [azurerm_virtual_network](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/virtual_network).
> * Create a subnet using [azurerm_subnet](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet).
> * Create a public IP using [azurerm_public_ip](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/public_ip).
> * Create a network security group using [azurerm_network_security_group](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_group).
> * Create a network interface using [azurerm_network_interface](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_interface).
> * Create an association between the network security group and the network interface using [azurerm_network_interface_security_group_association](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_interface_security_group_association).
> * Generate a random value for a unique storage account name using [random_id](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id).
> * Create a storage account for boot diagnostics using [azurerm_storage_account](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_account).
> * Create a Linux VM using [azurerm_linux_virtual_machine](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/linux_virtual_machine)
> * Create an AzAPI resource [azapi_resource](https://registry.terraform.io/providers/Azure/azapi/latest/docs/resources/azapi_resource).
> * Create an AzAPI resource to generate an SSH key pair using [azapi_resource_action](https://registry.terraform.io/providers/Azure/azapi/latest/docs/resources/azapi_resource_action).

## Prerequisites

- [Install and configure Terraform](/azure/developer/terraform/quickstart-configure)

## Implement the Terraform code

> [!NOTE]
> The sample code for this article is located in the [Azure Terraform GitHub repo](https://github.com/Azure/terraform/tree/master/quickstart/101-vm-with-infrastructure). You can view the log file containing the [test results from current and previous versions of Terraform](https://github.com/Azure/terraform/tree/master/quickstart/101-vm-with-infrastructure/TestRecord.md).
>
> See more [articles and sample code showing how to use Terraform to manage Azure resources](/azure/terraform)

1. Create a directory in which to test the sample Terraform code and make it the current directory.

1. Create a file named `providers.tf` and insert the following code:

    ```terraform
    terraform {
    required_version = ">=0.12"

    required_providers {
        azapi = {
        source  = "azure/azapi"
        version = "~>1.5"
        }
        azurerm = {
        source  = "hashicorp/azurerm"
        version = "~>3.0"
        }
        random = {
        source  = "hashicorp/random"
        version = "~>3.0"
        }
    }
    }

    provider "azurerm" {
    features {}
    }
    ```

1. Create a file named `ssh.tf` and insert the following code:

    ```terraform
    resource "random_pet" "ssh_key_name" {
    prefix    = "ssh"
    separator = ""
    }

    resource "azapi_resource_action" "ssh_public_key_gen" {
    type        = "Microsoft.Compute/sshPublicKeys@2022-11-01"
    resource_id = azapi_resource.ssh_public_key.id
    action      = "generateKeyPair"
    method      = "POST"

    response_export_values = ["publicKey", "privateKey"]
    }

    resource "azapi_resource" "ssh_public_key" {
    type      = "Microsoft.Compute/sshPublicKeys@2022-11-01"
    name      = random_pet.ssh_key_name.id
    location  = azurerm_resource_group.rg.location
    parent_id = azurerm_resource_group.rg.id
    }

    output "key_data" {
    value = azapi_resource_action.ssh_public_key_gen.output.publicKey
    }
    ```

1. Create a file named `main.tf` and insert the following code:

    ```terraform
    resource "random_pet" "rg_name" {
    prefix = var.resource_group_name_prefix
    }

    resource "azurerm_resource_group" "rg" {
    location = var.resource_group_location
    name     = random_pet.rg_name.id
    }

    # Create virtual network
    resource "azurerm_virtual_network" "my_terraform_network" {
    name                = "myVnet"
    address_space       = ["10.0.0.0/16"]
    location            = azurerm_resource_group.rg.location
    resource_group_name = azurerm_resource_group.rg.name
    }

    # Create subnet
    resource "azurerm_subnet" "my_terraform_subnet" {
    name                 = "mySubnet"
    resource_group_name  = azurerm_resource_group.rg.name
    virtual_network_name = azurerm_virtual_network.my_terraform_network.name
    address_prefixes     = ["10.0.1.0/24"]
    }

    # Create public IPs
    resource "azurerm_public_ip" "my_terraform_public_ip" {
    name                = "myPublicIP"
    location            = azurerm_resource_group.rg.location
    resource_group_name = azurerm_resource_group.rg.name
    allocation_method   = "Dynamic"
    }

    # Create Network Security Group and rule
    resource "azurerm_network_security_group" "my_terraform_nsg" {
    name                = "myNetworkSecurityGroup"
    location            = azurerm_resource_group.rg.location
    resource_group_name = azurerm_resource_group.rg.name

    security_rule {
        name                       = "SSH"
        priority                   = 1001
        direction                  = "Inbound"
        access                     = "Allow"
        protocol                   = "Tcp"
        source_port_range          = "*"
        destination_port_range     = "22"
        source_address_prefix      = "*"
        destination_address_prefix = "*"
    }
    }

    # Create network interface
    resource "azurerm_network_interface" "my_terraform_nic" {
    name                = "myNIC"
    location            = azurerm_resource_group.rg.location
    resource_group_name = azurerm_resource_group.rg.name

    ip_configuration {
        name                          = "my_nic_configuration"
        subnet_id                     = azurerm_subnet.my_terraform_subnet.id
        private_ip_address_allocation = "Dynamic"
        public_ip_address_id          = azurerm_public_ip.my_terraform_public_ip.id
    }
    }

    # Connect the security group to the network interface
    resource "azurerm_network_interface_security_group_association" "example" {
    network_interface_id      = azurerm_network_interface.my_terraform_nic.id
    network_security_group_id = azurerm_network_security_group.my_terraform_nsg.id
    }

    # Generate random text for a unique storage account name
    resource "random_id" "random_id" {
    keepers = {
        # Generate a new ID only when a new resource group is defined
        resource_group = azurerm_resource_group.rg.name
    }

    byte_length = 8
    }

    # Create storage account for boot diagnostics
    resource "azurerm_storage_account" "my_storage_account" {
    name                     = "diag${random_id.random_id.hex}"
    location                 = azurerm_resource_group.rg.location
    resource_group_name      = azurerm_resource_group.rg.name
    account_tier             = "Standard"
    account_replication_type = "LRS"
    }

    # Create virtual machine
    resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
    name                  = "myVM"
    location              = azurerm_resource_group.rg.location
    resource_group_name   = azurerm_resource_group.rg.name
    network_interface_ids = [azurerm_network_interface.my_terraform_nic.id]
    size                  = "Standard_DS1_v2"

    os_disk {
        name                 = "myOsDisk"
        caching              = "ReadWrite"
        storage_account_type = "Premium_LRS"
    }

    source_image_reference {
        publisher = "Canonical"
        offer     = "0001-com-ubuntu-server-jammy"
        sku       = "22_04-lts-gen2"
        version   = "latest"
    }

    computer_name  = "hostname"
    admin_username = var.username

    admin_ssh_key {
        username   = var.username
        public_key = azapi_resource_action.ssh_public_key_gen.output.publicKey
    }

    boot_diagnostics {
        storage_account_uri = azurerm_storage_account.my_storage_account.primary_blob_endpoint
    }
    }
    ```

1. Create a file named `variables.tf` and insert the following code:

    ```terraform
    variable "resource_group_location" {
    type        = string
    default     = "eastus"
    description = "Location of the resource group."
    }

    variable "resource_group_name_prefix" {
    type        = string
    default     = "rg"
    description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
    }

    variable "username" {
    type        = string
    description = "The username for the local account that will be created on the new VM."
    default     = "azureadmin"
    }
    ```

1. Create a file named `outputs.tf` and insert the following code:

    ```terraform
    output "resource_group_name" {
    value = azurerm_resource_group.rg.name
    }

    output "public_ip_address" {
    value = azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address
    }
    ```

## Initialize Terraform

Run terraform init to initialize the Terraform deployment. This command downloads the Azure provider required to manage your Azure resources.

```bash
terraform init -upgrade
```

Key points:

- The -upgrade parameter upgrades the necessary provider plugins to the newest version that complies with the configuration's version constraints.

## Create a Terraform execution plan

Run terraform plan to create an execution plan.

```bash
terraform plan -out main.tfplan
```

Key points:

- The terraform plan command creates an execution plan, but doesn't execute it. Instead, it determines what actions are necessary to create the configuration specified in your configuration files. This pattern allows you to verify whether the execution plan matches your expectations before making any changes to actual resources.
- The optional -out parameter allows you to specify an output file for the plan. Using the -out parameter ensures that the plan you reviewed is exactly what is applied.

## Apply a Terraform execution plan

Run terraform apply to apply the execution plan to your cloud infrastructure.

```bash
terraform apply main.tfplan
```

Key points:

- The example terraform apply command assumes you previously ran terraform plan -out main.tfplan.
- If you specified a different filename for the -out parameter, use that same filename in the call to terraform apply.
- If you didn't use the -out parameter, call terraform apply without any parameters.

Cost information isn't presented during the virtual machine creation process for Terraform like it is for the [Azure portal](quick-create-portal.md). If you want to learn more about how cost works for virtual machines, see the [Cost optimization Overview page](../plan-to-manage-costs.md).

## Verify the results

#### [Azure CLI](#tab/azure-cli)

1. Get the Azure resource group name.

    ```bash
    resource_group_name=$(terraform output -raw resource_group_name)
    ```

1. Run [az vm list](/cli/azure/vm#az-vm-list) with a [JMESPath](/cli/azure/query-azure-cli) query to display the names of the virtual machines created in the resource group.

    ```azurecli
    az vm list \
      --resource-group $resource_group_name \
      --query "[].{\"VM Name\":name}" -o table
    ```

#### [Azure PowerShell](#tab/azure-powershell)

1. Get the Azure resource group name.

    ```console
    $resource_group_name=$(terraform output -raw resource_group_name)
    ```

1. Run [Get-AzVm](/powershell/module/az.compute/get-azvm)  to display the names of all the virtual machines in the resource group.

    ```azurepowershell
    Get-AzVm -ResourceGroupName $resource_group_name
    ```

---

## Clean up resources

[!INCLUDE [terraform-plan-destroy.md](~/azure-dev-docs-pr/articles/terraform/includes/terraform-plan-destroy.md)]

## Troubleshoot Terraform on Azure

[Troubleshoot common problems when using Terraform on Azure](/azure/developer/terraform/troubleshoot)

## Next steps

In this quickstart, you deployed a simple virtual machine using Terraform. To learn more about Azure virtual machines, continue to the tutorial for Linux VMs.

> [!div class="nextstepaction"]
> [Azure Linux virtual machine tutorials](./tutorial-manage-vm.md)