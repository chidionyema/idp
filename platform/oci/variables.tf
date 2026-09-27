variable "tenancy_ocid" {
  description = "Tenancy OCID. docs/reference/oci-tenancy.md; an identifier, not a credential."
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment for every resource. The root compartment is acceptable on a single-owner Free Tier tenancy."
  type        = string
}

variable "region" {
  description = "Home region. Always Free resources exist only in the home region."
  type        = string
  default     = "uk-london-1"
}

variable "ssh_public_key" {
  description = "Public key for worker-node SSH. Public half only."
  type        = string
}

variable "worker_ocpus" {
  type    = number
  default = 6
}

variable "worker_memory_gb" {
  type    = number
  default = 24
}

variable "kubernetes_version" {
  type    = string
  default = "v1.35.2" # in both `oci ce cluster-options get` and the aarch64 OKE image list (`oci ce node-pool-options get`), 2026-08-25
}

variable "control_plane_allowed_cidrs" {
  type        = list(string)
  description = "CIDRs admitted to the Kubernetes API endpoint. Written by bin/idp-oci-login from the measured egress IP."
  default     = []
}

# crew#220 hand step 2: the name was the literal "estate", so a second cluster (a drill target,
# a blue/green move) could not exist. Pass -var cluster_name=estate-drill from bin/idp-oke-rebuild.
variable "cluster_name" {
  type    = string
  default = "estate"
}

# crew#713 CP1: how long a daily copy of the shop database is kept. A number, not a constant, so
# the retention story can be answered with a value rather than a rebuild (founder 2026-08-31,
# "configurable obvs"). 90 days of 5.3 MB is 480 MB against a 20 GB always-free allowance.
variable "shop_backup_retention_days" {
  type    = number
  default = 90
}

variable "oci_auth" {
  description = "Provider auth: APIKey on a laptop (bin/idp-oci-login), SecurityToken under GitHub OIDC."
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

variable "founder_email" {
  description = "Login for Langfuse's seeded user (platform/oci/langfuse.tf). Rendered into terraform.tfvars by bin/idp-oci-login from ESTATE_FOUNDER_EMAIL (repo variable in CI); never a literal here (LAW 46)."
  type        = string
}
