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
| No credential value travels over chat: every Telegram sender, the reply text on Stop and every `gh issue` and `gh pr` comment, create and edit body are refused on a credential shape; logins are IDCS SSO, break-glass values live only in the vault and are never read out (crew#407 incident) | A.5.24, A.8.15 | `pytest ~/.claude/scripts/tests/test_incident_crew407_no_credential_over_telegram.py ~/.claude/scripts/tests/test_incident_crew407_no_credential_in_reply_or_gh_comment.py` | ok, refused and permitted both ways (claude-guards#113, #118); sweep 36,229 rows, 0 live values | a value typed by a person into a prompt is not seen; secret-scrub.py redacts history on Stop |
| Every credential is born by a bootstrapper: at most one SSO consent, minted through the provider's API (or a console driven by the estate's own browser profile), verified, written to the vault in-process; a value a person types or pastes is a ticketed MISS, never a procedure (crew#66 ruling 5453747447, [root trust](policy/root-trust.md)) | A.5.17, A.8.24 | `bin/idp-root-trust` | PASS on 2026-08-28: 33 vault entries registered, MEETS 11, PARTIAL 1, MISS 19 (each ticketed crew#575–#580) | `--check` (every row MEETS) red until crew#575–#579 land: bin/idp-estate-seed, router keys in deploy hooks, GitHub App tokens, bin/idp-bootstrap-cloudflare, bin/idp-bootstrap-vendors |
| Only the gateway listens off loopback; every port is declared in the ledger | A.8.20 | `bin/port-gate --live` | ok, 19 declared, 0 findings | none |
| Identity is OIDC at the gateway; workloads carry SPIFFE identities | A.5.16 | `bin/idp-verify` (gateway + spire rows) | gateway ok; SPIRE pending live proof (idp#32) | SPIRE proof waits on cluster start |
| No static credential on any host; machines authenticate by workload identity (OCI WIF for CI, OKE workload identity in-cluster, SPIFFE between agents), people by hardware-rooted identity (WebAuthn / Secure Enclave); third-party API keys live only in OCI Vault and reach a workload through its identity | A.5.16, A.8.24 | `bin/static-secret-gate` | FAIL, 28 on the founder Mac on 2026-08-25 (1 OCI key, 1 gh token file, 6 .env, 19 vault files, 1 keychain item) | crew#227: GitHub OIDC -> OCI UPST for the rebuild; External Secrets from OCI Vault; delete each file as its identity goes green |
| Every external provider the estate depends on has a second owner and a recovery route that is not the founder's mailbox (crew#227 CP7) | A.5.2, A.5.30 | `bin/owner-account-gate` | FAIL 9 of 9 | one Google account is the login and the recovery route for GitHub, Oracle, Cloudflare, Stripe, Anthropic, OpenRouter, Apple; add a second owner per provider, recovery to a hardware key |
| Admission policy is code and is proved both ways before merge | A.8.9 | `bin/policy-test` | PASS | none |
| Every admission policy in the tree is installed by a Flux layer that waits on the policy engine, and this page lists exactly the policies the tree applies | A.8.9 | `bin/idp-admission-policies` | ok on 2026-08-28: 5 policies, 5 applied (crew#341's `secrets-not-from-env-vars` was in no kustomization for two days; crew#488 CP5) | `secrets-not-from-env-vars` and `capacity-affinity` are Audit; flip to Enforce after a zero-violation pass of `bin/idp-ci`'s kyverno row |
| Every image is built for amd64 and arm64 from one tag, no per-environment build | A.8.9 | `bin/multiarch-gate` | ok, 0 findings | none |
| Every published image carries an SBOM, a vulnerability report and a licence verdict | A.5.21 | `bin/supply-chain` | tool exists; not yet run in CI | run in CI, fail on critical, cosign sign (crew#197) |
| Every GitHub Action is pinned to a commit SHA | A.5.21 | `bin/actions-pinned` | FAIL, 0 of 7 pinned in this repo | pin + gate (crew#197) |
| Every repository's default branch refuses deletion and force-push | A.8.4 | `bin/repo-rulesets` | 47 of 48; 1 missing, 2 private BLOCKED by plan | fix the one; required checks per repo (crew#199) |
| The founder's account has MFA; each agent acts as its own identity | A.5.17 | `gh api /user -q .two_factor_authentication` | BLIND, field needs `read:user` scope | machine identity per agent (crew#199) |
| Data has a versioned, encrypted, off-host backup with a monthly restore drill | A.8.13 | `restic snapshots` | not configured; Fly teardown backups sit unencrypted in `~/backups` | restic to OCI object storage (crew#78) |
| Every AI system is registered with an Annex IV technical file, a risk register entry and declared data sources (Arts. 9, 10, 11 voluntary; Annex VI report on demand) | A.5.8 | `bin/ai-act-gate` | ok, prospector: 5 risks, 4 sources | outreach disclosure gate and Langfuse onboarding (crew#202) |
| Every mistake becomes a guard no session can walk past, swept across the estate | A.5.27 | `bin/idp-ci` (incident rows) | ok, each incident row named for its bug | none |
| Security incidents are logged with cause, cost and the guard that closed them | A.5.24 | `~/.claude/LAWS-INCIDENTS.md` (repo claude-guards) | exists, prose | move to crew issues with the `security` label |

## Cluster admission policies

What the cluster refuses at admission, whatever a chart or a session asks for. Generated by
`bin/idp-admission-policies` from `platform/` and `clusters/oke/`; the incident test refuses this
page when the table below differs from what the command prints, so a policy that is written but
not installed cannot appear here as installed. `Audit` records a violation in the policy report;
`Enforce` refuses the object. The engine is the `kyverno` Flux layer; `edge` and `scheduling`
wait on it. The upstream Pod Security Standards set (Enforce) ships with prospector's own
manifests (`prospector/deploy/k8s/policies`) and is judged by `bin/idp-kyverno-render` on every
PR alongside these.

<!-- admission-policies:begin -->
| Policy | Mode | Refuses | Flux layer | File |
|---|---|---|---|---|
| `capacity-affinity` | Audit | Preemptible capacity is for pods that can lose a node | `scheduling` | `platform/scheduling/capacity-affinity.yaml` |
| `capacity-requests-need-proof` | Audit 1, Enforce 1 | No paid capacity without proof (crew#584) | `edge` | `platform/edge/capacity-policy.yaml` |
| `dev-loop-mirrord-fence` | Enforce | mirrord agents only where the namespace allows the dev loop | `edge` | `platform/edge/dev-loop-policy.yaml` |
| `protect-namespaces` | Enforce | A platform namespace cannot be deleted | `edge` | `platform/edge/protect-namespaces.yaml` |
| `provider-independence` | Enforce | Provider independence (R43) | `edge` | `platform/edge/provider-independence.yaml` |
| `require-availability` | Enforce | Founder-facing workloads survive losing one node | `scheduling` | `platform/scheduling/require-availability.yaml` |
| `require-catalogue-entity` | Enforce | Everything that serves a port names its catalogue entity | `edge` | `platform/edge/require-catalogue-entity.yaml` |
| `require-priority-class` | Audit 1, Enforce 2 | Require a PriorityClass on platform workloads | `scheduling` | `platform/scheduling/require-priority-class.yaml` |
| `secrets-not-from-env-vars` | Audit | Disallow Secrets from Env Vars in CEL expressions | `edge` | `platform/edge/kyverno-secrets-policy.yaml` |
<!-- admission-policies:end -->

## Not yet a control

- Vulnerability SLA (critical fixed within 7 days) — needs the CI scan first.
- Dependency updates (Dependabot) — crew#197.
- Access review of the 48 repositories — crew#199.
- EU AI Act obligations — see [EU AI Act](eu-ai-act.md).

## How to change this page

Add a row with a proof command that already exists in `bin/` or on the path. The
gate refuses a row whose command is missing, so a control cannot be written before
it can be proved.
