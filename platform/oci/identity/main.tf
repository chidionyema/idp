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
  # The estate's own front door asking its own users to consent to itself is a click, not a control:
  # without this every first sign-in (founder and drill) stops at /ui/v1/myconsole/consent.
  bypass_consent            = true
  redirect_uris             = ["https://auth.${var.zone}/oauth2/callback"]
  post_logout_redirect_uris = ["https://catalogue.${var.zone}/"]
  show_in_my_apps           = false
  attribute_sets            = ["all"]
  lifecycle {
    # OCI appends its OCITags extension to schemas after create; without this every plan drifts.
    ignore_changes = [schemas]
  }
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

# ── The login drill (crew#292 CP1) ────────────────────────────────────────────────────────────
# A drill needs an account it may sign in as, and the estate holds no human password (ADR 0007).
# So the drill gets its own domain user, granted the same front-door app, with a password only
# Terraform and the vault ever see. bin/idp-login-drill reads it back by name; nothing prints it.
resource "random_password" "drill" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

# The domain flags every admin-set password mustChange=true (read-only on the user, no policy switch).
# So the user is created with an initial password and bin/idp-identity-apply changes it once, by known
# value, to drill_live -- the one the vault holds and the drill signs in with.
resource "random_password" "drill_live" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_upper        = 2
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
}

resource "oci_identity_domains_user" "drill" {
  idcs_endpoint = var.idcs_endpoint
  schemas       = ["urn:ietf:params:scim:schemas:core:2.0:User"]
  user_name     = "estate-drill"
  description   = "front-door login drill; owned by platform/oci/identity, signed in only by bin/idp-login-drill"
  active        = true
  password      = random_password.drill.result
  name {
    family_name = "Drill"
    given_name  = "Estate"
  }
  emails {
    value   = "estate-drill@${var.zone}"
    type    = "work"
    primary = true
  }
  emails {
    value   = "estate-drill@${var.zone}"
    type    = "recovery"
    primary = false
  }
  # Not a service user: the drill signs in through the same browser flow a person does, which is
  # the only reason the drill proves anything about the front door.
  urnietfparamsscimschemasoracleidcsextensionuser_user {
    service_user        = false
    creation_mechanism  = "api"
    bypass_notification = true
  }
  # schemas: the domain appends its own extensions after create. password: only the create needs it;
  # a later update would re-send the initial password over the live one set by bin/idp-identity-apply
  # (measured 2026-08-26 02:59Z: the vault password stopped working after an unrelated update).
  # The user extension: bypass_notification and creation_mechanism are write-only in the API.
  lifecycle {
    ignore_changes = [schemas, password, urnietfparamsscimschemasoracleidcsextensionuser_user]
  }
}

resource "oci_identity_domains_grant" "drill" {
  idcs_endpoint   = var.idcs_endpoint
  schemas         = ["urn:ietf:params:scim:schemas:oracle:idcs:Grant"]
  grant_mechanism = "ADMINISTRATOR_TO_USER"
  grantee {
    type  = "User"
    value = oci_identity_domains_user.drill.id
  }
  app {
    value = oci_identity_domains_app.front_door.id
  }
}

# Same vault and key the client secrets live in; the drill script fetches this by name.
resource "oci_vault_secret" "drill_password" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "front-door-drill-password"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.drill_live.result)
  }
}

output "drill_user_name" {
  value = oci_identity_domains_user.drill.user_name
}

output "drill_user_id" {
  value = oci_identity_domains_user.drill.id
}

output "drill_initial_password" {
  value     = random_password.drill.result
  sensitive = true
}

output "drill_live_password" {
  value     = random_password.drill_live.result
  sensitive = true
}

# ── The router console (crew#408) ─────────────────────────────────────────────────────────────
# LiteLLM's Admin UI at llm.<zone>/ui signs in through this domain, the same login as the catalogue.
# No console password exists (ADR 0007): a session once sent one over Telegram (crew#407), and the
# founder's answer was "I don't want to have to maintain passwords". LiteLLM reads the client as
# GENERIC_CLIENT_ID/GENERIC_CLIENT_SECRET (platform/llm/external-secret.yaml, litellm-sso).
resource "oci_identity_domains_app" "router_console" {
  idcs_endpoint = var.idcs_endpoint
  schemas       = ["urn:ietf:params:scim:schemas:oracle:idcs:App"]
  display_name  = "estate-router-console"
  description   = "LiteLLM Admin UI at llm.${var.zone}/ui; managed by platform/oci/identity, never by hand"
  based_on_template {
    value = "CustomWebAppTemplateId"
  }
  active                    = true
  is_oauth_client           = true
  client_type               = "confidential"
  allowed_grants            = ["authorization_code"]
  bypass_consent            = true
  redirect_uris             = ["https://llm.${var.zone}/sso/callback"]
  post_logout_redirect_uris = ["https://llm.${var.zone}/ui"]
  show_in_my_apps           = false
  attribute_sets            = ["all"]
  lifecycle {
    ignore_changes = [schemas]
  }
}

resource "oci_identity_domains_grant" "router_console_founder" {
  for_each        = data.oci_identity_domains_users.founder
  idcs_endpoint   = var.idcs_endpoint
  schemas         = ["urn:ietf:params:scim:schemas:oracle:idcs:Grant"]
  grant_mechanism = "ADMINISTRATOR_TO_USER"
  grantee {
    type  = "User"
    value = one(each.value.users).id
  }
  app {
    value = oci_identity_domains_app.router_console.id
  }
}

resource "oci_vault_secret" "router_console_client_id" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "litellm-sso-client-id"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(oci_identity_domains_app.router_console.name)
  }
}
resource "oci_vault_secret" "router_console_client_secret" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "litellm-sso-client-secret"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(oci_identity_domains_app.router_console.client_secret)
  }
}
# LiteLLM grants the proxy-admin role to the user whose id (the email claim) equals PROXY_ADMIN_ID.
resource "oci_vault_secret" "router_console_admin_id" {
  compartment_id = var.compartment_ocid
  vault_id       = var.vault_ocid
  key_id         = var.key_ocid
  secret_name    = "litellm-sso-admin-id"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(var.founder_emails[0])
  }
}

output "router_console_client_id" {
  value = oci_identity_domains_app.router_console.name
}
