output "resource_group_name" {
    value = module.azurerm_resource_group.name
}

output "acr_url" {
    value = module.container_registry.name
}