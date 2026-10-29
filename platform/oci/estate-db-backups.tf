# idp#7391: the estate database's daily dump (platform/estate-db/backup/cronjob.yaml) is written
# by the worker node's own identity, with no key anywhere. The bucket estate-db-backups already
# exists (measured 2026-09-15, clusters/oke/estate-config.yaml), so this file declares only the
# grant, not the bucket: creating it here would answer 409-BucketAlreadyExists.
#
# Same shape as shop-backups.tf: object-scoped to this one bucket; the nodes cannot list buckets.
resource "oci_identity_policy" "workers_write_estate_db_backups" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-write-estate-db-backups"
  description    = "worker nodes may write and read the estate database dumps in one bucket, nothing else (idp#7391)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to manage objects in compartment id ${var.compartment_ocid} where target.bucket.name='estate-db-backups'",
  ]
}
