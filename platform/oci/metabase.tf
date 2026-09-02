# Metabase's application-database password (crew#R74 CP1). Generated here so no person ever
# types it; platform/observability/metabase-external-secret.yaml reads it from the vault for
# both the app (MB_DB_PASS) and its Postgres (POSTGRES_PASSWORD_FILE).
resource "random_password" "metabase_db" {
  length  = 32
  special = false
}

resource "oci_vault_secret" "metabase_db_password" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "metabase-db-password"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.metabase_db.result)
  }
}

# Decision 0016: the first-admin password no person ever sees or types. The setup Job
# (platform/observability/metabase-setup.yaml) posts it to /api/setup once; the interactive
# door is Google Sign-In. Declarative on purpose: the audit graded imperative vault writes
# a defect class (docs/reference/security-audit-2026-09-02.md).
resource "random_password" "metabase_admin" {
  length  = 48
  special = false
}

resource "oci_vault_secret" "metabase_admin_password" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "metabase-admin-password"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.metabase_admin.result)
  }
}
