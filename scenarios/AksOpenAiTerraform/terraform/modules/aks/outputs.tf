output "name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "id" {
  value = azurerm_kubernetes_cluster.main.id
}

output "workload_identity" {
  value = azurerm_user_assigned_identity.workload
}

output "workload_identity_client_id" {
  value = azurerm_user_assigned_identity.workload.client_id
}

output "kubelet_identity" {
  value = azurerm_kubernetes_cluster.main.kubelet_identity.0
}

output "oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.main.oidc_issuer_url
}