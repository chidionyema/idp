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

variable "oci_auth" {
  description = "Provider auth, as platform/oci: APIKey on a laptop, SecurityToken under GitHub OIDC (crew#408: applied from oke-check, never a laptop)."
  type        = string
  default     = "APIKey"
  validation {
    condition     = contains(["APIKey", "SecurityToken"], var.oci_auth)
    error_message = "oci_auth is APIKey or SecurityToken."
  }
}

variable "oci_profile" {
  description = "Profile in ~/.oci/config that holds the credential."
  type        = string
  default     = "DEFAULT"
}
