resource "azurerm_user_assigned_identity" "workload" {
  name                = "WorkloadManagedIdentity"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_kubernetes_cluster" "main" {
  name                             = var.name
  location                         = var.location
  resource_group_name              = var.resource_group_name
  kubernetes_version               = var.kubernetes_version
  automatic_upgrade_channel        = "stable"
  sku_tier                         = var.sku_tier

  image_cleaner_enabled            = true
  image_cleaner_interval_hours     = 72

  workload_identity_enabled        = true
  oidc_issuer_enabled              = true

  default_node_pool {
    name           = "system"
    node_count     = 2
    vm_size        = var.system_node_pool_vm_size

    upgrade_settings {
      max_surge                     = "10%"
      drain_timeout_in_minutes      = 0
      node_soak_duration_in_minutes = 0
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = tolist([azurerm_user_assigned_identity.workload.id])
  }

  network_profile {
    network_plugin = "kubenet"
    outbound_type  = "userAssignedNATGateway"
  }

  oms_agent {
    msi_auth_for_monitoring_enabled = true
    log_analytics_workspace_id      = var.log_analytics_workspace_id
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "this" {
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  name                  = "user"
  mode                  = "User"
  orchestrator_version  = var.kubernetes_version
  vm_size               = var.user_node_pool_vm_size
  os_type               = "Linux"
  priority              = "Regular"
}

resource "azurerm_monitor_diagnostic_setting" "settings" {
  name                       = "AksDiagnosticsSettings"
  target_resource_id         = azurerm_kubernetes_cluster.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "kube-apiserver"
  }

  enabled_log {
    category = "kube-audit"
  }

  enabled_log {
    category = "kube-audit-admin"
  }

  enabled_log {
    category = "kube-controller-manager"
  }

  enabled_log {
    category = "kube-scheduler"
  }

  enabled_log {
    category = "cluster-autoscaler"
  }

  enabled_log {
    category = "guard"
  }

  metric {
    category = "AllMetrics"
  }
}