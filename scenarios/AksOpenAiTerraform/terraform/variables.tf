variable "resource_group_name_prefix" {
  type    = string
  default = "AksOpenAiTerraform"
}

variable "location" {
  type    = string
  default = "westus2"
}

variable "kubernetes_version" {
  type    = string
  default = "1.30.7"
}

variable "system_node_pool_vm_size" {
  type    = string
  default = "Standard_D8ds_v5"
}

variable "user_node_pool_vm_size" {
  type    = string
  default = "Standard_D8ds_v5"
}

variable "email" {
  type    = string
  default = "paolos@microsoft.com"
}