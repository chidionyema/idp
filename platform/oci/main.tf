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
      description = "one A1 node: the Always Free allowance plus paid growth under the estate-defaults cap"
      # crew#539 CP10: the capacity class a pod's affinity reads (platform/scheduling/capacity-affinity.yaml).
      # initial_node_labels reach NEW nodes only; the running node carries no label, which is why the
      # radio-room rule is NotIn [preemptible], never In [on-demand].
      node_labels = { "estate.io/capacity" = "on-demand" }
      shape       = "VM.Standard.A1.Flex"
      ocpus       = var.worker_ocpus
      memory      = var.worker_memory_gb
      size        = 1
      # crew#539 CP4 (2026-08-27): the Cluster Autoscaler (platform/oci/autoscaler) owns the size between
      # 1 and estate-defaults node_pool.max_nodes; the module then ignores `size` (autoscaler.tf).
      autoscale                = true
      ignore_initial_pool_size = true
      # 100, not 50 (crew#516 CP4, 2026-08-27): at 50 GB the node evicted hermes-agent-gateway with
      # 5.9 GB free under the 6.25 GB threshold (87 pods' images; oke-check 33096065995). Block storage
      # is 200 GB Always Free and the PVCs claim 21 GB. Reaches a NEW node only: oke-check mode=surge-node.
      boot_volume_size = 100
      # crew#289 (2026-08-26): a shape change reaches only new nodes; the running node stayed at
      # 2 OCPU / 12 GB after the pool moved to 4 / 24. node_cycling_* was tried and UpdateNodePool
      # refused it in run 32930359052: the cluster is BASIC_CLUSTER (`oci ce cluster get`), and OKE
      # offers node cycling on enhanced clusters only
      # (docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengcomparingenhancedwithbasicclusters_topic.htm).
      # Replacing a node on this cluster is a surge: `oci ce node-pool update --size 2 --force`, wait
      # for the new node Ready, then `delete-node --is-decrement-size true` on the old one.
      # AD-1 only (crew#289, 2026-08-26): the two block-volume PVs (backstage/pgdata-postgres-0,
      # prospector/prospector-store-api-data) carry nodeAffinity UK-LONDON-1-AD-1; a node in AD-2
      # could never mount them. A1.Flex is offered in AD-1 and AD-2 only, and the 2026-08-25
      # "Node shape is unavailable in subnet availability domain(s)" failure was AD-3. The module
      # ignores changes to this after creation, so it binds fresh creates (--teardown-rebuild) only.
      placement_ads = [1]
    }
    # crew#539 CP10 (2026-08-27): preemptible capacity, the same shape at half the price, size 0 until
    # the Cluster Autoscaler wants it (--nodes=0:<spot_max_nodes>). Oracle reclaims a preemptible node
    # with 30 s notice and TERMINATE is the only action OKE offers
    # (docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengusingpreemptiblecapacity.htm, read
    # 2026-08-27), so nothing in the radio-room set may land here: platform/scheduling/capacity-affinity.yaml
    # keeps infrastructure-critical pods off the label, and prefers it for everything else. Preemptible
    # is set at pool create (module: preemptible_config), so this is a second pool, never a flag on a1.
    a1-spot = {
      description              = "preemptible A1 burst: stateless and runner pods prefer it; reclaimed with 30 s notice"
      shape                    = "VM.Standard.A1.Flex"
      ocpus                    = var.worker_ocpus
      memory                   = var.worker_memory_gb
      size                     = 0
      autoscale                = true
      ignore_initial_pool_size = true
      boot_volume_size         = 100
      placement_ads            = [1]
      preemptible_config       = { enable = true, is_preserve_boot_volume = false }
      node_labels              = { "estate.io/capacity" = "preemptible" }
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
    burst = {
      max_nodes     = local.burst_max_nodes
      hours_monthly = local.burst_hours_monthly
      node_usd_hr   = local.burst_node_usd_hr
      monthly_usd   = local.burst_monthly_usd
    }
    spot = {
      max_nodes     = local.spot_max_nodes
      hours_monthly = local.spot_hours_monthly
      node_usd_hr   = local.spot_node_usd_hr
      monthly_usd   = local.spot_monthly_usd
    }
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
