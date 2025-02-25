variable "resource_group_name_prefix" {
  type    = string
  default = "AksOpenAiTerraform"
}

variable "location" {
  type    = string
  default = "westus3"
}

variable "kubernetes_version" {
  type    = string
  default = "1.30.7"
}