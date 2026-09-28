# Superset's two machine-minted secrets (decision 0018). Generated here so no person ever
# types them; platform/observability/superset-external-secret.yaml reads them from the vault
# as mounted files: the Flask session signing key, and the app-database password shared by
# the app (SQLALCHEMY_DATABASE_URI) and its Postgres (POSTGRES_PASSWORD_FILE).
resource "random_password" "superset_db" {
  length  = 32
  special = false
}

resource "oci_vault_secret" "superset_db_password" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "superset-db-password"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.superset_db.result)
  }
}

resource "random_password" "superset_secret_key" {
  length  = 42
  special = false
}

resource "oci_vault_secret" "superset_secret_key" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "superset-secret-key"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.superset_secret_key.result)
  }
}
