variable "name_prefix" {
  type        = string
}

variable "log_analytics_workspace_name" {
  default     = "Workspace"
  type        = string
}

variable "log_analytics_retention_days" {
  type        = number
  default     = 30
}

variable "location" {
  default     = "westus2"
  type        = string
}

variable "resource_group_name" {
  default     = "RG"
  type        = string
}

variable "system_node_pool_subnet_name" {
  default     =  "SystemSubnet"
  type        = string
}

variable "user_node_pool_subnet_name" {
  default     =  "UserSubnet"
  type        = string
}

variable "pod_subnet_name" {
  default     = "PodSubnet"
  type        = string
}

variable "vm_subnet_name" {
  default     = "VmSubnet"
  type        = string
}

variable "namespace" {
  description = "Specifies the namespace of the workload application that accesses the Azure OpenAI Service."
  type = string
  default = "magic8ball"
}

variable "service_account_name" {
  description = "Specifies the name of the service account of the workload application that accesses the Azure OpenAI Service."
  type = string
  default = "magic8ball-sa"
}

variable "email" {
  description = "Specifies the email address for the cert-manager cluster issuer."
  type = string
  default = "paolos@microsoft.com"
}