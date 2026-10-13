# Layer 4 of the Quad (platform/quad/ledger): the vault entry `quad-ledger` and the bucket its
# anchor CronJob writes to. Both were named in cmd/quad-ledger/README.md and read by two
# ExternalSecrets (platform/quad/ledger/ledger.yaml, platform/estate-db/cluster/secrets.yaml), but
# nothing created either. Measured 2026-10-13: `oci os bucket get` answered BucketNotFound, the
# vault held no quad-ledger secret, and both ExternalSecrets sat in SecretSyncedError with every
# quad pod in ContainerCreating for 10 days.
resource "oci_objectstorage_bucket" "quad_anchors" {
  # crew#310, learned on receipts.tf: the bucket grant lives in the compartment policy CI applies.
  depends_on     = [oci_identity_policy.operators_compartment]
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.estate.namespace
  name           = "${var.cluster_name}-quad-anchors"
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  # Every anchor has a distinct timestamped name, but the PAR below may overwrite (AnyObjectWrite
  # does not forbid it), so versioning is what keeps an overwritten anchor recoverable.
  versioning = "Enabled"
}

# The anchor job's only credential: create objects in this one bucket, never read, list or delete
# them (main.go: "the PAR is the only credential"). full_path ends in /o/, and main.go appends the
# object name to it.
resource "oci_objectstorage_preauthrequest" "quad_anchor_write" {
  namespace             = data.oci_objectstorage_namespace.estate.namespace
  bucket                = oci_objectstorage_bucket.quad_anchors.name
  name                  = "quad-ledger-anchor-write"
  access_type           = "AnyObjectWrite"
  bucket_listing_action = "Deny"
  time_expires          = var.quad_anchor_par_expires
}

# quad_ledger's Postgres role password. No special characters: it is interpolated raw into
# DATABASE_URL (postgres://quad_ledger:<password>@...), where they would need escaping.
resource "random_password" "quad_ledger_db" {
  length  = 48
  special = false
}

# One JSON entry, the two properties the ExternalSecrets read by name. Bumping
# var.quad_anchor_par_expires replaces the PAR and rewrites this entry; ESO picks it up within 10m.
resource "oci_vault_secret" "quad_ledger" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "quad-ledger"
  secret_content {
    content_type = "BASE64"
    content = base64encode(jsonencode({
      "postgres-password" = random_password.quad_ledger_db.result
      "anchor-par-url"    = oci_objectstorage_preauthrequest.quad_anchor_write.full_path
    }))
  }
}
