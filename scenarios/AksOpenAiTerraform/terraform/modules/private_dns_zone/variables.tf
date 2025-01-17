variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "virtual_networks_to_link" {
  type = map(string, object({
    subscription_id     = string
    resource_group_name = string
  }))
}