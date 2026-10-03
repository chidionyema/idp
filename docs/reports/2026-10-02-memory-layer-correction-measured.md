# Correction: what the estate's memory layer actually does (measured), and the real cortex comparison

Date: 2026-10-02. Supersedes the memory claims in
`2026-10-02-cortex-crate-deep-dive-and-rust-crate-plan.md`, Part 2.

The founder pushed back: *"estate implementation may be there but I have no evidence it works."*
That was correct. Part 2 of the first report cited `docs/specs/otto-capability-inventory.md` — a
document — rather than measuring. That is the exact defect AGENTS.md §3 names: asserting instead
of proving. This file is the measurement.

---

## 1. What I claimed, and what is true

I wrote that two-tier memory was **LIVE** and hybrid retrieval **BUILT, store deployed**.
Measured now:

| Claim | Measurement | Verdict |
|---|---|---|
| Memory writes happen on real traffic | `{"component":"memory","event":"memory.fact_round_tripped","stored":true,"retained":true}` in live gateway logs | **TRUE** |
| Turns are recorded | `memory.turn_recorded`, `worker.answered channel=telegram` | **TRUE** |
| Synchronous recall works | `fast_recall.configured()` → **`False`**; `recall()` → **0 facts** | **FALSE** |
| The store is deployed and populated | `otto-memory-store-8`: **7 pods in `Error`**, 22h | **FALSE** |
| Hybrid retrieval (pgvector + FTS) | embedding lane refuses every call; facts written without vectors | **NOT OPERATING** |

**The estate has a write-only memory.** Facts are stored; nothing can read them back. The
synchronous read path is a permanent no-op in the live pod.

## 2. Root cause — measured, one line of config

`otto/memory/fast_recall.py`:

```python
_LIBPQ_ENV = ("PGHOST", "PGDATABASE", "PGSERVICE", "PGURI")
def configured(config=None):
    if db.get_dsn(config): return True          # reads config.database_url_env
    return any(os.environ.get(n) for n in _LIBPQ_ENV)
```

Env actually present on the live gateway (`kubectl get deploy otto-gateway -o jsonpath`):

```
OTTO_INGRESS_DB_HOST/PORT/NAME/USER/PASSWORD_FILE   ← set
OTTO_MEMORY_EMBEDDING_URL/MODEL/DIM/TIMEOUT_S       ← set
OTTO_MEMORY_HINDSIGHT_URL, OTTO_MEMORY_BANK         ← set
PGHOST / PGDATABASE / PGSERVICE / PGURI             ← NOT SET
OTTO_MEMORY_DATABASE_URL                            ← NOT SET
```

The database is real and reachable — the ingress container points at
`estate-rw.estate-db.svc.cluster.local`, database `otto_gateway`, user `otto_gateway`. The
memory layer simply was never given those values under the names it looks for. So
`get_dsn()` returns `None`, the libpq fallback finds nothing, and recall is a no-op.

**This is not a missing capability. It is one env var, or one `PG*` block, away from working.**

## 3. The second failure, independent

`otto-memory-store-8` pod log, verbatim:

```
already up to date
read=1 written=0 already_present=0 empty=0 failed=0
ERROR:__main__:the embedding lane refused f2bb5257-...: embedding call to the estate router failed: HTTPError
```

Seven Error pods, 22 hours. The Job is on its **eighth rename** — the yaml itself documents
failed attempts at `-1`, `-5`, `-7`, and contains the comment *"It is not any more. Measured
2026-09-08 … 200 OK."* That comment is stale as of today; the lane is refusing again. A
comment asserting a past measurement is not a monitor.

The live gateway shows the same failure on the request path:

```
otto.memory.embeddings.EmbeddingUnavailableError:
  embedding call to the estate router failed: TimeoutError
```

Independent third failure in the same log stream:

```
{"event":"otto.obs.export_failure","state":"unhealthy",
 "exports_ok":0,"export_failures":4,
 "last_error":"ConnectTimeout(signoz-otel-collector.observability.svc:4318)"}
```

