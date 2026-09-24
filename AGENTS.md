# AGENTS.md — the rules of this repository

This file is the version-controlled boundary for agent work in `idp` (crew #180, CP6).
Estate-wide laws live in `~/AGENTS.md`; this file holds only what is specific to this repo.

Rules here are enforced as types or tools, run unconditionally by `bin/idp-ci`:
`docker compose config`, `check-jsonschema` (gateway), Backstage schema, `shellcheck`
(scripts), idempotent generators, the catalog relationship graph, and `bin/catalog-refcheck`
(proved both ways). No `rules.yaml` — the 100-row registry was deleted 2026-09-20 because
a registry that re-describes rules already enforced as types is a second copy that drifts.
A rule is a rung in `bin/idp-ci`, not a row in a table.

## Andon cord: main must be green; never more than 3 red PRs (2026-09-17)

**Estate-wide. Applies to every agent, every tool, every workflow.**

Toyota's Stop-the-Line principle, applied to this repository:

1. **main must never fail CI.** A broken main hands its failures to every branch
   drawn from it. If main is red, that is the only valid task until it is green.
   No new feature work. No new PRs. Fix main.

2. **Never more than 3 failing PRs open at once.** At the cap the pre-push hook
   refuses any new branch push. Agents must fix a red PR before opening another.

Both rules are machine-enforced at push time by `bin/idp-main-green-gate` and
`bin/idp-wip-gate`, wired into `.githooks/pre-push` (new-branch pushes only).
BLIND (no network / no `gh`) does not refuse the push — LAW 38: a fence a correct
machine cannot satisfy is an outage.

**Emergency overrides (typed deliberately, never scripted):**
```
IDP_MAIN_GREEN_GATE=0 git push   # you are the fix for main
IDP_WIP_GATE=0        git push   # genuine emergency past the cap
```

## No new workflow files without founder approval (2026-09-24)

**idp only. Applies to every agent.**

A `.github/workflows/*.yml` file added to this repository is a CI gate that every PR
in the estate will wait on. A workflow that fails blocks merges; a workflow that is
deleted from `main` but still exists on a branch posts ghost failures to that PR
every time CI runs. Both cases have caused multi-hour incidents.

**Rule: an agent must not add `.github/workflows/` files without explicit founder approval.**
This is not a governance discussion — it is a structural constraint. Any agent that
needs a new CI gate must describe the gate, get founder sign-off, and then the
founder adds it through the UI or a tracked PR.

## Done is operating, not pushed: a PR is only the beginning of done (2026-09-20)

**Estate-wide. Applies to every agent, every tool, every workflow.**

A commit is not done. A push is not done. **A PR open is only the beginning of
done.** The only thing that ends a piece of work is the thing running in
production, proven by a real log line — not by a green CI gate, not by an HTTP
200, not by "the diff looks right."

The full path: commit → push/PR → CI green → merge to `main` →
`build-multiarch.yml` (amd64+arm64, Trivy, cosign) → Flux image-reflector →
`image-automation` → `deploy-when-green` → **operating in the cluster,
evidenced by a production log line.** Steps 1–7 are "built", step 8 is
"operating" — different facts, never reported as one another (estate law:
built and operating are different facts; proof, not assertion). A step is
only reached when the one before it is measured green.

## Gateway-as-floor: agents emit events, the gateway writes (2026-09-17)

The gateway is the only writer; agents have no write capability and emit events to it. The full
rule — the harness it replaces (judge, PRM, Aevum, dod-guard, pareval, shadow-verify), the
break-glass protocol, and the agent-assisted cluster revival exception — is
`docs/reference/gateway-as-floor.md`.

## Definition of Done — a PR is the beginning, not the end (2026-09-17)

**Mandate: Never announce a pull request to the founder as an achievement. A merged PR is the start of the work.**

A task is only done when all three are true:
1. It executes on live traffic — a real cron, webhook, or event trigger in production, not a CI fixture
2. Its output reaches a surface the founder reads: Telegram, crew#102, or mumchimp.com
3. If it breaks, something reports it within one hour without the founder asking

A PR that writes to GITHUB_STEP_SUMMARY, a JSONL ledger file, a Backstage TechDocs page, or an OrbStack log is not done. It is ghost code. The next step after every merge is always: wire it into the live execution path. If wiring is blocked, say so explicitly and name the blocker — do not move on to the next build task.

## SPIFFE primary: never ask the founder to log in (2026-09-23)

**Estate-wide. Applies to every agent, every tool, every workflow.** Full architecture in `docs/reference/security-architecture.md`; every agent reads it before acting on estate security. The rules, one line each:

1. An agent never asks the founder to log in (Claude Code, OCI, `gh`, any LLM proxy).
2. An agent never pastes a static key (no `LITELLM_API_KEY`, no OCI API key on disk). The credential arrives through SPIFFE or it does not arrive.
3. An agent never tells the founder to "run this script" for security reasons. Hook install, workstation bootstrap, JIT enrollment, device-renew all run on the agent's own clock. The one-time per-Mac `bin/idp-jit enroll` is the only founder exception.
4. The "executive" / CEO function is a JWT-SVID audience, not a phone tap. `bin/idp-jit ask` fires the broker, the broker validates a SPIFFE-issued JWT-SVID instead of pinging a phone.

## Hooks first: the agent installs them, not the founder (2026-09-16)

**Mandate: The agent runs `bin/idp-install-hooks` itself, on its first action in any fresh checkout, before its first commit. The founder is not asked to do this.**

The estate's `.githooks/pre-push` is the hook the founder shipped (crew#584 CP2) to refuse a
push whose session-plane rules would fail in CI seven minutes later. It only fires when
`core.hooksPath` names `.githooks`, which a fresh clone does not do. On 2026-09-16 that gap cost
three CI cycles on idp#3627 to catch two static defects (portal-buttons drift, LAW 46 hardcode)
that this hook would have refused in seconds. Running `bin/idp-install-hooks` is idempotent and
takes under a second; `bin/idp-ci` prints a WARN banner at the tail of every run on a clone that
has not wired it, so the missing setup is impossible to miss.

## Token Efficiency: idp-exec wrapper (2026-09-15)

**Mandate: You are forbidden from running raw shell commands. You must prefix every command with `bin/idp-exec` to preserve token efficiency.**

Why: Raw command output can exceed 50 lines and bloat the context window. `bin/idp-exec` automatically:
- Clamps output to first 25 + last 25 lines if it exceeds 50 lines
- Saves full output to `~/.pi/agent/state/last_exec.log` for later inspection
- Returns the exact exit code of the underlying command

Usage: `bin/idp-exec cat large_file.log` instead of `cat large_file.log`

## Workstation bootstrap: the agent boots its own workstation (2026-09-17)

**Mandate: The agent runs `bin/idp-workstation-bootstrap` itself, once, on any fresh workstation it lands on. The founder is not asked to do this.**

Why (founder 2026-09-17): "our system must be able to bootstrap itself in any env". The prior bootstrap chain (`bin/idp-bootstrap-estate`) assumed the tool set was already installed and did not wire local `gh`/`kubectl` conveniences, so a fresh macbook on 2026-09-17 had age identity but no OCI config, no kubeconfig, and unauthed `gh` — which blocked Lane E (PR #3599) on a laptop-only credential gap. This script closes Level 0 (portable tool install per OS family) and Level 3 (local `gh auth` + `~/.kube/config`) around the existing Level 2 estate bootstrap.

The one hand a person still gives is the age identity restore (iCloud Keychain / paper / hardware key); this script refuses to proceed if `SOPS_AGE_KEY_FILE` is not readable.

## The estate twin: ask the graph, not the cluster (2026-09-12)

Ask before you touch the cluster: `bin/estate-twin-runtime --once --code|--dead|--state|--history <node>|--blast-radius <n>`.
Extends `catalog/estate.db` (no second store/bus/MCP server, per THE HEADLINE). `UNKNOWN` is
the default, not a failure; `stranded` is not serving. Full spec, rules and proof:
`docs/specs/2026-09-12-estate-twin-complete-spec.md`, `docs/evidence/estate-twin/PROOF-OF-WORK.md`.

## Platform queries go through the estate MCP server (ADR 0006)

A question about estate state is one `mcp__estate__*` call, never a shell recon. A state-changing
tool is two calls (propose, execute), execute refusing on a stale state hash. Extend `mcp/`; never
add a second server. Full text: `docs/decisions/0006-the-platform-answers-for-itself-over-one-mcp.md`.

### The tools, and how to call them when the door is shut

`mcp/plugins/` exposes `get_estate_state`, `get_workload_state(app)`, `get_workload_logs(app, tail)`,
`ask_holmes(q)`, `get_catalog_drift(rule)`, `recall`, and the propose/execute pairs. When
`bin/idp-mcp-door` BLINDs on an unset `MCP_GATEWAY_KEY`, the plugin functions run against the
local store — still one query, not a recon sweep. **When a peer's state is unknown, ask the peer**
(the crew board), never their transcript: `~/.claude/projects/*.jsonl` records what a session
believed, including beliefs it later corrected. Full text, with the 2026-09-19 incident that paid
for it: `docs/reference/platform-queries.md`.

## Zero-trust agent cluster access (WJ.1, 2026-09-17)

Agents get **read-only** cluster access through the JIT broker — no OCI login, no kubeconfig paste:
`bin/idp-kube get pods -n <namespace>`. Full path, provisioning, failure modes and the OTel
injection exclusion that must never be removed: `docs/reference/agent-identity.md`.

## Choosing a model to host: read this first

**Before proposing, sizing or arguing for any model in this estate, read
`docs/specs/2026-09-11-which-model-to-host.md`.** It is short and it settles the question:

- **The hardware is two ARM nodes at 19 GiB allocatable each, and NO GPU.** That is the ground.
- **The tier is chosen by the DECISION, not by ambition.** A 1.5B task expert (~1.1 GB) is the
  default; a 14B (~9 GB) when the expert abstains; a 32B (~19 GB) only on a dedicated node.
- **A binary expert measured 97.7% agreement here; a 7-way expert abstained on 93.6% and was
  refused.** Prefer many narrow experts to one multi-class one. An expert answers the question it was
  trained on; it does not notice the question was wrong, and nothing on this hardware replaces the
  paid lane at noticing.
- **A model is a download, not a purchase.** `platform/edge-runtime` loads one GGUF on ARM64.

Two arguments are answered there so they stop recurring: **"we need 70B to replace the frontier
lane"** (it fits no node at any quantisation, and a 1.5B expert got 97.7% on a real task) and
**"smaller models rival GPT-4 for architecture"** (they do not).

## Living policy (crew#219 R38): the block below is code, not prose

`sovereign/policy.py` parses the one ```toml block in this file, and `sovereign/config.py`
builds its `budget.usd_per_day.*`, `cost.*`, `routing.*` and `merge.*` keys from it. The
numbers config.py declares on its own are repeated under `[invariants]`, and
`sovereign/tests/bdd/test_policy.py` fails when the two disagree. Change a value here and the
code follows; change it in config.py alone and the suite goes red. Every key still takes the
usual env override (`sb config --lint` lists them).

- **Capabilities** (spec 4.4): what each agent class may do unattended. `destructive` ops need
  quorum and a hardware signature on top of budget; `nondestructive` need budget only.
- **FSM rules** (spec 4.3): `init -> planning -> tool_use -> synthesis -> terminal`; the
  cycle path repeated `max_cycles` times pauses the session before the next one.
- **Budget defaults** (spec 8, R40): USD per day per spender. The sum over `days_per_month`
  must sit inside the `[cost]` contract, $0 to $150 a month; the test proves it.
- **Model routing**: LiteLLM aliases from `llm/config.yaml`. `cheap` is the last entry of every
  fallback chain there, and the only one with zero marginal cost.
- **Merge criteria** (R41): `dev` is permissive, `main` is strict. A PR targeting a strict
  branch fails when any feature is still `pending`, or when a pending mark has no owner or
  says `unclaimed`. `.github/workflows/ci.yml` sets `SB_BDD_STRICT` from the PR's base branch,
  and `sovereign/tests/bdd/conftest.py` enforces it.

```toml
[capabilities]
nondestructive = ["fs_commit", "fs_read", "git_status", "tool_result", "doc_commit", "budget_refill"]
destructive = ["fs_delete", "git_push_force", "db_drop", "service_destroy", "rewind", "provision_paid_compute"]
engine = ["fs_read", "fs_commit", "git_status", "tool_result", "doc_commit"]
intake = ["fs_commit", "doc_commit"]
shadow = ["fs_read"]

[fsm]
initial_state = "init"
terminal_state = "terminal"
cycle_path = ["planning", "tool_use", "synthesis"]
max_cycles = 5

[budget.usd_per_day]
litellm = 3.0      # frontier calls through the proxy; llm/config.yaml max_budget is the hard ceiling
consensus = 1.0    # the three-model vote on destructive ops
vision = 0.5       # photo intake (spec 2.3)
ollama = 0.0       # local, no marginal cost
langfuse = 0.0     # self-hosted

[cost]
contract_min_usd_month = 0
contract_max_usd_month = 150
days_per_month = 31   # the longest month, so a sum under the cap holds in every month

[routing]
# default=minimax (floor, never a routing choice); cheap=groq (free, request-metered, since
# SEED_GROQ_API_KEY landed 2026-09-10 -- deepseek was the prior cheap lane, dead since 2026-09-04,
# history in ~/AGENTS-FULL.md). deepseek stays a consensus voter only (rejoins default/cheap the
# moment its key returns, no PR needed).
default = "minimax"
vision = "vision"
cheap = "groq"
consensus = ["deepseek", "minimax", "gemini"]

[merge]
strict_branches = ["main"]
require_bdd_green = true
pending_owner_required_on = ["main"]

[invariants]
"consensus.quorum" = "2/3"
"consensus.timeout_s" = 30
"branch.count" = 3
"branch.budget_pct" = 10
"approval.timeout_min" = 15
"blind.halt_after_min" = 5
"alerts.digest_over_per_hour" = 50
"spiffe.max_missed_heartbeats" = 3

[jev]
default_confidence_floor = 0.7
timeout_ms = 2000
escalate_on_timeout = true
model = "jev-1.13.0"
force_on_decisions = true   # when true, the Stop-hook blocks turns that skip Jev for bounded decisions
```

## Jev first: bounded decisions go through the layer (ADR 0030)

Before any bounded decision, call `jev_choice`, `jev_score`, or `jev_noul` via the MCP plugin.

**What counts as a bounded decision:**
- Tool selection when multiple tools could apply
- Retry vs. escalate vs. abandon
- Risk assessment (safe / warn / block)
- Pass/fail judgment on a test or gate
- Confidence thresholds (proceed / pause / ask)

**Exempt (not bounded):**
- Text generation (summaries, code, prose)
- File reads and searches
- Pure retrieval with no judgment attached

**Enforcement:** The Stop-hook `jev_decision_gate.py` blocks turns that skip Jev for expensive
operations (tool calls over the cost threshold, destructive ops, consensus triggers). The hook
checks the turn's tool-call log; if a bounded decision was made without a preceding `jev_*` call,
the turn is refused.

**Rationale:** 193x faster, 444x cheaper than frontier-model deliberation, and every decision
lands in the `jev_decisions` table with confidence, latency, and the input hash — an audit trail
that survives the context window.

References: ADR `docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md`,
MCP plugin `mcp/plugins/jev.py`, policy config `[jev]` section above.

THE EMPIRICAL PROOF RULE binds here too, verbatim, inherited from `~/AGENTS.md` — not repeated
below to avoid loading the same block twice in one context (measured duplicate, 2026-09-14).

## Three Planes: composition target (2026-09-22)

The estate's 480+ capability surfaces (per `docs/synthesis/2026-09-20-full-capability-map.md` extended 2026-09-22) compose into three independent planes that run as concentric filters, not a linear pipeline:

1. **Generative Swarm** (Inference & Memory) — agents think, route, and collaborate. ZeroEdge (cost/routing optimizer, off unless `ZEROEDGE_URL` set, fails open), LiteLLM (`platform/llm/config.yaml`), TTCS CRDT (`packages/idp_concurrency/src/idp_concurrency/ttcs/`, built unwired), Tuple Space (proposed), Efficiency Gateway's eight mechanisms (CacheGuardian, TokenKiller, MCPAdapter, TokenBudgetOrchestrator, SoLPi, DynamicContextPruning, CompactionManager, ToolPairValidator), growmos, .aevum/local.jsonl, Jev (decision service), the four forcing lints in `packages/idp_concurrency/lint/` (`no_ad_hoc`, `no_locks`, `no_unbounded`, `no_untraced`). Frictionless, stochastic, purely in-memory. Nothing here touches GitHub.

2. **Adversarial Crucible** (Semantic Evaluation) — AI evaluates AI. JudgeWorker (four-dim transcript scoring: `tool_f1` 0.35, `arg_validity` 0.30, `result_utilization` 0.20, `error_recovery` 0.15), JudgeDriftSentinel (JS-divergence vs baseline, threshold 0.15), GoldSetCalibrator (Cohen's kappa bands), ParEvalLayer (paired A/B + bootstrap CI + coverage_score), AgentCircuitBreaker (real-time loop detection on turns 3-4), RedTeamLoop with PayloadGenerator / Mutator / Catalog / Validator / promoter / Go proxy (`bin/negative-constraints-proxy/main.go`), **`bin/idp-reversibility-gate` and `verify_inverse` at `platform/executor/daemon.py:1178` (the reverifier)**, `probes/mutations.py` (graduated probes, UNPROVEN until 1 FAIL + 1 PASS). Runs asynchronously over the Swarm's output. Failures kick back as tuples, not PRs.

3. **Physics Engine** (Isolation & Proof) — cold, mathematical boundary, no LLMs. Kronos rings 0-4 (Firecracker ring0 built in a separate repo, **NOT operating on this machine**; the honest boundary today is `ISOLATION_KIND = "temp-tree-scrubbed-env"` at `sovereign/verifier.py:85`), gVisor/runsc + 12 hermes-agent arenas, `sovereign/verifier.py` four-stage gauntlet (compile / sqlite / Z3 / pytest in temp tree), Sigstore / Ed25519 attestation (fallback when `cosign` absent), Aevum (Ed25519 + ML-DSA-65 dual-signed COSE_Sign1, RFC 3161 timestamps, hash-chained), Flux + Kyverno admission.

**Highest-priority unsealed gap (2026-09-22): the Universal Write Boundary.** The cluster engine writes straight to disk via `open().write()` at `platform/idp_agent/engine.py:311`, bypassing every gate in Plane 3. The laptop executor daemon mediates via the AF_UNIX socket — they meet only at `git push`, which is *after* attestation, not before. Closing this means: the cluster engine emits via the gateway, the daemon mediates via the existing mutation flow (`propose_patch` → `verify` → `seal` → `admit`), and no agent write reaches disk without gauntlet + Sigstore seal. Implementation requires verified premises (actual CI failure breakdown, actual Dockerfile state, actual BDD test names) and **must not** override existing gates (`.githooks/pre-push` Andon cord, `[invariants]` block above, JSON-lines protocol on the daemon socket).

**Pre-condition for any Three Planes wiring:** the Andon Cord rule at the top of this file is non-negotiable. Main must be green by fixing failures, not by quarantining them as `xfail`. Quarantining failing tests as expected-failures to clear the gate is exactly the pattern the Andon Cord exists to prevent — it returns the estate to the pre-Andon state where the gate is theatre. Every BDD failure is a real signal; fixing it is the only path to green.

<!-- growmos:start — managed by `growmos integrate`; edits inside this block will be overwritten -->
## growmos — living knowledge graph (shared memory for humans + agents)

This repository keeps a knowledge graph in `.growmos/` (entities, typed relations, provenance,
profiles, a journal). It is the shared world model that survives context windows. Treat it as
memory you read at the start of work and write to as you develop. Zero-config commands:

1. **Session start** — run `growmos context` (a compact brief: hubs, health, pending work, latest journal).
   If it lists pending work, run the `growmos next` → apply loop (step 4) right away, without being asked —
   it is quick, needs no permission, and is how the graph stays alive.
2. **Before cross-cutting questions** ("what depends on X?", "why was Y decided?") — run
   `growmos query "<question>"`; answer from the returned subgraph and cite edge ids.
3. **When you learn or decide something durable** (new component, architectural decision, ownership,
   dependency, gotcha) — write it back immediately:
   - `growmos remember "<Name>" --type <TYPE> --desc "<one grounded sentence>"`
   - `growmos link "<A>" "<predicate>" "<B>"`   (short verb phrase predicates: "depends on", "replaces")
   - `growmos journal "<what changed and why>"`
4. **Feed the organism** — run `growmos next`. It hands you a *task packet* (extraction / resolution /
   profile / gold set / review) with the exact prompt, the JSON shape, and the `growmos apply …` command.
   Do the judgment work yourself, write the JSON, apply it. Repeat until `growmos next` says the graph is
   up to date — that loop covers everything, including the evaluation gold set and the periodic node review.
   If it reports the daily extraction cap, run `growmos next --force` (the cap only guards unattended runs).
   Never invent facts not in the source; every relation must connect two extracted entities.
5. **Before claiming facts about the repo in a summary/report** — `growmos check "<claim text>"` grounds
   your claims against edges with provenance (evaluator–optimizer loop).
6. **Session end** — `growmos journal "<summary of the session>"` so the next session picks up here.

Store files are plain JSONL under `.growmos/` — commit them with your code. Do not hand-edit
`entities.jsonl`/`relations.jsonl` (use the CLI); prompts in `.growmos/prompts/` are yours to tune.
More: `growmos --help`, docs at https://github.com/codician-team/growmos.
<!-- growmos:end -->
