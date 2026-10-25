# The Estate Capability Registry — architecture spec

- **Status:** proposed — founder go/no-go requested
- **Date:** 2026-10-25 · **Author:** kimi (chief architect), Phase A first build of the estate master epic (§25)
- **Scope:** the single source of truth about what the estate can do — for the founder and for every agent
- **Evidence rule:** every property below names its falsifier. A property that cannot be tested is deleted, not kept.

---

## 1. The contract, in one sentence

One queryable, realtime record of **every capability** in the estate — what it is, what it does, who
owns it, what it costs, and **when it was last proven working** — read by the founder, every agent at
bootstrap, the router before dispatch, and every surface before it renders a claim.

This is the answer to crew#962 ("76 capabilities built, 6 operational"): the declared-vs-operating gap
becomes a **queryable fact with a freshness bound**, not an audit somebody runs once.

## 2. Design principles (binding)

1. **One store, many renderers** (720-3). Face, Fleet, Otto, the CLI and agents render the same
   records. A surface holding a private copy is the F-09 defect and fails review.
2. **Declared ≠ operating.** A capability without an in-window proof receipt is `declared`. No receipt,
   no claim — the estate's §3 law applied to inventory.
3. **Stale is a finding, never a silence.** A record past its freshness window is served with
   `stale: true` and counted. A registry that cannot answer says BLIND (the telemetry-coverage pattern).
4. **Agent-readable first, human-rendered second.** The MCP surface ships before any page (§26, row 10:
   IDPs are converging on agent-consumable catalogs; the estate leads that, not follows it).
5. **Compose, never rebuild.** growmos (11.5k entities), estate-360, estate-inventory, the backstage
   catalog, the 340 intents and the telemetry-coverage gate are **writers and sources**, never parallel
   maps. A second inventory is a duplicate layer and is deleted (AGENTS.md §6).

## 3. The record

```yaml
capability:
  id: cap:<domain>/<name>            # stable, namespaced, never reused
  schema_version: 1                  # T-1: versioned or refused
  kind: intent | tool | service | layer | agent | surface | model | dataset | workflow
  summary: <one grounded sentence>
  contract:
    inputs:  [<typed parameters>]
    outputs: [<typed results>]
    errors:  [<typed failure modes>]
    cost_class:    free | cheap | metered | expensive
    latency_class: interactive | seconds | minutes | batch
  owner: <agent id | role | founder>          # exactly one
  plane: <the substrate plane it writes to>   # R-52: one writer per plane, named here
  health:
    state: operating | degraded | frozen | declared
    observed_at: <rfc3339>
    source: <the instrument that observed it>
  proof:
    receipt: <command or probe id + output hash>
    proven_at: <rfc3339>
    window_s: <freshness bound for this capability>
  consumers: [<capability ids>]      # an unconsumed capability is a candidate for deletion (R-62)
  cost: {estimate: <number>, unit: <tokens|usd|seconds>}
  rung: R1 | R2 | R3                 # evidence rung of the record itself
```

Schema enforcement is generative, not after-the-fact (T-1): producers emit through constrained decoding
(XGrammar-class, <40µs/token — §26 row 6), so a malformed record is a *gate refusal*, never a stored row.

## 4. Invariants — each with its falsifier

| ID | Invariant | Falsifier (the test that must be able to fail) |
|----|-----------|------------------------------------------------|
| I-1 | One capability, one record, one writer | a seeded duplicate `cap:` id must fail `bin/registry-gate` |
| I-2 | No `operating` without a receipt inside `window_s` | a seeded capability with an out-of-window receipt must be reported `declared` |
| I-3 | Every record names its plane; writers may target only their own plane (R-52) | a writer emitting a record for a plane it does not own is refused |
| I-4 | Stale reads are marked, never silent | a consumer reading past `window_s` receives `stale: true`; a silent stale read fails the gate |
| I-5 | Deletion converges: a capability removed from the estate is tombstoned within one reconciliation cycle | delete a real capability in a test estate; the registry must tombstone it within the cycle bound |

## 5. Consistency and convergence model

- **Event path (primary).** Writers publish `capability.changed` on the JetStream bus (proven, 1/1,
  PVC-backed). The registry consumes with a durable cursor. Convergence bound **S = 60s** from change to
  queryable record.
- **Reconciliation path (the net under the wire).** Every 15 min, a job diffs *declared* (registry)
  against *observed* (estate-inventory, cluster API, intent filesystem scan) — the telemetry-coverage
  pattern lifted one level. Every diff row is a finding with an owner; BLIND if a source cannot answer.
