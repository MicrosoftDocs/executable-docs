output "resource_group_name" {
    value = azurerm_resource_group.main.name
}

output "cluster_name" {
    value = module.aks.name
}

output "acr_name" {
    value = module.container_registry.name
}