variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "private_connection_resource_id" {
  type = string
}

variable "location" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "subresource_name" {
  type = string
}

variable "private_dns_zone_group_name" {
  type = string
}

variable "private_dns_zone_group_ids" {
  type = list(string)
}