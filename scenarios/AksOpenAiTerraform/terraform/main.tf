###############################################################################
# Plugin setup
###############################################################################
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.20.0"
    }
  }
}

provider "azurerm" {
  features {}
}
###############################################################################

data "azurerm_client_config" "current" {
}

resource "random_string" "this" {
  length  = 8
  special = false
  lower   = true
  upper   = false
  numeric = false
}

locals {
  tenant_id       = data.azurerm_client_config.current.tenant_id
  subscription_id = data.azurerm_client_config.current.subscription_id
  random_id       = random_string.this.result
}

resource "azurerm_resource_group" "main" {
  name     = "${var.resource_group_name_prefix}-${local.random_id}-rg"
  location = var.location

  lifecycle {
    ignore_changes = [tags]
  }
}

###############################################################################
# Kubernetes
###############################################################################
resource "azurerm_kubernetes_cluster" "main" {
  name                = "AksCluster"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  
  sku_tier                  = "Standard"
  dns_prefix                = "AksCluster${local.random_id}"
  kubernetes_version        = var.kubernetes_version
  automatic_upgrade_channel = "stable"

  workload_identity_enabled = true
  oidc_issuer_enabled       = true

  image_cleaner_enabled        = true
  image_cleaner_interval_hours = 72

  default_node_pool {
    name       = "agentpool"
    vm_size    = "Standard_DS2_v2"
    node_count = 1

    upgrade_settings {
      max_surge                     = "10%"
      drain_timeout_in_minutes      = 0
      node_soak_duration_in_minutes = 0
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = tolist([azurerm_user_assigned_identity.workload.id])
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "this" {
  name       = "userpool"
  mode       = "User"
  node_count = 1

  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  orchestrator_version  = var.kubernetes_version
  vm_size               = "Standard_DS2_v2"
  os_type               = "Linux"
  priority              = "Regular"
}

resource "azurerm_user_assigned_identity" "workload" {
  name                = "WorkloadManagedIdentity"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
}

resource "azurerm_federated_identity_credential" "this" {
  name                = azurerm_user_assigned_identity.workload.name
  resource_group_name = azurerm_user_assigned_identity.workload.resource_group_name
  parent_id           = azurerm_user_assigned_identity.workload.id
  audience  = ["api://AzureADTokenExchange"]
  issuer    = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject   = "system:serviceaccount:default:magic8ball-sa"
}

###############################################################################
# OpenAI
###############################################################################
resource "azurerm_cognitive_account" "openai" {
  name                = "OpenAi-${local.random_id}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  kind                          = "OpenAI"
  custom_subdomain_name         = "magic8ball-${local.random_id}"
  sku_name                      = "S0"
}

resource "azurerm_cognitive_deployment" "deployment" {
  name                 = var.model_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }

  sku {
    name = "Standard"
  }
}

resource "azurerm_role_assignment" "cognitive_services_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.workload.principal_id
  principal_type       = "ServicePrincipal"
  
  skip_service_principal_aad_check = true
}

###############################################################################
# Networking
###############################################################################
resource "azurerm_virtual_network" "this" {
  name                = "Vnet"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  address_space = ["10.0.0.0/8"]
}

resource "azurerm_subnet" "this" {
  name                 = "AzureBastionSubnet"
  resource_group_name  = azurerm_resource_group.main.name
  
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.243.2.0/24"]
}

resource "azurerm_public_ip" "this" {
  name                = "PublicIp"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
}

resource "azurerm_bastion_host" "this" {
  name                = "BastionHost"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                 = "configuration"
    subnet_id            = azurerm_subnet.this.id
    public_ip_address_id = azurerm_public_ip.this.id
  }
}