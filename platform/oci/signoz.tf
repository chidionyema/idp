# SigNoz root user (crew#495 CP8). SigNoz >= v0.112 provisions one admin at startup from
# SIGNOZ_USER_ROOT_* (platform/observability/signoz.yaml reads these from the vault through the
# signoz-root ExternalSecret). Same shape as langfuse.tf: the password is generated here, lives
# only in the vault, and is never typed or shown. The Terraform provider's access token is a
# service-account key minted once under this user and seeded as the signoz-access-token entry.
# crew#495 CP8, 2026-08-27: signoz-0 crashed 37 times on `failed to validate config "user"`.
# SigNoz refuses a root password without an upper, a lower, a digit and a symbol
# (pkg/types/factor_password.go IsPasswordValid, pkg/modules/user/config.go Validate); the first
# cut copied langfuse.tf's `special = false` and never carried a symbol. Every class is pinned
# to at least one character so the rule cannot be lost to chance. The symbol set leaves out
# the characters a shell, a URL or a YAML scalar would read ($ & ` ' " \ / : # ; , ? = @ space).
resource "random_password" "signoz_root" {
  length           = 32
  special          = true
  override_special = "!%^*_-+"
  min_upper        = 1
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
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
