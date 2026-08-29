# The money layer's own credentials (platform/commerce, crew#623). Generated here so that no
# person ever types or sees one, and so the layer has a birth path before it is switched on --
# a layer whose secrets have no origin is the half-stitched thing the headline bans.
#
# Two entries, both read by ExternalSecrets in platform/commerce/data/external-secret.yaml with
# `dataFrom.extract`, which parses the vault content as JSON and makes one Secret key per field.
# The third entry the layer reads, `commerce-payment-provider`, is NOT here: those are the
# payment provider's keys, not the estate's, and they are born from one root secret at the
# provider (R52). It stays a MISS row in docs/reference/policy/root-trust.md until crew#623 CP3.
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
    # POSTGRES_PASSWORD is the same value again: platform/commerce/data/postgres.yaml mounts this
    # Secret at /run/secrets/commerce and reads POSTGRES_PASSWORD_FILE from it, so the database
    # and the URL that dials it can never drift apart.
    "commerce-lago-credentials" = jsonencode({
      POSTGRES_PASSWORD = random_password.commerce_db.result
      databaseUrl       = "postgresql://lago:${random_password.commerce_db.result}@commerce-db.commerce.svc:5432/lago"
      redisUrl          = "redis://commerce-redis.commerce.svc:6379/0"
      redisCacheUrl     = "redis://commerce-redis.commerce.svc:6379/1"
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
