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

locals {
  storage_account_prefix = "boot"
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
  description = "A prefix for the name of all the resource groups and resources."
  type        = string
}

variable "log_analytics_workspace_name" {
  description = "Specifies the name of the log analytics workspace"
  default     = "Workspace"
  type        = string
}

variable "log_analytics_retention_days" {
  description = "Specifies the number of days of the retention policy"
  type        = number
  default     = 30
}

variable "location" {
  description = "Specifies the location for the resource group and all the resources"
  default     = "westus2"
  type        = string
}

variable "resource_group_name" {
  description = "Specifies the resource group name"
  default     = "RG"
  type        = string
}

variable "system_node_pool_subnet_name" {
  description = "Specifies the name of the subnet that hosts the system node pool"
  default     =  "SystemSubnet"
  type        = string
}

variable "user_node_pool_subnet_name" {
  description = "Specifies the name of the subnet that hosts the user node pool"
  default     =  "UserSubnet"
  type        = string
}

variable "pod_subnet_name" {
  description = "Specifies the name of the jumpbox subnet"
  default     = "PodSubnet"
  type        = string
}

variable "vm_subnet_name" {
  description = "Specifies the name of the jumpbox subnet"
  default     = "VmSubnet"
  type        = string
}

variable "aks_cluster_name" {
  description = "(Required) Specifies the name of the AKS cluster."
  default     = "Aks"
  type        = string
}

variable "kubernetes_version" {
  description = "Specifies the AKS Kubernetes version"
  default     = "1.29.10"
  type        = string
}

variable "system_node_pool_vm_size" {
  description = "Specifies the vm size of the system node pool"
  default     = "Standard_D8ds_v5"
  type        = string
}

variable "network_plugin" {
  description = "Specifies the network plugin of the AKS cluster"
  default     = "azure"
  type        = string
}

variable "system_node_pool_name" {
  description = "Specifies the name of the system node pool"
  default     =  "system"
  type        = string
}

variable "system_node_pool_max_pods" {
  description = "(Optional) The maximum number of pods that can run on each agent. Changing this forces a new resource to be created."
  type          = number
  default       = 50
}

variable "system_node_pool_node_labels" {
  description = "(Optional) A map of Kubernetes labels which should be applied to nodes in this Node Pool. Changing this forces a new resource to be created."
  type          = map(any)
  default       = {}
} 

variable "system_node_pool_node_taints" {
  description = "(Optional) A list of Kubernetes taints which should be applied to nodes in the agent pool (e.g key=value:NoSchedule). Changing this forces a new resource to be created."
  type          = list(string)
  default       = ["CriticalAddonsOnly=true:NoSchedule"]
} 

variable "system_node_pool_os_disk_type" {
  description = "(Optional) The type of disk which should be used for the Operating System. Possible values are Ephemeral and Managed. Defaults to Managed. Changing this forces a new resource to be created."
  type          = string
  default       = "Ephemeral"
} 

variable "user_node_pool_name" {
  description = "(Required) Specifies the name of the node pool."
  type        = string
  default     = "user"
}

variable "user_node_pool_vm_size" {
  description = "(Required) The SKU which should be used for the Virtual Machines used in this Node Pool. Changing this forces a new resource to be created."
  type        = string
  default     = "Standard_D8ds_v5"
}

variable "user_node_pool_availability_zones" {
  description = "(Optional) A list of Availability Zones where the Nodes in this Node Pool should be created in. Changing this forces a new resource to be created."
  type        = list(string)
  default = ["1", "2", "3"]
}

variable "user_node_pool_os_disk_type" {
  description = "(Optional) The type of disk which should be used for the Operating System. Possible values are Ephemeral and Managed. Defaults to Managed. Changing this forces a new resource to be created."
  type          = string
  default       = "Ephemeral"
} 

variable "user_node_pool_os_type" {
  description = "(Optional) The Operating System which should be used for this Node Pool. Changing this forces a new resource to be created. Possible values are Linux and Windows. Defaults to Linux."
  type          = string
  default       = "Linux"
} 

variable "user_node_pool_priority" {
  description = "(Optional) The Priority for Virtual Machines within the Virtual Machine Scale Set that powers this Node Pool. Possible values are Regular and Spot. Defaults to Regular. Changing this forces a new resource to be created."
  type          = string
  default       = "Regular"
} 

