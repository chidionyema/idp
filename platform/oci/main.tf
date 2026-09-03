module "oke" {
  source    = "oracle-terraform-modules/oke/oci"
  version   = "~> 5.2"
  providers = { oci = oci, oci.home = oci.home }

  tenancy_id     = var.tenancy_ocid
  compartment_id = var.compartment_ocid
  home_region    = var.region
  region         = var.region

  # Basic cluster: no control-plane charge (ADR 0004 decision 1).
  cluster_name       = "estate"
  cluster_type       = "basic"
  kubernetes_version = var.kubernetes_version
  cni_type           = "flannel"

  # Public API endpoint so Flux bootstrap and idp-verify reach it from the Mac; workers private.
  control_plane_is_public           = true
  assign_public_ip_to_control_plane = true                            # 2026-08-25: without it the module creates a private endpoint only (is_public_ip_enabled = both)
  control_plane_allowed_cidrs       = var.control_plane_allowed_cidrs # 2026-08-25: default [] admitted nobody; flux bootstrap timed out
  worker_is_public                  = false
  create_bastion                    = false
  create_operator                   = false

  ssh_public_key = var.ssh_public_key

  worker_pools = {
    a1 = {
      description      = "the whole Always Free A1 allowance, one node"
      shape            = "VM.Standard.A1.Flex"
      ocpus            = var.worker_ocpus
      memory           = var.worker_memory_gb
      size             = 1
      boot_volume_size = 50
      placement_ads    = [1, 2] # 2026-08-25 apply failed: "Node shape is unavailable in subnet availability domain(s)"; VM.Standard.A1.Flex is offered in AD-1 and AD-2 only (oci compute shape list per AD)
    }
  }
}

output "cluster_id" {
  value = module.oke.cluster_id
}

output "cluster_endpoints" {
  value = module.oke.cluster_endpoints
}
