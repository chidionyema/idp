# 0045. AEI is an observation plane, not a second evidence authority

- Status: DECIDED 2026-10-28.
- Date: 2026-10-28
- Deciders: agent `pi-aei-ops`, on the founder's instruction to make the delivered AEI build
  operational on a real estate path.
- Amends: nothing. Extends [0028](0028-aevum-replaces-popdd-as-the-evidence-layer.md) (Aevum
  is the estate's evidence layer) and sits under
  [0034](0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md) (the free-tier
  placement ladder).

## The problem

AEI arrived as an archive: a schema, a store, an emitter, an evaluator, a viewer, and a
research note that says the right thing about staging — a *local, append-only, evidence-first
staging plane* pending integration with the estate's evidence layer. It was code, not a
capability: nothing observed the estate, nothing was recorded, nothing could be compared.

Two failure modes were available, and both are worse than doing nothing.

1. **A second evidence authority.** The estate already has one: Aevum, the signed receipt
   chain, in the estate's own Postgres (decision 0028). If AEI also became a place where
   receipts live, the estate would have two answers to "what happened", and the one nobody
   signs is the one that gets read.
2. **A second implementation of the same contract.** The delivered build has a SQLite store;
   the cluster has Postgres. If the cluster version were a rewrite, the laptop's ledger and the
   cluster's ledger would speak different dialects of the same schema, and neither would be
   able to read the other's evidence.

There is a third, quieter one: **cost recorded as zero**. The estate has already paid for
that hole — 176 million tokens recorded at `$0.0000` because the lane had no price row. A
collector that copies that behaviour is worse than no collector, because it looks like
accounting.

## Decision

### 1. AEI observes; Aevum attests. Both stand, and neither replaces the other.

AEI records what was **observed**: which model answered, how many tokens it used, how long it
took, what status it returned. Aevum records what was **attested**: signed, verifiable
receipts. A claim that needs proof goes to Aevum. A question of the shape "what did the estate
spend, and where did the time go" is answered from AEI, because that is what AEI is for and
Aevum does not answer it.

Where the two overlap, Aevum wins. AEI never becomes the canonical record of a fact, and no
component is allowed to treat an AEI event as proof.

### 2. One contract, two stores, and the store is a parameter.

The AEI package (`packages/aei`) is the single implementation of the event contract. It runs
in two places:

| Where | Store | Who writes | What it is for |
|---|---|---|---|
| Laptop | SQLite at `~/.estate/aei/aei.sqlite3` | `bin/aei-collector` | the loop, while the loop is being proven |
| OKE | Postgres `aei_evidence` in `estate-db` | `platform/observability/aei.yaml` | the estate's standing ledger |

`packages/aei/src/aei/pgstore.py` is the same store over Postgres — same append, same
idempotency by `event_id`, same digest-conflict detection, same `events`/`runs`/`evaluate`
surface. The schema is the schema; the SQL is not a second dialect of it. The drift between
the two copies is what `packages/aei/tests/` refuses.

### 3. No volume. The long-term store is the estate's own database.

A PVC-backed SQLite file would be a stateful workload on the node with a volume nobody else
uses, and it would put the ledger's survival at the mercy of a node's disk (decision 0034,
and the estate's own "the records outlive the tool that wrote them" rule for Aevum). The AEI
tables live in their own database, `aei_evidence`, with their own role `aei_evidence`, in the
estate's CloudNativePG cluster: one database per consumer, so the collector can be reasoned
about, and revoked, on its own.

### 4. The observation seam is the router.

Every model call in the estate passes the LiteLLM router (AGENTS.md §7a), so the router is
where execution is observed without the work knowing. `platform/llm/callbacks/aei_observer.py`
turns each routed call into one event: model, tokens, latency, status, and the deployment that
answered. It is the same seam the estate's other router callbacks already use.

Because the callback is mounted into the router pod, where the `aei` package is not importable,
it carries its own copy of the schema's *builder*. That copy is not allowed to drift:
`packages/aei/tests/test_router_callback.py` imports both and fails if the schema version, the
attribute allowlist, the identifier names, or the built event disagree.

### 5. Metadata only, and unknown is unknown.

The schema has no attribute class for content: no prompt, no answer, no tool arguments are
recorded, because there is nowhere to record them. Money is **derived** from the estate's own
router price table (`platform/llm/config.yaml`) and is labelled `derived`; a deployment with
no price row yields **unknown**, never `$0.0000`. The same rule holds in the router callback:
a `response_cost` of zero against real tokens is recorded as unknown, because "free" and
"unpriced" are different facts and only one of them is free.

### 6. Telemetry never changes the work.

A collector that is down loses evidence, never a task (LAW 38). The emitter is asynchronous
with a bounded queue; the callback fails open; the adapter re-raises the original exception
after recording it. An AEI failure can never be the reason a task failed.

## Consequences

- The laptop collector is stdlib-only Python plus SQLite and fits in a laptop's footprint
  comfortably; the binding constraint on the laptop is machine-wide disk, not the collector.
- The OKE collector is two replicas of 50m CPU / 128Mi (100m of the node's 1.8 CPU ceiling),
  in the `observability` namespace, which is labelled `availability.idp/tier: founder-facing`
  and therefore requires two replicas, a topology spread and a PDB with `maxUnavailable: 1`.
- The collector binds a routable address in the cluster, which the reference build refused to
  do. The refusal is kept as the default and the loosening is an explicit opt-in
  (`AEI_ALLOW_PUBLIC_BIND=1`), behind a token on every data route, a `/healthz` that carries
  no data, and the namespace fence.
- The API token and the database password are estate-born credentials: one vault entry,
  `aei-observer`, two properties, minted by `bin/idp-estate-seed`, registered in
  `docs/reference/policy/root-trust.md`, and delivered to both pods as mounted files — never
  as environment variables (Kyverno `secrets-not-from-env-vars`).

## Not decided here

- Whether AEI ever reads from Aevum, or Aevum ever reads from AEI. The two answer different
  questions; joining them is a separate decision with its own proof.
- Retention. AEI keeps what it is given; the estate's retention decisions (SigNoz, Langfuse)
  are not extended to this plane by this record.
- The founder-facing surface. The collector has no HTTPRoute and no page: the availability
  gate grades routed surfaces, and an unread page on a read-only ledger is not worth one.
