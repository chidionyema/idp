# Ticket: estate-twin — the live graph of what the estate actually is

**Opened:** 2026-09-12
**Origin:** founder, 2026-09-12. The spec is a four-domain digital twin: code, runtime,
AI, data, all emitting to NATS JetStream, aggregated into a queryable SQLite graph, with a
founder CLI and an agent MCP reading the same file. Verbatim intent: *"i need to capture
everything one time, tired of running my whole estate blind."*

**What this ticket does with that spec.** It does not re-print it. It states what the
estate already has, what is genuinely missing, and what must not be rebuilt — because the
spec was written without the estate in front of it, and four of its five layers already
exist here under other names.

---

## 1. What the spec asks for, against what is already running

Measured 2026-09-12.

| spec component | estate today | verdict |
|---|---|---|
| NATS JetStream as the bus | `event-bus/nats-0` **2/2 Running**, JetStream **on** (API level 4, storage live) | **have it** — do not add a second |
| a SQLite graph | `catalog/estate.db`, written by `bin/db-gen` from `~/.estate/state/inventory.json` (457 rows today) | **have it** — extend it, do not create a second |
| k8s informer (runtime) | no informer; the cluster's declared state is read from `clusters/` at generation time | **missing** |
| git watcher (code) | no watcher; `bin/catalog-dark-matter` sweeps git at generation time | **partly missing** |
| AI telemetry (spend) | LiteLLM serves 16 lanes and logs spend per call (`LiteLLM_SpendLogs`, `x-litellm-key-spend`) | **have the data, no emitter** |
| Dagster / data lineage | Dagster runs **169 pods**; `estate-db` (Postgres, 3 pods) | **have the system, no emitter** |
| founder CLI | `bin/idp-status`, `bin/idp-publish`, `bin/idp-reconcile` already query the asset DB | **have the shape** |
| agent MCP | `mcp/` exists (estate MCP server, ADR 0006); it does not read this graph | **extend, do not add a server** |

**The spec's five layers are four existing things plus a gap. The gap is that all four are
*declared* state, sampled, and nothing is *observed*, streamed.**

### The rule this respects

`~/AGENTS.md`, THE HEADLINE: *"...a second Langfuse, a second secret store, a second
scheduler: that is the stitching, and that is what gets deleted."* A second SQLite graph
beside `catalog/estate.db` is that same mistake with a different noun. This ticket extends
the existing DB and the existing bus, and adds no new store, no new bus, no new MCP server.

## 2. The problem, stated as it was measured

The founder cannot see what the estate is. Not because there is no inventory — there are
three — but because every one reads **declared** state and reports it as if it were
**actual**:

- `docs/inventory.json` — 457 rows, from `~/.estate/state/inventory.json` (LAW 39)
- `backstage/platform/catalog-info.yaml` — 81 layers, generated from `clusters/` + `platform/`
- `backstage/platform/dark-matter.yaml` — 211 entities, generated 2026-09-12 (this session)

What none of them knows, measured 2026-09-12:

| measured | count | source |
|---|---|---|
| unmerged branches | **1,523** | `git branch --no-merged origin/main` |
| worktrees on disk | **178** | `git worktree list` |
| files on unmerged branches absent from main | **722+** | 300-branch sample; 581 in the 200 most recent |
| deployments scaled to zero | **11** | live cluster |
| agents deployed and dead | **3** — `research` 0/1, `hindsight` 0/1, `otto-gateway` 2/13 | live pods |

Three inventories, none of which can answer "what is broken right now".

## 3. Scope — what this ticket builds

Four emitters and one aggregator. One phase per emitter, each independently useful.

### Phase 1 — runtime emitter, first because it is the only bleeding one now

A pod in the cluster holding a watch on the Kubernetes API (informers, not polling). On
every pod/deployment/node transition it publishes one JSON object to
`estate.runtime.>`. It reads nothing else and holds no cluster write.

Answers immediately: which agents are dead, which deployments are scaled to zero, which
pods are crash-looping, and for how long.

**Why first:** the other three domains are stable enough to wait a day. Three dead agents
are production, right now.

### Phase 2 — code emitter

Same daemon shape, watching `~/.estate` on the machine that runs the sweep: `git
for-each-ref`, `git worktree list`, and the diff against `origin/main`. Publishes to
`estate.code.>`.

**This is the phase that retires `bin/catalog-dark-matter`'s 60-second sweep.** The
generator stays for the portal; the emitter makes it live. The two must agree — a test
asserts the emitter's counts equal the generator's.

### Phase 3 — AI emitter

LiteLLM already records spend per call in `LiteLLM_SpendLogs` and returns
`x-litellm-key-spend` on every response. This phase publishes a per-session rollup to
`estate.ai.>` — model, tokens, cost, consumer, session.

**No proxy change and no new middleware:** the ledger exists, this reads it. A custom
litellm `callback` is the integration point if a stream is wanted rather than a tail.

### Phase 4 — data emitter

Dagster run/asset sensors publish to `estate.data.>`. Dagster is the estate's one scheduler
(`bin/idp-one-scheduler`) and already has run status; this forwards it rather than
introducing a sensor framework.

### Phase 5 — the aggregator and the two readers

One consumer of `ESTATE_EVENTS.>` UPSERTs into the **existing** `catalog/estate.db`,
extended with the runtime/ai/data columns. Two readers over that one file:

