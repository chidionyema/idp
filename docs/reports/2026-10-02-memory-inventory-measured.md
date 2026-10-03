# The memory inventory, measured

Date: 2026-10-02
Method: every row below was measured this turn against the live cluster and the live repos.
Nothing here is copied from a document. Where a number appears, the command that produced it
appears with it.

Companion documents:
- Decision: `docs/decisions/0036-one-memory-plane-and-it-is-cortex.md`
- Design: `docs/specs/2026-10-02-memory-plane-cortex-adoption.md`
- Gate: `bin/memory-gate`
- The `otto/memory` failure itself, measured in full:
  `docs/reports/2026-10-02-memory-layer-correction-measured.md` — not restated here.

---

## 1. The answer to the question asked

> *"I just get told we have all these memory systems but I don't have any evidence they are in
> use or being effective at all."*

Measured: **eight memory systems exist. Three do work. Five do not.** Of the five, four fail for
a single shared reason — **no embedding is ever written** — and one was misread as dead when it
was asleep by design.

## 2. Every memory system, with evidence

| # | System | Where | Measured now | Verdict |
|---|---|---|---|---|
| 1 | **`remember`/`recall` MCP tools** | `estate-mcp` pod | `written: True, version: 1` → same fact returned by `recall` with provenance | ✅ **OPERATIONAL** — the estate's real door (ADR 0006) |
| 2 | **unified-memory-server** | `unified-memory` ns | `0/0` replicas, KEDA `min 1 / max 1`; **answered a live PUT with 200 CREATED** and a GET with the fact | ✅ **OPERATIONAL** — on-demand by design (`idp.estate.io/runtime: on-demand`) |
| 3 | **growmos** | `estate-graph` repo | 2,788 entities, 3,716 relations on disk; used every session | ✅ **OPERATIONAL** — but lexical only, no vectors, docs-only source |
| 4 | **otto/memory `fast_recall`** | `otto-gateway` | `configured()==False`; `recall()` → 0; writes fire (`stored=true`), reads never | ❌ **WRITE-ONLY** — memory that cannot be read |
| 5 | **`otto-memory-store-8` Job** | `otto-gateway` | **7 pods `Error`, 22–23h**, restart 0 (they never ran) | ❌ **BROKEN** — embed lane refuses |
| 6 | **Hindsight API** | `hindsight` ns | pod Running 3d21h; **24h logs: 0 lines matching retain/recall/POST/GET** | ❌ **IDLE** — up, never called |
| 7 | **9 plugins in hermes-agent** | image | byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory, +1 — no evidence any is enabled | ❌ **CODE ONLY** |
| 8 | **Cortex** | — | not installed; crate v0.3.1, MIT, 19,066 Rust lines, 42 docs read | ⏳ **to be adopted as the engine** |

**Effective memory systems: 3 of 8.** One of those three (growmos) cannot do semantic recall.

For the `otto/memory` rows in full — the DSN root cause, the verbatim `EmbeddingUnavailableError`,
and why the earlier "cortex duplicates a working layer" argument does not hold — see
`2026-10-02-memory-layer-correction-measured.md`. That measurement stands; this report adds the
systems it did not cover (the one door, the unified store, and Cortex), and the corrected
decision that follows from finding the door working.

## 3. The root cause, singular

Five of the six non-working systems fail for **one** reason. Evidence:

| System | The evidence it is the embedding |
|---|---|
| `unified-memory-server` | `main.py:390` ranks by `embedding <=> %s::vector` — nothing computes the embedding it compares against |
| `estate_memory.py` | `mentions()` matches words instead; its own comment: *"the server's vector search needs an embedding nobody computes yet"* |
| `otto/memory` | raises `EmbeddingUnavailableError` — *"embedding call to the estate router failed: TimeoutError"* |
| `otto-memory-store-8` | the Job whose single purpose is to backfill embeddings; every pod `Error` |

**The stores, the schema, the door, the guards and the auth are all built and correct. The
vector is missing.** That is one defect, not six, and it is the first thing to fix.

The estate's real local-embedding path already exists: **`edge-runtime` ships pure-Rust
`candle` + `tokenizers`, no ONNX fetch.** Nothing needs to be invented; it needs wiring.

## 4. Corrections made during this measurement

Recorded because both were errors caught by measuring, and both are the §3 defect —
asserting from a document instead of measuring the thing.

1. **`unified-memory-server 0/0 replicas` was reported as "never ran".** Wrong. Its
   Flux Kustomization declares `idp.estate.io/runtime: on-demand`; KEDA scales to zero between
   calls. The live probe proved it wakes and answers. Idle is not dead.
2. **A raw `PUT /memories/{ns}/{key}` returned 422, and the plugin was blamed.** Wrong. The
   server's `MemoryWritePayload` requires `namespace` and `key` **in the body**; the plugin sends
   them. The hand-rolled probe did not. The plugin was correct; the probe was broken. A gate
   built on that probe would have graded the probe, not the system.

## 5. What this changes

- **Cortex is adopted as the engine, not as a second store.** The door (`remember`/`recall`) and
  the store (unified memory server on the one Postgres) stay. Substituting a redb file beside
  Postgres would be the §6 duplication, and one Postgres is LAW.
- **The embedding is the first deliverable**, because until it exists none of Cortex's retrieval
  features — hybrid search, trust ranking, `valid_at` — are reachable.
- **`bin/memory-gate` exists so this can never be silent again.** It fails on a recall miss and
  on an unconfigured door. Proven: it exits 1 when the door is absent, exits 0 when the fact
  round-trips.
- **The alert is `CortexNotInUse`** — fires on a flat node count, i.e. a healthy system nobody
  uses. That is the Hindsight failure expressed as a number.
