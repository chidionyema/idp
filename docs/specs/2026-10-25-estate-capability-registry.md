# The Estate Capability Registry — architecture spec

- **Status:** implemented (2026-10-26) - see section 13 for what was built, what was not, and what it costs
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

---

## 13. What was built (2026-10-26), and what was not

Claim: idp#7203. Lane: `lane/capability-registry`. The spec above is the contract; this
section is the receipt: what exists, what it measures, and what is still missing.

### 13.1 What exists

| Piece | Where | What it does |
|-------|-------|--------------|
| The door | `bin/capability-index` | one record per capability, the §3 shape, the writers, the store, the event log, reconciliation, the query contract |
| The store | `~/.estate/state/registry.db` (SQLite) | `capabilities`, `events` (capability.changed), `findings`; one writer per plane (R-52) |
| The gate | `bin/registry-gate` | I-1..I-5 with the case that trips each, the §3 schema check, the coverage diff, the freshness report, the drift check, receipt integrity |
| The proof | `tests/test_capability_registry.py` | the same five falsifiers as tests, plus the query contract and the drift check |
| The CI rung | `bin/idp-ci` (rung 8f) | the gate, path-gated on the registry's own inputs |
| The committed snapshot | `catalog/estate-capability-registry.json` | the repo-derived half of the census, machine-generated, drift-checked |
| The witness refresher | `.github/workflows/registry-snapshot.yml` | regenerates the witness from the pull request's own tree and commits it to the branch as the bot: refreshing the evidence is the pipeline's job, not an agent's |
| The reconcile job | `scheduler/schedule.yml` (`com.estate.registry-reconcile`) | the live half is reconciled on a cycle (`bin/capability-index census --write`), where the estate's one scheduler runs |
| The agent surface | `mcp/plugins/estate_mcp.py` | `capability_get`, `capability_query`, `capability_prove` |

### 13.2 What it measures (this machine, 2026-10-26)

The live census names **1233 capabilities**: 434 tools (`bin/`), 344 intents (the installed
library), 212 layers (the estate's own implementation under `platform/`), 125 workflows (47
mac-plane launchd jobs and 78 GitHub Actions pipelines), 113 cluster workloads, 5 agent
runtimes. Of those, **185 are `operating`** (a receipt inside its freshness window), **88
`degraded`** (the last run failed) and **960 `declared`** (no receipt: the record exists, the
proof does not). The committed witness carries the repo-derived half alone: **936 records**,
byte-identical on 3.9, on the estate's uv 3.12 and on the CI runner.

That split is the founder's question answered as a fact: crew#962's "76 built, 6 operational" is
now a queryable count with a freshness bound, not an audit somebody runs once.

### 13.3 The decisions that are not in the spec above

- **The store is SQLite, not Postgres.** Section 7 measured 1,000 records at ~10 MB. SQLite
  is one file, no daemon, and it is what the estate's own executor already uses
  (`~/.estate/estate.db`). Postgres arrives when the store must be written by several
  planes at once, and the schema does not have to change when it does.
- **The event path is the store's own log, not JetStream.** `capability.changed` is written
  into `events` with the writer that caused it, so the convergence bound (S = 60s) is
  measurable without a bus. The JetStream consumer is NOT wired: the seam is the `events`
  table, and a bus consumer is a writer that reads it. Section 5's S is therefore *not yet*
  proven in production; the gate proves the same convergence inside one process.
- **One reader, not PyYAML.** The census reads manifests and intents with a small
  block-YAML reader (and the standard library's `json` for the manifests that are JSON
  wearing a `.yaml` name). Measured 2026-10-26: with PyYAML the census answered 154
  service records on one interpreter and 155 on another, which would have made the
  committed snapshot drift the moment CI and a laptop disagreed. One reader, one answer:
  the snapshot is byte-identical on 3.9, on the estate's uv 3.12 and on the CI runner.
