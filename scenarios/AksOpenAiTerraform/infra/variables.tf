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

variable "model_name" {
  type    = string
  default = "gpt-4o-mini"
}

variable "model_version" {
  type    = string
  default = "2024-07-18"
}