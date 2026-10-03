# The memory systems: what exists, what works, what is missing, and the plan

Date: 2026-10-02
Audience: the founder. This is the synthesis, not the raw measurement.
Method: every number below was measured this turn against the live cluster or the live repos.
Nothing is copied from a document.

Companion documents, in reading order:
1. **This file** — the whole picture, and what to do.
2. `docs/reports/2026-10-02-memory-inventory-measured.md` — the per-system evidence table.
3. `docs/reports/2026-10-02-memory-layer-correction-measured.md` — the `otto/memory` failure in full.
4. `docs/decisions/0036-one-memory-plane-and-it-is-cortex.md` — what was decided, and what the
   measurement overturned.
5. `docs/specs/2026-10-02-memory-plane-cortex-adoption.md` — the design.
6. `bin/memory-gate` — the thing that stops this being silent again.

---

## 1. The one-paragraph answer

The estate has **eight memory systems**. **Three work. Five do not.** Of the five that do not,
**four fail for a single shared reason: no embedding is ever written** — the store ranks by
vector, the vector is never computed, so recall finds nothing. The fifth (Hindsight) is
switched on and simply never called. Critically: **the embedding capability already exists and
is correctly configured — the LiteLLM `embed` lane — and it has served zero requests in 48
hours.** So the estate does not need a new memory system. It needs to call the thing it already
built, and it needs a gate so that when it doesn't, someone hears about it.

That is the whole diagnosis. Everything below is the evidence and the plan.

---

## 2. The eight systems, with status and gaps

### ✅ 1. `remember` / `recall` — the one MCP door

| | |
|---|---|
| **Where** | `mcp/plugins/estate_memory.py`, running in the `estate-mcp` pod (2/2, up 4h) |
| **What it is** | The estate's memory interface, per ADR 0006 (one MCP door). `remember` writes a structured fact; `recall` reads facts back with provenance. |
| **Status** | ✅ **OPERATIONAL — this is the estate's real memory** |
| **Evidence** | `remember` → `{'written': True, 'namespace': 'estate', 'version': 1}`; `recall` → the fact returned with its structured provenance. Driven through the real plugin code in the live pod. |
| **Gap** | `recall` matches **words, not meaning**. Its own comment: *"the server's vector search needs an embedding nobody computes yet."* So "what did we decide about deploys" misses a fact that says "rollout". |

### ✅ 2. `unified-memory-server` — the store

| | |
|---|---|
| **Where** | namespace `unified-memory`; `main.py` (584 lines) + `security_core.py` |
| **What it is** | The Postgres-backed store the door writes to. One estate Postgres (LAW). OWASP write guards, MAPLE guards, tenant/surface tokens, RLS, advisory-lock migrations. |
| **Status** | ✅ **OPERATIONAL — on-demand by design** |
| **Evidence** | `0/0` replicas with KEDA `min 1 / max 1`. It answered a live `PUT` with `200 CREATED` and a `GET` with the fact. |
| **Gap** | `main.py:390` ranks by `embedding <=> %s::vector` — **an embedding nothing writes**. The schema, guards and ranking are built and correct. Only the vector is missing. |
| **Correction** | This was previously reported as "never ran". Wrong: its Flux Kustomization declares `idp.estate.io/runtime: on-demand`. Idle is not dead — and that distinction matters, because the fix for "dead" and the fix for "idle" are opposites. |

### ✅ 3. growmos — the documentation graph

| | |
|---|---|
| **Where** | `~/Documents/code/estate-graph`, `.growmos/` |
| **What it is** | A knowledge graph derived **from documentation**. Entities, typed relations, provenance, a journal. |
| **Status** | ✅ **OPERATIONAL and genuinely used** |
| **Evidence** | 2,788 entities, 3,716 relations on disk; written to this session. |
| **Gap** | **Lexical only** — no vectors. And it indexes documents, not runtime events. It is a *different job* from the memory plane, which is why it is kept rather than folded in. |
| **Role** | Becomes an **ingest source** into `remember`, never a second store. |

### ❌ 4. `otto/memory` `fast_recall`

| | |
|---|---|
| **Where** | `otto-gateway` pods (`fast_recall.py`) |
| **Status** | ❌ **WRITE-ONLY — the estate's headline memory defect** |
| **Evidence** | `configured() == False`; `recall()` → **0 facts**. Writes fire (`fact_round_tripped stored=true`); reads never return. |
| **Gap — two independent causes** | **(a)** `fast_recall` probes `OTTO_MEMORY_DATABASE_URL` or `PGHOST`/`PGDATABASE`/`PGSERVICE`/`PGURI`; the pod sets only `OTTO_INGRESS_DB_*`. `get_dsn()` → `None` → recall is a permanent no-op. The DB is real and reachable. **(b)** `EmbeddingUnavailableError` — facts stored with no vector. |
| **Fix** | Set the DSN (one env var), and call the `embed` lane. |

