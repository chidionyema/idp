module "oke" {
  source    = "oracle-terraform-modules/oke/oci"
  version   = "~> 5.2"
  providers = { oci = oci, oci.home = oci.home }

  tenancy_id     = var.tenancy_ocid
  compartment_id = var.compartment_ocid
  home_region    = var.region
  region         = var.region

  # Basic cluster: no control-plane charge (ADR 0004 decision 1).
  cluster_name       = var.cluster_name # crew#220 hand step 2: a drill cluster is the same module under another name
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
      description      = "one A1 node: the Always Free allowance plus paid growth under the estate-defaults cap"
      shape            = "VM.Standard.A1.Flex"
      ocpus            = var.worker_ocpus
      memory           = var.worker_memory_gb
      size             = 1
      boot_volume_size = 50
      # crew#289: a shape change reaches only new nodes. On 2026-08-26 the apply moved the pool to
      # 4 OCPU / 24 GB while the running node stayed at 2 / 12 (`oci compute instance list`, kubectl
      # allocatable 1830m). Cycling replaces the node: surge 1 brings the new node Ready first,
      # unavailable 0 drains the old one only then. Same module setting the OKE docs call node cycling.
      node_cycling_enabled         = true
      node_cycling_max_surge       = 1
      node_cycling_max_unavailable = 0
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

# Paid capacity stays under the cap the founder wrote (estate-defaults.yaml node_pool.budget_monthly_usd, crew#289).
# The estimate is (paid OCPU x price + paid GB x price) x 730 hours; policy/node_pool.rego computes
# the same number from the `capacity` output below, and the fixtures pin both.
locals {
  estate_defaults      = yamldecode(file("${path.module}/../../estate-defaults.yaml"))
  monthly_cap_usd      = local.estate_defaults.node_pool.budget_monthly_usd
  paid_ocpus           = max(0, var.worker_ocpus - var.free_ocpus)
  paid_memory_gb       = max(0, var.worker_memory_gb - var.free_memory_gb)
  capacity_monthly_usd = (local.paid_ocpus * var.a1_ocpu_usd_per_hour + local.paid_memory_gb * var.a1_memory_gb_usd_per_hour) * 730
  capacity = {
    ocpus           = var.worker_ocpus
    memory_gb       = var.worker_memory_gb
    free            = { ocpus = var.free_ocpus, memory_gb = var.free_memory_gb }
    price_usd_hr    = { ocpu = var.a1_ocpu_usd_per_hour, memory_gb = var.a1_memory_gb_usd_per_hour }
    monthly_cap_usd = local.monthly_cap_usd
    monthly_usd     = local.capacity_monthly_usd
    prefer_free     = local.estate_defaults.node_pool.prefer_free
  }
}

resource "terraform_data" "capacity_cap" {
  input = local.capacity_monthly_usd
  lifecycle {
    precondition {
      condition     = local.capacity_monthly_usd <= local.monthly_cap_usd
      error_message = "Node pool ${var.worker_ocpus} OCPU / ${var.worker_memory_gb} GB is an estimated USD ${local.capacity_monthly_usd} a month, over estate-defaults node_pool.budget_monthly_usd ${local.monthly_cap_usd}. A paid billing authorisation is FOUNDER ACTION, not STAGED."
    }
  }
}

output "capacity" {
  description = "Input for policy/node_pool.rego; bin/idp-oke-rebuild --plan-pool reads local.capacity through tofu console so no apply is needed."
  value       = local.capacity
}
