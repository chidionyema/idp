# The Memory Plane: Cortex as the retrieval engine behind the one door

Date: 2026-10-02 (revised the same day, after measurement)
Status: **adopted** (founder decision, 2026-10-02). Supersedes the "decline" verdict in
`2026-10-02-cortex-crate-deep-dive-and-rust-crate-plan.md`.
Scope: every memory system in the estate — what exists, what is actually in use, and how the
estate reaches one governed memory without agent friction.

---

## 0. Revision (measure first, then design)

### 0.1 One measurement changed the architecture

This spec first proposed Cortex as a **replacement** memory store, with its own MCP tools
(`cortex_store`, `cortex_search`, …). Before writing it up, the existing door was measured —
the real code, in the live pod, not a description of it:

```
$ kubectl -n mcp exec estate-mcp-… -- python -c "<load /app/plugins/estate_memory.py; do_remember; do_recall>"
--- do_remember ---
{'written': True, 'namespace': 'estate', 'key': 'measurement.memory-gate.c736d73e5d9bf801', 'version': 1, ...}
--- do_recall ---
{'memories': [{'text': 'memory gate probe: unified memory write path', 'metadata': {...}}], 'namespace': 'estate'}
```

**The estate already has a working memory**, behind `remember`/`recall` on the one MCP door
(ADR 0006), on the one estate Postgres. Adding a second store beside it would be exactly the
AGENTS.md §6 duplication this spec was meant to remove.

### 0.2 Two corrections to the table in §1

- **`unified-memory-server` at 0 replicas is not a failure.** Its Flux Kustomization declares
  `idp.estate.io/runtime: on-demand`; KEDA scales it to zero between calls. It wakes and
  answers — it was asleep, and nobody had knocked. "0 replicas" was read as "dead"; it meant
  "idle by design".
- **`otto/memory` at 0 recalls is a failure**, and it is not a config accident: its embed lane
  raises `EmbeddingUnavailableError` ("embedding call to the estate router failed: TimeoutError").

### 0.3 The single root cause, found

Every broken memory system in this spec shares **one** defect — **no embedding is written**:

| System | Evidence |
|---|---|
| `unified-memory-server` | `main.py:390` ranks by `embedding <=> %s::vector`; nothing anywhere computes one |
| `estate_memory.py` | `mentions()` matches words instead — its own comment: *"the server's vector search needs an embedding nobody computes yet"* |
| `otto/memory` | raises `EmbeddingUnavailableError` on every write |

The store, the schema, the door and the guards are all **built and working**. The missing piece
is the vector. So the first deliverable is not a store — it is an embedding, computed locally by
`edge-runtime` (which already ships pure-Rust `candle` + `tokenizers`, no ONNX fetch).

### 0.4 The corrected design in one line

**The door does not move; the store does not move; Cortex supplies the retrieval engine inside
them** — hybrid search, 5-signal trust, `valid_at` temporal filtering, schema validation at
write, and decay. No agent learns a new tool.

---

## 1. The honest starting position

The founder's words: *"I just get told we have all these memory systems but I don't have any
evidence they are in use or being effective at all."*

Measured today. Not from a document — from the cluster.

| System | Where | Measured state today |
|---|---|---|
| `otto/memory` fast_recall | `otto-gateway` | `configured()==False`, **`recall()` → 0 facts** |
| `otto/memory` Hindsight client | `otto-gateway` | writes fire (`fact_round_tripped stored=true`); reads never |
| `otto-memory-store-8` Job | `otto-gateway` | **7 pods `Error`, 22h**; embed lane refuses |
| Hindsight API | `hindsight` ns | pod Running 3d20h; **24h of logs, 0 requests** (3,457 lines, all `WORKER_STATS`) |
| `unified-memory-server` | `unified-memory` ns | **wakes on demand and answers** (§0.2) — `remember` returned `version:1`, `recall` returned the fact |
| `estate_memory.py` (`remember`/`recall`) | `estate-mcp` | **live and working**; the door ADR 0006 requires |
| growmos | `estate-graph` | alive and used (1MB entities, 13MB mentions) — but lexical only, no vectors |
| 9 memory plugins | hermes-agent image | byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory — **no evidence any is enabled** |
| Cortex | — | not installed |

