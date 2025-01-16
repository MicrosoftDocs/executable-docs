terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.16.0"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {
}

resource "random_string" "prefix" {
  length  = 6
  special = false
  upper   = false
  numeric = false
}

resource "random_string" "storage_account_suffix" {
  length  = 8
  special = false
  lower   = true
  upper   = false
  numeric  = false
}

variable "name_prefix" {
  type        = string
}

variable "log_analytics_workspace_name" {
  default     = "Workspace"
  type        = string
}

variable "log_analytics_retention_days" {
  type        = number
  default     = 30
}

variable "location" {
  default     = "westus2"
  type        = string
}

variable "resource_group_name" {
  default     = "RG"
  type        = string
}

variable "system_node_pool_subnet_name" {
  default     =  "SystemSubnet"
  type        = string
}

variable "user_node_pool_subnet_name" {
  default     =  "UserSubnet"
  type        = string
}

variable "pod_subnet_name" {
  default     = "PodSubnet"
  type        = string
}

variable "vm_subnet_name" {
  default     = "VmSubnet"
  type        = string
}

variable "namespace" {
  description = "Specifies the namespace of the workload application that accesses the Azure OpenAI Service."
  type = string
  default = "magic8ball"
}

variable "service_account_name" {
  description = "Specifies the name of the service account of the workload application that accesses the Azure OpenAI Service."
  type = string
  default = "magic8ball-sa"
}

variable "email" {
  description = "Specifies the email address for the cert-manager cluster issuer."
  type = string
  default = "paolos@microsoft.com"
}

resource "azurerm_resource_group" "rg" {
  name     = "${var.name_prefix}${var.resource_group_name}"
  location = var.location
}

module "log_analytics_workspace" {
  source                           = "./modules/log_analytics"
  name                             = "${var.name_prefix}${var.log_analytics_workspace_name}"
  location                         = var.location
  resource_group_name              = azurerm_resource_group.rg.name
  
  solution_plan_map                = {
    ContainerInsights= {
      product   = "OMSGallery/ContainerInsights"
      publisher = "Microsoft"
    }
  }
}

module "virtual_network" {
  source                       = "./modules/virtual_network"
  vnet_name                    = "AksVNet"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.rg.name
  
  log_analytics_workspace_id   = module.log_analytics_workspace.id
  
  address_space                = ["10.0.0.0/8"]
  subnets = [
    {
      name : var.system_node_pool_subnet_name
      address_prefixes : ["10.240.0.0/16"]
      private_endpoint_network_policies : "Enabled"
      private_link_service_network_policies_enabled : false
      delegation: null
    },
    {
      name : var.user_node_pool_subnet_name
      address_prefixes : ["10.241.0.0/16"]
      private_endpoint_network_policies : "Enabled"
      private_link_service_network_policies_enabled : false
      delegation: null
    },
    {
      name : var.pod_subnet_name
      address_prefixes : ["10.242.0.0/16"]
      private_endpoint_network_policies : "Enabled"
      private_link_service_network_policies_enabled : false
      delegation = {
        name = "delegation"
        service_delegation = {
          name    = "Microsoft.ContainerService/managedClusters"
          actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
        }
      }
    },
    {
      name : var.vm_subnet_name
      address_prefixes :  ["10.243.1.0/24"]
      private_endpoint_network_policies : "Enabled"
      private_link_service_network_policies_enabled : false
      delegation: null
    },
    {
      name : "AzureBastionSubnet"
      address_prefixes : ["10.243.2.0/24"]
      private_endpoint_network_policies : "Enabled"
      private_link_service_network_policies_enabled : false
      delegation: null
    }
  ]
}

module "nat_gateway" {
  source                       = "./modules/nat_gateway"
  name                         = "${var.name_prefix}NatGateway"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.rg.name
  
  sku_name                     = "Standard"
  idle_timeout_in_minutes      = 4
  zones                        = ["1"]
  subnet_ids                   = module.virtual_network.subnet_ids
}

module "container_registry" {
  source                       = "./modules/container_registry"
  name                         = "${var.name_prefix}Acr"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.rg.name
  
  log_analytics_workspace_id   = module.log_analytics_workspace.id

  sku                          = "Basic"
  admin_enabled                = true
}

