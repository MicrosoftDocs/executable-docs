variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "sku_name" {
  type = string
}

variable "enabled_for_deployment" {
  type = bool
}

variable "enabled_for_disk_encryption" {
  type = bool
}

variable "enabled_for_template_deployment" {
  type = bool
}

variable "enable_rbac_authorization" {
  type = bool
}

variable "purge_protection_enabled" {
  type = bool
}

variable "soft_delete_retention_days" {
  type = number
}

variable "bypass" {
  type = string
}

variable "default_action" {
  type = string
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "log_analytics_retention_days" {
  type = number
}