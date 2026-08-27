# Healthchecks (platform/healthchecks, crew#177): the Django secret key, the database password and
# the project ping key, generated here so no person ever types or sees one. The row reads the three
# names through ExternalSecrets; bin/idp-hc-enroll writes the ping key to the Mac from the same entry.
resource "random_password" "healthchecks_secret_key" {
  length  = 50
  special = false
}
resource "random_password" "healthchecks_db" {
  length  = 32
  special = false
}
resource "random_uuid" "healthchecks_ping_key" {}

locals {
  healthchecks_secrets = {
    "healthchecks-secret-key"  = random_password.healthchecks_secret_key.result
    "healthchecks-db-password" = random_password.healthchecks_db.result
    "healthchecks-ping-key"    = random_uuid.healthchecks_ping_key.result
  }
}

resource "oci_vault_secret" "healthchecks" {
  for_each       = local.healthchecks_secrets
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = each.key
  secret_content {
    content_type = "BASE64"
    content      = base64encode(each.value)
  }
}
