variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "script_path" {
  type = string
}

variable "aks_cluster_id" {
  type = string
}

variable "azure_cli_version" {
  type = string
}

variable "managed_identity_name" {
  type = string
}

variable "aks_cluster_name" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "subscription_id" {
  type = string
}

variable "hostname" {
  type = string
}

variable "namespace" {
  type = string
}

variable "service_account_name" {
  type = string
}

variable "workload_managed_identity_client_id" {
  type = string
}

variable "email" {
  description = "Specifies the email address for the cert-manager cluster issuer."
  type        = string
}