# crew#6227: vault-seed runs in GitHub Actions and writes backstage-env to the ESO vault so the
# ExternalSecret in backstage can sync it. The GitHub OIDC token is exchanged for an OCI session
# token; the session token's principal is identified by the GitHub OIDC token's claims.
# This dynamic group matches all principals authenticated via GitHub Actions OIDC in the tenancy.
resource "oci_identity_dynamic_group" "github_actions" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  name           = "estate-github-actions"
  description   = "all GitHub Actions OIDC principals in this tenancy (crew#6227)"
  # Matches any OCI session token minted from a GitHub Actions OIDC token.
  # GitHub's OIDC issuer: https://token.actions.githubusercontent.com
  # The sub claim identifies the specific repo/workflow/run.
  matching_rule = "ALL {request.auth.claims.iss='https://token.actions.githubusercontent.com'}"
}

# Grant the GitHub Actions dynamic group SECRET_CREATE on the ESO vault compartment so vault-seed
# can write backstage-env to the ESO vault. The vault is in compartment estate (compartment B).
# Note: secret management in the estate compartment is already granted to estate-operators, but
# GitHub Actions uses a different identity (dynamic group, not user group), so a separate grant
# is needed. The where clause prevents overwriting the verdict-hmac-key.
resource "oci_identity_policy" "github_actions_secret_create" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "estate-github-actions-secret-create"
  description    = "GitHub Actions may create secrets (not read) in the estate compartment (crew#6227)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.github_actions.name} to manage secret-family in compartment id ${var.compartment_ocid} where target.secret.name != 'verdict-hmac-key'",
  ]
}