module "aks_cluster" {
  source                                  = "./modules/aks"
  name                                    = "${var.name_prefix}${var.aks_cluster_name}"
  location                                = var.location
  resource_group_name                     = azurerm_resource_group.rg.name
  resource_group_id                       = azurerm_resource_group.rg.id
  kubernetes_version                      = var.kubernetes_version
  sku_tier                                = "Free"
  
  depends_on = [
    module.nat_gateway,
    module.container_registry
  ]
}

module "openai" {
  source                                   = "./modules/openai"
  name                                     = "${var.name_prefix}OpenAi"
  location                                 = var.location
  resource_group_name                      = azurerm_resource_group.rg.name
  sku_name                                 = "S0"
  deployments                              = [
    {
      name = "gpt-35-turbo"
      model = {
        name = "gpt-35-turbo"
        version = "0301"
      }
      rai_policy_name = ""
    }
  ]
  custom_subdomain_name                    = lower("${var.name_prefix}OpenAi")
  public_network_access_enabled            = true
  log_analytics_workspace_id               = module.log_analytics_workspace.id
  log_analytics_retention_days             = var.log_analytics_retention_days
}

resource "azurerm_user_assigned_identity" "aks_workload_identity" {
  name                = "${var.name_prefix}WorkloadManagedIdentity"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
}

resource "azurerm_role_assignment" "cognitive_services_user_assignment" {
  scope                = module.openai.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.aks_workload_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_federated_identity_credential" "federated_identity_credential" {
  name                = "${title(var.namespace)}FederatedIdentity"
  resource_group_name = azurerm_resource_group.rg.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = module.aks_cluster.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.aks_workload_identity.id
  subject             = "system:serviceaccount:${var.namespace}:${var.service_account_name}"
}

resource "azurerm_role_assignment" "network_contributor_assignment" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Network Contributor"
  principal_id         = module.aks_cluster.aks_identity_principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "acr_pull_assignment" {
  role_definition_name = "AcrPull"
  scope                = module.container_registry.id
  principal_id         = module.aks_cluster.kubelet_identity_object_id
  skip_service_principal_aad_check = true
}

module "storage_account" {
  source                      = "./modules/storage_account"
  name                        = "boot${random_string.storage_account_suffix.result}"
  location                    = var.location
  resource_group_name         = azurerm_resource_group.rg.name
  account_kind                = "StorageV2"
  account_tier                = "Standard"
  replication_type            = "LRS"
}

module "bastion_host" {
  source                       = "./modules/bastion_host"
  name                         = "${var.name_prefix}BastionHost"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.rg.name
  subnet_id                    = module.virtual_network.subnet_ids["AzureBastionSubnet"]
  log_analytics_workspace_id   = module.log_analytics_workspace.id
  log_analytics_retention_days = var.log_analytics_retention_days
}

module "key_vault" {
  source                          = "./modules/key_vault"
  name                            = "${var.name_prefix}KeyVault"
  location                        = var.location
  resource_group_name             = azurerm_resource_group.rg.name
  tenant_id                       = data.azurerm_client_config.current.tenant_id
  sku_name                        = "standard"
  enabled_for_deployment          = true
  enabled_for_disk_encryption     = true
  enabled_for_template_deployment = true
  enable_rbac_authorization       = true
  purge_protection_enabled        = false
  soft_delete_retention_days      = 30
  bypass                          = "AzureServices"
  default_action                  = "Allow"
  log_analytics_workspace_id      = module.log_analytics_workspace.id
  log_analytics_retention_days    = var.log_analytics_retention_days
}

module "acr_private_dns_zone" {
  source                       = "./modules/private_dns_zone"
  name                         = "privatelink.azurecr.io"
  resource_group_name          = azurerm_resource_group.rg.name
  virtual_networks_to_link     = {
    (module.virtual_network.name) = {
      subscription_id = data.azurerm_client_config.current.subscription_id
      resource_group_name = azurerm_resource_group.rg.name
    }
  }
}

module "openai_private_dns_zone" {
  source                       = "./modules/private_dns_zone"
  name                         = "privatelink.openai.azure.com"
  resource_group_name          = azurerm_resource_group.rg.name
  virtual_networks_to_link     = {
    (module.virtual_network.name) = {
      subscription_id = data.azurerm_client_config.current.subscription_id
      resource_group_name = azurerm_resource_group.rg.name
    }
  }
}

