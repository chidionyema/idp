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
  type = number
  # 2026-10-28: the Always Free allowance is 2 OCPU, and the node that is actually running is
  # already 2 OCPU / 12 GB (oci compute instance list, 2026-10-28). The pool asked for 6 / 24,
  # and a shape the running node does not have is why every apply wanted a SURGE node -- which
  # wants a boot volume the allowance refuses. Ask for what the node already is.
  default = 2
}

variable "worker_memory_gb" {
  type = number
  # 2026-10-28: 24 -> 12, the free tier's allowance and the running node's own size.
  default = 12
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

# When the quad-ledger anchor PAR stops working (quad.tf). OCI requires an expiry; a dated value
# rather than timeadd(timestamp()), which would replace the PAR on every plan. When it lapses the
# quad-ledger-anchor CronJob fails its PUT with 404: move this date forward and apply.
variable "quad_anchor_par_expires" {
  type    = string
  default = "2027-10-13T00:00:00Z"
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
