output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "workload_identity_client_id" {
  value = azurerm_user_assigned_identity.workload.client_id
}

output "acr_login_url" {
    value = azurerm_container_registry.this.login_server
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}