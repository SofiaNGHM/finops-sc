variable "aws_region" {
  type    = string
  default = "us-east-2"
}
variable "enable_network" {
  type    = bool
  default = false
}
variable "enable_compute" {
  type    = bool
  default = false
}
variable "enable_nat" {
  type    = bool
  default = false
}
variable "instance_type" {
  type    = string
  default = "t3.micro"
  validation {
    condition     = contains(["t3.micro", "t3.small"], var.instance_type)
    error_message = "Solo se permiten t3.micro o t3.small para este laboratorio."
  }
}
variable "ami_id" {
  type    = string
  default = ""
}
variable "root_volume_gb" {
  type    = number
  default = 12
  validation {
    condition     = var.root_volume_gb >= 8 && var.root_volume_gb <= 30
    error_message = "El volumen raíz debe estar entre 8 y 30 GiB."
  }
}
variable "data_volume_gb" {
  type    = number
  default = 8
  validation {
    condition     = var.data_volume_gb >= 1 && var.data_volume_gb <= 30
    error_message = "El volumen de datos debe estar entre 1 y 30 GiB."
  }
}
variable "budget_limit_usd" {
  type    = number
  default = 10
}
