# 0027 — An approved below-Kubernetes action lands on a credential-less executor of its own

- Status: DECIDED 2026-09-08 on the founder's instruction in session
- Deciders: founder
- Extends: 0025 (agents hold no write on production and the Greenlane grows one row at a time),
  0021 (the founder wears two hats), 0006 (the platform answers for itself over one MCP),
  0026 (Crossplane owns Day-2 and Terraform owns the ground)
- Governs: `platform/jit/broker/`, `platform/jit/grants.yaml`, `platform/oci/bridge.tf`,
  `docs/reference/policy/temporary-grants.md`, and any future catalogue row whose `provider`
  is not `kubernetes`.

## The gap this closes

The JIT catalogue (0025/WJ.1-WJ.15) lists actions below Kubernetes — `oci-scale-node-pool`,
`dns-point-record`, `github-rerun-failed-checks`, and the newly added `oci-vault-write`
(PR #2496). But the broker cannot perform any of them, and this was invisible until one was
asked for for real.

Two verified facts:

1. `platform/jit/Dockerfile` ships Python and `pyyaml` only. There is no `oci` binary, no
   `gh` binary, no shell. `platform/jit/broker/broker.py`'s `_provider_runner("oci")` and
   `_provider_runner("gh")` call binaries the image does not contain.
2. `platform/jit/deployment.yaml` states it plainly: the broker holds no standing cloud
   credential, and everything it needs arrives as four files under `/etc/jit-secrets`
   (Telegram token, signing key, webhook secret, agent key). `platform/jit/broker/serve.py`
   exposes `/ask`, `/identity`, `/state`, `/grants` and the Telegram webhook — no door that
   performs an OCI act.

The `bin/idp-jit-grants --check` gate only proves a grant cannot be turned into standing
access (WJ.5). It does not prove the broker can execute it. So a below-Kubernetes row passes
the gate and then, on an approved tap, cannot actually run. `oci-vault-write` (PR #2496)
exposed the class: it merged clean, and nothing could perform it.

## Why the broker must not grow a cloud credential

The estate's own comment in `platform/jit/deployment.yaml` is the whole argument: the broker
is the one workload that mints write access, and the whole guarantee is that it holds
almost nothing. Adding an OCI credential to the broker — however scoped — turns the single
most security-critical pod into a target that, if compromised, could act on the tenancy with
whatever that credential could do. The distribution of power must stay asymmetric: the broker
keeps deciding, and never carries the means to do.

## The decision: a dedicated executor, riding a narrower identity

When a below-Kubernetes grant is approved, the broker does not perform the action. It hands a
short, signed, single-use request to a **dedicated executor**; the executor verifies the
signature, re-checks the request against the catalogue it loads itself, then performs the OCI
act under an identity that is **narrower than the estate's own nodes**.

Three founder choices, in session 2026-09-08, make the shape concrete:

1. **The executor rides the narrow bridge identity, not the broad worker nodes.**
   The estate already runs one machine that is the exact shape of narrow and credential-less:
   `platform/oci/bridge.tf` (crew#841), a single Always Free instance, no public IP,
   instance-principal identity, and a dynamic group pinned to that one OCID
   (`ALL {instance.id = '<bridge>'}`, `bridge.tf:180`). The executor runs on **that bridge
   machine**. The whole-`workers` dynamic group (`ALL {instance.compartment.id = ...}`,
   `vault.tf:30`) is never widened for vault writes.
2. **The vault-write scope stays the three named secrets.** The grant declares
   `secrets: [agent_foundry_runner, estate_seed_keys, estate_runbook_secrets]` and nothing
   wildcard. The executor's IAM act is scoped to exactly those names, never "any secret",
   never a wider class.
3. **The broker stays exactly as it is.** Holding nothing new. On approval it emits a signed
   request to the executor rather than trying to run OCI in-process and failing.

## What already carries the pattern (no new platform layer invented)

The autoscaler (`platform/oci/autoscaler/`, `platform/oci/autoscaler.tf`) is the estate's
living proof that an in-cluster workload can authenticate to OCI as itself via
`OCI_USE_INSTANCE_PRINCIPAL`. The bridge (`platform/oci/bridge.tf`) is the proof that a
single pinned instance principal can read the vault and reach the estate with no stored
credential. The executor is the composition of the two: the bridge's identity, structured to
answer the broker's signed requests.

## What must change (named, not built here yet)

- `platform/oci/vault.tf` — the bridge dynamic group gains one `manage secret-family` grant
  scoped to the three secret names the grant declares (never the verdict key; never a wildcard).
- `platform/jit/broker/broker.py` + `serve.py` — on an approved below-Kubernetes ask, sign and
  dispatch to the executor instead of invoking a missing binary.
- The executor itself — a small service on the bridge machine: verify the broker's signature,
  reload the catalogue, re-run `_check_params`, then create-or-update the named secret under
  `instance_principal`.
- `platform/jit/grants.yaml` already carries `oci-vault-write`; the executor becomes its
  first real performer.

## The honest catch, recorded once

The estate's existing vault-writer, `bin/idp-cloud secret put`, assumes the founder's laptop
idiom: `security_token`, sops envelope, `tofu output` for vault and key IDs, and a profile
(`bin/idp-oci-whoami`). A bridge-machine executor has none of those. It must authenticate as
`instance_principal` and carry compartment, vault and key identity as data it resolves at
runtime — not as laptop files. This is why the executor is a new component and not a reuse of
the laptop script.

## Proof boundary

None of this is finished by merging this document. The executor's first real vault write —
an approved ask that ends with a `secret` create or update visible in OCI's own audit trail,
performed under the bridge identity — is the only thing that closes the loop. Until then, the
below-Kubernetes catalogue remains what it is today: decided, catalogued, and unperformed, and
that is a true statement rather than a defect to hide.
