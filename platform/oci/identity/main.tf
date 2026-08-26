# One confidential OIDC client. oauth2-proxy (platform/identity) is the relying party; it learns
# nothing about the domain but the URLs in estate-config and the secrets ESO mounts.
resource "oci_identity_domains_app" "front_door" {
  idcs_endpoint = var.idcs_endpoint
  schemas       = ["urn:ietf:params:scim:schemas:oracle:idcs:App"]
  display_name  = "estate-front-door"
  description   = "oauth2-proxy at auth.${var.zone}; managed by platform/oci/identity, never by hand"
  based_on_template {
    value = "CustomWebAppTemplateId"
  }
  active          = true
  is_oauth_client = true
  client_type     = "confidential"
  allowed_grants  = ["authorization_code"]
  redirect_uris   = ["https://auth.${var.zone}/oauth2/callback"]
  post_logout_redirect_uris = ["https://catalogue.${var.zone}/"]
  show_in_my_apps = false
  attribute_sets  = ["all"]
}

# The allow-list is the domain's grant table: a user the domain has not granted this app is
# refused at the identity provider, before oauth2-proxy ever sees a token.
data "oci_identity_domains_users" "founder" {
  for_each      = toset(var.founder_emails)
  idcs_endpoint = var.idcs_endpoint
  user_filter   = "emails.value eq \"${each.value}\""
}

resource "oci_identity_domains_grant" "founder" {
  for_each        = data.oci_identity_domains_users.founder
  idcs_endpoint   = var.idcs_endpoint
  schemas         = ["urn:ietf:params:scim:schemas:oracle:idcs:Grant"]
  grant_mechanism = "ADMINISTRATOR_TO_USER"
  grantee {
    type  = "User"
    value = one(each.value.users).id
  }
  app {
    value = oci_identity_domains_app.front_door.id
  }
}

# The same two vault secrets platform/identity/external-secret.yaml already reads (ESO mounts
# them; the pod is blind to the vault). Existing placeholders are imported (import.tf).
resource "oci_vault_secret" "client_id" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "oauth2-proxy-client-id"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(oci_identity_domains_app.front_door.name)
  }
}
resource "oci_vault_secret" "client_secret" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "oauth2-proxy-client-secret"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(oci_identity_domains_app.front_door.client_secret)
  }
}

output "client_id" {
  value = oci_identity_domains_app.front_door.name
}
