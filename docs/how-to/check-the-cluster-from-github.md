# Check the cluster from GitHub, with no key on any laptop

Demo: `gh workflow run oke-check.yml -R chidionyema/idp && gh run watch -R chidionyema/idp`

What it proves: a GitHub Actions job can run `bin/idp-oke-rebuild --check` against the estate
tenancy using only the job's own OIDC token. The token is exchanged at the identity domain for a
one-hour OCI session token that impersonates the service user `estate-ci` (trust
`github-actions-estate`). No OCI API key exists for this path (crew#227 CP2).

Runs on: a daily schedule, `workflow_dispatch`, and pull requests touching `platform/oci/**`,
`bin/idp-oci-login`, `bin/idp-oke-rebuild` or the workflow itself.

Inputs, all set once by `bin/idp-oci-bootstrap` output and `gh secret set` / `gh variable set`:

| Name | Kind | Why it exists |
|---|---|---|
| `OIDC_CLIENT_IDENTIFIER` | secret | `client_id:client_secret` of the confidential app the trust names |
| `OCI_TENANCY_OCID`, `OCI_S3_ACCESS_KEY`, `OCI_S3_SECRET_KEY` | secret | tenancy id; the state bucket's customer secret key (OpenTofu 1.12's S3 backend cannot take a session token) |
| `DOMAIN_BASE_URL`, `OCI_REGION`, `OCI_COMPARTMENT_OCID`, `OCI_OS_NAMESPACE` | variable | identifiers, not secrets |
| `OKE_SSH_PUBKEY`, `OKE_ALLOWED_CIDRS` | variable | the applied worker public key and control plane allowlist, so a runner's plan reports real drift only |

What a runner cannot see: it is outside `control_plane_allowed_cidrs`, so the `flux` row prints
`n/a` and the `nodes` row is measured through the OCI API instead of kubectl. The `site` and
`catalog` rows are measured from outside and stand in for Flux.

Residual static credentials on this path: the OIDC client secret and the S3 key pair, both GitHub
repository secrets. `bin/static-secret-gate` counts them (idp#102).
