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

## Weekly, on a machine that has never seen the estate (crew#300)

Demo: `gh workflow run recover-drill.yml -R chidionyema/idp && gh run watch -R chidionyema/idp`

Recovery was a plan until 2026-08-27; now it is a drill. `recover-drill.yml` runs every Sunday at
04:41 UTC on a clean ubuntu runner holding only the OCI session it exchanged its OIDC token for,
and `bin/idp-recover-drill` prints one row per thing a rebuild needs and one verdict:

| Row | What it measures |
|---|---|
| `github-app` | an App installation token minted for the lane `recovery` (`platform/github-app/lanes.json`: metadata read, contents read, nothing else) |
| `repo` ×3 | `chidionyema/idp`, `chidionyema/crew`, `chidionyema/claude-estate` clone on that token; the row names the tip commit |
| `bundles` | every `bundles/<repo>/latest.bundle` in the R2 escrow (`estate_bundle_push.sh` on the Mac writes them hourly) is read with the keys the vault holds in `prospector-engine-env`, passes `git bundle verify`, and every complete history is cloned; incremental bundles are counted as needing their remote, which is the escrow job's own written limitation |
| `boot` | `bin/idp-verify-drill` from the fresh idp clone grades the live cluster on the same session |

The vault is found by its display name (`estate-secrets`), never through tofu state: a fresh
machine has none. `bin/idp-github-app` takes the vault it found as `ESTATE_VAULT_OCID` for the
same reason. The rows are the artifact `recover-receipt`; `drills/catalogue.yaml` row
`recover-clean-machine` turns a week without a green run into a red row of `bin/idp-verify`.

What a green run does not prove: the R2 escrow is a second vendor with static keys on the Mac
(risk register, crew#516), and an incremental bundle restores only next to its GitHub remote.
