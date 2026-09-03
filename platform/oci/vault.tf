# crew#227 CP3: secrets reach the cluster by identity, not by a key in the cluster.
# OCI Vault (software-protected key, no charge: `oci limits value list --service-name kms`
# shows virtual-vault-count 10 on 2026-08-25) holds the secrets; the worker nodes are an
# instance principal (dynamic group) allowed to read them; External Secrets Operator in the
# cluster (platform/secrets) turns them into Kubernetes Secrets. Nothing static lands in git
# or on a node. Workload identity per pod needs an Enhanced cluster (billed per hour), so the
# node identity is the boundary for now; the decision is recorded on crew#227.
resource "oci_kms_vault" "estate" {
  compartment_id = var.compartment_ocid
  display_name   = "${var.cluster_name}-secrets"
  vault_type     = "DEFAULT"
}

resource "oci_kms_key" "estate" {
  compartment_id      = var.compartment_ocid
  display_name        = "${var.cluster_name}-secrets"
  management_endpoint = oci_kms_vault.estate.management_endpoint
  protection_mode     = "SOFTWARE"
  key_shape {
    algorithm = "AES"
    length    = 32
  }
}

resource "oci_identity_dynamic_group" "workers" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  name           = "${var.cluster_name}-workers"
  description    = "every instance in compartment estate: the OKE worker nodes (crew#227 CP3)"
  matching_rule  = "ALL {instance.compartment.id = '${var.compartment_ocid}'}"
}

resource "oci_identity_policy" "workers_read_secrets" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-read-secrets"
  description    = "worker nodes may read secret bundles in this compartment, nothing else"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to read secret-family in compartment id ${var.compartment_ocid}",
  ]
}

output "vault_id" {
  value = oci_kms_vault.estate.id
}

output "vault_key_id" {
  value = oci_kms_key.estate.id
}