### ❌ 5. `otto-memory-store-8` — the backfill Job

| | |
|---|---|
| **Where** | `otto-gateway`, 7 pods |
| **Status** | ❌ **BROKEN — 7 pods `Error`, 23 hours, restart count 0** |
| **Evidence** | No pods started at all. Its log: `read=1 written=0` then `the embedding lane refused … embedding call to the estate router failed: HTTPError`. |
| **Gap** | The Job exists to backfill embeddings. It calls the embed lane, the lane refuses, the Job dies. **The Job is eighth rename** — the yaml documents failed attempts at `-1`, `-5`, `-7`. |

### ❌ 6. Hindsight

| | |
|---|---|
| **Where** | namespace `hindsight`, `hindsight-api` (1/1, up 24 days) |
| **Status** | ❌ **IDLE — running, never called** |
| **Evidence** | Pod healthy 3d21h (deployment 24d, 1/1). **24h of logs contain zero `retain`/`recall` calls.** It consolidates nothing. |
| **Gap** | Nothing routes to it. `estate_memory.py` moved off it to unified-memory on 2026-09-29. It is still wired into `hermes-agent` via `HERMES_HINDSIGHT_URL` — a URL alone makes the plugin *available*, and nothing uses it. |
| **Verdict** | **Retire.** It is the estate's named memory layer from 2026-09-05 that has never been asked a question. That is a cost with no return, and it is the second store §6 forbids. |

### ❌ 7. The memory plugins in `hermes-agent`

| | |
|---|---|
| **Where** | the `hermes-agent` image + `hermes-agent` gateway config |
| **What** | byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory (+1) |
| **Status** | ❌ **CODE ONLY — no evidence any is enabled** |
| **Evidence** | `gateway.yaml` wires **only** `HERMES_HINDSIGHT_URL`. No config selects any other plugin. |
| **Gap** | Nine vendors' worth of code shipped in an image, zero of it in use. |
| **Verdict** | **Delete from the image** after confirming nothing imports them. Every one is a future "we have all these memory systems" — the exact sentence this document exists to stop. |

### ⏳ 8. Cortex

| | |
|---|---|
| **Where** | not installed. `crates.io/crates/cortex-memory-core` v0.3.1, MIT, 19,066 Rust lines, 42 docs read. |
| **Status** | ⏳ **ADOPTED — as the engine, not as a store** |
| **What it brings** | Hybrid search (vector + graph) replacing word-matching; the 5-signal **computed trust**; `valid_at` **temporal filtering** ("what did we know in January?"); **per-kind schema validation** at write; **decay/consolidation**; NATS ingest off the estate bus. |
| **What it must NOT bring** | **Its own database.** redb beside the one estate Postgres would be a second store of record — the AGENTS.md §6 duplication. Its redb mode is for the laptop/offline shape only. |

---

## 3. The single root cause, and why it is good news

Four of the five broken systems fail for one reason. The chain is:

```
a fact is written
   → the store ranks by vector: embedding <=> %s::vector
   → NOBODY COMPUTES THE VECTOR
   → the row is stored with embedding = NULL
   → recall returns nothing
   → stored=true, retained=true, recall=0
```

**The good news is what this is not.** It is not a missing capability, a wrong architecture, or a
vendor problem. Measured:

| Component | State |
|---|---|
| The store, the schema, the RLS, the guards | ✅ built and correct |
| The ranking query (pgvector cosine) | ✅ built and correct |
| The MCP door and its structured format | ✅ built and correct |
| The embedding lane in LiteLLM (`embed` → `text-embedding-3-small`, 1536-dim) | ✅ configured, keyed, ordered first |
| **Something that calls the embedding lane on write** | ❌ **missing — 0 requests in 48h** |
| **Something that notices recall returning nothing** | ❌ **missing — this is why it ran for weeks** |

The estate built the entire memory machine except the hand that turns the crank, and no alarm for
when the machine runs empty.

**A note on the fallback, because it is instructive:** the `embed` lane is *correctly ordered
first*; a dead Gemini lane (`embed-fallback` — model id retired, account out of prepay) sits
behind it for the day its key returns. The router needs several seconds to walk past a refusing
hop; Otto's client gives up sooner. So Otto timed out on *every* call and wrote every fact with
no vector. **The config is right. The client's patience is too short for its own fallback chain.**

---

## 4. The Cortex plan

The goal, in one line: **the door does not move, the store does not move, and Cortex supplies the
intelligence inside them.** No agent learns a new tool; no client changes.

### Phase 0 — make the existing memory actually recall (days, not weeks)

This is the highest-value work in the entire document, and it needs no new technology:

