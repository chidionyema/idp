variable "zone" {
  type        = string
  description = "estate DNS zone, e.g. from clusters/oke/estate-config.yaml"
}
variable "team_name" {
  type        = string
  description = "Cloudflare Zero Trust team name; login lives at <team>.cloudflareaccess.com"
}
variable "founder_emails" {
  type        = list(string)
  description = "the people the front door admits, by email (one-time PIN)"
}
variable "compartment_ocid" { type = string }
variable "vault_ocid" { type = string }
variable "key_ocid" { type = string }
variable "session_duration" {
  type    = string
  default = "12h"
}
