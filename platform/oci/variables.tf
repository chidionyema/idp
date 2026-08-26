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

# Always Free A1 allowance since 2026-06-15: 2 OCPU / 12 GB in total (ADR 0004). Anything
# above it is paid, and paid capacity is auto-defaulted up to estate-defaults.yaml
# node_pool.budget_monthly_usd (crew#281 compute_tier auto-scale-paid; crew#289 the keys). The cap is the
# founder's sign-off that ruling R14 asked for, written once; the precondition on
# terraform_data.capacity_cap in main.tf refuses a plan over it, and policy/node_pool.rego is
# the same rule over `tofu output -json capacity`.
variable "worker_ocpus" {
  type    = number
  default = 4
}

variable "worker_memory_gb" {
  type    = number
  default = 24
}

variable "free_ocpus" {
  description = "Always Free A1 OCPU allowance (ADR 0004)."
  type        = number
  default     = 2
}

variable "free_memory_gb" {
  description = "Always Free A1 memory allowance in GB (ADR 0004)."
  type        = number
  default     = 12
}

# Oracle public price list, read 2026-08-26 from
# apexapps.oracle.com/pls/apex/cetools/api/v1/products/: part B93297 (A1 OCPU) and
# B93298 (A1 memory), PAY_AS_YOU_GO. Re-read them when the list changes; never from memory.
variable "a1_ocpu_usd_per_hour" {
  type    = number
  default = 0.01
}

variable "a1_memory_gb_usd_per_hour" {
  type    = number
  default = 0.0015
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
