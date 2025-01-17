output "name" {
  value = azurerm_virtual_network.vnet.name
}

output "subnet_ids" {
  value = { for subnet in azurerm_subnet.subnet : subnet.name => subnet.id }
}