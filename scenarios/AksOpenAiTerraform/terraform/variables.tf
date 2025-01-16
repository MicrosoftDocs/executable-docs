variable "name_prefix" {
  type = string
  default = "AksOpenAiTerraform"
}

variable "location" {
  default = "westus2"
  type    = string
}

variable "email" {
  type        = string
  default     = "paolos@microsoft.com"
}