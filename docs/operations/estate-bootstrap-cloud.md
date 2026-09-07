# Estate bootstrap from a button click

**Last verified:** 2026-09-08, against the `github-actions-estate` IdentityPropagationTrust
that `bin/idp-oci-bootstrap` already creates in the OCI tenancy, and the
`vault-reads.yml` pattern that runs `bin/idp-*` from a cloud runner via OIDC.

## The shape, end to end

```
operator
  │ click "Run" in Backstage (or `gh workflow run estate-bootstrap.yml`)
  ▼
.github/workflows/estate-bootstrap.yml
  │ OIDC token → OCI session token (gtrevorrow/oci-token-exchange-action@v2, crew#584)
  │ bin/idp-bootstrap-estate --preflight        (read-only, no SSO consent)
  │ → verdict: 0 ok, 1 FAIL (root-trust row MISS/PARTIAL), 2 BLIND (vault unreachable)
  │
  │ (mode=live only, after a green preflight in this run)
  │ opens one SSO consent redirect that lands in the operator's browser
  │ founder's session cookie authorizes the consent -- one click
  │ orchestrator continues the live seed, minting only what is missing
  ▼
bin/idp-vault-put
  │ the only writer; values stay in process; audit row is a key NAME
  ▼
bin/idp-root-trust --check        (the gate every run ends with)
  │ 0 = every row in docs/reference/policy/root-trust.md is MEETS
  │ 1 = at least one PARTIAL or MISS; the line names which row and which bootstrapper is missing
  │ 2 = the register file is gone
  ▼
P1 if non-zero; PASS otherwise
```

The operator's hands: **one button click + one SSO consent**. No script, no terminal, no
`~/.estate/.env` edit, no key on a laptop. Backstage stays stateless (Option 2 picked
2026-09-08 for the agent-foundry secrets; the same ruling binds here -- Backstage never
holds the operator's session).

## What already exists (no new platform layer)

| Layer | Already in estate | Source |
|---|---|---|
| OIDC trust between GitHub and OCI | `github-actions-estate` IdentityPropagationTrust | `bin/idp-oci-bootstrap` |
| Cloud runner that authenticates to OCI | `gtrevorrow/oci-token-exchange-action@v2` | `.github/workflows/vault-reads.yml` |
| Orchestrator + post-condition | `bin/idp-bootstrap-estate` ending with `bin/idp-root-trust --check` | `bin/idp-bootstrap-estate`, `bin/idp-root-trust` |
| Typed register of every credential | `docs/reference/policy/root-trust.md` | R45-root-trust, crew#66 |
| File-only CI gate | `.github/workflows/estate-bootstrap-preflight.yml` (PR gate, no OCI) | this repo |
| Operator's runbook fallback | `backstage/templates/estate-bootstrap-preflight/` (runbook PR on the laptop) | this repo |

## What this commit adds

- `.github/workflows/estate-bootstrap.yml` -- `workflow_dispatch` + `workflow_call`. Two
  jobs: a preflight that runs `bin/idp-bootstrap-estate --preflight` cloud-side (no
  laptop), and a live job that opens one SSO consent redirect. The live job's
  post-consent callback is the next-scope piece; until that lands, the live job
  prints the consent URL and stops at the gate the operator's runbook path uses.
- This document.

## Why the preflight is file-only enough for CI, but the live run needs the cloud

CI runs `bin/idp-root-trust --check` (the file-only gate, no OCI, no network -- two
kinds of file and nothing else). That is enough to catch "a vault key with no
bootstrapper" before it lands on main.

The live run needs the OCI tenancy, the vault, and the operator's browser session.
The first two are on the cloud runner via OIDC; the third is the one hand-off this
design does not pretend to automate -- the consent URL lands in the operator's
browser, they click, the runner's callback receives the answer, the orchestrator
continues. Until that callback is wired the live job ends with the consent URL and
the operator's laptop runbook is the path that finishes the run.

## A button click -- what's actually required

Three more pieces, separate scope:

1. **The consent callback.** A small HTTP server on the runner that receives the OCI
   OAuth2 redirect after the operator consents. Playwright on the runner opens the
   login page, the operator follows a deep link in their own browser (or accepts the
   consent in the runner's Playwright session if they trust that path), the
   callback fires, the workflow resumes. This is the part that needs Playwright on
   the runner -- not a Backstage problem, a runner problem.

2. **Backstage scaffolder action** `idp:bootstrap:dispatch` that wraps
   `actions:github:dispatch`. Tile renders the same form as the runbook tile
   (reason, scope, operator), the action calls `gh api repos/.../actions/workflows/.../dispatches`,
   the tile streams the Actions run back to the operator. One click to dispatch,
   one click for SSO consent. New scaffolder backend module under
   `backstage/plugins/`, registered in `backstage/packages/backend/src/index.ts`.

3. **Audit row in the estate DB** (LAW 50) -- when the live run completes, post one
   `task_executions` row with `reason`, `scope`, `operator`, `gate_verdict`,
   `consent_granted_at`. Same shape as the agent-foundry audit row from the
   earlier commit. Already wired in `af/db.py` (post-merge of feat/metering-and-live-fetch).

## Where the operator's runbook lives today

The Backstage tile `estate-bootstrap-preflight` opens a PR with a runbook script
under `bin/estate-preflight.d/`. The operator runs the script on their laptop. That
is the path that works today, end-to-end, with zero new platform work. The cloud
workflow above is what replaces that path with a button click.
