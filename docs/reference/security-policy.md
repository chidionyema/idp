# Security policy

**Owner:** the founder (chidionyema). **Scope:** every repository under the estate
account, every image the estate publishes, every host it runs on, every secret it
holds. **Review:** each row is re-run by `bin/idp-ci` on every pull request and by
`bin/idp-verify` on the live estate; this page is re-read at every quarterly review
and whenever a row changes. **Standard we measure against:** ISO/IEC 27001:2022
Annex A controls, named per row, because that is the checklist a buyer's engineer
brings. `bin/security-policy-gate` refuses this page if any control row lacks a
proof command that exists.

A control is a claim. The proof column is the command whose output makes it true.
A row whose proof prints FAIL or BLIND is an open incident, not a policy.

## Controls

| Control | ISO 27001 | Proof command | State on 2026-08-25 | Gap |
|---|---|---|---|---|
| Secrets are encrypted at rest in git, one file per secret, never overwritten by accident | A.8.24 | `estate-secrets/scripts/secret-add` (refuses an existing file without `SECRET_REPLACE=1`) | ok, guard proved both ways 2026-08-25 | one age recipient; no rotation; no decrypt audit. KMS-backed key on OCI Vault at OKE time (crew#198) |
| No secret value is ever printed to a log, a chat or a commit | A.8.15 | `bin/idp-ci` (LAW 21 rows) | ok | none known |
| Only the gateway listens off loopback; every port is declared in the ledger | A.8.20 | `bin/port-gate --live` | ok, 19 declared, 0 findings | none |
| Identity is OIDC at the gateway; workloads carry SPIFFE identities | A.5.16 | `bin/idp-verify` (gateway + spire rows) | gateway ok; SPIRE pending live proof (idp#32) | SPIRE proof waits on cluster start |
| Admission policy is code and is proved both ways before merge | A.8.9 | `bin/policy-test` | PASS | none |
| Every image is built for amd64 and arm64 from one tag, no per-environment build | A.8.9 | `bin/multiarch-gate` | ok, 0 findings | none |
| Every published image carries an SBOM, a vulnerability report and a licence verdict | A.5.21 | `bin/supply-chain` | tool exists; not yet run in CI | run in CI, fail on critical, cosign sign (crew#197) |
| Every GitHub Action is pinned to a commit SHA | A.5.21 | `bin/actions-pinned` | FAIL, 0 of 7 pinned in this repo | pin + gate (crew#197) |
| Every repository's default branch refuses deletion and force-push | A.8.4 | `bin/repo-rulesets` | 47 of 48; 1 missing, 2 private BLOCKED by plan | fix the one; required checks per repo (crew#199) |
| The founder's account has MFA; each agent acts as its own identity | A.5.17 | `gh api /user -q .two_factor_authentication` | BLIND, field needs `read:user` scope | machine identity per agent (crew#199) |
| Data has a versioned, encrypted, off-host backup with a monthly restore drill | A.8.13 | `restic snapshots` | not configured; Fly teardown backups sit unencrypted in `~/backups` | restic to OCI object storage (crew#78) |
| Every AI system is registered with an Annex IV technical file, a risk register entry and declared data sources (Arts. 9, 10, 11 voluntary; Annex VI report on demand) | A.5.8 | `bin/ai-act-gate` | ok, prospector: 5 risks, 4 sources | outreach disclosure gate and Langfuse onboarding (crew#202) |
| Every mistake becomes a guard no session can walk past, swept across the estate | A.5.27 | `bin/idp-ci` (incident rows) | ok, each incident row named for its bug | none |
| Security incidents are logged with cause, cost and the guard that closed them | A.5.24 | `~/.claude/LAWS-INCIDENTS.md` (repo claude-guards) | exists, prose | move to crew issues with the `security` label |

## Not yet a control

- Vulnerability SLA (critical fixed within 7 days) — needs the CI scan first.
- Dependency updates (Dependabot) — crew#197.
- Access review of the 48 repositories — crew#199.
- EU AI Act obligations — see [EU AI Act](eu-ai-act.md).

## How to change this page

Add a row with a proof command that already exists in `bin/` or on the path. The
gate refuses a row whose command is missing, so a control cannot be written before
it can be proved.
