# Langfuse's first org, project, API keys and founder login (crew#286 CP6). Generated here so no
# person ever signs up or types a password; platform/observability/langfuse.yaml reads these names.
resource "random_uuid" "langfuse_public_key" {}
resource "random_uuid" "langfuse_secret_key" {}
resource "random_password" "langfuse_user" {
  length  = 32
  special = false
}
# ClickHouse admin, shared by SigNoz and Langfuse (platform/observability). Replaces the SigNoz
# chart's default password.
resource "random_password" "clickhouse_admin" {
  length  = 32
  special = false
}

locals {
  langfuse_secrets = {
    "langfuse-init-public-key"    = "pk-lf-${random_uuid.langfuse_public_key.result}"
    "langfuse-init-secret-key"    = "sk-lf-${random_uuid.langfuse_secret_key.result}"
    "langfuse-init-user-email"    = var.founder_email
    "langfuse-init-user-password" = random_password.langfuse_user.result
    "clickhouse-admin-password"   = random_password.clickhouse_admin.result
  }
}

resource "oci_vault_secret" "langfuse" {
  for_each       = local.langfuse_secrets
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = each.key
  secret_content {
    content_type = "BASE64"
    content      = base64encode(each.value)
  }
}
