output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "workload_identity_client_id" {
  value = azurerm_user_assigned_identity.workload.client_id
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_deployment" {
  value = azurerm_cognitive_deployment.deployment.name
}

output "hostname" {
  value = azurerm_public_ip.this.fqdn
}

output "static_ip" {
  value = azurerm_public_ip.this.ip_address
}

output "dns_label" {
  value = azurerm_public_ip.this.domain_name_label
}