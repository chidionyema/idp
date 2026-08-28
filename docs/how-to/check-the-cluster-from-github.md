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

## Hourly, with nobody logged in (crew#345)

Demo: `gh workflow run verify-drill.yml -R chidionyema/idp && gh run watch -R chidionyema/idp`

A laptop's OCI browser session is a 60-minute JWT, refreshable to 24 h from the login and then
dead; a `--no-browser` token-exchange session cannot be refreshed at all (measured 2026-08-26,
crew#345). So no scheduled verification runs from a laptop. `verify-drill.yml` runs every hour
on the same `estate-ci` identity as above and `bin/idp-verify-drill` prints three rows: the
session subject is `estate-ci` and a token exchange (a person's OCID or a browser login is a
red row), the cluster and node pools are ACTIVE, and the cluster's own receipt `state/cluster`
grades green through `bin/idp-cluster-state` (fresh, every node Ready). That receipt is written
from inside every 15 minutes by the CronJob `cluster-state` (`platform/state/`, idp#267) on the
worker node's instance principal. The proof of the ticket is 24 consecutive green scheduled
runs, counted by crew's estate snapshot.

## Break-glass: a hand into the cluster from the same machine identity (crew#539)

When the cluster cannot heal itself (2026-08-28: coredns dead behind the Cilium chain, so Flux
could not fetch the merged revert idp#514) no session has a kube path: runners are outside
`control_plane_allowed_cidrs` and the laptop session token is retired (crew#345). The door is:

    gh workflow run oke-check.yml -f mode=break-glass -f playbook=diagnose

`bin/idp-oke-rebuild --break-glass` appends the runner's egress `/32` to the applied list, applies it
through tofu (one NSG rule), mints a kubeconfig on the same one-hour session token, runs ONE named
playbook from `bin/idp-oke-break-glass` (`diagnose` is read-only; `cilium-unchain` executes
idp#514 by hand), and applies the original list again from an `EXIT` trap, so a failed playbook
never leaves the door open. The job log is the receipt: `admit-apply`, the playbook's step lines,
`revoke-apply`. Nothing is typed ad hoc: a new playbook is a reviewed function in the script and a
name in the workflow's `playbook` choice.
