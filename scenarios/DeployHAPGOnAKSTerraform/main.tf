provider "azurerm" {
  features {}
  subscription_id = "325e7c34-99fb-4190-aa87-1df746c67705"
}

resource "azurerm_resource_group" "rg" {
  name     = "pg-ha-rg"
  location = "East US"
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "pg-ha-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "pgha"

  default_node_pool {
    name       = "agentpool"
    node_count = 3
    vm_size    = "Standard_DS2_v2"
  }

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_postgresql_server" "pg_server" {
  name                         = "pg-ha-server"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  version                      = "11"
  administrator_login          = "pgadmin"
  administrator_login_password = "YourPassword123!"
  ssl_enforcement_enabled      = true
  sku_name                     = "B_Gen5_2"
  storage_mb                   = 5120
}

resource "azurerm_postgresql_database" "pg_database" {
  name                = "mydatabase"
  resource_group_name = azurerm_resource_group.rg.name
  server_name         = azurerm_postgresql_server.pg_server.name
  charset             = "UTF8"
  collation           = "English_United States.1252"
}