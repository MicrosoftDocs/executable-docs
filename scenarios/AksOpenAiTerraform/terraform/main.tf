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

module "openai" {
  source              = "./modules/openai"
  name                = "OpenAi-${local.random_id}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  sku_name = "S0"
  deployments = [
    {
      name = var.model_name
      model = {
        name    = var.model_name
        version = var.model_version
      }
    }
  ]
  custom_subdomain_name = "magic8ball-${local.random_id}"

  log_analytics_workspace_id = module.log_analytics_workspace.id
}

module "aks" {
  source              = "./modules/aks"
  name                = "AksCluster"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  resource_group_id   = azurerm_resource_group.main.id
  tenant_id           = local.tenant_id

  kubernetes_version       = var.kubernetes_version
  sku_tier                 = "Standard"
  system_node_pool_vm_size = "Standard_DS2_v2"
  user_node_pool_vm_size   = "Standard_DS2_v2"

  system_node_pool_subnet_id = module.virtual_network.subnet_ids["SystemSubnet"]
  user_node_pool_subnet_id   = module.virtual_network.subnet_ids["UserSubnet"]
  pod_subnet_id              = module.virtual_network.subnet_ids["PodSubnet"]

  log_analytics_workspace_id = module.log_analytics_workspace.id

  depends_on = [module.nat_gateway]
}

module "container_registry" {
  source              = "./modules/container_registry"
  name                = "acr${local.random_id}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  sku = "Premium"

  log_analytics_workspace_id = module.log_analytics_workspace.id
}

module "storage_account" {
  source              = "./modules/storage_account"
  name                = "boot${local.random_id}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
}

module "key_vault" {
  source              = "./modules/key_vault"
  name                = "KeyVault${local.random_id}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  tenant_id = local.tenant_id
  sku_name  = "standard"

  log_analytics_workspace_id = module.log_analytics_workspace.id
}

module "log_analytics_workspace" {
  source              = "./modules/log_analytics"
  name                = "Workspace"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  sku               = "PerGB2018"
  retention_in_days = 30
}

module "virtual_network" {
  source              = "./modules/virtual_network"
  name                = "AksVNet"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name

  address_space = ["10.0.0.0/8"]
  log_analytics_workspace_id = module.log_analytics_workspace.id
}

resource "azurerm_federated_identity_credential" "this" {
  name                = "FederatedIdentity"
  resource_group_name = azurerm_resource_group.main.name

  audience  = ["api://AzureADTokenExchange"]
  issuer    = module.aks.oidc_issuer_url
  parent_id = module.aks.workload_identity.id
  subject   = "system:serviceaccount:default:magic8ball-sa"
}

# resource "azurerm_role_assignment" "cognitive_services_user_assignment" {
#   role_definition_name = "Cognitive Services User"
#   scope                = module.openai.id
#   principal_id         = module.aks.workload_identity_client_id
# }

# resource "azurerm_role_assignment" "network_contributor_assignment" {
#   role_definition_name = "Network Contributor"
#   scope                = azurerm_resource_group.main.id
#   principal_id         = module.aks.workload_identity_client_id
# }

# resource "azurerm_role_assignment" "acr_pull_assignment" {
#   role_definition_name = "AcrPull"
#   scope                = module.container_registry.id
#   principal_id         = module.aks.workload_identity_client_id

#   skip_service_principal_aad_check = true
# }