# The collector's front door for programs off the cluster (crew#516 CP5 slice 3). The Mac's
# science tick (crew science/collect.py, crew#522) posts OTLP/HTTP to signoz.<zone>/v1/logs; the
# edge (platform/observability/httproute.yaml, route otlp-ingest) admits that path only with this
# credential, checked by Traefik's basicAuth Middleware against the htpasswd line below. One
# program credential, not a person: ADR 0007 still holds, nobody's password is here.
#
# Two vault entries from one password: otlp-ingest-password is what the sender reads (a vault
# read on the Mac, never typed), otlp-ingest-users is the `science:<bcrypt>` line the Middleware
# reads through ExternalSecret otlp-ingest-users. bcrypt() salts anew on every plan, so the users
# entry ignores content changes after the first write and is replaced whenever the password is;
# rotate with `tofu taint random_password.otlp_ingest`.
resource "random_password" "otlp_ingest" {
  length  = 40
  special = false # travels in an Authorization: Basic header and a k=v env pair; letters and digits only
}

resource "oci_vault_secret" "otlp_ingest_password" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "otlp-ingest-password"
  secret_content {
    content_type = "BASE64"
    content      = base64encode(random_password.otlp_ingest.result)
  }
}

resource "oci_vault_secret" "otlp_ingest_users" {
  compartment_id = var.compartment_ocid
  vault_id       = oci_kms_vault.estate.id
  key_id         = oci_kms_key.estate.id
  secret_name    = "otlp-ingest-users"
  secret_content {
    content_type = "BASE64"
    content      = base64encode("science:${bcrypt(random_password.otlp_ingest.result)}")
  }
  lifecycle {
    # bcrypt() salts anew on every plan: without this the entry would rewrite on every apply.
    ignore_changes = [secret_content]
    # ...and with only that, a tainted password would never reach the vault and every tick would
    # 401 against the old line (idp#436 review, d5ae1960). A new password replaces the entry.
    replace_triggered_by = [random_password.otlp_ingest]
  }
}
