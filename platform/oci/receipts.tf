# crew#292 CP4: a drill that runs inside the cluster leaves its receipt where a runner can read
# it. Runners have no kube path (control_plane_allowed_cidrs), so the Chaos Mesh Workflow's last
# step writes one object to this bucket from the worker node's own identity (the same dynamic
# group vault.tf lets read secrets), and the chaos-drill job in oke-check.yml reads it back
# through its OIDC session. No token in a pod, no key on a runner. Object Storage is in the
# always-free tier (20 GB); the receipt is one line.
data "oci_objectstorage_namespace" "estate" {
  compartment_id = var.compartment_ocid
}

resource "oci_objectstorage_bucket" "drill_receipts" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.estate.namespace
  name           = "${var.cluster_name}-drill-receipts"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Disabled"
}

resource "oci_identity_policy" "workers_write_receipts" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-write-receipts"
  description    = "worker nodes may write drill receipts into one bucket, nothing else (crew#292 CP4)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to manage objects in compartment id ${var.compartment_ocid} where target.bucket.name='${oci_objectstorage_bucket.drill_receipts.name}'",
  ]
}

output "drill_receipt_bucket" {
  value = oci_objectstorage_bucket.drill_receipts.name
}
