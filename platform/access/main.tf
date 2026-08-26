data "cloudflare_zone" "estate" { filter = { name = var.zone } }
locals { account_id = data.cloudflare_zone.estate.account.id }

# One-time PIN: the founder proves an email he already owns. No password exists anywhere.
resource "cloudflare_zero_trust_organization" "estate" {
  account_id       = local.account_id
  name             = var.team_name
  auth_domain      = "${var.team_name}.cloudflareaccess.com"
  session_duration = var.session_duration
}
resource "cloudflare_zero_trust_access_identity_provider" "otp" {
  account_id = local.account_id
  name       = "one-time-pin"
  type       = "onetimepin"
  config     = {}
}
resource "cloudflare_zero_trust_access_policy" "founder" {
  account_id = local.account_id
  name       = "front-door-founder"
  decision   = "allow"
  include    = [for e in var.founder_emails : { email = { email = e } }]
}
# The front door's OIDC client. oauth2-proxy (platform/identity) is the relying party.
resource "cloudflare_zero_trust_access_application" "front_door" {
  account_id       = local.account_id
  name             = "front-door"
  type             = "saas"
  session_duration = var.session_duration
  policies         = [{ id = cloudflare_zero_trust_access_policy.founder.id, precedence = 1 }]
  saas_app = {
    auth_type     = "oidc"
    redirect_uris = ["https://auth.${var.zone}/oauth2/callback"]
    grant_types   = ["authorization_code"]
    scopes        = ["openid", "email", "profile"]
  }
}

# Into the estate vault under the names platform/identity/external-secret.yaml already reads.
resource "oci_vault_secret" "client_id" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "oauth2-proxy-client-id"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(cloudflare_zero_trust_access_application.front_door.saas_app.client_id)
  }
}
resource "oci_vault_secret" "client_secret" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "oauth2-proxy-client-secret"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(cloudflare_zero_trust_access_application.front_door.saas_app.client_secret)
  }
}
output "issuer_url" { value = "https://${cloudflare_zero_trust_organization.estate.auth_domain}" }
