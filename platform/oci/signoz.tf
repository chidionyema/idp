# SigNoz root user (crew#495 CP8). SigNoz >= v0.112 provisions one admin at startup from
# SIGNOZ_USER_ROOT_* (platform/observability/signoz.yaml reads these from the vault through the
# signoz-root ExternalSecret). Same shape as langfuse.tf: the password is generated here, lives
# only in the vault, and is never typed or shown. The Terraform provider's access token is a
# service-account key minted once under this user and seeded as the signoz-access-token entry.
resource "random_password" "signoz_root" {
  length  = 32
  special = false
}

locals {
  signoz_secrets = {
    "signoz-root-email"    = var.founder_email
    "signoz-root-password" = random_password.signoz_root.result
  }
}

resource "oci_vault_secret" "signoz" {
  for_each       = local.signoz_secrets
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = each.key
  secret_content {
    content_type = "BASE64"
    content      = base64encode(each.value)
  }
}