- **Coverage is a finding before it is a failure.** A missing *intent* record fails the
  gate (the estate's verbs are the registry's own contract). A running workload the
  repository does not declare is a finding with its names, and a failure under `--strict`,
  because until the A2 writers for layers and services land the cluster runs things the
  repo does not describe - that is drift to reconcile, not a gate to trip on every lane.
- **BLIND is a verdict, not a shrug.** On a CI runner there is no `~/.estate`, so the live
  coverage is BLIND and the gate prints `BLIND: store, intents` rather than passing a
  vacuous check or failing on a missing laptop.
- **The implementation is in the map, not only the scripts.** Measured 2026-10-26: the census
  named `bin/` (434 executables) and the manifests, and it did NOT name `platform/**.py` --
  the efficiency chain, the cache guardian, the request ceiling, the symbol slicer. A query
  for `symbol-slicer` answered 0 records on a main that has shipped
  `platform/estate/libexec/symbol_slicer.py` since #7212. A map that cannot answer "does the
  estate already have this?" is not a map, so the implementation is in it now: 212 modules
  under `platform/`, one record each, keyed by path, summarised by their own first docstring
  line. The consequence is the point: the Micro-Token components are found by a query, not
  by an agent's memory.

### 13.4 What is NOT built (the honest list)

1. The JetStream consumer for `capability.changed` (section 5's S = 60s is unproven).
2. The 15-minute reconciliation job is now DECLARED but not yet running on this machine.
   `scheduler/schedule.yml` carries `com.estate.registry-reconcile` (every 15 min, `runs_on: mac`),
   which runs `bin/capability-index census --write` -- the same cycle, as a scheduled job rather
   than something an agent remembers to run. Measured 2026-10-26: the estate's one scheduler
   (`ai.estate.scheduler`, the launchd job that runs the Dagster daemon) is NOT loaded on this
   Mac, so the row ticks wherever that scheduler runs and not before. The door is the door either
   way: `bin/capability-index census --write` reconciles, tombstones and writes the store, and it
   was run by hand to prove the cycle (two deleted tools tombstoned in one pass).
3. The router pre-dispatch read (section 8): the router does not consult the registry yet,
   so `unknown capacity is refuse` is not enforced anywhere.
4. The Face/Fleet tiles (A3). The MCP surface is the agent-readable half and it ships.
5. A live-cluster writer for workloads. The cluster writer reads the repository's
   manifests; the live cluster is read by the gate's coverage diff, not by a writer, so a
   workload that runs but is not declared has no record of its own yet.
6. The kill criterion's measurement (two weeks after A3, is the registry read at
   bootstrap?) needs the query logs the A3 surface would produce.

### 13.5 The gate's own limits

`bin/registry-gate` fails on: a broken invariant, a malformed record, a snapshot that names
a capability the repository no longer has, a snapshot that LAGS behind the repository (a newly
built capability the witness does not name -- section 14), a missing intent record, a forged
receipt, and (under `--strict`) any BLIND, any record past its freshness window, and a live
half whose reconcile heartbeat has gone past an hour. It does not fail on: a workload the
repository does not declare, a capability with no proof (that is `declared`, which is the
point), or a stale reconcile heartbeat outside `--strict` (the estate's one scheduler may
simply be running somewhere else -- so it is a named finding, not a false red).

---

## 14. The evidence lifecycle: what happens when a component is built

The question a registry has to answer before it is trusted: **we built something. What now?**

Three answers, and the third is the one that decides whether the registry is worth having.

**1. The witness is a pure function of the tree.** `catalog/estate-capability-registry.json` is
generated by `bin/capability-index emit --write` from the repository's own surfaces (bin scripts,
platform manifests, cluster manifests, CODEOWNERS, docs). Nothing in it is typed by a human, so it
cannot be wrong about what the repository contains; it can only be out of date, and "out of date"
has an exact meaning here: it differs from a fresh generation, byte for byte.

