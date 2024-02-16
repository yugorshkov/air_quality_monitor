variable "timeweb_token" {
  description = "timeweb API token"
  type = string
  sensitive = true
}

variable "db_user" {
  type = string
  sensitive = true
}

variable "db_pass" {
  type = string
  sensitive = true
}