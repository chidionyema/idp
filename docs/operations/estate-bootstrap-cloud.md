# Estate bootstrap from a button click

**Last verified:** 2026-09-08, against the `github-actions-estate` IdentityPropagationTrust
that `bin/idp-oci-bootstrap` already creates in the OCI tenancy, and the
`vault-reads.yml` pattern that runs `bin/idp-*` from a cloud runner via OIDC.

## The honest split

The orchestrator `bin/idp-bootstrap-estate` runs five steps:

| Step | Trust boundary | Cloud-executable? |
|---|---|---|
| `bin/idp-estate-seed` | OCI vault + IAM | Yes (OIDC, already wired) |
| `bin/idp-bootstrap-tailscale` | Tailscale API console | No (operator SSO) |
| `bin/idp-bootstrap-cloudflare` | Cloudflare API console | No (operator SSO) |
| `bin/idp-bootstrap-vendors` | Each vendor console | No (operator SSO) |
| `bin/idp-github-app` install + refresh | GitHub App permissions | No (operator identity) |

The OCI half is the one pre-trust covers, because `vault-reads.yml` already
exchanges the GitHub Actions OIDC token for an OCI session token via
`gtrevorrow/oci-token-exchange-action@v2`. The IAM grant the federated
principal needs for vault-write is a one-time founder action documented
under "One-time setup" below.

The vendor halves each cross a different trust boundary (the vendor's own
console). Cloud-execution cannot complete them without a long-lived service
principal in each vendor, which is a separate founder decision. So they stay
on the laptop runbook under `bin/estate-preflight.d/`.

This is not a stitched-together solution. It is the truthful split between
"trust boundary cloud-execution already crosses" and "trust boundary it does
not".

## What already exists (no new platform layer)

| Layer | Already in estate | Source |
|---|---|---|
| OIDC trust between GitHub and OCI | `github-actions-estate` IdentityPropagationTrust | `bin/idp-oci-bootstrap` |
| Cloud runner that authenticates to OCI | `gtrevorrow/oci-token-exchange-action@v2` | `.github/workflows/vault-reads.yml` |
| Orchestrator + post-condition | `bin/idp-bootstrap-estate` ending with `bin/idp-root-trust --check` | `bin/idp-bootstrap-estate`, `bin/idp-root-trust` |
| Typed register of every credential | `docs/reference/policy/root-trust.md` | R45-root-trust, crew#66 |
| File-only CI gate | `.github/workflows/estate-bootstrap-preflight.yml` (PR gate, no OCI) | this repo |
| Operator's runbook fallback | `backstage/templates/estate-bootstrap-preflight/` (runbook PR on the laptop) | this repo |
| Vault merge-safe writer | `bin/idp-vault-put --merge` (R52) | this repo |

## What this commit adds

- `.github/workflows/estate-bootstrap.yml` -- `workflow_dispatch` + `workflow_call`.
  Two jobs: a preflight that runs `bin/idp-bootstrap-estate --preflight` cloud-side
  (no laptop, no OCI write), and a live job that runs `bin/idp-estate-seed` (the
  OCI half, which is what cloud-execution can complete). The live job's `if`
  gate refuses vendor scopes on purpose -- those need the laptop runbook until a
  vendor service principal is approved.
- This document.

## Operator's hands, end-to-end

1. **First time only** -- one IAM grant, documented below. After that, every
   subsequent run is one button click + zero laptop.
2. **On a fresh bring-up or rotation** -- the operator opens the Backstage tile
   (or runs `gh workflow run estate-bootstrap.yml -f scope=estate-seed -f reason=... -f mode=live`),
   watches the run, reads the verdict line. No terminal, no script, no paste.
3. **For vendor halves** (tailscale / cloudflare / vendors / github-app) -- the
   operator opens the same tile, picks the vendor scope, sees the workflow
   refuse the live job and point at the laptop runbook under
   `bin/estate-preflight.d/`. The runbook carries the exact sequence, including
   the OIDC trust assumption and the merge-safe writer.

## One-time setup (founder action)

The federated principal `github-actions-estate` already has vault-read (the
`vault-reads.yml` workflow proves it). To let the bootstrap live job write,
the founder runs once:

```bash
oci iam policy create --compartment-id "$ROOT_COMPARTMENT_OCID" \
  --name "github-actions-estate-vault-writer" \
  --statements '[
    "Allow dynamic-group github-actions-estate to manage secret-family in compartment id <ESTATE_COMPARTMENT_OCID>",
    "Allow dynamic-group github-actions-estate to manage secret-bundles in compartment id <ESTATE_COMPARTMENT_OCID>"
  ]'
```

After this IAM grant exists, the live job's `bin/idp-estate-seed` succeeds.
A P1 already on the board for the missing grant is the only reason this is
not granted on day one -- the preflight path catches the refusal cleanly,
and the live-vendor-refused job catches the wrong-scope case.

## Why the preflight is file-only enough for CI, but the live run needs the cloud

CI runs `bin/idp-root-trust --check` (the file-only gate, no OCI, no network --
two kinds of file and nothing else). That is enough to catch "a vault key with
no bootstrapper" before it lands on main.

The live run needs the OCI tenancy, the vault, and the IAM grant documented
above. The first two are on the cloud runner via OIDC; the third is the
founder's one-time setup.

## Patterns considered, why they did not land

- **OAuth2 auth-code paste-back.** Operator follows the consent URL, gets an
  auth code, pastes it into a follow-up `workflow_dispatch`. Does not work: the
  auth code lives in the operator's browser URL bar and is tied to a redirect
  URI the runner does not own. There is no callback URL GitHub Actions can
  accept that would also be a valid OAuth2 redirect.
- **Playwright on the runner opens the consent.** Requires the operator's SSO
  cookie to cross onto the runner's headless browser, which is brittle across
  IdPs and re-introduces "the operator's session on a server" the design is
  trying to avoid.
- **Device-code flow.** OCI IAM does not currently expose the device-code
  endpoint through the IdentityPropagationTrust used by `vault-reads.yml`.
  Worth re-evaluating if/when that endpoint is enabled in the estate's IAM
  domain.

## Where the operator's runbook lives today

The Backstage tile `estate-bootstrap-preflight` opens a PR with a runbook
script under `bin/estate-preflight.d/`. The operator runs the script on
their laptop. That is the path that works today, end-to-end, with zero
new platform work. The cloud workflow above is what replaces the OCI half
of that path with a button click.
