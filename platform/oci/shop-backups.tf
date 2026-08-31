# crew#713 CP1: the shop's whole database is one SQLite file on one block volume, and until this
# bucket existed nothing copied it anywhere. Census taken inside the running pod on 2026-08-31:
# 23 tables, 202 packs, 76 price-history rows, 41,035 analytics events, 3 orders, 2 entitlements,
# 1 account, in 5,324,800 bytes. The offsite writers the estate already declared for it are Mac
# launchd jobs that are not loaded, and infra is never Mac-bound (founder 2026-08-25), so the copy
# is made by the cluster, from the worker node's own identity, with no key anywhere.
#
# Same shape as receipts.tf: one bucket, one object-scoped statement for the dynamic group the
# nodes are already in. The nodes may write and read objects in this bucket and nothing else; they
# cannot list the compartment's buckets (proved 2026-08-31: `os bucket list` from a pod on the
# node answers 404 NamespaceNotFound, which is how Object Storage says "not authorised to list").
resource "oci_objectstorage_bucket" "shop_backups" {
  # crew#310, learned on receipts.tf: the bucket grant lives in the compartment policy CI applies.
  depends_on     = [oci_identity_policy.operators_compartment]
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.estate.namespace
  name           = "${var.cluster_name}-shop-backups"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  # Every object is written under a distinct timestamped name, so history comes from the names.
  # Versioning is on anyway for the one object that IS overwritten, shop/latest.json, and because
  # a buyer's engineer asks whether an overwrite is recoverable before they ask anything else.
  versioning = "Enabled"
}

# The retention story, in the bucket rather than in a runbook nobody runs: a daily copy is kept for
# var.shop_backup_retention_days, and superseded versions of the receipt for a week. 5.3 MB a day
# against the 20 GB always-free allowance is 0.03% of it at 90 days.
resource "oci_objectstorage_object_lifecycle_policy" "shop_backups" {
  bucket    = oci_objectstorage_bucket.shop_backups.name
  namespace = data.oci_objectstorage_namespace.estate.namespace

  rules {
    name        = "expire-daily-copies"
    action      = "DELETE"
    is_enabled  = true
    time_amount = var.shop_backup_retention_days
    time_unit   = "DAYS"
    target      = "objects"
    object_name_filter {
      inclusion_prefixes = ["shop/store-"]
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

resource "oci_identity_policy" "workers_write_shop_backups" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-write-shop-backups"
  description    = "worker nodes may write and read the shop database backups in one bucket, nothing else (crew#713 CP1)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to manage objects in compartment id ${var.compartment_ocid} where target.bucket.name='${oci_objectstorage_bucket.shop_backups.name}'",
  ]
}

output "shop_backup_bucket" {
  value = oci_objectstorage_bucket.shop_backups.name
}