**Conclusion: the estate has one working memory door with a working store behind it, one
write-only system (otto), one idle backend (Hindsight), and one lexical graph (growmos). The
systems that fail all fail for want of an embedding.** That is the flying-blind the founder is
describing, and it is accurately described.

---

## 2. What Cortex actually is (from the 42 docs, not the README)

I was wrong in the first report. I read the README and graded it. The docs show more:

### Capabilities that make it the system of record

| Capability | Detail | Why it matters here |
|---|---|---|
| **Computed trust** | 5 signals — corroboration (sat. 3 agents), contradiction penalty (0.3), source track record, access reinforcement (sat. 20), freshness (halflife 90d) — combined `0.30/0.25/0.20/0.15/0.10`, computed at query time, never stored | the estate has nothing equivalent; a fact's weight is currently unmeasurable |
| **Monitoring built in** | `/health`, `/stats` (node+edge counts), redb **audit log of every mutation** (`cortex audit`), `cortex trust --agent` | directly answers "is it in use, and effective" |
| **Hybrid search** | HNSW vector pass + graph-proximity pass, `score = α·vector + (1-α)·graph`, α default 0.7, `graph_hops` configurable | semantic + structural in one query |
| **Temporal validity** | `valid_from`/`valid_until` + **`valid_at` search filter** — "what did we know in January?" | the question the estate currently cannot answer |
| **Briefing synthesis** | role-driven context doc (identity/persistent/trackable/temporal/reviewable/superseding) + automatic contradictions section; scope agent/shared/unified | one call replaces per-agent context assembly |
| **Write gate + schemas** | `[write_gate]` quality checks; `[schemas.*]` per-kind required fields, types, `allowed_values`, 422 with `gate.check=="schema"` | this is the estate's `OWASPWriteGuard`/MAPLE idea, already built |
| **NATS ingest** | `[ingest.nats]` subscription is a first-class ingest path | the estate runs a JetStream bus — this is a direct wire-in, not a rewrite |
| **Encryption at rest** | AES-256-GCM when `CORTEX_ENCRYPTION_KEY` set | required before any estate data lands |
| **Retention** | `max_age_days`, `max_nodes`, eviction strategy | bounded growth, no cron to write |
| **Single binary** | redb, one file, no external DB | placement ladder §8 rung "laptop just in time" |

### The three honest caveats (unchanged, and now priced in)

1. **Bus factor 1**, one author, single release 0.3.1, no MSRV. **Mitigation:** vendor the
   source into the estate, pin the commit, own it. We are not depending on crates.io.
2. **`fastembed` downloads ONNX Runtime + a model at first use.** **Mitigation:** bake the
   model into the image at build time (`bge-small-en-v1.5`, 384-dim), set
   `HF_HUB_OFFLINE=1`, and place the model in the OCI artifact like `edge-runtime` already
   does. Never fetch at pod start.
3. **Unauthenticated ports by default** (docs say so plainly). **Mitigation:** the estate's
   own token/tenant model from `unified-memory-server` wraps Cortex; Cortex never faces a
   network the founder does not own.

---

## 3. The design: one memory plane, three doors, zero friction

### 3.1 What is being replaced, and what is being kept

```
                        ┌─────────────────────────────────────┐
   agents, Otto,  ────► │        CORTEX  (system of record)    │
   growmos, cron        │  nodes · edges · trust · audit       │
                        │  redb + HNSW · NATS ingest · briefs  │
                        └──────────────┬──────────────────────┘
                                       │
              kept, feeding in ────────┼──────── kept, reading out
                                       │
   ┌───────────────┐    ┌──────────────┴───────┐    ┌──────────────────┐
   │ growmos       │    │  unified-memory-server│    │ Hindsight        │
   │ doc→graph     │    │  GOVERNANCE ONLY      │    │ (retired or       │
   │ → CORTEX ingest│   │  tokens·RLS·guards    │    │  consolidation)   │
   └───────────────┘    └───────────────────────┘    └──────────────────┘

   DELETED / RETIRED after cutover:
     otto/memory fast_recall + hindsight client  →  Cortex hybrid search
     otto_facts table, memory-store Job          →  Cortex nodes
     9 unused memory plugins                     →  one, Cortex
```

