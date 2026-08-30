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
# crew#684 CP5: the project's read-only API key. Healthchecks sets it at enrol (enrol.py), the portal
# sends it as X-Api-Key from a mounted file (app-config.container.yaml proxy /healthchecks). One value,
# two ExternalSecrets, no person ever sees it.
resource "random_uuid" "healthchecks_ro_key" {}
# Incident crew#684, 2026-08-30 07:31Z (oke-check 33299061377, playbook healthchecks-door): both pods held
# the same 36-character UUID, enrol had saved it, and Healthchecks still answered `missing api key`.
# The vendor refuses any key whose length is not 32 before it looks at the database
# (healthchecks/healthchecks v4.3, hc/api/decorators.py:79 `if len(api_key) != 32`). The dashes go.

locals {
  healthchecks_secrets = {
    "healthchecks-secret-key"  = random_password.healthchecks_secret_key.result
    "healthchecks-db-password" = random_password.healthchecks_db.result
    "healthchecks-ping-key"    = random_uuid.healthchecks_ping_key.result
    "healthchecks-ro-key"      = replace(random_uuid.healthchecks_ro_key.result, "-", "")
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
