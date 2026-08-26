# crew#292 CP4: a drill that runs inside the cluster leaves its receipt where a runner can read
# it. Runners have no kube path (control_plane_allowed_cidrs), so the Chaos Mesh Workflow's last
# step writes one object to this bucket from the worker node's own identity (the same dynamic
# group vault.tf lets read secrets), and the chaos-drill job in oke-check.yml reads it back
# through its OIDC session. No token in a pod, no key on a runner. Object Storage is in the
# always-free tier (20 GB); the receipt is one line.
data "oci_objectstorage_namespace" "estate" {
  compartment_id = var.compartment_ocid
}

# crew#292 / crew#301: the bucket already exists in the tenancy but was not in state after the
# 2026-08-26 state overwrite; the apply hit 409-BucketAlreadyExists (run 32965258786). Adopt it
# rather than re-create it. The block is a no-op once the bucket is in state.
import {
  to = oci_objectstorage_bucket.drill_receipts
  id = "n/${data.oci_objectstorage_namespace.estate.namespace}/b/${var.cluster_name}-drill-receipts"
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
