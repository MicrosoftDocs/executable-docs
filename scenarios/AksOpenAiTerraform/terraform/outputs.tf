output "resource_group_name" {
    value = azurerm_resource_group.main.name
}

output "cluster_name" {
    value = module.aks.name
}

output "workload_managed_identity_client_id" {
    value = azurerm_user_assigned_identity.aks_workload.client_id
}

output "acr_name" {
    value = module.container_registry.name
}