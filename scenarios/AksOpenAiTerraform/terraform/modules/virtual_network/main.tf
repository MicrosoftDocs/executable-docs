resource "azurerm_virtual_network" "vnet" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  
  address_space       = var.address_space
}

resource "azurerm_subnet" "bastion" {
  name                 = "AzureBastionSubnet"
  resource_group_name  = var.resource_group_name
  
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.243.2.0/24"]
}

resource "azurerm_public_ip" "public_ip" {
  name                = "PublicIp"
  location            = var.location
  resource_group_name = var.resource_group_name
  
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_bastion_host" "bastion_host" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                 = "configuration"
    subnet_id            = azurerm_subnet.bastion.id
    public_ip_address_id = azurerm_public_ip.public_ip.id
  }
}

resource "azurerm_monitor_diagnostic_setting" "settings" {
  name                       = "BastionDiagnosticsSettings"
  target_resource_id         = azurerm_bastion_host.bastion_host.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "BastionAuditLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "pip_settings" {
  name                       = "BastionDdosDiagnosticsSettings"
  target_resource_id         = azurerm_public_ip.public_ip.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "DDoSProtectionNotifications"
  }

  enabled_log {
    category = "DDoSMitigationFlowLogs"
  }

  enabled_log {
    category = "DDoSMitigationReports"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "settings" {
  name                       = "VirtualNetworkDiagnosticsSettings"
  target_resource_id         = azurerm_virtual_network.vnet.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "AllMetrics"
  }
}