variable "storage_account_kind" {
  description = "(Optional) Specifies the account kind of the storage account"
  default     = "StorageV2"
  type        = string

   validation {
    condition = contains(["Storage", "StorageV2"], var.storage_account_kind)
    error_message = "The account kind of the storage account is invalid."
  }
}

variable"key_vault_enabled_for_disk_encryption" {
  description = " (Optional) Boolean flag to specify whether Azure Disk Encryption is permitted to retrieve secrets from the vault and unwrap keys. Defaults to false."
  type        = bool
  default     = true
}

variable"key_vault_enabled_for_template_deployment" {
  description = "(Optional) Boolean flag to specify whether Azure Resource Manager is permitted to retrieve secrets from the key vault. Defaults to false."
  type        = bool
  default     = true
}

variable"key_vault_enable_rbac_authorization" {
  description = "(Optional) Boolean flag to specify whether Azure Key Vault uses Role Based Access Control (RBAC) for authorization of data actions. Defaults to false."
  type        = bool
  default     = true
}

variable"key_vault_purge_protection_enabled" {
  description = "(Optional) Is Purge Protection enabled for this Key Vault? Defaults to false."
  type        = bool
  default     = false
}

variable "key_vault_soft_delete_retention_days" {
  description = "(Optional) The number of days that items should be retained for once soft-deleted. This value can be between 7 and 90 (the default) days."
  type        = number
  default     = 30
}

variable "key_vault_bypass" { 
  description = "(Required) Specifies which traffic can bypass the network rules. Possible values are AzureServices and None."
  type        = string
  default     = "AzureServices" 

  validation {
    condition = contains(["AzureServices", "None" ], var.key_vault_bypass)
    error_message = "The valut of the bypass property of the key vault is invalid."
  }
}

variable "key_vault_default_action" { 
  description = "(Required) The Default Action to use when no rules match from ip_rules / virtual_network_subnet_ids. Possible values are Allow and Deny."
  type        = string
  default     = "Allow" 

  validation {
    condition = contains(["Allow", "Deny" ], var.key_vault_default_action)
    error_message = "The value of the default action property of the key vault is invalid."
  }
}

variable "admin_username" {
  description = "(Required) Specifies the admin username of the jumpbox virtual machine and AKS worker nodes."
  type        = string
  default     = "azadmin"
}

variable "keda_enabled" {
  description = "(Optional) Specifies whether KEDA Autoscaler can be used for workloads."
  type        = bool
  default     = true
}

variable "vertical_pod_autoscaler_enabled" {
  description = "(Optional) Specifies whether Vertical Pod Autoscaler should be enabled."
  type        = bool
  default     = true
}

variable "workload_identity_enabled" {
  description = "(Optional) Specifies whether Azure AD Workload Identity should be enabled for the Cluster. Defaults to false."
  type        = bool
  default     = true
}

variable "oidc_issuer_enabled" {
  description = "(Optional) Enable or Disable the OIDC issuer URL."
  type        = bool
  default     = true
}

variable "open_service_mesh_enabled" {
  description = "(Optional) Is Open Service Mesh enabled? For more details, please visit Open Service Mesh for AKS."
  type        = bool
  default     = true
}

variable "image_cleaner_enabled" {
  description = "(Optional) Specifies whether Image Cleaner is enabled."
  type        = bool
  default     = true
}

variable "azure_policy_enabled" {
  description = "(Optional) Should the Azure Policy Add-On be enabled? For more details please visit Understand Azure Policy for Azure Kubernetes Service"
  type        = bool
  default     = true
}

variable "http_application_routing_enabled" {
  description = "(Optional) Should HTTP Application Routing be enabled?"
  type        = bool
  default     = false
}

variable "openai_name" {
  description = "(Required) Specifies the name of the Azure OpenAI Service"
  type = string
  default = "OpenAi"
}

variable "openai_sku_name" {
  description = "(Optional) Specifies the sku name for the Azure OpenAI Service"
  type = string
  default = "S0"
}

variable "openai_custom_subdomain_name" {
  description = "(Optional) Specifies the custom subdomain name of the Azure OpenAI Service"
  type = string
  nullable = true
  default = ""
}

variable "openai_public_network_access_enabled" {
  description = "(Optional) Specifies whether public network access is allowed for the Azure OpenAI Service"
  type = bool
  default = true
}

