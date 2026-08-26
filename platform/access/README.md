# platform/access — OIDC clients by Terraform, never by console

Founder ruling (crew#281): an OAuth client is created by a provider, in code, and its secret goes
to the vault without a person seeing it. GitHub cannot do this (no API creates an OAuth App), so
the broker is Cloudflare Access for SaaS: one-time PIN to an email the founder owns, OIDC to
oauth2-proxy. Swapping the broker later is this directory plus `oidc-issuer-url`; nothing else.

Run (the only credential is the estate Cloudflare token with Account → Zero Trust: Edit):
    CLOUDFLARE_API_TOKEN=… tofu -chdir=platform/access init && tofu -chdir=platform/access apply
Inputs come from `platform/oci` outputs and `clusters/oke/estate-config.yaml`; see `bin/idp-access-apply`.
