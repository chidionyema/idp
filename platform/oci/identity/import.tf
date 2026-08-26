

variable "client_id_secret_ocid" {
  type    = string
  default = ""
}
variable "client_secret_secret_ocid" {
  type    = string
  default = ""
}
import {
  for_each = var.client_id_secret_ocid != "" ? { one = var.client_id_secret_ocid } : {}
  to       = oci_vault_secret.client_id
  id       = each.value
}
import {
  for_each = var.client_secret_secret_ocid != "" ? { one = var.client_secret_secret_ocid } : {}
  to       = oci_vault_secret.client_secret
  id       = each.value
}
