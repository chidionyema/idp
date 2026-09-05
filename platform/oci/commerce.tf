# The money layer's own credentials (platform/commerce, crew#623). Generated here so that no
# person ever types or sees one, and so the layer has a birth path before it is switched on --
# a layer whose secrets have no origin is the half-stitched thing the headline bans.
#
# Two entries, both read by ExternalSecrets in platform/commerce/data/external-secret.yaml with
# `dataFrom.extract`, which parses the vault content as JSON and makes one Secret key per field.
# The third entry, `commerce-payment-provider`, is created here EMPTY and filled at the provider.
# Its keys are the payment provider's, not the estate's, and they are born from one root secret
# there (R52) -- so Terraform mints the slot and never the value. It has to exist before the
# layer is switched on all the same: the ExternalSecret that reads it is applied by a Flux row
# with `wait: true`, and a reference to a vault entry that is not there is a row that never goes
# Ready. `ignore_changes` is what keeps the two apart: the day a provider is chosen, its keys are
# written into this entry in the vault and Terraform leaves them alone for ever after.
#
# The key names are not a guess. They were read out of the lago 1.28.0 chart on 2026-08-29:
# every `secretKeyRef` in its templates against `global.existingSecret` asks for databaseUrl,
# redisUrl and redisCacheUrl, and every one against `encryption.existingSecret` asks for
# encryptionPrimaryKey, encryptionDeterministicKey and encryptionKeyDerivationSalt. None of the
# three URL references is marked optional, so a missing redisCacheUrl is a pod that never starts.
resource "random_password" "commerce_db" {
  length = 32
  # The password is embedded in a postgres:// URL; special characters would need escaping there
  # and the escaping is where these break.
  special = false
}
resource "random_password" "commerce_encryption_primary" {
  length  = 32
  special = false
}
resource "random_password" "commerce_encryption_deterministic" {
  length  = 32
  special = false
}
resource "random_password" "commerce_encryption_salt" {
  length  = 32
  special = false
}

locals {
  commerce_secrets = {
    # POSTGRES_PASSWORD is the same value again, and it is still here after the layer's own
    # database was deleted: platform/estate-db/cluster/secrets.yaml reads this very field to mint
    # the `lago` role on the estate cluster, so the role and the URL that dials it cannot drift.
    "commerce-lago-credentials" = jsonencode({
      POSTGRES_PASSWORD = random_password.commerce_db.result
      # The one Postgres, not a seventh (founder 2026-09-04: a new layer never brings its own
      # database). estate-rw is CloudNativePG's read-write endpoint for the `estate` cluster and
      # follows a failover; `lago` is a database on it, owned by a role no other consumer holds.
      databaseUrl   = "postgresql://lago:${random_password.commerce_db.result}@estate-rw.estate-db.svc.cluster.local:5432/lago"
      redisUrl      = "redis://commerce-redis.commerce.svc:6379/0"
      redisCacheUrl = "redis://commerce-redis.commerce.svc:6379/1"
    })
    # Lose these and the ledger is unreadable: Lago encrypts customer and payment-method data at
    # rest with them. Terraform state is the only copy, which is why it lives in the estate bucket.
    "commerce-lago-encryption" = jsonencode({
      encryptionPrimaryKey        = random_password.commerce_encryption_primary.result
      encryptionDeterministicKey  = random_password.commerce_encryption_deterministic.result
      encryptionKeyDerivationSalt = random_password.commerce_encryption_salt.result
    })
  }
}

# The empty slot. One field, and it is not a credential: it says which provider is configured,
# and `none` is the truthful answer today. `dataFrom.extract` needs at least one field to sync
# (an entry with no fields is an ExternalSecret that never goes Ready), and a fake secret_key
# would be worse than an empty slot -- it would look real to whoever read it next.
resource "oci_vault_secret" "commerce_payment_provider" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "commerce-payment-provider"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(jsonencode({ PROVIDER = "none" }))
  }
  lifecycle {
    # The provider's keys are written into this entry by hand at the provider's own console, once.
    # Terraform must never overwrite them with the empty object it created the slot with.
    ignore_changes = [secret_content]
  }
}

resource "oci_vault_secret" "commerce" {
  for_each       = local.commerce_secrets
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = each.key
  secret_content {
    content_type = "BASE64"
    content      = base64encode(each.value)
  }
}
