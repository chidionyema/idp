# The estate's OIDC clients are provisioned here, never in a console (crew#281, estate-defaults
# policy.oauth_creation). Cloudflare Access for SaaS issues the OIDC client; the client id and
# secret go straight into the estate vault, so no person ever sees or pastes them. Providers are
# named here because this is the identity-broker provisioner, the fourth place a vendor may be
# named (bin/cloud-agnostic-gate); the platform behind it speaks plain OIDC (oauth2-proxy).
terraform {
  required_version = ">= 1.6"
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 5.0" }
    oci        = { source = "oracle/oci", version = ">= 8.19.0" }
  }
}
provider "cloudflare" {} # CLOUDFLARE_API_TOKEN from the environment (LAW 46)
provider "oci" {}        # ~/.oci/config profile from the environment, as platform/oci
