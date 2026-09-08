# 0007. Bootstrap depends on the OpenTofu half of decision 0026, not on the Crossplane operator

2026-09-08. The bootstrap path (`bin/idp-bootstrap-estate`, the cloud workflow at
`.github/workflows/estate-bootstrap.yml`, the Backstage scaffolder tile at
`backstage/templates/estate-bootstrap-preflight/`) was built on the assumption that the OCI half
of bootstrap crosses a trust boundary the runner already crosses via OIDC
(`gtrevorrow/oci-token-exchange-action@v2`, the same identity path `vault-reads.yml` uses,
crew#584). The four vendor halves (Tailscale, Cloudflare, GitHub App, vendor SaaS) cross separate
trust boundaries and require either operator SSO or a long-lived service principal.

Decision 0026 changed the picture. This record states where bootstrap fits in 0026's split, what
stays the same, what changes when 0026 step 3 (Claim emitter) lands, and the empirical-proof gap
that PR #2461 names — the same gap the bootstrap live job inherits.

## What 0026 actually says, as it applies to bootstrap

0026's table names six irreducible bootstrap resources and the answer to each is "Crossplane
cannot own this, because the cluster does not exist yet." Four of those six are the vault's
identity surface, which is exactly the surface the bootstrap orchestrator writes into:

| 0026 resource | file | bootstrap's relationship |
|---|---|---|
| the `oke` module | `main.tf` | bootstrap does not touch it; the cluster is its precondition |
| `oci_identity_policy.operators_compartment` | `iam.tf` | bootstrap does not touch it; it is the compartment grant everything hangs off |
| `oci_kms_vault.estate` | `vault.tf` | bootstrap writes VALUES into this vault, never creates it |
| `oci_kms_key.estate` | `vault.tf` | same |
| `oci_identity_dynamic_group.workers` | `vault.tf` | bootstrap reads the dynamic group identity to prove it; never creates it |
| `oci_identity_policy.workers_read_secrets` | `vault.tf` | bootstrap assumes this IAM grant exists; the founder's one-time grant is documented at `docs/operations/estate-bootstrap-cloud.md` |

The orchestrator `bin/idp-bootstrap-estate` does not CREATE any of these six resources. It mints
values that go INTO the four vault ones, via `bin/idp-vault-put --merge` (R52). It stays in the
right lane under 0026.

The four Day-2 candidate files named in 0026 (`langfuse.tf`, `flux-webhook.tf`,
`healthchecks.tf`, `otlp-ingest.tf`, `bridge.tf`, `commerce.tf`, `signoz.tf`, `superset.tf`) hold
38 application resources. Bootstrap does not touch them either — they are workload secrets, not
estate credentials. The migration of those 38 off OpenTofu onto Crossplane Claims is 0026 step 4,
decided by measurement, not asserted here.

## What stays the same

- `bin/idp-bootstrap-estate` runs `bin/idp-estate-seed`, `bin/idp-bootstrap-tailscale`,
  `bin/idp-bootstrap-cloudflare`, `bin/idp-bootstrap-vendors`, `bin/idp-github-app` installation
  + refresh, ending with `bin/idp-root-trust --check`.
- The typed register `docs/reference/policy/root-trust.md` (R45) names every credential, its
  birth path, and its bootstrapper. Nothing in 0026 changes that. The vocabulary has no estate
  name; the bootstrapper reference is the only field the orchestrator reads.
- The OIDC identity path (`gtrevorrow/oci-token-exchange-action@v2`) is unchanged.
- `bin/idp-vault-put --merge` (R52) is unchanged.

## What changes when 0026 step 3 (Claim emitter in `compile_storage()`) lands

The four vendor halves become Day-2 candidates under 0026's split-brain rule. The orchestrator
does not change; what changes is the writer behind the vault.

- **Tailscale.** `bin/idp-bootstrap-tailscale` currently writes a Tailscale API key as a vault
  secret via `bin/idp-vault-put`. Under step 3, the same intent could emit a Crossplane Claim for
  a Tailscale OAuth client instead, and the runner exchanges its OIDC token for a Tailscale
  session at run time (RFC 7523 jwt-bearer, 5-minute TTL, no stored credential).
- **Cloudflare.** Same shape: a Crossplane Claim for a Cloudflare scoped API token via
  Cloudflare Access OIDC. The runner reads the scope from the intent, mints via OIDC, writes
  to the vault, never holds the long-lived key.
- **GitHub App.** GitHub Apps already use JWT exchange (App ID + private key → installation
  token). The private key lives in OCI Vault (Crossplane Claim, not a Terraform resource, after
  step 3). The runner constructs the JWT from the OIDC identity and exchanges for an
  installation token. No human login.
- **Vendor SaaS long tail.** Three sub-cases: vendors with OIDC get direct exchange; vendors
  without get Playwright-in-sandbox with the founder doing MFA on their phone; the rest get a
  quarterly-rotated long-lived key in OCI Vault, rotated by a cron the runner owns.

The split-brain guard (`bin/idp-split-brain`, shipped 2026-09-07 in #2449) enforces "one
target, one owner" across both writers. Bootstrap does not grow its own guard.

## The empirical-proof gap is the same one PR #2461 names

PR #2461's summary states the gap explicitly: "Whether the workload-identity exchange actually
works is read off the provider pod's logs after this merges and tofu applies the policy, not
asserted here." The bootstrap live job has the same shape: synthetic CI gates are not proof;
proof is the runner pod successfully authenticating to OCI, writing a value via
`bin/idp-vault-put`, and `bin/idp-root-trust --check` exiting 0 on a real change.

The empirical-proof rule (founder 2026-09-05) is binding: no system is WORKING or MEASURED_OK
based on synthetic probes. The bootstrap live job's first real run, on real cluster traffic,
with a real vault write, is the empirical proof. Until that run lands, the live job is
UNVERIFIED — not because the code is wrong, but because synthetic gates lie.

## What this turn ships

Branch `feat/estate-autobot-surface`, commits `06066c01` and `bdf71872`.

- `bin/idp-vault-put` usage check fix (no `$1: unbound variable` on missing arg; exits 2 with
  usage).
- `.github/workflows/estate-bootstrap-preflight.yml` — file-only CI gate; runs
  `bin/idp-root-trust --check` on every PR that touches bootstrap-relevant paths.
- `backstage/templates/estate-bootstrap-preflight/` — scaffolder tile; opens a PR with a
  runbook script under `bin/estate-preflight.d/` that the operator runs on their laptop.
- `.github/workflows/estate-bootstrap.yml` — `workflow_dispatch` + `workflow_call` cloud
  workflow. Two jobs: preflight (read-only, no OCI write needed) and live (scope=estate-seed
  only; refuses vendor scopes on purpose with a clear pointer at the runbook).
- `docs/operations/estate-bootstrap-cloud.md` — the operator-facing doc.

## What this turn does NOT ship

- The post-consent callback that would let `mode=live` finish without a laptop (the honest
  constraint: the runner owns no callback URL the OAuth2 flow can redirect to).
- The four vendor WIF wirings (Tailscale, Cloudflare, GitHub App, vendor SaaS). Each is a
  separate decision-and-build turn; the order is 0026 step 3 (Claim emitter) → step 4 (one
  workload migrated).
- The OCI vault-write grant. The runner never holds an OCI write verb; the broker applies the
  write through its own compartment-scoped principal with the TTL the founder approved. Proposed
  as an `oci-vault-write` row in `platform/jit/grants.yaml` (`mode: broker-applies`) — glass-break
  under WJ.8, founder-only on `/platform/`. See "Proposed grant" below for the YAML shape; this
  doc does NOT land the row itself, only the dependency it implies.

## Open items, named

- **Capacity is the precondition, not architecture** (0026, §"What actually blocks it"): the
  cluster is misdeclared, 49% of CPU is reserved but idle, three pods in `observability` need
  right-sizing. That is its own session's lane, named here so it is not forgotten.
- **The pre-existing 10 MISS rows** in `docs/reference/policy/root-trust.md`
  (`commerce-payment-provider`, `cyrus-linear`, `cyrus-linear-api-token`, `DEEPSEEK_API_KEY`,
  `TELEGRAM_ALERTS_BOT_TOKEN`, `otto-staging-telegram`, etc.). The preflight gate refuses this
  PR for those rows; they are a founder action (drop, rotate, or assign a bootstrapper).

## Proposed grant: oci-vault-write

The cloud-side `live` job in `estate-bootstrap.yml` (mode=estate-seed) needs to write vault
values. The runner's OIDC identity names the vault key and value; the broker performs the write
through its own compartment-scoped principal with the TTL the founder approved. Pattern follows
`oci-scale-node-pool` (`mode: broker-applies`, `max_ttl: 10m`, `rate_per_hour: 2`):

```yaml
- id: oci-vault-write
  provider: oci
  why: The bootstrap workflow writes a vault value during seed and the runner never holds the verb
  mode: broker-applies
  operations: [create-secret, update-secret]
  compartment: estate
  secrets: [agent_foundry_runner, estate_seed_keys, estate_runbook_secrets]
  max_ttl: 10m
  rate_per_hour: 5
  parameters:
    secret_name: {type: name, required: true}
    contents_b64: {type: base64_blob, required: true, encrypted_in_transit: true}
```

Glass-break (WJ.8). CODEOWNERS on `/platform/` names the founder; no merge bot may land this
change. The bootstrap doc points at this row; the row does not point back at the bootstrap.
Same direction as `oci-scale-node-pool`, `dns-point-record`, `github-rerun-failed-checks`.