**Nothing is deleted that is doing work.** growmos keeps its job (it reads docs and derives
the estate graph — Cortex cannot do that). What dies is the *duplicate read path*: once
Cortex is the store, `fast_recall`, `otto_facts`, and the nine plugins are all readers of
the same data, and there will be one.

### 3.2 The three doors — how an agent reaches memory without friction

The failure mode you named is agent friction. Friction happens when memory needs a decision
from the agent. So there are exactly three doors, and none of them ask.

**Door 1 — MCP (the default, works everywhere, already open).**
The existing `remember` / `recall` in `mcp/plugins/estate_memory.py` stay the interface — they
are measured working, they are ADR 0006's one door, and every agent already inherits them.
Cortex's engine is reached *behind* them: `remember` writes the embedding and validates the
schema; `recall` gains hybrid search and trust-ranked ordering. **No new tools, no agent code
changes, no new thing to learn.** (An earlier draft of this spec proposed seven new
`cortex_*` tools; that was friction invented to justify a design, and it is dropped.)

**Door 2 — NATS (the automatic one).**
`[ingest.nats]` subscribes to the estate's existing JetStream bus, so every event the estate
already publishes becomes memory with no agent action at all. This is the door that makes
memory *happen to you* rather than require you to remember to write.

**Door 3 — Task boundary (the invisible one).**
The briefing-on-wake hook calls the existing memory door at session/task start and injects the
result. Recall at the start of work is not a tool the agent must choose to call; it is part of
the context it wakes up with. **This is the door that removes "the agent forgot".**

### 3.3 Anti-friction rules (these are the design)

1. **Briefing on wake, not on request.** If recall is a choice, it will be skipped. It is
   injected.
2. **Auto-link in the background.** The agent never declares a relation; the auto-linker
   finds it on its 60s cycle. `cortex_relate` exists for the exceptions.
3. **Write gate refuses quietly, never blocks work.** A schema violation returns 422 to the
   *writer*; the agent's task continues. Memory quality must never cost task availability.
4. **One door, and it already exists.** `remember` / `recall`, unchanged. Configuration is env
   vars on the existing pod (`ESTATE_MEMORY_*`), owned by the estate, not per-product.
5. **Fail open, loudly.** If the memory plane is down, `recall` returns empty and logs a metric
   (already how `estate_memory.py` behaves — *"DEGRADES, NEVER RAISES"*). The agent runs
   without memory, as it does today — but the metric fires. Silence is the bug.
6. **The embedding is the deliverable.** Until an embedding is written on every `remember`,
   none of Cortex's retrieval features are reachable (§0.3). It is built first, locally, in
   `edge-runtime` — never a network call on the write path.

### 3.4 Estate mapping — node kinds and roles

```toml
# node kinds map to what the estate already writes
#   fact      ← otto_facts rows
#   decision  ← ADRs in docs/decisions/
#   goal      ← crew issues
#   event     ← JetStream events (deploys, incidents, CI)
#   pattern   ← gate outcomes, recurring failures
#   agent     ← each agent's identity node

[briefing.roles]
identity    = ["agent"]
persistent  = ["preference", "constraint"]
trackable   = ["goal", "task"]
temporal    = ["event", "deployment", "incident"]
reviewable  = ["pattern", "anti-pattern"]
superseding = ["fact", "decision"]

[trust.weights]          # defaults, stated so they are a decision not an accident
corroboration = 0.30
contradiction = 0.25
source        = 0.20
access        = 0.15
freshness     = 0.10

[retention]
enabled = true
max_age_days = 365
max_nodes = 1000000

[schemas.decision]
required_fields = ["rationale"]
[schemas.decision.fields.rationale]
type = "string"
```