**2. The merge point must be true.** `bin/registry-gate` fails, by default, when the committed
witness differs from a fresh generation in either direction:

- **LAG** -- the repository grew a capability the witness does not name;
- **FAIL** -- the witness names a capability the repository no longer has.

It is a rung in `bin/idp-ci`, and `ci-success` is a required check, so a lagging witness cannot
land. That is the guarantee, and it is arithmetic rather than vigilance: the witness is a function
of the tree, and the merge point is checked against that function.

**3. Refreshing it is machine work, not a task.** `.github/workflows/registry-snapshot.yml`
regenerates the witness on every pull request and commits it to the branch as the bot. The agent
that built the component never has to know the witness exists. This is the part that was missing
when this section was first asked (2026-10-26: "what happens when we build new components"), and
it is the part that made the answer "an agent must remember to refresh it" -- which is the thing
that causes drift, and a map that drifts is trusted anyway.

### 14.1 The edge cases the first version of this spec did not account for

| ID | Edge case | Behaviour now |
|----|-----------|----------------|
| E-1 | A component is added (a new bin script, a new module under `platform/`, a new service, a new intent in the repo, a new pipeline) | the census grows, the witness lags, the gate fails, the workflow regenerates it, the merge point is true |
| E-2 | A component is removed | the witness names a capability the estate no longer has: the gate fails (FAIL), and the live half tombstones it on the next reconciliation cycle (I-5) |
| E-3 | main moves under the lane | the truth is a function of the tree, so a moved main can change it: the gate re-derives the witness against the lane's own tree, and the workflow regenerates it. Measured 2026-10-26, on the lane that built this registry: a rebase onto a moved main changed the tree, and the witness had to be re-derived against it |
| E-4 | somebody hand-edits the witness | drift: the gate compares the committed bytes with a fresh generation and fails. The claim-gate exempts the witness path from claim coverage (it is generated, so it belongs to nobody's claim); the gate is what proves its content -- two layers, each doing its own job |
| E-5 | the live estate changes (an intent installed, a workload deleted on the cluster) | the live half is reconciled on a cycle: `com.estate.registry-reconcile` in `scheduler/schedule.yml` runs `bin/capability-index census --write` every 15 minutes, which tombstones what was removed and records what appeared. It is a scheduled job, not a ritual. The reconcile leaves a heartbeat (`census.reconciled`), so the gate can name the live half's age instead of assuming it: a heartbeat older than an hour is a finding, and a failure under `--strict` |
| E-6 | CI has no estate state (`~/.estate`, the installed intents) | BLIND is a verdict: the gate says BLIND for the live coverage and does not pretend. The repo half is still checked in full |
| E-7 | the gate has to be shown able to fail | every invariant ships with the case that trips it, and the drift check ships with a seeded lag (`tests/test_capability_registry.py`) |

### 14.2 What this does not do

- It does not make the live store a shared service: it is one file on one machine, reconciled by
  a job on that machine. Postgres arrives when a second plane writes it (section 7).
- It does not make the registry the estate's only inventory: growmos, estate-inventory and the
  backstage catalogue remain writers (section 2, principle 5).
- It does not prove a capability WORKS: it proves the estate knows what it has. The receipt is
  the proof of operation, and a capability with no receipt is `declared`, which is the point.
- It does not own a timer of its own. The live half's reconcile runs on the estate's one
  scheduler (`ai.estate.scheduler`, the Dagster daemon), and on this Mac that launchd job is
  NOT loaded (measured 2026-10-26: `launchctl list` shows only `ai.estate.executor`; the
  webserver on 127.0.0.1:3210 is down), so the row ticks wherever that scheduler runs and not
  before. The committed half does not depend on it: the witness is regenerated by the pull
  request pipeline and graded by the gate, which is why the guarantee holds while the laptop
  timer is dark. The gate prints the live store's last write, so the age of the live half is
  always on the record.
