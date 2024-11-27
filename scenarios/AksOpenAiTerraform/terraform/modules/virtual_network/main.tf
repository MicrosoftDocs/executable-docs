resource "azurerm_virtual_network" "vnet" {
  name                = var.vnet_name
  address_space       = var.address_space
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  lifecycle {
    ignore_changes = [
        tags
    ]
  }
}

resource "azurerm_subnet" "subnet" {
  for_each = { for subnet in var.subnets : subnet.name => subnet }

  name                                           = each.key
  resource_group_name                            = var.resource_group_name
  virtual_network_name                           = azurerm_virtual_network.vnet.name
  address_prefixes                               = each.value.address_prefixes
  private_endpoint_network_policies              = each.value.private_endpoint_network_policies
  private_link_service_network_policies_enabled  = each.value.private_link_service_network_policies_enabled

  dynamic "delegation" {
    for_each                                     = each.value.delegation != null ? [each.value.delegation] : []
    content {
      name                                       = "delegation"
      
      service_delegation {
        name                                     = delegation.value.service_delegation.name
        actions                                  = delegation.value.service_delegation.actions
      }
    }
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