- **CLI** — `bin/estate ls --dead`, `--stranded`, `estate blast-radius <node>`. This may be
  `bin/idp-status` extended rather than a new binary; check before adding one.
- **MCP** — a tool on the **existing** `mcp/` server, per ADR 0006 ("extend `mcp/`; never
  add a second server").

## 4. What must not be built

| refused | why |
|---|---|
| a second SQLite file | `catalog/estate.db` is the estate's asset graph; extend it |
| a second bus or a second stream family | `event-bus/nats-0` runs; `ESTATE_EVENTS` lands there |
| a second MCP server | ADR 0006: extend `mcp/` |
| polling in any emitter | the spec's own word is informer; a poll is the thing being replaced |
| an AI in the gathering path | the spec's first line; every emitter is deterministic |
| a dashboard | rejected already; the surfaces are a CLI and an MCP tool |

## 5. Definition of done

1. `estate ls --dead` names all three dead agents and all 11 zero-scaled deployments, from
   live state, within 60 seconds of a change.
2. Killing a pod makes it appear in that output **without** a manual run.
3. The code emitter's branch and file counts equal `bin/catalog-dark-matter`'s — proved by
   a test, so the two cannot drift.
4. One agent session's spend, as reported by `estate ls --ai`, equals the router's own
   ledger for that session.
5. The MCP tool returns the same rows as the CLI for the same question.
6. A test proves the aggregator is idempotent: replaying the same events changes no row.
7. No new SQLite file, no new NATS stream, no new MCP server exists — asserted by a gate.

## 6. Risks, named

- **The fast path is the bus; the founders' view is a file.** If the aggregator dies, the
  CLI goes stale silently. Mitigate with a freshness window on every query (the estate's
  own three-state rule: `MEASURED_OK` / `MEASURED_FAIL` / `UNKNOWN`, default 180s).
- **178 worktrees times a diff is slow.** Phase 2 must be incremental — watch refs, do not
  re-diff the estate on a timer. This is why it is an emitter and not a cron.
- **JetStream retention.** Events accumulate. The stream needs a max-age and the aggregator
  needs to tolerate a gap rather than rebuild from nothing.

## 7. Build order and the first commit

Phases 1 → 5 as above. Phase 1 is a pod plus one test; it is the only one that fixes
something already broken.

---

# PROOF

Every claim below has a command. Run it; read the output. The raw capture of all of them is
`docs/evidence/estate-twin/PROOFS.txt`.

| # | claim | reproduce with | what you will see | state |
|---|---|---|---|---|
| P1 | 8 acceptance scenarios pass | `python3 -m pytest sovereign/tests/bdd/test_estate_twin.py -v` | `8 passed` | **PROVED** |
| P2 | every receipt field is in the graph | `bin/estate-twin-runtime --once --code` then `sqlite3 catalog/estate.db "select type,count(*) from nodes group by 1"` | 12/12 fields carried | **PROVED** |
| P3 | the graph remembers changes | `bin/estate-twin-runtime --history k8s:deployment:commerce` | `active -> dead` with timestamps | **PROVED** |
| P4 | blast radius answers | `bin/estate-twin-runtime --blast-radius flux:Kustomization:flux-system/secret-store` | ~20 depending rows | **PROVED** |
| P5 | stale reads UNKNOWN | `sqlite3 catalog/estate.db "update freshness set updated_at=datetime('now','-30 days')"` then `--state` | `UNKNOWN`, never `MEASURED_OK` | **PROVED** |
| P6 | the graph and the catalogue agree | `bin/catalog-dark-matter --check` | `648 stranded branch(es)`, twin says 648 | **PROVED** |
| P7 | the guard refuses a bad graph | `python3 tests/test_estate_twin_rule.py tests/fixtures/twin/disagreed.json` | `refused: ... would read two different numbers` | **PROVED** |
| P8 | the guard passes the live estate | build the summary, grade it | `ok: the estate's graph is consistent` | **PROVED** |

## Defects these proofs found — all fixed

1. **28 of 317 flux objects silently lost.** Node id was `flux:<kind>:<name>` and
   `ExternalSecret/ghcr-pull` exists once per namespace. The id now carries the namespace.
2. **534 of 648 branches marked `active`** while adding files main does not have — stale state
   from an earlier rule, never reconciled. All 648 are now `stranded`.
3. **`MEASURED_OK` over 648 stranded branches.** Stranded work is not serving. The rule now
   counts it and names the breakdown.
4. **`--check` took 6m20s.** A gate nobody runs is not a gate. Now 0.2s.
5. **G4 was reported proved when it was not.** The first version built only inward edges, so
   blast radius returned nothing for every node. Withdrawn and rebuilt on Flux's own
   `dependsOn`. The withdrawal is recorded rather than hidden.

## NOT PROVED

| item | state |
|---|---|
| G2 — the ten missing domains | not built; specified in the spec §13.2 |
| G5 — running in-cluster as a pod | not built; runs on a laptop |
| G7 — the founder view reading the graph | not built |
| `--publish` to the NATS bus | written, **no event has been sent** |
| the collector's new fields in-cluster | in git; needs a Flux reconcile |

## Rules

The estate-twin row is in `rules.yaml` and `AGENTS.md`:

```
ok    twin     the estate's graph knows what the estate is, and no second
               surface contradicts it (2026-09-12)
```

`bin/idp-rules run --only estate-twin` — three cases: two refusals (disagreed numbers, a
stale domain claiming OK) and one pass.
