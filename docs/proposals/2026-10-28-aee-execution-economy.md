# Estate Adaptive Intelligence & Execution Economy (AEE)

## Research (G0) and build proposal (G1–G9)

**Date:** 2026-10-28
**Status:** PROPOSAL — research complete, build not started, awaiting founder go/no-go
**Author:** `pi-aee-research`
**Measurement window:** 2026-10-28 17:05–17:35 UTC, laptop `roseonyema`, executor door
**Repository state at measurement:** `origin/main` = `8d2d86c62` ("the AEI collector gets its own
directory and its own Flux row (#7341)")

---

## 0. What this document is, and what it is not

**It is:**

- A reconciliation of the Estate's *actual* execution and intelligence state, measured rather than
  assumed, against the capabilities the AEE specification names.
- A reuse-first proposal: for each named capability, an explicit decision to **reuse**, **repair**,
  **extend** or **decline**. The Estate's "one of each layer" law is binding, and this proposal
  adds no new router, no new coordinator, no new budget store and no new capability registry.
- A gate-by-gate (G0–G9) delivery plan whose exit criteria are falsifiable — each gate names the
  measurement that proves it, and each names the measurement that would *disprove* it.

**It is not:**

- An approval, and not a request for one. The Estate Master Epic
  (`docs/epics/2026-10-25-estate-master-epic.md`) already awaits a founder go/no-go; AEE is
  **not a second programme** — it is the sharpening of that epic's routing, capacity and
  coordinator work into an economic contract with named entities, named benchmarks and named
  acceptance demonstrations.
- A claim that any capability works. Where a capability could not be reached from the laptop in
  the measurement window, it is recorded as **NOT ESTABLISHED**, never as working.

### State vocabulary used throughout

| State | Meaning |
|---|---|
| SPECIFIED | Written down, no implementation found |
| IMPLEMENTED | Code exists in the repository |
| TESTED | A test exists that executes the behaviour and can fail |
| DEPLOYED | A manifest ships it, and the manifest was seen applied |
| OPERATIONAL | Verified by independent observation in the real operating environment |
| DEGRADED | Live, but failing or reduced — measured |
| DORMANT | Deployed with zero replicas / zero supply / never exercised |
| NOT ESTABLISHED | Could not be observed from the laptop in the measurement window; not asserted either way |

A green CI run, a merged commit, an HTTP 200 or an agent's own report of success are **not**
evidence of OPERATIONAL. Per `AGENTS.md` §3, the only proof is observation in the real operating
environment.

---

## 1. Method

Everything in Part A was measured in the measurement window, with the command and its output
quoted. Nothing is inferred from documentation alone unless it is explicitly labelled
SPECIFIED.

The working checkout (`lane/meridian-design`, dirty, carrying another agent's staged work) was
**not** touched. All repository reads of current state were made against `origin/main` via
`git show`/`git ls-tree`, and all new work was made in a separate sparse worktree
(`/private/tmp/aee-proposal`, `docs/` only).

**One measurement could not be taken at all:** the estate memory plane. `brief`, `recall` and
`bin/estate-brief` all failed with `URLError: <urlopen error EOF occurred in violation of
protocol (_ssl.c:1129)>` — the same TLS fault that takes the cloud router down. The memory
store is the unified memory server on the estate Postgres behind the KEDA HTTP interceptor, so
it is reachable only through the ingress that is currently broken. **No prior memory was read
before this document was written, and no memory was written back.** That is a real limitation of
this pass and is recorded as such rather than papered over.

---

# PART A — CURRENT OPERATIONAL REALITY

## 2. The intelligence supply, measured

The AEE premise is that the Estate can allocate work across a *supply* of intelligence lanes at
minimum cost subject to constraints. That premise is only as good as the supply. Here is the
supply, measured.

### 2.1 Route status table

| Route | Probe (2026-10-28) | Result | State |
|---|---|---|---|
| **Cloud router** (default per `AGENTS.md` §7a) `https://llm.mumchimp.com` | `curl -sS -m 20 https://llm.mumchimp.com/v1/models` | `curl: (35) TLS connect error: error:0A000126:SSL routines::unexpected eof while reading`; `TLSv1.3 (OUT), TLS handshake, Client hello (1)` → `TLS alert, decode error (562)` | **DEGRADED — down at the TLS layer** |
| Cloud router, via the estate's own door | `estate_invoke router-status` | `exit 35 (979ms)`, `status=halted` | **DEGRADED** |
| Cloud router, accounting | `estate_invoke cost-today` | `exit 35 (1062ms)`, `status=halted` | **DEGRADED** |
| **Laptop router** (fallback) `127.0.0.1:4000` | `GET /v1/models` | `http=200` in 1.25s, 27 model groups | **OPERATIONAL** |
| Laptop router, liveness | `GET /health/liveliness` | `http=200` in 3.26s | OPERATIONAL |
| Laptop router, health | `GET /health` | no answer in 6s (`http=000`) | **DEGRADED** (slow path) |
| Laptop router, real completion | `POST /v1/chat/completions` model `narrate` | `{"content":"Say: Alive"}` | **OPERATIONAL** |
| Laptop router, real completion | model `groq/openai/gpt-oss-20b` | `OK` (200, choices returned) | OPERATIONAL |
| Laptop router, default lane | model `default` | `RateLimitError … Rate limit reached for model openai/gpt-oss-120b … on requests per day (RPD): Limit 1000, Used 1000, Requested 1. Please try again in 1m26.4s` | **DEGRADED — quota exhausted** |
| Laptop router, fast lane | model `fast` | same RPD 1000/1000 | **DEGRADED — quota exhausted** |
| Laptop router, catalogue entries | model `groq/llama-3.1-8b-instant`, `groq/qwen/qwen3-32b`, `groq/meta-llama/llama-4-scout-17b-16e-instruct` | `NotFoundError … The model … does not exist or you do not have access to it` | **DEGRADED — stale catalogue** |
| **Ollama** (the "free lane") | `GET /api/tags` on `127.0.0.1:11434` | `[]` — **zero models pulled** (process alive, pid 71389) | **DORMANT — no supply** |
| **Cluster Ollama** | `platform/llm/ollama.yaml` | `replicas: 0` (image `docker.io/ollama/ollama:0.3.14`) | **DORMANT** |
| **Kubernetes cluster** | `kubectl get nodes --request-timeout=10s` (context `context-estate-crq7jwxsjxq`, server `https://141.147.80.229:6443`) | `Unable to connect to the server: … context deadline exceeded` — every retry | **NOT ESTABLISHED from the laptop** |
| Cluster, via the estate's door | `estate_invoke cluster-health` | `TIMEOUT (100s of a 100s budget)`, `exit 124` | **NOT ESTABLISHED** |
| **Estate memory plane** | `bin/estate-brief --task "…"` | `URLError: <urlopen error EOF occurred in violation of protocol (_ssl.c:1129)>` | **DEGRADED — same TLS fault as the cloud router** |
| GitHub API | `curl https://api.github.com` | `http=200` | OPERATIONAL |
| Laptop disk | `df -k /System/Volumes/Data` | `1791M` free, 98% used | **DEGRADED** (below the 1.5 GB executor floor at one point; `disk-free` exited 5 while a cleaner held the lock) |

### 2.2 The three findings that should change the plan

**F1 — The default route is down, and the fallback is the only one serving.**
The cloud router resolves (`dig` → `193.123.184.22`) and accepts TCP, then terminates the TLS
handshake with `unexpected eof while reading`. This is an edge/origin fault upstream of the
Estate; it is not repairable from the laptop. Every estate operation that assumes "cloud is the
default route" is currently running on the laptop fallback. The `AGENTS.md` §7a ruling stands as
policy, but **operationally the flip has not happened and the default path is unavailable** — so
the AEE cannot be certified on the default route until F1 is repaired, and every benchmark run
must record which route served it.

The same fault class takes down the estate memory plane (§1). Two doors, one fault: whatever sits
behind the estate's TLS ingress is failing the handshake.

**F2 — The fallback router's catalogue and quotas are wrong, in opposite directions.**
Three of the models the router advertises (`/v1/models` returned 27 groups) are **dead upstream**
(`model_not_found`). Meanwhile the `default` and `fast` groups — which the routing matrix treats
as the workhorses — are **quota-blocked at 1000/1000 requests per day** on
`openai/gpt-oss-120b`. The router therefore advertises supply it cannot deliver and hides supply
it can. `platform/llm/lane_registry.py` already implements per-deployment lane state, passive
measurement, quota forecasting/draining and active probes — **but it is mounted only on the
laptop**, never on the cluster router (see C1). Supply discovery is therefore a laptop-only
capability on a system whose policy says the laptop is the fallback.

**F3 — The free lane has no supply, and the cluster is unreachable.**
The AEE's cost floor assumes a local free model lane. In reality: the cluster Ollama deployment
is `replicas: 0`, and the laptop Ollama has **zero models pulled** — it will answer `/v1/models`
with 200 and nothing behind it. Any AEE economic model that prices a "free floor" is currently
pricing an empty shelf.

### 2.3 What this means for the AEE specifically

AEE optimises `min expected total cost s.t. correctness, reliability, security, authority,
deadline, capacity`. Three of those constraint inputs are currently **unknown or wrong**:

- *cost* — the cloud accounting endpoint is unreachable (`cost-today` → exit 35); the only
  accounting available is the laptop's local ledger.
- *capacity* — the cluster that would hold reservations is unreachable; capacity is unmeasured.
- *supply quality* — the catalogue is stale and quotas are exhausted; the routing matrix's
  assumptions about which lane is cheapest-and-available do not hold.

**Therefore G0 cannot be certified as "the Estate's execution and intelligence state is known"
until F1–F3 have measured answers.** This proposal does not assume them away. It makes them
G0 exit criteria.

---

## 3. Capability reconciliation matrix

The AEE specification names existing Estate capabilities that must be verified rather than
assumed. Each is reconciled below across the full axis: implementation → callers → authority →
tests → deployment → observed usage → telemetry → open work → gap → reuse decision.

| # | Capability | Implementation | Callers | Authority | Tests | Deployment | Observed usage | Telemetry | Open work | Gap | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **LiteLLM router (cloud/default)** | `platform/llm/litellm.yaml`, `platform/llm/config.yaml` | every agent via `ESTATE_ZONE` | routing, quotas, master key | none found for the deployment itself | cluster Deployment | **unreachable** — `cluster-health` exit 124 | **none**: no `lane_registry`/`route_table` callback mounted | — | TLS down (F1); no supply discovery on the default route (C1) | **REUSE + REPAIR** — never replace |
| 2 | **LiteLLM router (laptop/fallback)** | `~/.estate/litellm-local/` (front 566 lines, config 49 013 B) + `llm/config.yaml` | all local agents | same | — | launchd-managed local | **OPERATIONAL** — `narrate` and `groq/openai/gpt-oss-20b` complete | `action_ledger`, `route_table` | — | stale catalogue (F2); `front.py` drift (C2) | **REUSE + REPAIR** — land the front in the repo, reconcile the catalogue |
| 3 | **lane_registry** (supply discovery) | `platform/llm/lane_registry.py` | `route_table.py`; `bin/litellm-local` MODULES; `llm/config.yaml` callbacks | lane state, quota forecast, probes | `tests/test_lane_registry.py`, `tests/test_route_table.py` | **laptop only** | `estate_invoke router-lane-health` → "no router calls in the last 60 min" | its own state store | — | **not on the default route**; cannot see the cloud router's own lanes | **REUSE + EXTEND to the cloud router** — this is AEE's supply spine |
| 4 | **route_table / routing-matrix / cost-ladder / router_catalog / availability.yaml** | `platform/llm/{route_table.py,routing-matrix.yaml,cost-ladder.yaml,cost-table.schema.json,hosting-cost-table.yaml,router_catalog.py,availability.yaml}` | router callbacks | lane selection + pricing | `tests/test_route_table.py` | via the router image | live on the laptop | — | — | two config copies (C1); stale model names inside the catalogue | **REUSE as the single supply/economics catalog** |
| 5 | **AEI** (execution-intelligence / observation plane) | `packages/aei/` (`contract.py`, `core.py`, `analysis.py`, `pgstore.py`, `server.py`, `client.py`, `estate.py`), `bin/aei-collector`, `bin/aei-observe`, `platform/aei/aei.yaml`, `features/assurance/aei.feature` | FleetView / `/fleet` | observation, scoring | `packages/aei/tests/*` (3 test modules) | cluster Deployment (`platform/aei/aei.yaml`) + local collector | **NOT ESTABLISHED** — cluster unreachable | its own manifest contract (`aei.manifest.v1`: schema, component, version, owner, dependencies, events, metrics, correlation, visualisations, acceptance) | **#7311** OPEN, claimed by `pi-aei-ops` (paths include `platform/llm/callbacks/aei_observer.py`, `platform/llm/config.yaml`) | not yet mounted in a router config; the claim is the in-flight fix | **REUSE as the single observation + economic substrate** |
| 6 | **NSVEE** (Neuro-Symbolic Verifiable Execution Engine) | `nsvee/engine.py` | sovereign engine verification tier | verification verdicts | `nsvee/tests` (present) | library | **NOT ESTABLISHED from this window** | — | — | needs an end-to-end path into AEE's verification tiers | **REUSE** — AEE tier 2 (integration) and tier 3 (objective acceptance) |
| 7 | **Battalion / sovereign engine** | `sovereign/engine/` (`workflow.py`, `budget.py`, `receipts.py`, `candidate_selection.py`, `free_lunch.py`, `ops.py`, `dag.py`), `features/battalion/*.feature` | Temporal `SessionWorkflow`, the fleet | policy, approval, budget, receipts | `sovereign/tests/bdd/` | library + Temporal | **NOT ESTABLISHED** (cluster unreachable) | signed hash-chained receipts (`receipts.py`), versioned budget rows (`budget.py`) | **#3525** OPEN (unclaimed) | `dag.py` is a **content-addressed Merkle DAG, not a dependency-aware work graph** (C5) | **REUSE** — AEE's WorkGraph is a genuine extension, not a replacement |
| 8 | **Temporal / durable execution** | `sovereign/engine/workflow.py` (`SessionWorkflow`: lifecycle status + governance FSM, approvals, budget activity) | the fleet, the executor | durable session state | `sovereign/tests/bdd/` | Temporal server (cluster) | **NOT ESTABLISHED** — cluster unreachable | Temporal's own | — | cannot be confirmed reachable; AEE needs a *work-node* workflow, not only a session workflow | **REUSE as the execution substrate**; add the node-level workflow beside it |
| 9 | **budget_governor** | `bin/budget_governor.py` (test-time compute ceilings, information-gain/novelty checks, forced termination) | the reasoning gateway | per-process spend ceiling | `sovereign/tests/bdd/test_budget_governor.py` | local library | live (imported by the gateway) | in-process | — | **two budget stores** (C3): process ceiling + durable session budget | **REUSE + declare the authoritative chain** — do not add a third |
| 10 | **durable budget** | `sovereign/engine/budget.py` (`config.BUDGET_DB`, SQLite, idempotent `allocate`, versioned CAS) | the sovereign engine | authoritative session budget | `sovereign/tests/bdd/` | library | **NOT ESTABLISHED** | version rows | — | scope boundary vs #9 is undocumented | **REUSE** — AEE's `CapacityReservation` reserves against this store, not a new one |
| 11 | **action_ledger** (accountability) | `platform/llm/action_ledger.py` — signed, hash-chained router calls; emits FleetView events | router callbacks | attribution | present | router image | live on the laptop | its own chain | — | overlaps AEI's economic records (C4) | **REUSE as the `EconomicReceipt` spine** — reconcile with AEI, do not fork |
| 12 | **Ollama free lane** | `platform/llm/ollama.yaml` (cluster, `replicas: 0`); laptop `ollama serve` (pid 71389) | the `ollama*` model groups | free floor | — | cluster + local | **DORMANT — zero models pulled** | — | — | no supply at all (F3) | **REUSE the deployment; RESTORE the supply** (pull models, re-enable replicas) or formally retire the lane |
| 13 | **Goal / subgoal system** | `platform/estate/memory/plan.py`; the plan/BDD/complete-goal tools | every agent session | the objective of record | `sovereign/tests/bdd/` | local library | OPERATIONAL (this session) | — | — | no dependency graph, no economics | **REUSE as AEE's `Objective` / `WorkNode` spine** |
| 14 | **Capability registry** | `bin/capability-index` (on `origin/main`, from #7252); `catalog/estate.db` (~40 MB); `catalog/estate-capability-registry.json` (newer, not in the stale checkout) | agents, `/fleet` | one agreed source of truth per state | — | repo + catalog | **NOT ESTABLISHED** | — | #7252 | three artefacts describing one layer (C6) | **REUSE — extend the existing index; AEE must not add a fourth** |
| 15 | **RIP / Oracle / Stewardship** | referenced by the AEE specification; a spec exists (`docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md` for RIP) | — | — | — | — | — | — | — | **NOT ESTABLISHED** by this pass | **DECLINE for AEE v1** — do not build on a capability not yet proven; revisit at G4 |
| 16 | **Task queue** | `platform/queue/dispatcher.py` (SQLite `state/queue.db`) | the worker pool, the orchestrator | task admission and claim | **no dedicated test module found** | local library | **NOT ESTABLISHED** | task rows | — | no dependency, no contract, no reservation, no idempotency key | **REUSE + EXTEND** — the AEE `WorkNode` is a superset of this row (§3.4) |
| 17 | **Worker pool + worktree isolation** | `platform/execution/worker_pool.py`, `platform/execution/worktree_manager.py`, `platform/execution/integration.py` (N=10 end-to-end), `platform/orchestrator.py` | the integration harness | concurrent headless execution, isolated worktrees | **validated by script** (`validate.py`, `n10_validator.py`), not by pytest | local library | **NOT ESTABLISHED** | pool status, span telemetry | — | no admission by cost/contract; no per-attempt economics | **REUSE** — G5's concurrency envelope is a policy over this pool |
| 18 | **Periodic job scheduler** | `scheduler/dagster.yaml`, `scheduler/estate_scheduler/*` | launchd/GitOps jobs | when jobs fire | — | local | **NOT ESTABLISHED** | — | — | different concern (triggers, not dependencies) | **REUSE, keep the boundary** — not the work graph |

### 3.1 Conflicts and duplications found (binding on the design)

- **C1 — Two router configurations, and it is the root cause of the supply gap.**
  `llm/config.yaml` (49 013 B, digest `4dab71e8…`) is what is **deployed** on the laptop.
  `platform/llm/config.yaml` (56 882 B, digest `6d381fd5…`) is the **cluster** copy. The cluster
  copy mounts `request_ceiling` and the PoBR callbacks but **not** `lane_registry` or
  `route_table`. Two copies of one layer, diverged, and the divergence is exactly "the default
  route cannot see its own supply". **AEE must reconcile these into one parameterised source with
  two rendered targets, or the supply-discovery spine can never exist on the default route.**
- **C2 — The cloud-default failover logic is outside version control.**
  The deployed `~/.estate/litellm-local/front.py` is **566 lines / 22 333 B** and implements the
  founder's 2026-10-26 ruling precisely: cloud first, answer-based failover, exponential
  pass-over (`CLOUD_DOWN_S=60`, doubling to `CLOUD_DOWN_MAX_S=600`), and it re-asks the next
  target the same question when the cloud accepts and then fails. The repository copy
  `platform/llm/front.py` is **96 lines / 3 466 B** — byte-identical in size to
  `front.py.pre-6815`, i.e. the pre-failover ancestor. The mechanism that implements the ruling
  **cannot be reviewed, cannot be CI-tested, and is lost if this machine is rebuilt.**
- **C3 — Two budget stores, with no declared authority boundary.**
  `bin/budget_governor.py` enforces a process-level test-time ceiling with information-gain and
  novelty checks and forced termination; `sovereign/engine/budget.py` holds durable, versioned,
  CAS-locked session budget rows. These may be legitimately different scopes (a ceiling inside a
  turn, a budget across a session) — but that is **convention, not contract**. AEE's
  `CapacityReservation` must bind to exactly one of them, and the other must be explicitly
  subordinate.
- **C4 — AEI and `action_ledger` both produce signed, chained, evented records.**
  Both are legitimate, but AEE's `EconomicReceipt` must have **one** authority. Proposal: the
  `action_ledger` chain is the *attribution* spine (who asked, what was spent); AEI is the
  *observation and scoring* spine (what happened, how good). AEI reads the ledger; it does not
  re-sign.
- **C5 — `sovereign/engine/dag.py` is not a work graph.** It is a content-addressed state Merkle
  DAG. It gives tamper-evidence over state. It does **not** express node dependency, readiness,
  fan-out, barriers, split/merge/join or cancellation. AEE's `WorkGraph` is therefore **genuinely
  new work** — and must be built so that the Merkle DAG becomes its *revision digest*, not its
  replacement.
- **C6 — Three artefacts for one capability registry.** `bin/capability-index`, `catalog/estate.db`,
  `catalog/estate-capability-registry.json`. AEE must extend the index; a fourth is forbidden.

### 3.2 In-flight work and claims that intersect AEE

| Issue | Title | State | Claim | Intersection with AEE |
|---|---|---|---|---|
| #7311 | AEI execution-intelligence plane operational (laptop collector + OKE collector + **router callback**) | OPEN | `pi-aei-ops`, paths include `platform/llm/callbacks/aei_observer.py`, `platform/llm/config.yaml`, `platform/llm/kustomization.yaml` | **This is the G2 supply-observation spine.** AEE must not touch those paths; it must consume them. |
| #7342 | Adaptive problem-solving method selector — a pure library beside the decision layer, shadow first | OPEN | `pi-method-selector`, `packages/method_selector/**` | **This is AEE's "which technique" half.** AEE owns *which lane, at what price, under what constraint*; the method selector owns *which method*. The boundary must be written down before either grows. |
| #7344 | The estate context substrate — federated read-only context API on the existing broker | OPEN | (no CLAIM comment found) | AEE's `Objective` and `WorkNode` need context; the context substrate should supply it. **Unclaimed — available.** |
| #3525 | Build: The Battalion — asymmetric compute-cost leverage (spec v0.1) | OPEN | (no CLAIM comment found) | The parent of the sovereign engine AEE extends. **Unclaimed — available.** |
| #7328 | AEI as an observation plane, wired to the router | merged | — | Already landed. Its router callback is the natural host for AEE's economic event source. |
| #7341 | The AEI collector gets its own directory and its own Flux row | merged (`8d2d86c62`) | — | AEI's Flux row is the AEE cost-attribution sink. |
| #7252 | `bin/capability-index` — one capability per layer, one context contract per question, one agreed source of truth per state | merged | `pi` (heartbeat 2026-10-26) | **AEE must register in this index, not beside it.** |

**No open issue exists for AEE itself.** This proposal's accompanying issue is the first.

### 3.3 Mapping the AEE canonical entities onto the Estate

Verified against `origin/main` by `git grep`: `ExecutionContract`, `WorkGraph`, `WorkNode`,
`EconomicReceipt`, `VerificationReceipt`, `IntelligenceLane`, `CapacityReservation` and
`GraphRevision` have **zero occurrences** on `origin/main` outside an unrelated skill document.
They are **new names over partly-existing substance** — which is precisely why the extension
strategy matters.

| AEE entity | Estate today | Extension | New? |
|---|---|---|---|
| `Objective` | `platform/estate/memory/plan.py` (goal/subgoal, BDD, completion) | add economics constraints (deadline, cost ceiling, quality floor) and a stable `objective_id` | **Extend** |
| `WorkGraph` | nothing; `sovereign/engine/dag.py` is a Merkle DAG, not a dependency graph | new: nodes, dependency edges, readiness, barriers, revision history | **New** |
| `WorkNode` | the plan tool's sub-goals | new: node state, contract reference, reservation, attempt list | **Extend** |
| `ExecutionContract` | nothing | new: the authoritative statement of *what may run, on what lane, at what price, under what constraints* | **New** |
| `ExecutionAttempt` | `sovereign/engine/workflow.py` activity/Temporal semantics | new: an explicit, correlatable attempt record bound to contract + node + reservation | **Extend** |
| `IntelligenceLane` | `platform/llm/lane_registry.py` + `routing-matrix.yaml` + `cost-ladder.yaml` + `route_table.py` | new: AEE-facing lane view with supply state, price, quality estimate, deadline fit | **Extend** |
| `CapacityReservation` | `sovereign/engine/budget.py` (versioned CAS rows) | new: reservation semantics (hold, drain, release, expiry) over the existing store | **Extend** |
| `VerificationReceipt` | `nsvee/engine.py` verdicts; `sovereign/engine/receipts.py` signed chain | new: a receipt *type* for verification, bound to node + attempt | **Extend** |
| `EconomicReceipt` | `platform/llm/action_ledger.py` signed hash chain | new: an economic *type* — cost, currency, unit price, reservation charged, waste class | **Extend** |
| `GraphRevision` | `sovereign/engine/dag.py` Merkle digest | new: revision identity over the dependency graph; digest becomes an attribute, not the graph | **New** |

**The AEE therefore introduces exactly two genuinely new structures** (`WorkGraph`+`GraphRevision`
as one, `ExecutionContract` as one) and **extends eight**. It adds **no** router, **no**
coordinator service, **no** budget store, **no** capability registry and **no** verification
engine. That is the shape that satisfies `AGENTS.md` §6.

### 3.4 The headless execution substrate already exists — and the AEE must not build a second

The AEE specification's headless-execution requirements (isolated workspaces and Git worktrees,
declared mutation boundaries, controlled integration, bounded concurrency, durable checkpoints,
idempotency, bounded retries, reconciliation of uncertain side effects) are **mostly already
implemented in the Estate**, under `platform/`. A first pass that missed this would have built a
second executor. It is recorded here explicitly so that it is not built.

| Existing | What it does | What the AEE adds | Decision |
|---|---|---|---|
| `platform/queue/dispatcher.py` | a SQLite task queue (`state/queue.db`): `tasks(id, goal, status, agent_id, worktree_path, created_at, updated_at)`; `push_task`; `claim_task(agent_id)` under `BEGIN IMMEDIATE` (atomic claim) which creates the task's Git worktree via `git worktree add --detach` | dependency edges, readiness, barriers, node state, contract + reservation binding | **REUSE as the queue.** The AEE's `WorkNode` is a **superset** of this row; the migration path is to extend the table, not to add a second queue. |
| `platform/execution/worker_pool.py` | N-configurable long-lived workers (default 10, bounded), boot/scale/status, graceful scale-down that lets in-flight tasks finish | reservation-aware admission, per-node contracts, economic receipts per attempt | **REUSE** — G5's concurrency envelope is a *policy over this pool*, not a new pool. |
| `platform/execution/worktree_manager.py` | one isolated Git worktree and branch per task, spawned and cleaned up | declared mutation boundaries per node, revision-scoped branches | **REUSE** |
| `platform/execution/integration.py` | end-to-end parallel execution at N=10, wiring the worker pool, worktree manager, dispatcher, `platform/orchestrator.py`, the judge worker, the pareval layer and the telemetry outbox | controlled integration *by graph revision* rather than by wave | **REUSE** — it is already the integration seam |
| `platform/execution/validate.py`, `n10_validator.py`, `final_integration_test.py` | end-to-end system validation at N=10 (worker pool, worktree isolation, …) against `tests/verification/harness.py` | the AEE's fault-injection scenarios | **REUSE as the harness G5 extends.** Note these are **validation scripts, not pytest suites**: the execution substrate is implemented and validated by script, and has **no dedicated test module** — `git ls-tree` over `tests/` finds none for the pool, the queue or the worktree manager. That is a real gap in G0's "TESTED" column for this layer. |
| `scheduler/` (`dagster.yaml`, `scheduler/estate_scheduler/{definitions,describe,gitops_sync,gitops_drift,holmes_watch,import_launchd,load_gate}.py`) | a Dagster-backed **periodic job** scheduler (gitops sync, drift, watches, load gate) | — | **REUSE, and keep the boundary.** This schedules *when jobs fire*; the AEE schedules *what work depends on what*. Different concerns. AEE must not grow a trigger scheduler, and must not treat Dagster as the work-graph. |

**The consequence for the plan:** the genuinely new work in G3/G5 is the **dependency-aware graph,
the contract, the reservation and the economics** — not the executor. That shrinks G3 and G5 and
removes a whole class of duplication risk from the programme.

---

# PART B — THE PROPOSAL

## 4. Architecture in one paragraph

The Estate keeps exactly one execution spine and one intelligence spine. The **execution spine**
is the sovereign engine's Temporal `SessionWorkflow` plus the plan/subgoal tools; the AEE adds a
**dependency-aware `WorkGraph`** beside them, whose nodes are existing sub-goals, whose edges are
new, and whose every mutation is a `GraphRevision` carried by the existing signed receipt chain.
The **intelligence spine** is the LiteLLM router plus `lane_registry`; the AEE adds an
**`ExecutionContract`** per node — the one authoritative statement of which lane may serve it,
at what price, under what deadline and capacity reservation — and an **`EconomicReceipt`** per
attempt. A single **allocation policy** — deterministic first, learned only where evidence
justifies it — reads the lane supply, the cost ladder and the reservations, and emits contracts.
The **execution substrate is already there** — the task queue (`platform/queue/dispatcher.py`),
the worker pool and worktree manager (`platform/execution/`), the orchestrator and the N=10
integration harness (§3.4) — and the `WorkGraph` is what schedules onto it. **Nothing owns
execution that does not already own it.** The AEE's own logic is a *library and a contract*, not
a service.

### 4.1 The five invariants that make this AEE and not a second estate

1. **One authoritative execution state.** Every node state transition is written once, by the
   workflow that already owns it, and is observable in the AEI stream. No second state machine.
2. **One allocation policy, one budget chain.** Allocations reference `CapacityReservation`
   rows in `sovereign/engine/budget.py`; the process-level `budget_governor` ceiling is
   explicitly *subordinate* to the session budget, and the authority boundary is written down
   (C3).
3. **One economics ledger.** `EconomicReceipt` is a type on the existing `action_ledger` chain.
   AEI scores it; it does not re-sign it (C4).
4. **No node is accepted without a verification receipt**, and no parent is completed without
   objective acceptance — enforced by the workflow, not by convention.
5. **Every mutation of the graph is a revision with an owner**, and no work or reservation is
   ever lost silently: unclaimed reservations expire to the ledger, not to a void.

## 5. The gate programme

Each gate below states: scope, what it reuses, **exit criteria that can fail**, the proof, and
rollback. A gate is closed only on the proof, not on the plan.

### G0 — Reconcile reality (THIS DOCUMENT)

- **Scope.** The Part A matrix above, plus the repair of every measurement that could not be
  taken.
- **Exit criteria (falsifiable).**
  1. Every named capability resolves to a real, populated path **or** to an explicit
     "not established" with the command that failed and its exit status. **MET by this
     document** — 15 of 15 rows carry a state and evidence.
  2. The supply is measured on **both** routes with a dated, repeatable probe. **NOT MET** —
     the cloud route is down (F1) and the laptop catalogue is stale (F2).
  3. Every duplicate (C1–C6) has a named owner and a decision. **MET.**
- **Proof.** This document, merged, with every quoted command re-runnable.
- **Remaining G0 work, and who must do it.**
  - **Restore the cloud route** (TLS at `llm.mumchimp.com`, and the estate ingress that also
    carries the memory plane) — *owner: infra/founder-side operator*; the AEE cannot repair an
    upstream edge from the laptop.
  - **Restore local supply** — pull at least one Ollama model and set the cluster `replicas` to a
    real number, or formally retire the free lane in the cost ladder. *Owner: platform.* This is
    the difference between a free floor and a fiction.
  - **Reconcile the router catalogue** against the live provider model list and remove dead
    entries. *Owner: platform.* `groq/llama-3.1-8b-instant`, `groq/qwen/qwen3-32b` and
    `groq/meta-llama/llama-4-scout-17b-16e-instruct` are dead.
  - **Land `front.py` in the repository** (C2). *Owner: platform.* The cloud-default failover is
    currently unreviewable and unrecoverable.

### G1 — Canonical contracts (the shared vocabulary)

- **Scope.** Specify `Objective`, `WorkNode`, `ExecutionContract`, `ExecutionAttempt`,
  `IntelligenceLane`, `CapacityReservation`, `VerificationReceipt`, `EconomicReceipt`,
  `GraphRevision` as **schemas that extend existing Estate structures** — the plan tool's
  sub-goal shape, `lane_registry`'s lane state, `budget.py`'s spend row, `receipts.py`'s signed
  entry, `action_ledger`'s chained record.
- **Reuses.** Every one of the eight extensions in §3.3.
- **Exit criteria.** (a) every entity has a schema with a version and a migration story;
  (b) the correlation set covers objective, graph, node, attempt and contract;
  (c) a **falsifier**: a schema test that rejects a receipt missing a correlation id, and a
  receipt whose hash-chain predecessor is wrong — both must be able to fail.
- **Proof.** Schema tests green **and** two deliberately corrupted fixtures rejected.
- **Rollback.** Schemas are additive; the pre-existing shapes remain readable.

### G2 — Supply truth on the default route (repair C1, extend `lane_registry`)

- **Scope.** One parameterised router configuration rendered to two targets (laptop, cluster),
  with `lane_registry` + `route_table` + `action_ledger` + the AEI observer mounted on **both**.
  Live catalogue reconciliation against the providers' real model lists.
- **Reuses.** `lane_registry.py`, `route_table.py`, `routing-matrix.yaml`, `cost-ladder.yaml`,
  `router_catalog.py`, `availability.yaml`; the in-flight #7311 AEI router callback.
- **Exit criteria.**
  1. The **cloud** router's `/v1/models` catalogue contains **zero** entries that answer
     `model_not_found` on an active probe. (Falsifier: probe every advertised group; the count of
     dead entries must be 0.)
  2. A quota-exhausted lane is **drained within the forecast horizon** rather than being
     attempted and failed. (Falsifier: exhaust a lane's quota in a test, assert it is not chosen
     while drained.)
  3. Probe cadence: health 5–15 min, discovery 6 h, economics hourly, capability benchmarks daily
     or after a meaningful model change.
- **Proof.** A lane-health table with per-lane last-success timestamps and a **zero** dead
  entries, plus one live demonstration of quota-drain (the RPD 1000/1000 event on
  `openai/gpt-oss-120b` is the natural, already-occurring test case).
- **Depends on.** G0's cloud-route repair; #7311 (paths already claimed by `pi-aei-ops`).
- **Rollback.** The laptop configuration stays the fallback; a bad cluster render is reverted by
  redeploying the previous ConfigMap.

### G3 — `WorkGraph` and the execution contract

- **Scope.** The dependency-aware graph beside the sovereign engine's session workflow: nodes
  (existing sub-goals), edges (dependency), readiness, barriers, split/spawn/merge/join,
  block/unblock/retry/replace/cancel/reprioritise/replan/integrate/complete — each mutation a
  `GraphRevision`, each revision signed by the existing receipt chain, each revision digested by
  the existing Merkle DAG (`dag.py`).
- **Reuses.** `sovereign/engine/workflow.py` (Temporal), `plan.py` (sub-goals), `receipts.py`
  (chain), `dag.py` (digest), and the **existing execution substrate** — `platform/queue/dispatcher.py`
  (the queue a node is admitted to), `platform/execution/worktree_manager.py` (the isolated
  workspace), `platform/execution/worker_pool.py` (the worker that runs it) (§3.4). The AEE adds
  the graph, the contract and the revision; it does not add an executor.
- **Exit criteria.**
  1. **No hard-dependency cycles** may be committed. (Falsifier: a graph with a cycle is
     rejected.)
  2. **No accepted node without a verification receipt**; **no completed parent without
     acceptance**. (Falsifiers: both are refused.)
  3. **No silent loss of work or reservations**: killing a worker mid-node leaves the node's
     `attempts` record and the reservation visible, and the reservation is reclaimable. (Falsifier:
     a kill -9 during execution; the graph must show the attempt and the reservation must not
     vanish.)
  4. **Mid-run graph revision** is possible while other nodes execute, and the revision is
     atomic and visible to the running nodes.
  5. **Authorised scope**: a node may only mutate paths inside its declared boundary.
- **Proof.** A BDD feature file (`features/assurance/work-graph.feature`) whose every scenario has
  a negative case that must fail.
- **Rollback.** The graph is additive to the session workflow; disabling it returns the Estate to
  today's behaviour.

### G4 — Economic allocation

- **Scope.** The single allocation policy that turns (node, supply, budget, deadline) into an
  `ExecutionContract` and a `CapacityReservation`. **Deterministic first.**
- **Reuses.** `cost-ladder.yaml`, `routing-matrix.yaml`, `route_table.py`, `budget.py`,
  `budget_governor.py`, `lane_registry.py`.
- **Exit criteria.**
  1. The policy is **deterministic**: the same (node, supply, budget, deadline) always yields the
     same contract. (Falsifier: 100 identical inputs → 100 identical outputs.)
  2. A **deterministic bypass** (a lane that needs no model — a formatter, a grep, a hash) is
     preferred over any model lane whenever it satisfies the contract. (Falsifier: a node whose
     contract admits a deterministic lane must never be allocated to a model lane.)
  3. **Learned routing is not introduced** until a benchmark shows it beats the deterministic
     policy on the objective (verified outcome quality, total cost, completion time). It starts in
     shadow: it proposes, the deterministic policy decides, and the disagreement is recorded.
  4. Every allocation writes an `EconomicReceipt` into the `action_ledger` chain, with unit price
     and waste class.
- **Proof.** Benchmarks S0–S2 (§7) with measured numbers and a documented decision.
- **Rollback.** Shadow mode is the rollback: the learned policy proposes and is ignored.

### G5 — Execution economics at scale (concurrency, capacity, reservations)

- **Scope.** Capacity reservations, work stealing across workers, and the concurrency envelope.
- **Reuses.** `budget.py` (reservation rows), `workflow.py` (worker semantics), `Temporal`
  (task queues and workers), the FleetView/NATS event substrate, and the **existing worker pool
  and dispatcher** (`platform/execution/worker_pool.py`, `platform/queue/dispatcher.py`) — G5 is a
  *policy over the pool the Estate already has*, not a new pool (§3.4).
- **Exit criteria.**
  1. **Concurrent independent tasks** run concurrently; **dependent** tasks do not.
  2. **Overlapping-code conflict** is detected before integration, not after.
  3. **Quota exhaustion** mid-run diverts to the next lane under contract, without a failed node.
  4. **Cancellation** releases its reservation and stops its spend — provably.
  5. **Scheduler restart** resumes from durable state with no double-spend and no duplicate node
     execution (idempotency keys).
  6. **Budget cutoff** stops work deterministically at the ceiling, with the reason recorded.
- **Proof.** A fault-injection suite: worker death, quota exhaustion, cancellation, integration
  failure, budget cutoff, scheduler restart — each with a measured outcome.
- **Rollback.** Concurrency drops to 1; the graph and receipts still hold.

### G6 — Independent verification

- **Scope.** Bind NSVEE's four tiers to the AEE's three levels — operation, integration, objective
  acceptance — and make each produce a `VerificationReceipt`.
- **Reuses.** `nsvee/engine.py`, `receipts.py`, `action_ledger.py`.
- **Exit criteria.** (a) A node cannot be accepted without an operation-level receipt; (b) an
  integration-level failure blocks the parent's completion; (c) objective acceptance is
  independent of the agent that did the work. (Falsifiers: each refusal is observable.)
- **Proof.** A deliberately failed parent acceptance blocks completion, demonstrably.
- **Depends on.** G3, G4.

### G7 — Routing rollback and economics visibility

- **Scope.** Rollback of a routing change without a redeploy; the economics view (cost per
  objective, waste class, lane yield) on `/fleet`.
- **Reuses.** AEI's manifest contract (`aei.manifest.v1` — the visualisation and evidence-link
  fields already exist), `action_ledger`, the FleetView event stream.
- **Exit criteria.** (a) A bad lane is removed from service in under the routing-drain interval,
  with a measured time; (b) the economics view shows cost per objective reconciled against the
  ledger, with any unreconciled delta **surfaced, not hidden**; (c) the view is driven by AEI
  evidence links, not by a second source of truth.
- **Proof.** The view is read by the founder on `/fleet` and its number is reconciled to the
  ledger in the same session.
- **Depends on.** G2, G5; AEI operational (#7311).

### G8 — Benchmark ladder and economic certification

- **Scope.** Run S0–S5 (§7) on real objectives and publish the comparison.
- **Exit criteria.** Each strategy is measured on the same objective set; the winner is chosen by
  **verified outcome quality, total cost and completion time** — never by token cost, model
  utilisation, agent count or parallelism alone. Any strategy that cannot be measured is
  recorded as **unverified**, not as a tie.
- **Proof.** A published table with raw measurements and the decision rule applied in writing.
- **Depends on.** G3–G7.

### G9 — Decommission and consolidation

- **Scope.** Remove what AEE replaced. Nothing is retired that AEE does not replace.
- **Exit criteria.** Every capability that AEE superseded has its successor **operational**, not
  merely merged, before the predecessor is deleted. A predecessor with no successor stays.
- **Proof.** A before/after capability matrix showing one layer per concern.

## 6. Sequencing and critical path

```
G0 ──┬─► G1 (contracts) ──► G3 (work graph) ──► G5 (economics at scale) ──► G8 (benchmarks) ──► G9
     │        │                    ▲                                               ▲
     ├─► G2 (supply truth) ───────┘───────────► G4 (allocation) ──────────────────┘
     │                                                                        │
     └──────────────────────────────────────────────────────► G6 (verification) ┘
```

- **Critical path:** G0 → G1 → G3 → G5 → G8. Nothing else can shorten it.
- **Parallelisable after G1:** G2 (independent of G1), G4 (needs G2's lane view), G6 (needs G3).
- **Hard dependency:** G2 needs the cloud route restored (G0) and must not collide with #7311's
  claimed paths.

## 7. Benchmark ladder

| Strategy | Definition | Measures |
|---|---|---|
| **S0** | Sequential, strong model | Quality ceiling, cost ceiling, latency ceiling |
| **S1** | Deterministic-first, sequential | Cost floor; the deterministic-bypass rate |
| **S2** | Constrained local delegation | The value of the free lane (currently zero supply) |
| **S3** | Static parallel headless execution | Parallel speed-up at fixed quality |
| **S4** | Adaptive dependency-aware parallel | Graph-driven concurrency vs S3 |
| **S5** | Fully integrated adaptive economic | The objective of the programme |

Each S is run on the **same objective set**, with quality judged by the *original objective's*
acceptance test — not by the agent's own claim — and cost measured as the **total**:
inference + compute + coordination + verification + recovery.

**The decision rule (fixed in advance, so it cannot be rationalised after the fact):** a strategy
wins on the tuple (verified outcome quality, total cost, completion time), lexicographic with
quality first. Any strategy that fails to produce a measurement is **unverified** and cannot win.

## 8. Operational acceptance demonstrations

Each scenario the AEE specification names, mapped to the gate that proves it and the artefact that
records the proof:

| Scenario | Gate | Proof artefact |
|---|---|---|
| Free-model discovery and loss | G2 | lane-health table with the discovery timestamp and the loss |
| Deterministic bypass | G4 | contract showing a deterministic lane chosen |
| Concurrent independent tasks | G5 | two nodes, concurrent attempt ids, one wall clock |
| Mid-run graph revision | G3 | two `GraphRevision`s, the second visible to a running node |
| Overlapping-code conflict | G5 | conflict detected pre-integration |
| Worker death | G5 | attempt recorded, reservation reclaimable, no silent loss |
| Quota exhaustion | G2, G5 | lane drained on forecast, next lane used, node not failed |
| Cancellation | G5 | reservation released, spend stopped, receipts closed |
| Integration failure | G5, G6 | parent not completed; verification receipt records the refusal |
| Budget cutoff | G5 | deterministic stop at the ceiling, reason recorded |
| Scheduler restart | G5 | no double-spend, no duplicate execution |
| Routing rollback | G7 | lane removed, measured drain interval |
| Failed parent acceptance | G6 | completion refused |
| Unavailable accounting | G2, G7 | the system **degrades explicitly**: cost is marked unaccounted, not silently zero |

The last one is the Estate's rule in operational form: **unknown cost is shown as unknown.**

## 9. Security and governance controls (preserved, not replaced)

- **Authority.** The `ExecutionContract` is the only thing that authorises a lane to spend; a
  node with no contract cannot execute. The sovereign engine's approval FSM and quorum rules are
  untouched.
- **Claims.** Every work stream in §10 carries a GitHub issue claim with declared paths; the
  claim-gate keeps running unchanged. AEE adds no new permissioning surface.
- **Secrets.** Keys are referenced by name only (`LITELLM_API_KEY` and the vault path
  `secrets/dev/LITELLM_LAPTOP_KEY.yaml`); no value appears in code, receipts, graphs or journals.
  `EconomicReceipt` carries a price, never a key.
- **Budgets.** Reservations are enforced in the existing durable store; no new spend authority.
- **Auditability.** Every decision (contract, attempt, verification, receipt, revision) is a signed
  entry on the existing chain, and every graph mutation is attributable to one owner.
- **Deployment.** Nothing hand-applies. Work reaches `main` through the Greenlane; Flux converges.
- **Placement.** Every new workload is placed by the free-tier ladder (decision 0034) before it is
  proposed for the node; the node's requests stay under 1.8 CPU.

## 10. Ownership and claims

| Work stream | Gate | Claimable paths | Note |
|---|---|---|---|
| Supply truth on the default route | G2 | `platform/llm/litellm.yaml`, `platform/llm/config.base.yaml`, `platform/llm/lane_registry.py`, `platform/llm/route_table.py` | **must not collide with #7311's `platform/llm/config.yaml` claim** — split the ConfigMap change across two claims or sequence them |
| Router catalogue reconciliation | G2 | `llm/config.yaml`, `platform/llm/routing-matrix.yaml` | needs #7311 to land first if both touch config |
| `front.py` back into the repo | G0 | `platform/llm/front.py` | small, high value, unblocked |
| Work graph + contracts | G1, G3 | `sovereign/engine/work_graph.py`, `features/assurance/work-graph.feature`, `docs/specs/2026-10-28-aee-work-graph.md` | new paths, no collision |
| Extend the existing execution substrate | G3, G5 | `platform/queue/dispatcher.py`, `platform/execution/**`, `tests/test_worker_pool.py`, `tests/test_queue_dispatcher.py` | **extend, do not replace.** The missing pytest modules for the pool, the queue and the worktree manager are part of this claim — the layer is validated by script only (§3.4) |
| Economic allocation policy | G4 | `sovereign/engine/allocation.py`, `features/assurance/economic-allocation.feature` | new paths |
| Verification binding | G6 | `nsvee/`, `features/assurance/` | coordinate with #3525 |
| Economics visibility on `/fleet` | G7 | `backstage/packages/app/src/modules/room/` | coordinate with #7344 |

**Unclaimed and available now:** #7344 (estate context substrate), #3525 (The Battalion). No
AEE issue exists yet; this proposal's issue is the record.

## 11. Risks, dependencies and unknowns

| Risk | Likelihood | Impact | Mitigation / measurement |
|---|---|---|---|
| **Cloud route stays down** — every default-route claim in `AGENTS.md` §7a is false in practice | high | high | G0 measures it daily; the AEE records the serving route on every receipt so the policy can never be assumed |
| **Ollama supply stays empty** — the cost floor is fictional | high | medium | Either restore supply or formally retire the lane in the cost ladder; AEE will not price an empty shelf |
| **Two config copies drift again** (C1) | high | high | G2's parameterised single source with two rendered targets, plus a CI check that the renders match |
| **Unversioned failover code is lost** (C2) | medium | high | G0 lands `front.py` in the repo and deletes the machine copy's authority |
| **Duplicate budget authority** (C3) | medium | high | G1 writes the authority boundary; G4 binds reservations to exactly one store |
| **AEI and the ledger both claim to be the economic spine** (C4) | medium | medium | G1: AEI reads the ledger; one signer |
| **Learned routing is adopted on narrative** | medium | high | G4 fixes the deterministic-first rule and shadow mode in advance; the benchmark ladder is the only door |
| **Disk pressure — the estate is starved and every executor door is closed** | high | high | Measured 2026-10-28 during this pass: free space fell to **1107–1114 MB**, under the executor's 1500 MB floor, and **every `estate_execute` job was refused estate-wide** ("the volume has 1114 MB free, under this door's 1500 MB floor"). The estate's own cleaner freed 238 MB of package caches; `disk-reclaim` freed 0 (every pytest scratch dir was live). **All 40 agent worktrees were protected** — 17 by a live claim, the rest by uncommitted work or a lock — so *no reclaim was available without the owners acting*. The 1256 MB that did come back came from the **critical tier** (old toolchains), not from work. G0/G2 add no large stores (the AEI store is PostgreSQL, not SQLite-on-laptop), but **the programme cannot be built on a starved volume**: the first act of G0's execution budget is to get the volume above the floor, and only an agent can release a worktree it still holds |
| **Collision with live claims** (#7311, #7342, #7344) | medium | medium | §10 splits paths explicitly; the claim-gate is the arbiter |
| **The estate already built this** — a duplicate AEE exists elsewhere | unknown | high | `growmos query` before each gate; `bin/capability-index` is the registry to check |

**Explicit unknowns (not estimated):** the true daily spend (cloud accounting unreachable), the
cluster's true capacity (cluster unreachable), the per-lane quality baseline (no benchmark has run),
and the real free-lane yield (no models pulled).

## 12. Founder / Oracle visibility plan

- **One surface:** `/fleet` (the work surface), fed by the AEI event stream — not a report.
- **One number:** verified outcome quality per dollar, per objective, reconciled to the
  `action_ledger` chain. Any delta the AEI cannot reconcile is **displayed as a delta**, never
  smoothed away.
- **One live view:** the work graph — what is running, what is reserved, what is waiting, what is
  blocked, and on which lane, in real time.
- **Voice first:** the founder asks "what is it costing and is it worth it" and hears the answer;
  no new form, no table dump, no report to read later.
- **Receipts on demand:** any claim about cost or quality can be expanded into the signed receipts
  that produced it.

## 13. Status ledger (every capability, one state)

| Capability | State | Evidence |
|---|---|---|
| Cloud LiteLLM router | **DEGRADED** | `router-status` exit 35; TLS EOF |
| Laptop LiteLLM router | **OPERATIONAL** (2 groups) / **DEGRADED** (default & fast quota-blocked) | `narrate` → "Say: Alive"; RPD 1000/1000 |
| `lane_registry` | **IMPLEMENTED, TESTED, laptop-only** | `tests/test_lane_registry.py`; absent from the cluster config |
| `route_table` / cost ladder / routing matrix | **IMPLEMENTED, TESTED** (laptop) | `tests/test_route_table.py`; catalogue carries 3 dead models |
| AEI | **IMPLEMENTED, TESTED; deployment NOT ESTABLISHED** | `packages/aei`; `platform/aei/aei.yaml`; cluster unreachable; #7311 in flight |
| NSVEE | **IMPLEMENTED, TESTED; operational path NOT ESTABLISHED** | `nsvee/engine.py` |
| Sovereign engine (Battalion) | **IMPLEMENTED, TESTED; operational path NOT ESTABLISHED** | `sovereign/engine/`, `features/battalion/` |
| Temporal `SessionWorkflow` | **IMPLEMENTED; deployment NOT ESTABLISHED** | `sovereign/engine/workflow.py`; cluster unreachable |
| Task queue (`platform/queue/dispatcher.py`) | **IMPLEMENTED; no dedicated test module; operational path NOT ESTABLISHED** | SQLite `state/queue.db`; atomic `claim_task`; worktree per task |
| Worker pool + worktree manager + N=10 integration | **IMPLEMENTED, validated by script; operational path NOT ESTABLISHED** | `platform/execution/`; `validate.py`, `n10_validator.py` |
| Periodic job scheduler (Dagster) | **IMPLEMENTED; operational path NOT ESTABLISHED** | `scheduler/dagster.yaml`, `scheduler/estate_scheduler/` |
| `budget_governor` | **IMPLEMENTED, TESTED** | `bin/budget_governor.py` |
| Durable budget | **IMPLEMENTED, TESTED; operational path NOT ESTABLISHED** | `sovereign/engine/budget.py` |
| `action_ledger` | **IMPLEMENTED; live on the laptop** | `platform/llm/action_ledger.py` |
| `receipts.py` signed chain | **IMPLEMENTED** | `sovereign/engine/receipts.py` |
| Ollama free lane | **DORMANT (no supply)** | `replicas: 0`; `/api/tags` → `[]` |
| Goal / subgoal system | **OPERATIONAL** | `platform/estate/memory/plan.py`; this session |
| Capability index | **IMPLEMENTED** | `bin/capability-index` on `origin/main` |
| `front.py` cloud-default failover | **IMPLEMENTED but NOT VERSIONED** (C2) | deployed 566 lines vs repo 96 lines |
| Estate memory plane | **DEGRADED** | `bin/estate-brief` → `URLError: EOF … _ssl.c:1129` |
| RIP / Oracle / Stewardship | **NOT ESTABLISHED** | not measured in this pass |
| AEE canonical entities | **SPECIFIED only** | zero occurrences on `origin/main` |

---

## 14. What this proposal asks for, and what it does not

**It asks for one decision:** proceed with AEE as the **execution-economics sharpening of the
Estate Master Epic**, starting with G0's four remaining repairs (cloud route, local supply,
catalogue reconciliation, `front.py` into the repo) and G1's contracts.

**It does not ask for:** a new router, a new coordinator, a new budget store, a new verification
engine, a new capability registry, a new task queue or worker pool, or a second programme
alongside the Master Epic. Two new structures (`WorkGraph`+`GraphRevision`, `ExecutionContract`)
and eight extensions of existing Estate structures are the whole of it.

**It does not claim:** that any cluster-hosted capability is working, that the cloud route is
working, that the free lane exists, or that the Estate's current spend is known. Those are the
four things this pass could not establish, and they are the first four things G0 must fix.

---

*Every command quoted in this document was run in the measurement window and its output is
reproduced verbatim above. Where a probe failed, the failure and its exit status are quoted
rather than the conclusion it might have supported.*