module "key_vault_private_dns_zone" {
  source                       = "./modules/private_dns_zone"
  name                         = "privatelink.vaultcore.azure.net"
  resource_group_name          = azurerm_resource_group.rg.name
  virtual_networks_to_link     = {
    (module.virtual_network.name) = {
      subscription_id = data.azurerm_client_config.current.subscription_id
      resource_group_name = azurerm_resource_group.rg.name
    }
  }
}

module "blob_private_dns_zone" {
  source                       = "./modules/private_dns_zone"
  name                         = "privatelink.blob.core.windows.net"
  resource_group_name          = azurerm_resource_group.rg.name
  virtual_networks_to_link     = {
    (module.virtual_network.name) = {
      subscription_id = data.azurerm_client_config.current.subscription_id
      resource_group_name = azurerm_resource_group.rg.name
    }
  }
}

module "openai_private_endpoint" {
  source                         = "./modules/private_endpoint"
  name                           = "${module.openai.name}PrivateEndpoint"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.rg.name
  subnet_id                      = module.virtual_network.subnet_ids[var.vm_subnet_name]
  private_connection_resource_id = module.openai.id
  is_manual_connection           = false
  subresource_name               = "account"
  private_dns_zone_group_name    = "AcrPrivateDnsZoneGroup"
  private_dns_zone_group_ids     = [module.openai_private_dns_zone.id]
}

module "acr_private_endpoint" {
  source                         = "./modules/private_endpoint"
  name                           = "${module.container_registry.name}PrivateEndpoint"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.rg.name
  subnet_id                      = module.virtual_network.subnet_ids[var.vm_subnet_name]
  private_connection_resource_id = module.container_registry.id
  is_manual_connection           = false
  subresource_name               = "registry"
  private_dns_zone_group_name    = "AcrPrivateDnsZoneGroup"
  private_dns_zone_group_ids     = [module.acr_private_dns_zone.id]
}

module "key_vault_private_endpoint" {
  source                         = "./modules/private_endpoint"
  name                           = "${module.key_vault.name}PrivateEndpoint"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.rg.name
  subnet_id                      = module.virtual_network.subnet_ids[var.vm_subnet_name]
  private_connection_resource_id = module.key_vault.id
  is_manual_connection           = false
  subresource_name               = "vault"
  private_dns_zone_group_name    = "KeyVaultPrivateDnsZoneGroup"
  private_dns_zone_group_ids     = [module.key_vault_private_dns_zone.id]
}

module "blob_private_endpoint" {
  source                         = "./modules/private_endpoint"
  name                           = var.name_prefix == null ? "${random_string.prefix.result}BlocStoragePrivateEndpoint" : "${var.name_prefix}BlobStoragePrivateEndpoint"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.rg.name
  subnet_id                      = module.virtual_network.subnet_ids[var.vm_subnet_name]
  private_connection_resource_id = module.storage_account.id
  is_manual_connection           = false
  subresource_name               = "blob"
  private_dns_zone_group_name    = "BlobPrivateDnsZoneGroup"
  private_dns_zone_group_ids     = [module.blob_private_dns_zone.id]
}

module "deployment_script" {
  source                              = "./modules/deployment_script"
  name                                = "${var.name_prefix}BashScript"
  location                            = var.location
  resource_group_name                 = azurerm_resource_group.rg.name
  azure_cli_version                   = "2.9.1"
  managed_identity_name               = "${var.name_prefix}ScriptManagedIdentity"
  aks_cluster_name                    = module.aks_cluster.name
  hostname                            = "magic8ball.contoso.com"
  namespace                           = var.namespace
  service_account_name                = var.service_account_name
  email                               = var.email
  primary_script_uri                  = "https://paolosalvatori.blob.core.windows.net/scripts/install-nginx-via-helm-and-create-sa.sh"
  tenant_id                           = data.azurerm_client_config.current.tenant_id
  subscription_id                     = data.azurerm_client_config.current.subscription_id
  workload_managed_identity_client_id = azurerm_user_assigned_identity.aks_workload_identity.client_id

  depends_on = [ 
    module.aks_cluster
   ]
}
