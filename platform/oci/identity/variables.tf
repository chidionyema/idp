variable "idcs_endpoint" {
  type        = string
  description = "the identity domain URL (DOMAIN_BASE_URL, written by bin/idp-oci-bootstrap)"
}
variable "zone" {
  type        = string
  description = "estate DNS zone, from clusters/oke/estate-config.yaml"
}
variable "founder_emails" {
  type        = list(string)
  description = "the people the front door admits; each must be a user of the identity domain"
}
variable "compartment_ocid" { type = string }
variable "vault_ocid" { type = string }
variable "key_ocid" { type = string }