1. **Call the embed lane on write.** `estate_memory.do_remember` computes an embedding via the
   existing `embed` lane and writes it with the fact. Same for `otto/memory`.
2. **Fix the Otto DSN.** Add `OTTO_MEMORY_DATABASE_URL` (or the `PG*` block).
3. **Backfill.** Re-run `otto-memory-store-8` once the lane is called — every existing fact gains
   its vector, and semantic recall starts working over history.
4. **Widen the client timeout** past the fallback-walk time, or reorder so a refusing hop costs
   nothing.
5. **Prove it** with `bin/memory-gate`, which already fails on a recall miss.

### Phase 1 — Cortex as the engine behind the door

With vectors present, switch the *ranking* to Cortex's engine: hybrid search (vector + graph),
5-signal computed trust, `valid_at` temporal filtering, per-kind schema validation at write, and
decay. The door, the store and the API are unchanged.

### Phase 2 — the automatic doors

- **NATS ingest** off the estate's existing JetStream bus: every event the estate already
  publishes becomes memory with no agent action.
- **Briefing on wake**: a session/task-start hook injects recall, so the agent does not have to
  choose to remember.

### Phase 3 — retire the duplicates

Delete `otto/memory`'s fast_recall path, the `otto-memory-store` Job, Hindsight, and the unused
hermes-agent plugins — **after** the Phase 0 import has proven facts move across. Until then,
nothing is deleted; the estate's rule is that nothing is deleted for living outside `idp`, and a
duplicate is only deleted once its replacement is demonstrated.

---

## 5. The gaps, stated plainly

These are the things that are missing or wrong. Each is a decision or a piece of work, not an
observation.

| # | Gap | Impact | Fix |
|---|---|---|---|
| G1 | **Nothing computes an embedding on write** | all semantic recall is dead; facts are write-only | call the existing `embed` lane in `remember` (Phase 0.1) |
| G2 | **`fast_recall`'s DSN is unset** | Otto's recall is a permanent no-op | set `OTTO_MEMORY_DATABASE_URL` (Phase 0.2) |
| G3 | **No alarm for "healthy but unused"** | Hindsight ran 24 days serving nobody; otto ran weeks write-only | `MemoryNotInUse` alert (built) + `bin/memory-gate` in CI (built) |
| G4 | **`embed-fallback` is a dead hop in front of a working lane's patience** | every Otto write times out walking past it | widen the client timeout, or reorder |
| G5 | **Two stores of record would exist if Cortex ships its redb file** | AGENTS.md §6 duplication | Cortex is the engine; one Postgres stays LAW |
| G6 | **Nine unused memory plugins ship in an image** | "we have all these memory systems" recurs | delete after confirming no imports |
| G7 | **Hindsight is up and unused** | a running pod with zero return, and a second store | retire after Phase 0 import |
| G8 | **`recall` matches words, not meaning** | misses paraphrase; "deploy" ≠ "rollout" | Cortex hybrid search (Phase 1) |
| G9 | **No temporal query** | cannot ask "what did we know in January?" | Cortex `valid_at` (Phase 1) |
| G10 | **No consolidation/decay** | the store grows monotonically | Cortex auto-linker + decay (Phase 1) |

---

## 6. How this stops being silent

The reason this ran for weeks is not that the systems were broken — it is that **nothing
measured recall**. A green pod and a `stored=true` are both true statements about a system that
cannot answer a question. Three things now exist so it cannot recur:

1. **`bin/memory-gate`** — offline it asserts the door, store, write schema and spec invariants;
   live it drives the **real plugin** in the live pod, writes a fact and reads it back, and
   **fails on a recall miss**. Proven able to fail: exit 1 when the door is absent, exit 0 when
   the fact round-trips. Wired into `bin/idp-ci` as its own rung.
2. **The `MemoryNotInUse` alert** — fires on a **flat node count for 6h**. That is the Hindsight
   failure expressed as a number: the process is healthy and nobody is using it.
3. **`MemoryRecallEmpty`** — fires when the store holds facts but serves no briefings. That is the
   2026-10-02 signature exactly.

---

## 7. What to do next, in order

1. **Phase 0** — turn the crank: call the embed lane on write, fix Otto's DSN, backfill, prove
   with `bin/memory-gate`. This makes the estate's existing memory actually recall, and it is the
   only step that changes what the founder experiences.
2. **Phase 1** — Cortex as the engine behind the unchanged door.
3. **Phase 2** — the automatic doors (NATS, briefing-on-wake).
4. **Phase 3** — retire Hindsight, the otto store Job, and the nine unused plugins, once the
   import has proven facts move.

**The measure of success is not "memory systems exist". It is a number the founder can read:**
facts written, facts recalled, and the gap between them. When those two numbers move together,
the estate has memory. Until then it has a log file with a schema.