- **Read semantics.** Snapshot-consistent per record with `observed_at` on every field. Cross-record
  transactional consistency is **deliberately not provided** — the registry is a discovery surface, not
  a ledger of record; work_item and interaction records live in Postgres (§14 substrate).
- **Convergence proof (falsifier for S):** inject a capability change in the test estate; the record
  must reflect within 60s or the gate fails.

## 6. Failure modes — enumerated, with behaviour

| ID | Failure | Behaviour |
|----|---------|-----------|
| F-a | A source dies (estate-inventory, catalog, bus) | its records age past window → `stale`, counted, pushed (H-3); never silently trusted |
| F-b | A writer emits a malformed record | schema gate refuses; the refusal is a finding against the writer |
| F-c | Bus partition | reconciliation bounds divergence at 15 min; cursor resumes, no loss (JetStream retention) |
| F-d | Registry store unreachable | surfaces render last snapshot with `stale: true`; queries answer BLIND; no fabricated freshness |
| F-e | Poison message | DLQ (`platform/messaging/dlq`, already deployed) + a ticket (R-65) |

## 7. Capacity math (measured inputs, not hopes)

- Records: 340 intents + 440 bin tools + ~120 layers/services/agents/surfaces ≈ **~1,000 records**;
  at ~10 KB per record ≈ **10 MB** — trivial for Postgres; SQLite would suffice at 10× growth.
- Write rate: bursts on catalog/intent change; steady-state < 5/min; peak < 100/min (a mass import).
- Read rate: agent bootstraps + router pre-dispatch + surfaces ≈ **10 qps peak**, 99% cacheable within
  the freshness window.
- Headroom: 10× growth needs no re-architecture; 100× moves reads behind the Brain API's fold (C-16
  p95 budget applies).

## 8. The query contract

- **Agents (MCP, day one):** `capability_get(id)`, `capability_query(verb|kind|plane|state)`,
  `capability_prove(id)` — re-runs the receipt probe on demand. An agent decision that names no
  registry read is a guess (720-1), and the 720 gate can be wired to refuse it.
- **Founder (Face/Fleet):** the same API rendered; a capability tile shows state, receipt age and
  consumers. Voice: "what do we have for X" answers from this store, citing the receipt.
- **Router (pre-dispatch):** reads `health.state`, `cost_class` and the capacity contract (§6.3 of the
  epic) before admission; unknown capacity is `refuse`, never `admit`.

## 9. Security and trust boundaries

- Receipts are HMAC-anchored (the sovereign receipts pattern) so a receipt cannot be forged by the
  component it proves.
- Records carry no secrets — references by env-var name only (AGENTS.md §4).
- All writes through the door (an intent); no direct store writes from any surface or agent.

## 10. Proof harness

`bin/registry-gate`, wired into `bin/idp-ci` as a rung:

1. the I-1…I-5 falsifiers above, run against the test estate;
2. a coverage diff: every running workload and every intent must have a record (the
   telemetry-coverage verdict shape: ok / FAIL with names / BLIND);
3. a freshness report: per-domain stale counts, pushed to monitoring as a metric (H-5).

A gate that cannot fail is not a gate — each falsifier ships with the case that must trip it.

## 11. Rollout and kill criteria

| Step | Work | Exit test (falsifiable) |
|------|------|------------------------|
| A1 | Schema, store, writers for the 340 intents (auto-derived) | `capability_query(kind=intent)` returns 340±ε records, each with a contract |
| A2 | Writers for layers/services/agents (backstage catalog + estate-inventory) | the coverage diff shows zero running workloads without a record |
| A3 | MCP surface + router pre-dispatch read + Face/Fleet tiles | an agent bootstrap and one routing decision read the registry, logged |
| A4 | registry-gate as a CI rung; the freshness metric on /fleet | the I-2 falsifier fails the gate on demand |

**Kill criterion (honest):** if, two weeks after A3, agent query logs show the registry is not read at
bootstrap (measured, not surveyed), the design is wrong — not the agents. Re-cut the contract before
adding a single feature.

## 12. Scope fences — what this is not

- Not a second memory store (T-2: memory consolidates elsewhere; the registry *references* it).
- Not a dashboard — dashboards render it; it owns no pixels.
- Not a growmos replacement — growmos is a writer of relations; the registry is the capability ledger.
- Not a work-item store — `work_item` (EPIC-060) lives in Postgres on the state plane.