Every span export is failing. The estate's "every turn is a trace" claim is also not operating.

## 4. What this changes about the cortex question

**Honestly: it weakens my original argument, and the founder is right to press.**

I argued "cortex duplicates a working estate layer." The layer is **not** working. The
argument "you already have this" is much weaker when the thing you have is write-only and
its store has failed eight times.

But the correct response is not "adopt cortex." Measured reasons:

1. **Cortex would have inherited the same broken embedding lane.** Cortex's `briefing` and
   `hybrid search` also need embeddings. `fastembed` downloads ONNX + a model at container
   start. In a cluster whose embed lane already times out and whose observability collector
   is unreachable, a crate that needs a model fetch to boot does not fix the failure — it
   moves it.
2. **The estate's failure is configuration, not capability.** One env var restores recall.
   Adopting a second memory system does not restore the first; it adds a second thing that
   is also unconfigured.
3. **Cortex has no provenance model.** The estate's genuinely valuable asset here is
   `Provenance` + taint marking on untrusted input (AGENTS.md §0 gate 7, §3). Cortex derives
   confidence from topology. Swapping them loses the trust boundary the estate actually
   needs.

Where I was wrong, plainly: I graded a proxy (an inventory document) instead of the thing
itself (a recall call). You were right.

## 5. Revised recommendation

**Fix the estate's memory before adopting anything.** In order:

1. **Set the DSN.** Add `OTTO_MEMORY_DATABASE_URL` (or `PGHOST`/`PGDATABASE`/`PGUSER`) to the
   gateway deployment pointing at the same `otto_gateway` database the ingress already uses.
   Prove with `fast_recall.configured() == True` and a non-zero `recall()` — a real fact read
   back, not a green deploy.
2. **Fix the embed lane** (the `-8` Job / router timeout). Until it answers, every fact is
   vectorless and hybrid search cannot work, whatever the backend.
3. **Add a gate that fails.** A `/health/memory` probe or a scheduled recall assertion that
   goes red when `configured()` is False or recall returns empty. The reason this went
   unnoticed for 22 hours is that nothing measures it. A gate that cannot fail is not a gate.
4. **Then, and only then, evaluate cortex** against a *working* baseline — with a measured
   delta, per §0 gates 3 and 4. If it wins on a benchmark against a live store, that is a
   real decision. Right now there is no baseline to beat.

I am not withdrawing the crate-leverage plan (Part 4 of the first report). `secrecy` +
`zeroize`, `gix`, `blake3`, `tracing` and the rest stand on their own, and leaning into crates
is the right instinct. What I am withdrawing is the specific claim that the estate's memory
layer already makes cortex redundant. It does not — because it does not work yet.

## 6. Measurement log

| Command | Result |
|---|---|
| `kubectl get pods -A \| rg otto` | `otto-memory-store-8` ×7 `Error` 22h; `otto-registration-reconciler` `Error` |
| `kubectl logs otto-memory-store-8-5cvfb` | `the embedding lane refused … HTTPError` |
| `kubectl logs deploy/otto-gateway -c gateway \| rg memory` | `fact_round_tripped stored=true`, `turn_recorded`, `EmbeddingUnavailableError: TimeoutError` |
| `fast_recall.configured()` (in-pod) | **`False`** |
| `fast_recall.recall("estate")` (in-pod) | **`0`** |
| `env \| rg '^PG\|OTTO_MEMORY\|DATABASE_URL'` | no `PG*`, no `OTTO_MEMORY_DATABASE_URL` |
| `OTTO_INGRESS_DB_HOST` | `estate-rw.estate-db.svc.cluster.local`, db `otto_gateway` |
| `obs.export_failure` | `state: unhealthy, exports_ok: 0` |

Not measured: whether any historical fact predating this deployment is recallable, and the
current state of the `otto_facts` table (the container lacked `psycopg2` and I did not
install it into a production pod). Both are the next measurement, and step 1 above produces it.
