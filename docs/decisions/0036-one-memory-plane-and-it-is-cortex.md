# 0036 — One memory plane: the unified memory server, with Cortex as its retrieval engine

Date: 2026-10-02 (revised the same day, after measurement)
Status: accepted (founder: *"we are adopting crate and using every feature available that is
useful"*)
Supersedes in part: `docs/specs/hosted-session-memory.md` (2026-09-05), which named Hindsight as
the estate's memory layer.
Related: 0006 (one MCP door), 0023 (boundary enforced by infrastructure), 0030 (unified
confidence service), `docs/specs/2026-10-02-memory-plane-cortex-adoption.md`

---

## Revision note (read this first)

The first version of this decision said Cortex **replaces** the estate's memory systems. That was
written before measuring them, and one measurement overturned it:

```
remember  ->  {'written': True, 'namespace': 'estate', 'key': 'measurement.memory-gate.c736d73e5d9bf801', 'version': 1}
recall    ->  fact returned, with its structured provenance
```

Run 2026-10-02 inside the live `estate-mcp` pod, through `mcp/plugins/estate_memory.py` — the
real code, not a description of it. **The estate already has a working unified memory**, behind
`remember`/`recall` on the one MCP door, on the one estate Postgres. Deleting it to install a
second store would have been AGENTS.md §6 stitching, committed by the person citing §6.

The corrected decision is below. Cortex is still adopted — the founder's instruction stands, and
its engine is genuinely better than what is there. But it is adopted as the **retrieval engine
under the existing door**, not as a rival plane.

## Context

On 2026-09-05 the founder recorded that memory would be *hosted and sold, never a store on a
machine*, and that **Hindsight remains the estate's memory layer** reached through the one MCP
door. That decision assumed the layer worked. Measured 2026-10-02:

- `otto/memory/fast_recall` — `configured() == False`, `recall() == 0`. Facts written, never
  readable. **Write-only memory.**
- `Hindsight` — pod up 3d20h; **24 hours of logs contain zero requests** (3,457 lines, all
  `WORKER_STATS`). The estate's named memory layer has never been called.
- `unified-memory-server` — 0 replicas **by design** (KEDA scale-to-zero,
  `idp.estate.io/runtime: on-demand`). It wakes on demand and answers: `remember`/`recall` above
  are that server. It is not dead; it was asleep and no one had knocked.
- Seven further memory plugins in the `hermes-agent` image with no evidence any is enabled.

**The one defect every broken memory system shares is the missing embedding.**
`unified-memory-server/main.py:390` ranks by pgvector cosine (`embedding <=> %s::vector`), but
nothing in the estate computes an embedding and writes it — which is why
`estate_memory.py:mentions()` falls back to word-matching (its own comment: *"the server's vector
search needs an embedding nobody computes yet"*), and why `otto/memory` raises
`EmbeddingUnavailableError`. Same root cause, two systems.

## Decision

**One memory plane, reached through one door, with Cortex as the retrieval engine inside it.**

- **The door does not move.** `remember`/`recall` stay exactly where they are, on `estate-mcp`,
  per ADR 0006. No agent learns a new tool; no client changes.
- **The store stays** the unified memory server on the one estate Postgres. One Postgres is LAW.
- **Cortex supplies what the store lacks**, as a library inside that server's write and read
  path: hybrid search (vector + graph, replacing word-matching), the 5-signal computed trust,
  `valid_at` temporal filtering, per-kind schema validation at write, and decay.
- **Cortex does not bring its own database.** redb would be a second store of record beside
  Postgres — the exact duplication §6 forbids. Its redb/HNSW binary remains for laptop-local
  and offline use, which is a deployment, not a second plane.
- **The missing embedding is the first thing built.** Until an embedding is written on every
  `remember`, every other Cortex feature is unreachable. `edge-runtime` already ships `candle`
  and `tokenizers` — pure Rust, no ONNX fetch — and is the estate's real local-embedding path.

### Why Cortex's engine, over what is there now

| Requirement | Cortex | unified-memory-server today | otto/memory | Hindsight |
|---|---|---|---|---|
| Semantic recall over prose | HNSW + vectors | pgvector present, **no embeddings written** | built, unconfigured | yes |
| Computed trust from topology | 5-signal formula | `trust_tier` string | no | no |
| Temporal validity + `valid_at` query | yes | `valid_from` only | no | partial |
| Per-kind schema validation at write | `[schemas.*]` | MAPLE/OWASP guards | no | no |
| Consolidation / decay | auto-linker + decay | `curation_worker.py` | no | worker |
| NATS ingest (estate bus) | first-class | no | no | no |
| Evidence it is used | — | **written and recalled 2026-10-02** | **0 recalls** | **0 requests/24h** |

### Why this is not "a second memory platform"

`hosted-session-memory.md` said a second memory *platform* would be stitching. Correct. So this
decision **removes**, it does not add:

- `otto/memory/fast_recall.py` and `otto_facts` — **deleted**; its writes move to `remember`.
- The `otto-memory-store` Job — **deleted**; the embed lane it calls is broken.
- Hindsight — **retired**; consolidation moves to the Cortex engine.
- The seven unused plugins — **deleted** from the image.

`growmos` is **kept**, with a named different job: it derives the graph from documentation, which
none of the above do. It becomes an *ingest source* into `remember`, not a second store.

## Consequences

**Positive.** One place facts live; recall that works and is measured; trust and provenance
visible; the founder can ask "is memory being used" and get a number; no agent learns a new
interface.

**Negative, accepted.**
1. **Embedding latency lands on the write path.** Mitigated: embeddings computed locally in
   `edge-runtime` (candle), and the write must never fail the agent's task — a missing embedding
   is a degradation, not an error (§ fail-open, loudly).
2. **Cortex is Rust inside a Python service.** Mitigated: it is a library call at the write and
   search boundary, not a rewrite of the server.
3. **Bus factor 1** upstream (Mike Darlington). Mitigated by vendoring and pinning.
4. **A new failure mode — memory looks healthy and recalls nothing.** Mitigated by
   `bin/memory-gate`, which fails on an empty graph and on a recall miss, and by the
   `CortexRecallEmpty` alert.

## Enforcement

`bin/memory-gate` (`--check` offline, no flag live), wired into `bin/idp-ci` and run on a
schedule, fails when:

- the memory plane is unreachable, or
- a written probe fact is not returned by `recall`, or
- a probe on an empty store is reported healthy (the 2026-10-02 signature), or
- the probe's write is missing from the audit log.

A memory layer that cannot fail this gate is not deployed. This is the artifact that would have
caught the 2026-10-02 incident on day one.
