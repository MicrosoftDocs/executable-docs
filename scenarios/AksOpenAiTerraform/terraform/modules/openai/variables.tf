variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "sku_name" {
  type = string
}

variable "custom_subdomain_name" {
  type = string
}

variable "public_network_access_enabled" {
  type    = bool
  default = true
}

variable "deployments" {
  type = list(object({
    name = string
    model = object({
      name    = string
      version = string
    })
    rai_policy_name = string
  }))
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "log_analytics_retention_days" {
  type = number
}