variable "openai_deployments" {
  description = "(Optional) Specifies the deployments of the Azure OpenAI Service"
  type = list(object({
    name = string
    model = object({
      name = string
      version = string
    })
    rai_policy_name = string  
  }))
  default = [
    {
      name = "gpt-35-turbo"
      model = {
        name = "gpt-35-turbo"
        version = "0301"
      }
      rai_policy_name = ""
    }
  ] 
}

variable "nat_gateway_name" {
  description = "(Required) Specifies the name of the Azure OpenAI Service"
  type = string
  default = "NatGateway"
}

variable "nat_gateway_sku_name" {
  description = "(Optional) The SKU which should be used. At this time the only supported value is Standard. Defaults to Standard"
  type = string
  default = "Standard"
}

variable "nat_gateway_idle_timeout_in_minutes" {
  description = "(Optional) The idle timeout which should be used in minutes. Defaults to 4."
  type = number
  default = 4
}

variable "nat_gateway_zones" {
  description = " (Optional) A list of Availability Zones in which this NAT Gateway should be located. Changing this forces a new NAT Gateway to be created."
  type = list(string)
  default = ["1"]
}

variable "workload_managed_identity_name" {
  description = "(Required) Specifies the name of the workload user-defined managed identity."
  type = string
  default = "WorkloadManagedIdentity"
}

variable "subdomain" {
  description = "Specifies the subdomain of the Kubernetes ingress object."
  type = string
  default = "magic8ball"
}

