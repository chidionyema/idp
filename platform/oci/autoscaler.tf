# crew#539 CP4 (2026-08-27): the node pool grows and shrinks by itself. The Kubernetes Cluster
# Autoscaler for OKE (platform/oci/autoscaler) runs in the cluster as the worker nodes' instance
# principal; this file is the identity it needs and the moved block that hands the pool's size to
# it. The cluster is BASIC (no add-ons, no workload identity: crew#289), so the standalone
# Deployment is the only shape Oracle offers, and the node dynamic group (vault.tf) is its
# identity, exactly as for the vault reads.
#
# The six statements are Oracle's list, read 2026-08-27 from
# docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengusingclusterautoscaler_topic-Working_with_the_Cluster_Autoscaler.htm
# ("Step 1: Setting up an Instance Principal ..."). Scoped to this compartment, never the tenancy.
resource "oci_identity_policy" "workers_autoscale" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-autoscale"
  description    = "the in-cluster autoscaler (worker instance principal) may resize this cluster's node pools (crew#539 CP4)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to manage cluster-node-pools in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to manage instance-family in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to use subnets in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to read virtual-network-family in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to use vnics in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to inspect compartments in compartment id ${var.compartment_ocid}",
  ]
}

# The module keeps an autoscaled pool (`ignore_initial_pool_size = true`) under a different
# resource address and ignores `size` there, so a scale-out is never read back as drift and a
# scheduled apply never shrinks the pool under running pods. The address change would otherwise
# be a destroy-and-create of the live pool (and bin/idp-recreate-guard would refuse it).
moved {
  from = module.oke.module.workers[0].oci_containerengine_node_pool.tfscaled_workers["a1"]
  to   = module.oke.module.workers[0].oci_containerengine_node_pool.autoscaled_workers["a1"]
}

# bin/idp-autoscaler-seed reads the pool id from the OCI API by name; this output is the same fact
# from state, for a person reading `tofu output`.
output "worker_pool_ids" {
  value = module.oke.worker_pool_ids
}

# Paid burst stays under the same cap as the base pool (policy/node_pool.rego, crew#289). The second
# node is all paid (the free allowance is spent on the first), so its cost is hours x node price;
# the hours are the founder's number in estate-defaults node_pool.burst_hours_monthly, and the
# precondition refuses a combination that could exceed the cap.
locals {
  burst_max_nodes     = local.estate_defaults.node_pool.max_nodes
  burst_hours_monthly = local.estate_defaults.node_pool.burst_hours_monthly
  burst_node_usd_hr   = var.worker_ocpus * var.a1_ocpu_usd_per_hour + var.worker_memory_gb * var.a1_memory_gb_usd_per_hour
  burst_monthly_usd   = (local.burst_max_nodes - 1) * local.burst_node_usd_hr * local.burst_hours_monthly
}

# crew#539 CP10: the preemptible pool (main.tf a1-spot) is all paid at the discounted rate; its hours
# are the founder's number (estate-defaults node_pool.spot_hours_monthly) and base + burst + spot
# stays under the one cap. policy/node_pool.rego computes the same sum from local.capacity.
locals {
  spot_max_nodes     = local.estate_defaults.node_pool.spot_max_nodes
  spot_hours_monthly = local.estate_defaults.node_pool.spot_hours_monthly
  spot_node_usd_hr   = local.burst_node_usd_hr * (1 - var.a1_preemptible_discount)
  spot_monthly_usd   = local.spot_max_nodes * local.spot_node_usd_hr * local.spot_hours_monthly
}

resource "terraform_data" "burst_cap" {
  input = local.burst_monthly_usd + local.spot_monthly_usd
  lifecycle {
    precondition {
      condition     = local.capacity_monthly_usd + local.burst_monthly_usd + local.spot_monthly_usd <= local.monthly_cap_usd
      error_message = "Base pool USD ${local.capacity_monthly_usd} plus ${local.burst_max_nodes - 1} burst node(s) for ${local.burst_hours_monthly} h at USD ${local.burst_node_usd_hr}/h plus ${local.spot_max_nodes} preemptible node(s) for ${local.spot_hours_monthly} h at USD ${local.spot_node_usd_hr}/h is over estate-defaults node_pool.budget_monthly_usd ${local.monthly_cap_usd}. A paid billing authorisation is FOUNDER ACTION, not STAGED."
    }
  }
}
