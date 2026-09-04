# Flux webhook Receiver token. GitHub sends this as an HMAC-SHA256 signature in the
# X-Hub-Signature-256 header; the notification-controller verifies it. Generated once,
# stored in Vault, never rotated without re-registering the webhook on GitHub.
resource "random_password" "flux_webhook" {
  length  = 48
  special = false # GitHub sends it raw in the signature header; no special chars needed
}

resource "oci_vault_secret" "flux_webhook_token" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "flux-webhook-token"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.flux_webhook.result)
  }
}
