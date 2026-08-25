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

# Always Free A1 allowance since 2026-06-15: 2 OCPU / 12 GB in total (ADR 0004). One node
# holds all of it; a second pool or a bigger node is a paid resource and refused by R14.
variable "worker_ocpus" {
  type    = number
  default = 2
  validation {
    condition     = var.worker_ocpus <= 2
    error_message = "Always Free A1 is 2 OCPU total (ADR 0004). More is paid infra, refused by ruling R14."
  }
}

variable "worker_memory_gb" {
  type    = number
  default = 12
  validation {
    condition     = var.worker_memory_gb <= 12
    error_message = "Always Free A1 is 12 GB total (ADR 0004). More is paid infra, refused by ruling R14."
  }
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