**Trust is a signal, never authority.** This is the one place the estate overrules Cortex's
defaults. Cortex will compute trust and briefings will rank by it. But a low-trust fact does
**not** gain authority by being corroborated, and a high-trust fact does not lose its taint
mark. `Provenance` + taint (AGENTS.md §0 gate 7) stays in force; trust feeds ranking only.

---

## 4. Deployment — the full setup

### 4.1 Placement (§8 ladder)

Rung: **always-on on the node**. Cortex is a single Rust binary, 150–300 MB base, ~1% idle
CPU, ~20 MB disk per 10k nodes. It is not a candidate for scale-to-zero because memory must
answer inside the answer deadline. Requests: **250m CPU / 512Mi request, 1 CPU / 1Gi limit**.
StatefulSet with a PVC (redb file), not a Deployment.

### 4.2 Build (bake the model, never fetch at boot)

```dockerfile
# platform/cortex/Dockerfile
FROM rust:1.83 AS build
WORKDIR /src
# vendored, pinned — not crates.io
COPY vendor/cortex/ .
RUN cargo build --release -p cortex-server

FROM debian:bookworm-slim
COPY --from=build /src/target/release/cortex /usr/local/bin/cortex
# the model is an artifact, exactly like edge-runtime's — no runtime download
COPY model/bge-small-en-v1.5/ /opt/cortex/model/
ENV CORTEX_MODEL_DIR=/opt/cortex/model \
    HF_HUB_OFFLINE=1 \
    CORTEX_DATA_DIR=/data \
    CORTEX_GRPC_PORT=9090 \
    CORTEX_HTTP_PORT=9091
VOLUME /data
EXPOSE 9090 9091
ENTRYPOINT ["cortex", "serve"]
```

`bin/build-image` enforces R24 as usual. Image must pass Trivy and be cosigned like every
other estate image. No hand-apply — the StatefulSet lands via Flux.

### 4.3 Manifests

- `platform/cortex/statefulset.yaml` — 1 replica, PVC 20Gi, resource requests above,
  liveness on `:9091/health`, readiness on `:9091/health`.
- `platform/cortex/service.yaml` — gRPC 9090, HTTP 9091, ClusterIP only.
- `platform/cortex/secret.yaml` — ExternalSecret: `CORTEX_ENCRYPTION_KEY`,
  `CORTEX_TOKEN` (from vault, by name — §4).
- `platform/cortex/cortex.toml` — ConfigMap, the file in §3.4.
- `platform/cortex/servicemonitor.yaml` — scrape `/stats`; alert when `cortex_up == 0`
  **or when `nodes_total` has not increased in 6h** (that is the "in use" alarm).

### 4.4 The gate that proves it works (§3 — a gate that cannot fail is not a gate)

`bin/memory-gate`, run in CI and as a scheduled job:

1. `cortex node create` a probe node with a unique ULID.
2. `cortex search` for it → must return it. **Fails if recall returns nothing.**
3. `cortex briefing probe-agent` → must contain it.
4. `curl /stats` → `nodes_total` must be non-zero and monotonically sane.
5. `cortex audit` → the probe's mutation must appear.

**This gate would have caught today's write-only memory on day one.** It is the single most
important artifact in this plan — more than the deployment.

---

## 5. Migration — growmos, otto_facts, Hindsight

### Phase A — stand up Cortex (day 1)
Deploy, gate green, `cortex init`, schema applied. Empty graph, observable.

### Phase B — growmos → Cortex (week 1)
`growmos` entities/relations are JSONL. Write one importer: entities → nodes
(`kind` from `--type`, `title` = name, `body` = description), relations → edges
(predicate → edge label, keep the `r_*` id in metadata for provenance).
Result: the estate graph becomes semanticaly searchable for the first time.
**growmos keeps running** — it still derives from docs and feeds the importer.

