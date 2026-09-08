# crew#713 / 2026-09-08: the estate holds 15 application databases on one CloudNativePG cluster
# plus a standalone temporal Postgres. For four days their only copy was the block volume the pod
# runs on (crew#713: no backup running); pg_dumpall to a laptop is a rescue, not a policy, and
# "infra is never Mac-bound" (founder 2026-08-25). So the offsite DB copy is made by the cluster
# from the worker node's own identity into one bucket, no key anywhere, exactly the shop-backups
# road (and receipts.tf with NoPublicAccess + versioning). The dumps are big (the estate cluster's
# pg_dumpall gzips to ~40 MB), so retention defaults lower than the shop's 90 days.
#
# Same shape as receipts.tf / shop-backups.tf: one bucket, one object-scoped statement for the
# dynamic group the worker nodes are already in. The nodes may write and read objects in this
# bucket and nothing else.
variable "db_backup_retention_days" {
  type    = number
  default = 14
  # crew#713 CP2: how long a nightly logical dump of the estate databases is kept offsite. Dumps are
  # ~40 MB gz; 14 nights is 560 MB against the 20 GB always-free allowance. A number, not a
  # constant, so retention is answerable with a value (founder 2026-08-31, "configurable obvs").
}

# The bucket already exists (created out-of-band 2026-09-08 to get the first DB dumps off the
# laptop before this file applied), so terraform adopts it rather than re-creating it (a 409
# BucketAlreadyExists otherwise, the exact failure receipts.tf records). Import id is
# <namespace>/<bucket>.
import {
  to = oci_objectstorage_bucket.db_backups
  id = "${data.oci_objectstorage_namespace.estate.namespace}/${var.cluster_name}-db-backups"
}

resource "oci_objectstorage_bucket" "db_backups" {
  # crew#310: the bucket grant lives in the compartment policy CI applies; create that first.
  depends_on     = [oci_identity_policy.operators_compartment]
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.estate.namespace
  name           = "${var.cluster_name}-db-backups"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  # Every dump is written under its own timestamped name; versioning is on so an overwrite (e.g.
  # a rerun writing the same object name) is still recoverable, which a diligence engineer asks
  # before they ask anything else.
  versioning = "Enabled"
}

# Because the dump names carry their own date, history comes from the names and the lifecycle
# cleans up rather than relying on a scheduler. Keep db/* for db_backup_retention_days; any
# overwrite is additionally guarded by versioning for a week.
resource "oci_objectstorage_object_lifecycle_policy" "db_backups" {
  bucket    = oci_objectstorage_bucket.db_backups.name
  namespace = data.oci_objectstorage_namespace.estate.namespace

  rules {
    name        = "expire-db-dumps"
    action      = "DELETE"
    is_enabled  = true
    time_amount = var.db_backup_retention_days
    time_unit   = "DAYS"
    target      = "objects"
    object_name_filter {
      inclusion_prefixes = ["db/"]
    }
  }

  rules {
    name        = "expire-superseded-versions"
    action      = "DELETE"
    is_enabled  = true
    time_amount = 7
    time_unit   = "DAYS"
    target      = "previous-object-versions"
  }
}

resource "oci_identity_policy" "workers_write_db_backups" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-write-db-backups"
  description    = "worker nodes may write and read the estate database logical backups in one bucket, nothing else (crew#713 CP2)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to manage objects in compartment id ${var.compartment_ocid} where target.bucket.name='${oci_objectstorage_bucket.db_backups.name}'",
  ]
}

output "db_backup_bucket" {
  value = oci_objectstorage_bucket.db_backups.name
}
