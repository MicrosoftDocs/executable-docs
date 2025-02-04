variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group Name"
  type        = string
}

variable "location" {
  description = "Azure Region"
  type        = string
}

variable "aks_cluster_name" {
  description = "AKS Cluster Name"
  type        = string
}

variable "postgres_server_name" {
  description = "PostgreSQL Server Name"
  type        = string
}

variable "postgres_database_name" {
  description = "PostgreSQL Database Name"
  type        = string
}

variable "postgres_database_user" {
  description = "PostgreSQL Database User"
  type        = string
}

variable "postgres_database_password" {
  description = "PostgreSQL Database Password"
  type        = string
  sensitive   = true
}