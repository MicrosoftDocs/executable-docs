---
title: 'Quickstart: Create an Azure Container Instance with a public IP address using Terraform'
description: 'In this article, you create an Azure Container Instance with a public IP address using Terraform'
ms.topic: quickstart
ms.service: azure-container-instances
ms.date: 08/29/2024
ms.custom: devx-track-terraform, linux-related-content, innovation-engine
author: TomArcherMsft
ms.author: tarcher
content_well_notification: 
  - AI-contribution
ai-usage: ai-assisted
---

# Quickstart: Create an Azure Container Instance with a public IP address using Terraform

Use Azure Container Instances to run serverless Docker containers in Azure with simplicity and speed. Deploy an application to a container instance on-demand when you don't need a full container orchestration platform like Azure Kubernetes Service. In this article, you use [Terraform](/azure/terraform) to deploy an isolated Docker container and make its web application available with a public IP address.

[!INCLUDE [Terraform abstract](~/azure-dev-docs-pr/articles/terraform/includes/abstract.md)]

In this article, you learn how to:

> [!div class="checklist"]
> * Create a random value for the Azure resource group name using [random_pet](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/resource_group/pet)
> * Create an Azure resource group using [azurerm_resource_group](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group)
> * Create a random value for the container name using [random_string](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/string)
> * Create an Azure container group using [azurerm_container_group](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/container_group)

## Prerequisites

- [Install and configure Terraform](/azure/developer/terraform/quickstart-configure)

## Implement the Terraform code

> [!NOTE]
> The sample code for this article is located in the [Azure Terraform GitHub repo](https://github.com/Azure/terraform/tree/master/quickstart/101-aci-linuxcontainer-public-ip). You can view the log file containing the [test results from current and previous versions of Terraform](https://github.com/Azure/terraform/tree/master/quickstart/101-aci-linuxcontainer-public-ip/TestRecord.md).
> 
> See more [articles and sample code showing how to use Terraform to manage Azure resources](/azure/terraform)

1. Create a directory in which to test and run the sample Terraform code and make it the current directory.

1. Create a file named main.tf and insert the following code:

```text
resource "random_pet" "rg_name" {
  prefix = var.resource_group_name_prefix
}

resource "azurerm_resource_group" "rg" {
  name     = random_pet.rg_name.id
  location = var.resource_group_location
}

resource "random_string" "container_name" {
  length  = 25
  lower   = true
  upper   = false
  special = false
}

resource "azurerm_container_group" "container" {
  name                = "${var.container_group_name_prefix}-${random_string.container_name.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  ip_address_type     = "Public"
  os_type             = "Linux"
  restart_policy      = var.restart_policy

  container {
    name   = "${var.container_name_prefix}-${random_string.container_name.result}"
    image  = var.image
    cpu    = var.cpu_cores
    memory = var.memory_in_gb

    ports {
      port     = var.port
      protocol = "TCP"
    }
  }
}
```

1. Create a file named outputs.tf and insert the following code:

```text
output "container_ipv4_address" {
  value = azurerm_container_group.container.ip_address
}
```

1. Create a file named providers.tf and insert the following code:

```text
terraform {
  required_version = ">=1.0"
  required_providers {
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

1. Create a file named variables.tf and insert the following code:

```text
variable "resource_group_location" {
  type        = string
  default     = "eastus"
  description = "Location for all resources."
}

variable "resource_group_name_prefix" {
  type        = string
  default     = "rg"
  description = "Prefix of the resource group name that's combined with a random value so name is unique in your Azure subscription."
}

variable "container_group_name_prefix" {
  type        = string
  description = "Prefix of the container group name that's combined with a random value so name is unique in your Azure subscription."
  default     = "acigroup"
}

variable "container_name_prefix" {
  type        = string
  description = "Prefix of the container name that's combined with a random value so name is unique in your Azure subscription."
  default     = "aci"
}

variable "image" {
  type        = string
  description = "Container image to deploy. Should be of the form repoName/imagename:tag for images stored in public Docker Hub, or a fully qualified URI for other registries. Images from private registries require additional registry credentials."
  default     = "mcr.microsoft.com/azuredocs/aci-helloworld"
}

variable "port" {
  type        = number
  description = "Port to open on the container and the public IP address."
  default     = 80
}

variable "cpu_cores" {
  type        = number
  description = "The number of CPU cores to allocate to the container."
  default     = 1
}

variable "memory_in_gb" {
  type        = number
  description = "The amount of memory to allocate to the container in gigabytes."
  default     = 2
}

variable "restart_policy" {
  type        = string
  description = "The behavior of Azure runtime if container has stopped."
  default     = "Always"
  validation {
    condition     = contains(["Always", "Never", "OnFailure"], var.restart_policy)
    error_message = "The restart_policy must be one of the following: Always, Never, OnFailure."
  }
}
```

## Initialize Terraform

Before initializing Terraform, set the necessary environment variables. These variables are used by Terraform to provide default values for variables defined in the configuration files.

```bash
export TF_VAR_resource_group_location="eastus"
export TF_VAR_resource_group_name_prefix="rg"
export TF_VAR_container_group_name_prefix="acigroup"
export TF_VAR_container_name_prefix="aci"
export TF_VAR_image="mcr.microsoft.com/azuredocs/aci-helloworld"
export TF_VAR_port=80
export TF_VAR_cpu_cores=1
export TF_VAR_memory_in_gb=2
export TF_VAR_restart_policy="Always"
```

In this section, Terraform is initialized; this command downloads the Azure provider required to manage your Azure resources. Before running the command, ensure you are in the directory where you created the Terraform files.

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

Run terraform apply to execute the execution plan.

```bash
terraform apply main.tfplan
```

Key points:

- The example terraform apply command assumes you previously ran terraform plan -out main.tfplan.
- If you specified a different filename for the -out parameter, use that same filename in the call to terraform apply.
- If you didn't use the -out parameter, call terraform apply without any parameters.

## Verify the results

1. When you apply the execution plan, Terraform outputs the public IP address. To display the IP address again, run [terraform output](https://developer.hashicorp.com/terraform/cli/commands/output).

    ```bash
    terraform output -raw container_ipv4_address
    ```

<!-- expected_similarity=0.3 -->
```text
"xxx.xxx.xxx.xxx"
```

2. Enter the sample's public IP address in your browser's address bar.

    :::image type="content" source="./media/container-instances-quickstart-terraform/azure-container-instances-demo.png" alt-text="Screenshot of the Azure Container Instances sample page" :::



## Troubleshoot Terraform on Azure

[Troubleshoot common problems when using Terraform on Azure](/azure/developer/terraform/troubleshoot)

## Next steps

> [!div class="nextstepaction"] 
> [Tutorial: Create a container image for deployment to Azure Container Instances](./container-instances-tutorial-prepare-app.md)