variable "domain" {
  description = "Specifies the domain of the Kubernetes ingress object."
  type = string
  default = "contoso.com"
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

variable "deployment_script_name" {
  description = "(Required) Specifies the name of the Azure OpenAI Service"
  type = string
  default = "BashScript"
}

resource "azurerm_resource_group" "rg" {
  name     = var.name_prefix == null ? "${random_string.prefix.result}${var.resource_group_name}" : "${var.name_prefix}${var.resource_group_name}"
  location = var.location
}

module "log_analytics_workspace" {
  source                           = "./modules/log_analytics"
  name                             = var.name_prefix == null ? "${random_string.prefix.result}${var.log_analytics_workspace_name}" : "${var.name_prefix}${var.log_analytics_workspace_name}"
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
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = var.location
  vnet_name                    = "AksVNet"
  address_space                = ["10.0.0.0/8"]
  log_analytics_workspace_id   = module.log_analytics_workspace.id

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
  name                         = var.name_prefix == null ? "${random_string.prefix.result}${var.nat_gateway_name}" : "${var.name_prefix}${var.nat_gateway_name}"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = var.location
  sku_name                     = var.nat_gateway_sku_name
  idle_timeout_in_minutes      = var.nat_gateway_idle_timeout_in_minutes
  zones                        = var.nat_gateway_zones
  subnet_ids                   = module.virtual_network.subnet_ids
}

module "container_registry" {
  source                       = "./modules/container_registry"
  name                         = "${var.name_prefix}Acr"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = var.location
  sku                          = "Basic"
  admin_enabled                = true
  log_analytics_workspace_id   = module.log_analytics_workspace.id
}

module "aks_cluster" {
  source                                  = "./modules/aks"
  name                                    = var.name_prefix == null ? "${random_string.prefix.result}${var.aks_cluster_name}" : "${var.name_prefix}${var.aks_cluster_name}"
  location                                = var.location
  resource_group_name                     = azurerm_resource_group.rg.name
  resource_group_id                       = azurerm_resource_group.rg.id
  kubernetes_version                      = var.kubernetes_version
  dns_prefix                              = lower(var.aks_cluster_name)
  private_cluster_enabled                 = false
  sku_tier                                = "Free"
  system_node_pool_name                   = var.system_node_pool_name
  system_node_pool_vm_size                = var.system_node_pool_vm_size
  vnet_subnet_id                          = module.virtual_network.subnet_ids[var.system_node_pool_subnet_name]
  pod_subnet_id                           = module.virtual_network.subnet_ids[var.pod_subnet_name]
  system_node_pool_availability_zones     = ["1", "2", "3"]
  system_node_pool_node_labels            = var.system_node_pool_node_labels
  system_node_pool_max_pods               = var.system_node_pool_max_pods
  system_node_pool_os_disk_type           = var.system_node_pool_os_disk_type
  network_dns_service_ip                  = "10.2.0.10"
  network_plugin                          = var.network_plugin
  outbound_type                           = "userAssignedNATGateway"
  network_service_cidr                    = "10.2.0.0/24"
  log_analytics_workspace_id              = module.log_analytics_workspace.id
  role_based_access_control_enabled       = true
  tenant_id                               = data.azurerm_client_config.current.tenant_id
  azure_rbac_enabled                      = true
  admin_username                          = var.admin_username
  keda_enabled                            = var.keda_enabled
  vertical_pod_autoscaler_enabled         = var.vertical_pod_autoscaler_enabled
  workload_identity_enabled               = var.workload_identity_enabled
  oidc_issuer_enabled                     = var.oidc_issuer_enabled
  open_service_mesh_enabled               = var.open_service_mesh_enabled
  image_cleaner_enabled                   = var.image_cleaner_enabled
  azure_policy_enabled                    = var.azure_policy_enabled
  http_application_routing_enabled        = var.http_application_routing_enabled

  depends_on = [
    module.nat_gateway,
    module.container_registry
  ]
}

module "node_pool" {
  source = "./modules/node_pool"
  resource_group_name = azurerm_resource_group.rg.name
  kubernetes_cluster_id = module.aks_cluster.id
  name                         = var.user_node_pool_name
  vm_size                      = var.user_node_pool_vm_size
  mode                         = "User"
  availability_zones           = var.user_node_pool_availability_zones
  vnet_subnet_id               = module.virtual_network.subnet_ids[var.user_node_pool_subnet_name]
  pod_subnet_id                = module.virtual_network.subnet_ids[var.pod_subnet_name]
  enable_host_encryption       = false
  enable_node_public_ip        = false
  orchestrator_version         = var.kubernetes_version
  max_pods                     = 50
  os_type                      = var.user_node_pool_os_type
  priority                     = var.user_node_pool_priority
}

module "openai" {
  source                                   = "./modules/openai"
  name                                     = var.name_prefix == null ? "${random_string.prefix.result}${var.openai_name}" : "${var.name_prefix}${var.openai_name}"
  location                                 = var.location
  resource_group_name                      = azurerm_resource_group.rg.name
  sku_name                                 = var.openai_sku_name
  deployments                              = var.openai_deployments
  custom_subdomain_name                    = var.openai_custom_subdomain_name == "" || var.openai_custom_subdomain_name == null ? var.name_prefix == null ? lower("${random_string.prefix.result}${var.openai_name}") : lower("${var.name_prefix}${var.openai_name}") : lower(var.openai_custom_subdomain_name)
  public_network_access_enabled            = var.openai_public_network_access_enabled
  log_analytics_workspace_id               = module.log_analytics_workspace.id
  log_analytics_retention_days             = var.log_analytics_retention_days
}

resource "azurerm_user_assigned_identity" "aks_workload_identity" {
  name                = var.name_prefix == null ? "${random_string.prefix.result}${var.workload_managed_identity_name}" : "${var.name_prefix}${var.workload_managed_identity_name}"
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
  name                        = "${local.storage_account_prefix}${random_string.storage_account_suffix.result}"
  location                    = var.location
  resource_group_name         = azurerm_resource_group.rg.name
  account_kind                = var.storage_account_kind
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
  enabled_for_template_deployment = var.key_vault_enabled_for_template_deployment
  enable_rbac_authorization       = var.key_vault_enable_rbac_authorization
  purge_protection_enabled        = var.key_vault_purge_protection_enabled
  soft_delete_retention_days      = var.key_vault_soft_delete_retention_days
  bypass                          = var.key_vault_bypass
  default_action                  = var.key_vault_default_action
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
  name                                = var.name_prefix == null ? "${random_string.prefix.result}${var.deployment_script_name}" : "${var.name_prefix}${var.deployment_script_name}"
  location                            = var.location
  resource_group_name                 = azurerm_resource_group.rg.name
  azure_cli_version                   = "2.9.1"
  managed_identity_name               = "${var.name_prefix}ScriptManagedIdentity"
  aks_cluster_name                    = module.aks_cluster.name
  hostname                            = "${var.subdomain}.${var.domain}"
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
