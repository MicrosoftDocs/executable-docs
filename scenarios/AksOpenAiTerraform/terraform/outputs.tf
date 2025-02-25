output "resource_group_name" {
    value = azurerm_resource_group.main.name
}

output "acr_url" {
    value = module.container_registry.name
}