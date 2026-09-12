# Onboarding: the evidence layer

## What it is for

An AI agent did something. Six months later an auditor, a regulator or a court asks you to prove
what it did, and to prove nobody edited the record afterwards. Logs cannot answer that — they are
mutable, self-attested and operator-controlled, and nothing stops the record being changed after
the fact.

This layer records every agent action as a **signed, hash-chained receipt**, so the answer is an
artefact a third party checks with a public key rather than a claim they have to believe.

## What it is not

It is **not enforcement**. Nothing here sits in a request path. If this layer is down, the estate
behaves exactly as it does today — what breaks is the evidence, not a workload. Enforcement (a
gateway `ExtAuthz` with `failureMode: deny`, scoped to irreversible actions) is a separate, later
decision, made on evidence from this ledger and deliberately not switched on the same day.

It is also not a guarantee that every action *was* captured. Aevum names that distinction itself:
tamper-evidence is a property of the record; faithfulness-at-capture is a property of the
integration. Recording is a byproduct of work already happening; an action that takes a path
outside the estate's doors is not recorded, and the layer's job is to make a gap visible rather
than silent.

## Where it lives

| What | Where |
|---|---|
| The workload | `platform/observability/aevum.yaml` in namespace `observability` |
| The image | `platform/observability/aevum.Dockerfile` (Aevum publishes no container) |
| The gate | `bin/idp-evidence-gate`; rule `aevum-evidence` in `rules.yaml` |
| The ledger | the estate's own Postgres, `estate-db`, so the records outlive the tool |
| Signing key + DB role | vault entry `aevum-evidence`, minted by `bin/idp-estate-seed` |
| The decision | `docs/decisions/0028-aevum-replaces-popdd-as-the-evidence-layer.md` |

## What a new repo has to do

**Nothing.** That is the point. The layer runs on the platform, once; a repo created tomorrow
records agent actions the same way it has DNS and secrets — by running on the platform. There is
no dependency to add, no adapter to write, and no copy to drift.

## What it costs

- Two pods at `100m` CPU / `256Mi` memory requested, `1Gi` limit each, seated at
  `priorityClassName: infrastructure-critical`.
- A Postgres role and one table in `estate-db`. The evidence grows with the actions recorded, so
  retention is a capacity question and belongs in the same review as every other table there.
- Signing keys are the estate's, in the vault. **Whoever holds them can produce a chain that
  verifies.** Custody is the same problem as every other secret.

## How to stop it

```
kubectl -n observability scale deploy/aevum --replicas=0
```

Recording stops. Every workload keeps running, because nothing is in a request path. The receipts
already written stay in Postgres and keep verifying — that is what "the records outlive the tool"
means. To remove it entirely, drop the `aevum.yaml` line from
`platform/observability/kustomization.yaml`; Flux prunes the Deployment, the Service and the
ExternalSecret, and the ledger table is left untouched until someone decides what to do with the
evidence.

## What to watch

- **The empty ledger.** Aevum's default store is in-memory. It reports a valid chain after every
  restart while recording nothing, which looks present and is not. The manifest never configures
  it, the factory refuses to start without `AEVUM_POSTGRES_DSN`, and `bin/idp-ci`'s evidence rung
  asserts both. If you ever see `verify_sigchain: true` with zero events, that is this failure.
- **A key that is not the key it was signed with.** `Engine.verify_sigchain()` verifies stored
  events against whatever sigchain the Engine was built with. Building an Engine with a ledger but
  without `sigchain=` mints a random one and reports every chain invalid — it does not raise. The
  factory passes the same object to both, and the live rung asserts that line is present.
- **Where a person goes next:** `docs/tutorials/demo/evidence.md` shows it running.
