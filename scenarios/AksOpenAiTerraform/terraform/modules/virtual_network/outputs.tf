output "name" {
	value = azurerm_virtual_network.vnet.name
}

output "subnet_ids" {
  value = azurerm_subnet.subnet.*.id
}