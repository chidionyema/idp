# The two vault secrets already exist (created as placeholders on idp#146); a create would 409.
# Import by OCID on first apply, then Terraform owns them. The ids come from the wrapper by name.
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
