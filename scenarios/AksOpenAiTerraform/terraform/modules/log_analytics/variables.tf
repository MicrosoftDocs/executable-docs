variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "sku" {
  type = string
}

variable "solution_plan_map" {
  type = map(any)
}

variable "retention_in_days" {
  type = number
}