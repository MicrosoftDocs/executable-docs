resource "azurerm_kubernetes_cluster_node_pool" "node_pool" {
  kubernetes_cluster_id        = var.kubernetes_cluster_id
  name                         = var.name
  vm_size                      = var.vm_size
  mode                         = var.mode
  node_labels                  = var.node_labels
  node_taints                  = var.node_taints
  zones                        = var.availability_zones
  vnet_subnet_id               = var.vnet_subnet_id
  pod_subnet_id                = var.pod_subnet_id
  proximity_placement_group_id = var.proximity_placement_group_id
  orchestrator_version         = var.orchestrator_version
  max_pods                     = var.max_pods
  os_disk_size_gb              = var.os_disk_size_gb
  os_disk_type                 = var.os_disk_type
  os_type                      = var.os_type
  priority                     = var.priority
  tags                         = var.tags

  lifecycle {
    ignore_changes = [
        tags
    ]
  }
}