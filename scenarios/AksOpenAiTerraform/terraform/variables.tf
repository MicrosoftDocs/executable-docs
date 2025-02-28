variable "resource_group_name_prefix" {
  type    = string
  default = "AksOpenAiTerraform"
}

variable "location" {
  type    = string
}

variable "kubernetes_version" {
  type    = string
}

variable "model_name" {
  type    = string
}

variable "model_version" {
  type    = string
}