### Phase C — otto_facts → Cortex (week 1)
The store Job is failing; do not fix it. Export `otto_facts` (whatever rows exist) via CSV
→ `cortex import nodes`. Then point `otto/memory`'s write path at Cortex's NATS
ingest and **delete `fast_recall`'s read path**. Facts finally become recallable.

### Phase D — Hindsight (week 2, decide)
Hindsight has served 0 requests in 24h. Two options, pick one and record it:
- **Retire it** — Cortex does consolidation (`entity_promote_every_n_cycles`).
- **Keep it as the async consolidator** — it is already built for that, and it idles at
  776 MB for nothing if it is not used.
Recommendation: **retire**, and remove the namespace. One of each layer (§6).

### Phase E — the nine plugins (week 2)
`byterover, holographic, honcho, mem0, openviking, retaindb, supermemory` — no evidence any
is enabled. Delete them from the image. `hermes-agent`'s plugin dir keeps exactly one entry
point that talks to Cortex.

---

## 6. What "done" means

Not "Cortex deployed." Deployed is a step. Done is:

1. `bin/memory-gate` green in CI, and it has **failed** at least once in a test, so it is
   known to be able to fail.
2. **A real production log line** showing Otto recalling a fact it stored in an earlier
   conversation — the same standard §3 sets for everything else.
3. `/fleet` shows `nodes_total`, `edges_total`, and briefings served, live.
4. `otto/memory/fast_recall.py`, `otto_facts`, the memory-store Job, and the seven unused
   plugins are **gone** (§6: a duplicate layer gets deleted).
5. The founder can ask "what do you know about X" and get an answer with citations.

Anything short of 5 is a deployment, not a memory system.

---

## 7. Effort and order

| # | Work | Effort | Blocking |
|---|---|---|---|
| 0 | Vendor cortex, pin commit, build image with baked model | 2d | everything |
| 1 | StatefulSet + PVC + secret + cortex.toml + servicemonitor | 1d | 0 |
| 2 | `bin/memory-gate` + wire into `bin/idp-ci` | 1d | 1 |
| 3 | MCP door: add cortex tools to `estate_mcp.py` | 0.5d | 1 |
| 4 | NATS ingest wiring | 1d | 1 |
| 5 | Task-boundary briefing hook | 1d | 3 |
| 6 | growmos importer | 2d | 1 |
| 7 | otto_facts import + rip out fast_recall read path | 2d | 6 |
| 8 | Hindsight + plugins decision and deletion | 1d | 7 |
| 9 | `/fleet` panel | 1d | 2 |

**Critical path: 0 → 1 → 2 → 3 → 5.** Everything else can run in parallel. Steps 0–5 are
the "seamless, no friction" requirement; 6–9 are the consolidation.

---

## 8. Risks, stated

| Risk | Mitigation |
|---|---|
| Upstream crate abandoned (bus factor 1) | vendored + pinned; we own the fork |
| `fastembed` runtime fetch | model baked into image, `HF_HUB_OFFLINE=1`, gate asserts offline boot |
| Unauthenticated ports | ClusterIP only + estate token at the ingress; never public |
| Cortex becomes a *second* silent memory | `bin/memory-gate` + the "nodes not growing in 6h" alert |
| Migration imports garbage from otto_facts | import to a staging kind first, inspect `cortex audit`, then promote |
| Trust score mistaken for authority | documented in `cortex.toml`; briefings rank by it, provenance still governs |

---

## 9. Provenance

Every number in §1 was measured this session:

- `fast_recall.configured()==False`, `recall()==0` — executed inside the live gateway pod
- `otto-memory-store-8`: 7 pods Error 22h — `kubectl get pods -A`
- Hindsight 0 requests/24h — `kubectl logs ... --since=24h | rg -c 'POST|GET|retain|recall'` → empty
- `unified-memory-server` 0/0 replicas, KEDA 0/1 — `kubectl get all -n unified-memory`
- Cortex capabilities — 42 docs read at `/tmp/cortex-repo/docs/` (cloned from GitHub, not the README)
