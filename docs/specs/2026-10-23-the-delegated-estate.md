# The Delegated Estate — tiered routing, cross-harness delegation, and visible state

**Status: PROPOSED — for the founder and an external consultant to evaluate. Not approved, not built.**
**Date: 2026-10-23 · Author: estate agent (pi) · Builds on:** the routing cost layer
(`docs/specs/2026-09-24-llm-routing-cost-layer.md`), the anticipatory router
(`docs/specs/2026-10-01-anticipatory-router.md`, APPROVED), the Battalion
(`docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md`, PROPOSED), the deterministic
verifier door (`docs/specs/2026-09-13-deterministic-verifier-door.md`, OPERATIONAL), the
problem-solving playbook (`docs/specs/2026-10-19-problem-solving-playbook.md`), the Face audit
(`docs/specs/2026-10-22-face-superpowers-audit.md`), and ADRs 0029, 0030, 0034, 0036.

**Nothing here claims something works.** Every number carries the command that measured it
(§11 Appendix A). Every statement about existing code carries a `file:line` citation (§11
Appendix B). Statements I could not measure are marked **[unverified]**. No secret value appears
anywhere in this document; keys are referenced by name only.

---

## 0. One page

**The wish.** Frontier models plan and reason and decompose a goal into sub-goals; mid models
create new files; the cheapest/free tier produces the diff; the plan is executed in parallel,
one sub-task per worker, across models *and* harnesses (Claude Code, opencode, pi); every
agent's position and ownership is known at all times; a session that dies mid-flight is resumed
without redoing work; the estate keeps driving until the work is operating; the routing is
"ultra intelligent" and "ultra resilient"; the whole thing must work like electricity — the
founder never chooses a model, never sees a mode switch, never waits on a laptop door; and
everything must be visible on **/fleet** and spoken on **face**, with monitoring.

**The honest answer.** About two thirds of the machinery already exists and is measured working:
a router with 35 live aliases and per-alias fallback chains (§2.1), a cost ladder and routing
matrix as versioned config (§2.2), a durability engine with checkpoints, rewind and signed
receipts (§2.3), a deterministic verifier with real gates (§2.4), a claim system that stops two
agents touching the same files (§2.5), a greenlane that proves work green and lands it (§2.6),
a Jev decision layer (§2.7), and three harnesses on this laptop that already support
non-interactive run, explicit model, machine-readable output and session resume (§2.8).

What does **not** exist anywhere in the tree is the thing the founder is actually describing: **a
unit of delegated work that crosses harness and model boundaries with a contract, an owner, a
price, a resume token and a live position.** Today everything is either (a) one harness doing
everything, (b) one Temporal session running one runner against one repo, or (c) a per-*request*
routing decision with no notion of "this request is step 3 of a plan".

**So the proposal is not "build intelligence".** It is one thin missing layer — the **Delegation
Contract** (§4.1) plus a **Task Graph** (§4.4) — plugged into the router, the verifier, the
claims and the greenlane that already exist. The intelligence lives in a **role→tier table**
(§4.2) and in the **hard-problem mechanisms** (§7); both are config and contracts, not new
infrastructure.

**The six hard problems the founder named** (§7), and the short answers:

| Hard problem | Why it is hard | Mechanism | Proving measurement |
|---|---|---|---|
| Feedback loops between models | agreement is not evidence; loops burn budget; a "five-model" quorum can be one model counted five times | bounded rounds, **family-diverse reviewers**, a deterministic gate between rounds, stop on gate-pass not on agreement (§7.1) | false-accept rate of a collapsed reviewer pool vs a diverse one, on the same packets |
| Which model to route to | cold start; fitness is task-class-specific; failure attribution is confounded | deterministic role→tier prior → measured per-lane posterior → Jev as arbiter **only when available** (§7.2) | a routing decision log; per-lane, per-class success table read from the action ledger |
| Credit running out mid-session | credit is an account property that changes between plan and step 7; half-funded plans lose paid work | pre-flight, budget reservation, a **degradation ladder** (frontier→mid→free→local), and "checkpoint and hand back" as a terminal state (§7.3) | a plan that loses a lane mid-flight and *finishes* on the next rung |
| Continuity and ownership | three clocks disagree (harness session, estate state, worktree); claims are issue-scoped and one-per-issue | one state row per sub-task in `estate.db`, the resume token, one issue = one claim = one packet (§4.7, §4.8) | SIGKILL a harness mid-sub-task; restart; the same sub-task resumes without redoing passed gates |
| Driving to completion despite setbacks | blind retry burns budget on deterministic failures; stopping early is the default failure | cause classification before reaction (environment / plan / execution / gate defect), a bounded setback budget, the estate's five-check "done" (§7.5) | a gate that fails twice is re-planned, not retried, and the plan's other sub-tasks continue |
| Resiliency routing | health checks that ask "can I connect?" cannot see saturation | latency/saturation health (not connect-refused), a warm standby door, load-shedding to the free tier (§7.6) | stop the primary door mid-plan; the plan completes on the standby |
| Portability and interoperability (the last challenge) | the estate's brain and hands are laptop-bound; the cloud side already runs a *second* router-side layer (ZeroEdge) that the local harness cannot share | late binding, **one policy and many renderers**, per-sphere lane discovery, transport extension instead of a second implementation, isolation-aware evidence (§4.11, §7.7, §7.8) | the same packet runs in two spheres with identical acceptance and different bindings; a config-drift check proves the spheres share one policy |

**Recommendation: Option A** (§5) — a thin delegation layer in `idp` that reuses the router, the
verifier, the claims and the greenlane. Estimated: 3–5 days to a first operational proof, then
steady. Net new always-on resources: **zero** (Decision 0034's ladder, rung "laptop just in
time"). Net new money: **≈ $0** — the executing tier is Groq's free `gpt-oss-120b` and the local
Ollama models, both of which answered a live call measured this session (§11 A4, A5).

**The bar the founder set — "smoothly and seamlessly like electricity"** — is taken literally
from the estate's own law: the Battalion spec §10 turns it into three testable requirements
(UX-01 no visible mode switch, UX-02 every edge case enumerated with a named degradation path,
UX-03 a floor lane that config cannot switch off). §6.5 maps those three onto this proposal,
because "invisible" and "always available" are properties of the *whole* path — router,
orchestrator, harness, gate — not of the new layer alone.

**The portability answer, in one paragraph (the founder's last challenge, 2026-10-23).** The
estate's brain and hands are laptop-bound today: the router is a local process
(`front.py` → `127.0.0.1:4000` → a local LiteLLM slot), the harnesses are local binaries, and the
substrate available locally is `temp_tree` — **no isolation at all** — while the cluster's
hardened `gvisor` rung is used by **0 pods**. The cloud side already runs a *second* router-side
layer, the **ZeroEdge** cost gateway, "off unless `ZEROEDGE_URL` is set", and the harness
inventory (2026-10-23, on `main`) explicitly leaves the one-of-each-layer question about it
unresolved. That is what "coupled to the current situation" looks like in code. The answer in this
proposal has four parts: **one policy and many renderers** (the lanes, tiers, budgets and health
classes are the portable artefact; each sphere's router renders them, and a config-drift check
refuses a divergence); **late binding** (a packet names a role and a capability, never a binary or
a lane key, so the same packet binds in a laptop and a cloud sandbox); **transport extension, not
a second implementation** (the estate's own rule from `platform/estate/memory/runtimes.json` — a
runtime that cannot speak MCP gets its tools from a link to the same bridge, never a bespoke
integration); and **one optimizer** (ZeroEdge folds into the cluster renderer under the same
policy, or stays off — never a second routing policy beside the platform's router, decision D9).
Evidence stays comparable across spheres because every gate verdict records the substrate it ran
under. Full mechanism and proof: §4.11, §7.7, §7.8.

**Ten decisions are needed** to start work; they are numbered D1–D10 in §10, each with options,
a recommended default, and what the choice costs. This document is written so that those ten
answers are sufficient to begin, and so a reader with no prior context can choose Option A, B
or C without asking a question this document fails to answer.

---

## 1. The wish, decoded into requirements

The founder's messages (2026-10-23) contain the requirements below. Each maps to what the
estate already has and to what is genuinely missing. **This table is the proposal in miniature**;
the rest of the document argues the "gap" column.

| # | Requirement (founder's words) | Already exists (citation) | Genuine gap |
|---|---|---|---|
| R1 | "truly ultra intelligent ultra resilient routing that truly standardises planning, execution and verification" | routing cost layer + anticipatory router (APPROVED) + the sovereign FSM `init→planning→tool_use→synthesis→terminal` (`AGENTS.md` §11 `[fsm]`) + the deterministic verifier door (OPERATIONAL) | No **task-level** standard: nothing says "this artifact class is produced at this tier and must pass this gate" |
| R2 | "plays well with our goals, subgoals, BDD, edge cases" | `declare_plan` / `add_bdd` / `address_edgecases` / `complete_goal` exist as the seven gates of the agent harness | The plan is per-agent and lives in a context window; it is not a first-class, shareable, machine-readable artifact a cheap tier can execute |
| R3 | "using Jev and ultra intelligent routing" | ADR 0030, `mcp/plugins/jev.py`, the `jev.decide` intent, `sovereign/consensus/`, the `estate.db jev_decisions` table | **Jev is not live in this environment**: `TYPESAFE_API_KEY` is unset, so every decision returns `{escalated: true, _fallback: "jev_unavailable", confidence: null}` (measured §11 A6). Tier policy must have a deterministic default that does not depend on it |
| R4 | "the most intelligent models should plan, reason, create goals, subgoals to the correct degree of decomposition" | The problem-solving playbook (2026-10-19) is already a model-agnostic seven-move method distilled from real transcripts | No *decomposition policy*: nothing defines what makes a good sub-goal split, and nothing bounds granularity |
| R5 | "invoke the cheapest models and harnesses if necessary to get it done" | Live aliases include free Groq (`gpt-oss-120b`), free OpenRouter (`nemotron-3.5-lightning:free`) and local Ollama (`llama3.2`, `moondream` for vision) — all in `lanes.json` | No **task→tier assignment**: the router picks a model per *request*, not per *artifact role* |
| R6 | "frontier, mid, cheapest/free tier" | `platform/llm/cost-ladder.yaml` rungs 0–3 and `platform/llm/routing-matrix.yaml` axes (resource tier × candidate volume × selection method × escalation pattern) | The matrix's `resource_tier` is a **compute** tier (local / router / flat-rate box / GPU), not a **capability** tier (frontier reasoner / mid author / cheap executor). The two are conflated |
| R7 | "the output most of the time should be a diff by cheapest tier; new file creations can be done by mid tier; frontier plans, reasons, assigns, invokes" | — | This rule exists nowhere. It is the sharpest and cheapest win in the whole message (§4.2) |
| R8 | "invoke parallel per sub-task to get things done faster" | Greenlane batches lanes (§2.6); `sovereign/engine/dag.py` is a **content-addressed diff DAG**, not a task DAG | No task-graph fan-out. `sovereign/engine/runners.py:159` `REGISTRY` = `echo, sleep, ask, burn, llm` — one runner, one repo, sequential steps (`workflow.py`) |
| R9 | "coordination and ownership to fully operational, considering agents and harnesses can fail mid-session for any reason" | Claims (`bin/claim-open`, `bin/claim-gate`), the `/fleet` claims panel, `bin/estate-checkpoint`, `bin/estate-work-audit` | Ownership is **per issue**, and the claims reader keeps the **newest claim per issue** (`backstage/plugins/fleetview-backend/src/fleetview_backend/claims.py:106-109`) — two agents cannot hold disjoint path claims on one issue. No per-sub-task owner, no "where is everyone", no resume token |
| R10 | "should know exactly where any agent is and where they left off" | `bin/estate-checkpoint` writes branch/HEAD/dirty files/open PR to the issue; `/fleet` shows claims with heartbeat age | Live *position* is visible per issue only, not per running sub-task, and not while the agent is mid-flight |
| R11 | "should be able to restart in interruptions to drive to fully operational" | `sovereign/engine/checkpoint.py` (rewind/recover/audit), Temporal session durability, `bin/estate-checkpoint` | Nothing joins a *delegated sub-task* to a resumable token. All three harnesses can resume (measured: `claude --resume`, `opencode -s/--session`, `pi --resume/-r`) — nobody uses it |
| R12 | "models running out of credit mid-session", "resiliency routing", "driving to completion despite setbacks" | Lane registry with error classes (`402/429/401` → dead/exhausted) and per-alias fallback chains | The **plan** has no funding model: a plan may start on a metered lane and die at step 7 with no credit and no rung to fall to |
| R13 | "smoothly and seamlessly like electricity" | The Battalion spec §10 already turns this into UX-01/02/03 with acceptance criteria | The bar has never been applied to the *end-to-end* path (router → orchestrator → harness → gate → /fleet → face) |
| R15 | "the core engine and intelligence needs to work across spheres and be fully portable anywhere"; "we can't be fully coupled to the current situation" | The estate's policy is already portable in principle (`AGENTS.md` §11 one block; `platform/estate/memory/runtimes.json` — "a new runtime is a new entry, not a new integration"); the cluster already runs `estate-mcp` (ns `mcp`) and the harness inventory already specifies `where: laptop | cloud | both` plus an `isolation` field | The *implementations* are bound early: local router (`front.py` → `127.0.0.1:4000`), local binaries, local worktrees, and a second cost/routing layer in the cluster (ZeroEdge) that the local harness does not share. There is no sphere-neutral unit of work and no per-sphere lane discovery |
| R16 | "cloud harnesses like zero edge … don't work with our local harness" | The estate's own interop law: a runtime without an MCP client gets a transport extension, never a second implementation (`runtimes.json`); opencode already speaks ACP | The harness registry has no `transports` or `resumable` field, and the "one of each layer" question for ZeroEdge is explicitly unresolved (harness inventory, 2026-10-23) |
| R14 | "monitoring and visibility to other systems like fleet and face" | `/fleet` claims panel; the Face at `catalogue.mumchimp.com/face/`; the live-mind event contract `estate.agent.event` (kinds `phase/tool/wait/done/steer/gate`) | The Face can run 64 **arg-free** intents by name but "cannot pass an argument to anything … cannot choose or steer or stop an agent, cannot start a fleet session, cannot claim work or land it" (Face audit §1). The plan layer has no voice/board surface, and no delegated decision is emitted as a live-mind row |

---

## 2. Current state — what already exists (citations in Appendix B)

### 2.1 The model door

`platform/llm/front.py` is a bytes-only TCP forwarder to a LiteLLM slot (4001/4002) chosen by
`~/.estate/router-state/active` (measured: `4002`, §11 A3). Live state at 2026-10-22T22:02:28Z
(`~/.estate/router-state/lanes.json`): **35 aliases served, 0 dropped**, providers carrying keys
for openrouter, deepseek, gemini, minimax, groq (×3 accounts), cerebras (×3), sambanova (×2),
nvidia, zai, moonshot, cohere, plus local `ollama` and the `claude-*` passthrough.

Per-alias fallback chains already exist and are configured: `deepseek → gemini → minimax → groq`,
`groq → cerebras → sambanova → nvidia → openrouter`, `voice → narrate → fast → groq`. The routing
cost layer (`docs/specs/2026-09-24-llm-routing-cost-layer.md`) and the anticipatory router
(`docs/specs/2026-10-01-anticipatory-router.md`, APPROVED 2026-10-01) already carry the doctrine:
lane registry held warm off the request path, error classes as facts, a compiled route table.

**Live proof the free tier answers:** a `groq` chat completion through the laptop router returned
`http=200 time=5.695s` when measured earlier in this session with the vault-loaded laptop router
key (§11 A4). Re-measured later without that key, the router answered `http=401` with an
explanatory body naming the vault entry it needs and stating that "lanes that carry your own
credential need nothing" — the guard rail works, and no key value appears in this document
(§11 A4).

### 2.2 Cost and routing policy as config

`platform/llm/cost-ladder.yaml` — four rungs (local_free $0/mo → router_metered $0.0000003 in /
$0.0000012 out per token → flat-rate Apple Silicon $69/mo → GPU burst $73–146/mo), with a `grade:`
field carrying provenance (`vendor-doc` vs `founder-supplied-unverified`).
`platform/llm/routing-matrix.yaml` — axes `resource_tier × candidate_volume × selection_method ×
escalation_pattern`, plus off-by-default toggles for three **named gaps** (`filter_depth` =
semantic intent routing, `pillar2_execute_python`, `pillar3_grind_tool`,
`pillar4_darwin_machines`), each labelled with the gap it waits for. The house discipline is
explicit: a rung's price is a config edit, never a Python literal; an axis that names a gap that
does not exist may not be switched on.

House routing policy lives in `AGENTS.md` §11 `[routing]`: `default = minimax`, `cheap = groq`
(free, request-metered), `consensus = [deepseek, minimax, gemini]`, with
`[cost] contract_max_usd_month = 150` and `[budget.usd_per_day] litellm 3.0 / consensus 1.0 /
vision 0.5 / ollama 0.0`.

### 2.3 Durable state, budgets, receipts

`sovereign/engine/` is ~9,800 lines and is the estate's durability plane: `workflow.py` (Temporal
`SessionWorkflow`: steps, budget, approvals, FSM cycle, halt at zero token budget until a signed
refill), `budget.py`, `receipts.py` (signed hash chain, HMAC under an estate key in the macOS
Keychain), `checkpoint.py` (rewind / recover / audit over a content-addressed Merkle DAG of
**diffs**, never snapshots), `dag.py`, `projection.py`, `undo.py`, `tracing.py` (Langfuse),
`tier_budget.py`, `free_lunch.py`, `offload_audit.py`, `routing_path_audit.py`,
`disagreement_escalation.py`, `candidate_selection.py`, `weighted_vote.py`,
`verifier_escalation.py`, `fallback_chain.py`, `jit_provisioning.py`, `cost_ladder.py`,
`routing_matrix.py`.

The doctrine is already written down: `sovereign/policy.py` parses the single `[toml]` block in
`AGENTS.md` §11, and `sovereign/tests/bdd/test_policy.py` fails when the code and the prose
disagree. **That is the pattern this proposal must follow**: a policy that lives in one config
block, checked by a test against the code that reads it.

### 2.4 Verification

`sovereign/verifier.py` (745 lines as of 2026-09-14) plus the deterministic verifier door
(`docs/specs/2026-09-13-deterministic-verifier-door.md`, OPERATIONAL, merged `65588127`), whose
acceptance suite runs **9 passed in 12.90s, exit 0**. The door exposes four verbs —
`propose_patch`, `verify`, `seal`, `admit` — that an agent can actually call. ADR 0029 makes
"done" five checks, none self-graded. `sovereign/engine/candidate_selection.py` refuses
best-of-N on domains with no real verifier and caps N at 3 for unverifiable domains (`VER-02`,
`VER-04`).

### 2.5 Ownership and coordination

The claim of record is a comment on an open GitHub issue, in exactly this form:
`CLAIM agent=<name> paths=<glob,glob> heartbeat=<UTC ISO time>`. `bin/claim-gate` refuses a change
with no claim, a closed issue, another agent's claim, or a file outside the claim's paths; it runs
in `ci-success`, the one check the merge queue gates on. `/fleet` shows live claims: who, what,
which paths, heartbeat age (`claims.py:192` `claims_snapshot`).

**A constraint that shapes the whole design:** the claims reader keeps the **newest claim per
issue** (`claims.py:106-109`). Two agents therefore cannot hold disjoint path claims on one issue —
the second claim shadows the first, and the first agent's files then fall outside "the" claim and
are refused by `claim-gate`. **Consequence: one sub-task = one issue.**

### 2.6 Landing

`greenlane/engine.py` is the only sanctioned path to `main`: a lane branch is proved green on top
of current `main`, the engine raises the pull request itself and fast-forwards `main` to the tested
commit; a red or conflicting lane keeps its branch and carries the reason on its head's `greenlane`
commit status. The engine models `Lane` (name, head, status, reason, attempts, FIFO sequence,
`judged_on` base sha) and `Batch` (base sha, tip sha, members). It is **one repo, one stack at a
time** — no fan-out across agents within a task.

### 2.7 The decision layer

ADR 0030 makes Jev the estate's one decision layer; `mcp/plugins/jev.py` calls
`https://api.typesafe.ai/v1/systemone` with model `jev-1.13.0`, a 2,000 ms timeout and a 0.7
confidence floor; the `jev.decide` intent exposes it to agents; decisions are recorded in
`estate.db jev_decisions` and read by `/fleet`. `docs/jev-capability-map.md` audits the estate for
binary decisions without confidence — exactly the pattern the founder wants Jev to fix.

**But Jev is not live here.** `TYPESAFE_API_KEY` is unset in this environment, so `jev.decide`
returned `{escalated: true, _fallback: jev_unavailable, confidence: null}` (§11 A6). The layer
degrades honestly (an escalation is not a "no"), which is right — but it means **no tier decision
may depend on Jev being available**. Jev is an override and an escalation route, never the primary
arbiter.

### 2.8 The harnesses that exist on this laptop

Measured (§11 A2): `claude` → `/Users/roseonyema/.local/bin/claude`; `opencode` →
`/Users/roseonyema/.opencode/bin/opencode`; `pi` → the nvm global `pi`; `ollama` →
`/usr/local/bin/ollama`. **Not installed:** `aider`, `gemini`, `cursor`, `codex`.

All three agent harnesses already expose what a delegation contract needs, measured from their own
`--help` (§11 A1):

| Capability | Claude Code | opencode | pi |
|---|---|---|---|
| Non-interactive run | `-p/--print` | `run <message>` | `-p/--print` |
| Explicit model | (config/alias) | `-m/--model provider/model` | `--model provider/id` |
| Machine-readable output | text/JSON | `--format json` | `--mode json` (`rpc` too) |
| Resume a prior session | `--resume <session-id>` | `-s/--session <id>`, `-c/--continue` | `--resume/-r`, `--session <path\|id>`, `--session-id` |
| Background / detach | `--bg` (prints an id for `claude attach/logs/stop`) | `serve` (headless server) + `--attach <url>` | — |
| Restricted tool set | `--allowedTools`, `--add-dir` | `--agent`, `--auto` (dangerous) | `--tools`, `--no-tools`, `--exclude-tools` |
| Agent personas | `--agents <json>` | `--agent`, `opencode agent` | — |
| Cost accounting | — | `opencode stats` | — |
| Standard protocol | — | `opencode acp` (Agent Client Protocol) | — |

**The substrate exists.** Nothing in the founder's wish needs a new model, a new vendor or a new
harness — it needs a contract that drives these three CLIs.

### 2.9 The surfaces the founder watches

* **/fleet** — Backstage plugin `backstage/plugins/fleetview-backend/`; serves the claims panel
  (`claims.py:192`), spend, and Jev decisions; the Face audit measured it live in the
  `backstage/catalogue` pod.
* **face** — the Face is a Backstage image in the cluster, live at `https://catalogue.mumchimp.com/face/`
  (200, 10,835 b), with the voice router on `127.0.0.1:8091` and the backend on `127.0.0.1:18790`
  on the laptop (launchd `ai.estate.fleetview-backend`); the pod forwards intent execution to the
  **laptop** over Tailscale (`fleetview-mac`) — so closing the Mac silences the Face's hands
  while its page survives (Face audit §1–§2). The Face can run 64 **arg-free** estate intents by
  name, and *cannot* pass an argument, steer or stop an agent, start a fleet session, or claim
  work (Face audit §1).
* **the live-mind bus** — `platform/event-bus/contract/estate.agent.event.json`: one subject
  family `estate.agent.<runtime>.<session_id>.<kind>`, kinds `phase | tool | wait | done | steer |
  gate`, phases `planning | executing | waiting | done | failed`, runtime enum
  `claude-code | sovereign | cyrus | otto | dagster | github-actions`, and the `tool.name` example
  in the contract is literally **`delegate`**. An adapter that emits a row the schema refuses fails
  CI. **The estate already has the vehicle for the delegation layer's monitoring; the contract
  already names the verb.**

---

## 3. What is genuinely missing — the six gaps

**Gap 1 — There is no unit of delegated work.** Every executor in the estate takes a *string*.
`sovereign/engine/runners.py` runners receive `(task: str, repo, step, steer)` and return
`{output, done, ask, tokens}`; the Temporal workflow runs them sequentially against one repo. A
sub-task with an owner, a budget, an acceptance predicate, a resume token and a path scope does
not exist anywhere.

**Gap 2 — No task-level tier policy.** The router chooses a model per request. The cost ladder's
rungs are compute classes. Nothing maps **"produce a diff" → cheapest tier**, **"create a new
file" → mid tier** or **"plan" → frontier tier**. The routing matrix's axes cannot express it,
because its `resource_tier` axis is a compute rung.

**Gap 3 — No cross-harness delegation.** `REGISTRY` (`runners.py:159`) is `echo, sleep, ask, burn,
llm`; the engine README claims a `claude` runner the registry does not contain. No code path
starts `opencode` or `pi` as a worker of a task, and no code path starts any harness *at all* on
behalf of another.

**Gap 4 — No fan-out, no join.** Greenlane merges lanes; the Temporal workflow is one session. The
`dag.py` DAG stores **diffs**, not tasks. Nothing expresses "these four sub-tasks may run at once
and must all pass before the parent proceeds".

**Gap 5 — Ownership stops at the issue.** A claim names paths on an issue; the newest claim wins
(§2.5). There is no per-sub-task owner, no live position ("which agent is where"), and no mapping
from a running harness process to a sub-task.

**Gap 6 — No plan-level funding or degradation.** A lane can die for credit (2026-10-01 kimi:
`429 … account suspended due to insufficient balance`, two retries, then failure — quoted in the
anticipatory-router spec §1). The router can fail over; the *plan* cannot, because the plan has
no notion of what it can afford to redo and what it can afford to continue.

---

## 4. Target design

### 4.1 The Delegation Contract (the one new artifact)

One JSON document, one schema (`docs/schemas/delegation-packet.schema.json`), versioned. It is
the only thing that crosses a harness or model boundary: written by a planner (frontier tier),
read by an executor (cheap tier) that has no other context.

```json
{
  "packet_version": 1,
  "id": "idp-7042/03",
  "parent": "idp-7042",
  "goal": "Add the retry budget to the router watchdog",
  "why": "plan step 3 of 5; satisfies plan criterion P3",
  "artifact_class": "edit_diff",           // new_file | edit_diff | test | plan | review | merge
  "role": "implementer",                  // planner | implementer | reviewer | verifier
  "requires": {                           // capability requirements, never a product name
    "tier": "cheap",                      // the artifact-tier table's answer for this class
    "harness_capabilities": ["non-interactive", "machine-output", "resumable"],
    "max_usd": 0.02
  },
  "binding": {                            // written by the binder at dispatch, per sphere
    "sphere": null, "harness": null, "lane": null, "model": null, "isolation": null, "price": null
  },
  "repo": "chidionyema/idp",
  "worktree": null,                       // assigned by the binder in the executing sphere
  "paths": ["platform/llm/watchdog.py"],   // the ONLY paths this packet may touch
  "context": [                            // a list of references, never a blob of prose
    "docs/specs/2026-10-23-the-delegated-estate.md#4.2",
    "platform/llm/watchdog.py"
  ],
  "preconditions": ["claim idp#7042 is live and holds these paths"],
  "acceptance": [                         // deterministic gates, run by the estate, not the model
    {"kind": "command", "cmd": "bin/idp-ci", "timeout_s": 900},
    {"kind": "diff_scope", "paths": ["platform/llm/watchdog.py"]}
  ],
  "budget": {"usd_max": 0.02, "tokens_max": 200000, "wall_clock_s": 1800},
  "resume": {"session_key": null, "checkpoint_ref": null},
  "escalate_if": ["acceptance fails twice", "model reports low confidence", "paths conflict"]
}
```

Rules that make it a contract and not a suggestion:

1. **A packet is self-contained.** The executor gets the goal, the paths, the acceptance and the
   context. It never asks the planner a question mid-flight; a question is an escalation (§4.3).
2. **A packet may not widen its own scope.** `paths` is the whole universe of files it may
   modify; the `diff_scope` acceptance proves it.
3. **Acceptance is a machine command, never a model's opinion.** The model cannot declare its
   work accepted; the estate runs the gate.
4. **A packet is idempotent.** Re-running after a crash converges rather than duplicates: the
   executor works in its own worktree and the merge is a rebase-onto-main by the greenlane.
5. **The packet is the unit of ownership and of spend.** One packet = one claim = one issue.
6. **A packet names a role and a capability, never a product** (§7.7, §7.8). The planner cannot
   write `groq/gpt-oss-120b` or `opencode` into the packet — it writes the artifact class, the
   role and the capability requirements. The **binder** resolves them per sphere at dispatch and
   writes the `binding` block. That is what makes the same packet runnable on the laptop and in a
   cloud sandbox with byte-identical bodies and different bindings, and it is why the tier table
   (§4.2) is the only place that decides which lane a role gets.

### 4.2 Artifact-role tiering — "the cheapest tier that can produce this artifact class"

This is R7, the sharpest win in the founder's message. The rule is a table, in the same discipline
as `cost-ladder.yaml` (config, versioned, with `grade:` and `source:`), and it lives in **one**
place: `platform/llm/artifact-tier.yaml`. The router's lanes are the *implementation* of each
tier; the table says which role uses which.

| Artifact class | Tier | Candidate lanes (live) | Why | Cost |
|---|---|---|---|---|
| `plan`, `decompose`, `reason`, `assign` | **frontier** | `claude-*` (frontier via the laptop's own session token, passthrough lane), `minimax_m31f`, `deepseek-v4-pro` | needs long-horizon reasoning and cross-file judgement | metered (rung 1), a handful of calls per task |
| `review` of a diff | **mid** | `minimax`, `glm`, `gemini`, `deepseek` | needs code comprehension, not planning | metered, small |
| `new_file` | **mid** | as above | a new file has no diff to copy; hallucinated scaffolding is expensive to undo | metered, small |
| `edit_diff` | **cheap** | `groq` (`gpt-oss-120b`), `cerebras`, `sambanova`, `nvidia`, `openrouter` free models, `ollama` local | a mechanical change with a known shape and a deterministic gate | **$0** on the free lanes |
| `test` generation | **cheap** | same | tests are mechanical; the gate is the suite | $0 |
| `merge`, `land`, `verify` | **none** | — | deterministic estate actions (greenlane, claim-gate, `bin/idp-ci`) | $0 |

Escalation rule when the cheap tier fails twice: **re-plan, do not retry**. A cheap model that has
failed the same gate twice has produced a *plan* defect, not a *luck* defect; the frontier tier is
asked to re-decompose that sub-task, and the packet's budget is not extended blindly (§7.5).

The router already guarantees the "never run out of cheap" half: `groq → cerebras → sambanova →
nvidia → openrouter` is a five-deep free chain, and `ollama` is local and free. **What does not
exist is the mapping from artifact class to that chain** — roughly forty lines of config.

### 4.3 The planner (frontier tier)

The planner's output is a **plan**: sub-tasks, each with an artifact class, a path scope, a
dependency, an acceptance predicate and a tier hint — in other words, a list of Delegation
Contracts. Its quality is judged by three checkable properties:

* **Decomposition granularity** — a sub-task must be checkable by one deterministic command. A
  sub-task needing two commands to verify is two sub-tasks. This is the operational meaning of
  "the correct degree of decomposition", and it is checkable, not a matter of taste.
* **Path disjointness** — sibling sub-tasks must claim disjoint path sets, because of §2.5. The
  planner is *required* to output disjoint sets; the claim gate then enforces what the planner
  promised.
* **No orphan criterion** — every plan criterion is claimed by at least one sub-task, and every
  sub-task's acceptance maps to a criterion. This is the same mechanical traceability check the
  Battalion spec used: a plan whose criteria and sub-tasks do not cover each other fails a test.

The planner is also where Jev belongs — **when it is available** (§7.2): the borderline cases
("is this a diff or a new file?", "does this sub-task need frontier reasoning?") are exactly the
bounded questions Jev is built for. When it is not available, the deterministic table decides and
the decision is recorded as low-confidence, so the estate can later measure how often the table
was wrong.

### 4.4 The task graph, fan-out and join

A plan is a DAG of sub-tasks with:

* **Join semantics** — a sub-task runs when all its dependencies' acceptance gates have *passed*,
  not when the parent's neighbours merely finished.
* **Fan-out bound** — three simultaneous limits, all measured rather than guessed:
  1. **claim disjointness** (structural, §2.5);
  2. **machine capacity** — the 2026-10-21 incident measured 4 cores, 8 GB RAM, load average 95
     (5-minute), 3.3–4 GB of 4–5 GB swap in use with 473M swapouts, and 13 claude processes at
     ~1.1 GB each. **A fan-out that ignores this reproduces the outage.** The bound is therefore a
     measured capacity ceiling (configurable; default: never exceed the laptop's measured
     sustainable headroom for the harness mix);
  3. **router health** — fan-out may not exceed the healthy capacity of the free chain.
* **Fan-in** — the join runs the parent's acceptance; a failed child re-enters the graph as a
  re-plan (§4.2), never as a silent no-op.

### 4.5 The adapter set (one per harness, three total)

Each adapter is a small, testable object with the same five verbs:

| Verb | Meaning | claude | opencode | pi |
|---|---|---|---|---|
| `plan_context` | environment facts the packet must carry | cwd, git state, `CLAUDE.md` | cwd, git state, `AGENTS.md` | cwd, git state, `AGENTS.md` |
| `invoke` | run the packet non-interactively | `claude -p "<prompt>" --allowedTools …` | `opencode run "<prompt>" -m <model> --format json` | `pi -p "<prompt>" --mode json --model <id>` |
| `capture` | parse the result into {diff, stdout, session_id, tokens} | text/JSON | `--format json` events | `--mode json` |
| `resume` | continue an interrupted sub-task | `claude --resume <session-id> -p …` | `opencode run -s <session-id> …` | `pi --resume <session> -p …` |
| `terminate` | stop a runaway sub-task | `claude stop <id>` (via `--bg` ids) | server / `--attach` | process kill |

Each adapter records the **session key** into the packet's `resume.session_key` on every
invocation, so an interrupted sub-task can be resumed by the same harness with the same context.
This is the concrete form of R11.

**The adapter must never let the model judge its own work.** The adapter returns a diff; the
estate runs the gate. If the model says "done", that is a claim — ADR 0029 check 1: no
self-declaration.

### 4.6 Verification, and the cheap tier's central risk

The cheap tier's failure mode is not crashing; it is producing a **plausible, wrong diff** that
passes a weak gate. Three defences, in order:

1. **Scope gate** — the diff touches only the packet's paths. Cheap, deterministic, and it catches
   the most common cheap-tier failure (drifting into neighbouring files).
2. **The real gate** — the estate's own test/acceptance command (`bin/idp-ci`, a feature suite, a
   lint), run by the estate, not by the model.
3. **Plan conformance** — the diff must satisfy the criterion it claims. Where the criterion is
   semantic ("the watchdog must treat a starved router as failed"), a **mid-tier** reviewer is
   used — and *that* review is itself checked by the deterministic scope and gate gates. Only if
   the mid-tier review is itself ambiguous does Jev enter (§7.1).

The ordering rule: **verification never gets cheaper than the artifact it verifies**, and a
reviewer may never be the same model family that wrote the artifact (independent verification,
mirroring `sovereign/consensus/`).

### 4.7 Resumable state and "where is everyone"

One state record per sub-task, in the estate's own database — not a vendor file. The lesson is the
estate's own: `bin/estate-checkpoint` exists precisely because the continuity layer used to be
keyed to one vendor's private transcript format, so a non-Claude agent got no checkpoint, no ticket
binding, and was invisible.

```
subtask_state {
  packet_id, issue, claim_ref, harness, model, tier,
  session_key, worktree, branch, head_sha,
  state:        planned | running | gated | blocked | done | failed,
  attempts, last_gate_result, last_heartbeat, owner_agent,
  cost_usd, tokens
}
```

Written on every state change and every heartbeat. It answers, on demand:

* **Where is agent X?** — the live row: harness, model, current gate, heartbeat age, tokens.
* **Where did they leave off?** — the last completed gate, the last diff sha, the session key.
* **Can it be resumed?** — `session_key` + `worktree` + `state`.
* **Who owns this path?** — the claim on the issue, and the packet's `paths`.

The board is the existing `/fleet` claims panel extended with a *plan* panel — this is where the
founder watches it happen (AGENTS.md §3: a safeguard is operational only when /fleet shows it
deciding on real agent actions). The voice path (Otto / the Face) answers "where is everyone" and
"restart plan" from the same rows (§6.4) — arg-free, because the Face cannot pass an argument
(§11 A11); "restart plan" means the newest plan, and addressing a specific plan by id needs an
argument, which is out of the Face's reach and stays on `/fleet`.

### 4.8 Ownership: one sub-task, one issue

Because the claims reader keeps the newest claim per issue (§2.5), parallel sub-tasks must not
share an issue. Therefore:

* **one sub-task = one issue = one claim**, with `paths` = the packet's path scope;
* the parent plan is a *meta-issue* listing the child issues (it holds no claim and no paths);
* fan-out is conflict-free by construction, and `bin/claim-gate` enforces it as it does today.

The cost of this choice is issue noise: a five-sub-task plan creates five issues. The alternative —
allowing several disjoint path-claims per issue — is a small change to `claims.py` and
`bin/claim-gate` (decision D6, §10), worth doing only if issue noise proves painful in the pilot.

### 4.9 Spend, budgets and the funding ladder

* Every packet carries `budget.usd_max` and `budget.tokens_max`; the executor spends against it and
  stops at the bound (the sovereign engine already halts at zero budget until a signed refill).
* The plan reserves a **total budget** at plan time; each sub-task's reservation is checked against
  the remaining reservation before it starts. A plan that cannot fund its remaining steps does not
  start half of them — it starts, or it does not (§7.3).
* Daily caps stay where they are: `AGENTS.md` §11 `[budget.usd_per_day]` and
  `[cost] contract_max_usd_month = 150`, enforced by `sovereign/policy.py` and its BDD test.

### 4.10 Placement

Decision 0034 puts workloads on the free tier first. This proposal adds **no new always-on
workload**: the adapter layer is laptop-local by necessity (it drives laptop-local CLIs), exactly
as `platform/llm/front.py` is laptop-local, and the state records live in the `estate.db` that
/fleet already reads. **Net new always-on resources: zero.** (A cluster-side planner, if the
founder wants planning to survive the laptop dying, is decision D8, §10.)

---

### 4.11 Spheres, harnesses and interoperability — the portability architecture

The estate's own vocabulary, from the harness inventory (2026-10-23, on `main`): "harness" means
three different layers — the **substrate** (where the work is isolated: `platform/executor/sandbox.py`'s
ladder `firecracker → gvisor → docker → temp_tree`), the **runtime** (what executes the agent's
turns: the CLIs, `agent-workforce`, the gateways), and the **door** (how work is handed in). A
change that swaps "the harness" can mean any of the three, and they are not interchangeable. The
same inventory records the measured facts that make portability urgent: on this laptop
`detect_backend()` returns **`temp_tree`** (no isolation; `firecracker` unreachable on macOS by
construction, no `runsc`, Rancher Desktop not running); on the cluster the `gvisor` RuntimeClass is
registered and **0 pods carry a `runtimeClassName`**; `zeroedge` is a **second cost/routing layer
next to the platform's own router** ("off unless `ZEROEDGE_URL` is set"), and the inventory
explicitly leaves the "one of each layer" question unresolved.

**That is the coupling the founder is pointing at.** The laptop's harness calls
`127.0.0.1:4000` → `platform/llm/front.py` → a *local* LiteLLM slot → local lanes. The cluster's
harness calls the cluster's LiteLLM in ns `llm`, optionally through the ZeroEdge gateway. Two
routers, two configurations, two cost policies, two lane registries — and a cloud harness that
does not understand the laptop's harness at all.

**The portability architecture in five rules.**

1. **The policy is portable; the implementation is local.** What must be identical in every
   sphere is the *policy*: the lane namespace and its aliases (`lanes.json`), the health classes and
   fallback chains, the artifact-role tier table (§4.2), the budget ceilings, and the acceptance
   contract. These live in the repo and in `AGENTS.md` §11's single policy block. What is local is
   the *renderer*: a router process in each sphere that reads the same policy and serves it over
   one protocol (OpenAI-compatible HTTP on the laptop at `127.0.0.1:4000`; the cluster's LiteLLM
   Service in ns `llm`). **One policy, many renderers** — never two policies.
2. **ZeroEdge's question gets answered here, not deferred.** ZeroEdge is an *optimizer* (cache,
   compress, route, enforce). It must be either (a) the cluster renderer's optimizer — one layer,
   in front of one router — or (b) off. The proposal's recommendation is (a): the cluster's
   ZeroEdge becomes the cluster renderer's optimizer, configured by the *same* artifact-tier and
   lane policy; the laptop keeps its local router with no second optimizer. What must never happen
   is the current state — an optimizer that changes routing in one sphere under a policy the other
   sphere does not have. (This is decision D9.)
3. **The harness registry gains three fields, and the delegation layer reads it.** The inventory
   already specifies the shape: `name`, `where: laptop | cloud | both`, and
   `isolation: temp_tree | docker | gvisor | firecracker`, read from the substrate that will
   actually run it, so a request for `firecracker` on this laptop is **refused with the reason**
   (`/dev/kvm absent`) instead of silently running in `temp_tree`. The delegation layer adds two
   more fields to each entry: `transports` (which of `cli-args`, `acp`, `mcp` the runtime speaks)
   and `resumable` (whether it can resume a session). The adapter set (§4.5) is then *the
   registry's transport column*, not a parallel invention.
4. **Interoperability rule, taken from the estate's own precedent.** The runtime manifest
   (`platform/estate/memory/runtimes.json`) states it: pi has no MCP client, so it "gets its tools
   from the 'tools' links instead, which point at the same bridge every other runtime runs" — *a
   runtime that cannot speak the protocol gets a transport extension, never a second
   implementation*. So a cloud harness that cannot be driven by CLI flags gets an MCP or ACP
   bridge (opencode already speaks `opencode acp`), **not** a bespoke executor. The estate's rule
   for "one of each layer" is the portability rule.
5. **Evidence is comparable across spheres only if the isolation is recorded.** A `temp_tree`
   acceptance result is weaker evidence than a `gvisor` one, and a laptop CI result is weaker than
   a greenlane proof on `main`. So every gate verdict recorded against a packet carries the
   substrate it ran under (`isolation`, `sphere`, `harness`, `lane`), and the plan's "operating"
   state still requires the estate's own bar (ADR 0029's five checks, a landed change, a production
   log line) — not merely a green gate somewhere.

**What this buys, concretely.** Moving the estate's execution from the laptop to the cloud becomes
a *binding* change, not a rewrite: the packets, the tier table, the lanes and the gates stay; the
sphere changes; the binder re-resolves harness, lane, isolation and price. And the estate already
has the doors in both spheres — the cluster runs `estate-mcp` (ns `mcp`), the laptop runs the
`fleetview-backend` and the executor intents — so the same three intents are reachable from either.

## 5. Options

### Option A — A thin delegation layer in `idp` (RECOMMENDED)

Add: `platform/llm/artifact-tier.yaml` (the role→tier table); a `delegation/` package with the
packet schema, the adapter set (claude/opencode/pi), the task graph and the state store; three new
intents (`plan.delegate`, `subtask.run`, `plan.status`); a `/fleet` plan panel; a Face voice
surface; and the plan/packet conformance tests.

*Reuses:* router (model choice), `bin/claim-gate` (ownership), `bin/idp-ci` and the deterministic
verifier (acceptance), `greenlane` (landing), `estate.db` (state), `AGENTS.md` §11 (budgets).

*Cost:* 3–5 days to a first operational proof. Money: ≈ $0 (the free tier executes).

*Risk:* the layer is laptop-local, so a laptop death loses in-flight sub-tasks — mitigated by the
state store in `estate.db`, by every packet being re-runnable from its issue, and by the
dual-plane decision D8 (a cloud sphere may bind the same packets; nothing is rewritten to move).

*Portability is inside Option A, not a later option.* The packet body is sphere-neutral by schema
(late binding, §4.11): it names a role and a capability, never a binary and a lane key. The
policy — aliases, tier table, budgets, health classes — is the portable artefact; each sphere's
router is a renderer of it, and a config-drift check refuses two spheres disagreeing. The harness
registry gains `transports` and `resumable` beside the `where` and `isolation` fields the harness
inventory already specifies. So "move to the cloud" is a binding change, not a rewrite (§7.8).

### Option B — Build "the Battalion" properly (the 2026-09-15 spec, completed)

Implement the full matrix from `docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md`:
all four rungs × candidate volume × selection method × escalation pattern × the three pillar gaps
(`execute_python` sandbox, grind tool, Darwin machines), semantic intent routing (`filter_depth`),
and the tier-routing this proposal adds.

*Strength:* one config surface that answers every future compute question, as the founder asked in
that spec.
*Cost:* far larger; the three pillar gaps are each a project; semantic intent routing is a
misclassification risk the spec itself names.
*Risk:* it duplicates the delegation layer unless the delegation layer is designed as one of its
cells. **The recommendation is A now, with the artifact-tier table designed as the axis the
Battalion wants** — so B later is a superset, not a rewrite.

### Option C — Extend the sovereign/Temporal engine into a multi-runner DAG

Make `SessionWorkflow` a DAG of sub-sessions, each with its own runner (harness + model), budget
and receipt; fan-out and join become Temporal-native; durability, approvals and budget halts come
for free.

*Strength:* the strongest continuity story (Temporal survives worker crash; receipts already form a
signed chain).
*Cost:* Temporal on the laptop, a runner registry that must grow real harness adapters (today it is
`echo, sleep, ask, burn, llm`), and the runner still returns `{output: str}` — a *string*, not a
diff — so the artifact contract is new anyway.
*Risk:* highest and slowest to first proof. It also puts the estate's one durability engine in
charge of work a laptop-local orchestrator can do today.

### Trade-off matrix

| Axis | A — thin layer | B — full Battalion | C — sovereign DAG |
|---|---|---|---|
| Days to first operational proof | **3–5** | 30+ | 15+ |
| New always-on resources | none | depends on rung 2/3 (paid) | none if laptop Temporal |
| Duplicates an existing estate layer | no | risk (routing, selection) | no, but extends one heavily |
| Continuity across harness crash | good (issue + state + session key) | good | **best** (Temporal) |
| Works with the claim system | **yes, natively** | yes | yes, with work |
| Founder-visible on /fleet and face | yes (new panel, new verbs) | yes | yes |
| Reversibility | high (one package) | low | medium |
| Fits "one of each layer" | **yes** | needs care | yes |
| Cost to the estate's operating burden | low | high | medium |

**Recommendation: A, designed so that B is a superset.** The deciding argument is the estate's own
law (AGENTS.md §6): *exactly one of each layer*. The router, the verifier, the claims and the
greenlane already exist; the missing layer is the delegation/task-graph layer. Building Option B
or C now would rebuild the router's job inside a new engine and violate that law.

---

## 6. Integration into the current stack

### 6.1 What plugs into what (and what must not be duplicated)

| Existing component | Its role today | What the delegation layer adds | What it must NOT do |
|---|---|---|---|
| `platform/llm/front.py` + LiteLLM | the single model door; per-request routing; per-alias fallbacks | asks it for the alias the *packet* names | never choose a model outside `lanes.json`; never hold a vendor key |
| `platform/llm/lane_registry.py`, `watchdog.py` | lane health, error classes, failover | consumes lane health as the fan-out bound (§4.4) | never implement its own health probe |
| `platform/llm/cost-ladder.yaml` | compute rungs and prices | adds `platform/llm/artifact-tier.yaml` (capability tiers) beside it | never restate a price; reference the ladder |
| `platform/llm/routing-matrix.yaml` | axes: tier × N × selection × escalation | the artifact-role table becomes the semantic `filter_depth` axis that is currently a **named gap** (`ROUTE-05`) | never enable `filter_depth` before the classifier exists |
| `platform/llm/action_ledger.py` | spend attribution by harness and model | the routing decision log of §7.2 reads it | never write spend rows directly |
| `sovereign/engine/workflow.py`, `runners.py` | one session, one runner, sequential steps | the delegation layer is a *peer* orchestrator; it may later call `sb start` for a durable long job | never fork the FSM or the budget logic |
| `sovereign/verifier.py` + deterministic verifier door | scoring; `propose_patch/verify/seal/admit` | acceptance gates call these doors | never re-implement a verifier |
| `sovereign/policy.py` + `AGENTS.md` §11 `[toml]` | budgets, routing aliases, caps | the artifact-tier table is a **new** `[artifact_tier]` block in the same policy source, with the same drift test | never put a price or an alias in Python |
| `bin/claim-open` / `bin/claim-gate` | the ownership contract | creates one claim per packet | never write a claim comment directly |
| `greenlane/engine.py` | the only path to `main` | packets land through lanes, never by hand | never `git push main`, never hand-raise a PR |
| `estate.db` + `/fleet` | claims panel, spend, Jev decisions | a **plan panel**: sub-task states, owners, heartbeats, gate verdicts | never a second store of claim truth |
| `platform/event-bus/contract/estate.agent.event.json` | one live-mind row schema, one subject family | the layer emits `phase/tool/wait/done/steer/gate` rows per packet | never invent a second event schema |
| `estate-memory` (cortex) | one memory plane for every runtime | plan and decision records are written through `remember` | never write to `~/.claude` or a vendor directory |
| Otto / the Face | the founder's doorway | "where is everyone", "plan status", "restart plan" | never a form, never a required argument |
| The other sphere (the cluster: LiteLLM in ns `llm`, the ZeroEdge gateway, `estate-mcp` in ns `mcp`) | the cluster is a **sphere**, not a copy: it has its own router, its own optimizer and its own intent door | treats every sphere as a **renderer of one policy** (the same aliases, tiers, budgets); the binder resolves harness, lane, isolation and price per sphere (§4.11) | never assume the laptop's router exists; never let ZeroEdge become a second routing policy (D9); never bind a packet to a harness the sphere's substrate cannot run (§7.7) |

### 6.2 The data flow

```
 founder (voice)  ──▶ Face / Otto ──▶ plan.delegate intent
                                      │
                 ┌────────────────────┴─────────────────────┐
                 │  PLANNER (frontier tier)                 │  via a router alias verified live
                 │  goal ─▶ plan (criteria, sub-tasks)       │  context: policy, tier table, claims
                 └────────────────────┬─────────────────────┘
                                      │  plan = list of Delegation Contracts (disjoint paths)
                    ┌────────────────┼─────────────────┬────────────────┐
                    ▼                ▼                 ▼                ▼
             ┌───────────┐    ┌───────────┐     ┌───────────┐    ┌───────────┐
             │ subtask 1 │    │ subtask 2 │     │ subtask 3 │    │ subtask 4 │  ← one issue + one claim each
             │ cheap     │    │ cheap     │     │ mid       │    │ cheap     │
             │ opencode  │    │ pi        │     │ claude    │    │ opencode  │
             └─────┬─────┘    └─────┬─────┘     └─────┬─────┘    └─────┬─────┘
                   │ diff          │ diff            │ diff          │ diff
                   ▼               ▼                 ▼               ▼
             ┌────────────────────────────────────────────────────────────┐
             │ GATE (deterministic: scope + bin/idp-ci)                   │ ← estate runs it
             └──────────────────────────┬─────────────────────────────────┘
                                        │ all green
                                        ▼
                          lane ─▶ greenlane ─▶ main ─▶ Flux ─▶ production
                                        │
              estate.db subtask_state ─┴─▶ estate.agent.event rows ─▶ /fleet plan panel
                                        │                              └─▶ Face / Otto voice
                                        └─▶ action_ledger (spend + outcome)
```

### 6.3 New intents and new state — the smallest possible surface

Three intents, in the estate's existing YAML registry (`~/.estate/intents/`, §7 of AGENTS.md):

| Intent | What it does | Who calls it |
|---|---|---|
| `plan.delegate` | takes a goal, returns a plan (criteria + sub-tasks) and opens one issue + claim per sub-task | Otto/Face, an agent, `/fleet` |
| `subtask.run` | executes one packet in its worktree on its harness, runs the acceptance gates, writes the state row, lands or blocks | the plan driver (and Otto/Face "restart") |
| `plan.status` | reads the state rows and answers "where is everyone / what is blocked / what did it cost" | `/fleet`, Otto/Face |

Two new tables in `estate.db` (the database `/fleet` already reads), following the `jev_decisions`
pattern:

```
plan_state    { plan_id, issue, goal, state, criteria_json, created_at, owner_agent }
subtask_state { packet_id, plan_id, issue, claim_ref, harness, model, tier, session_key,
                worktree, branch, head_sha, state, attempts, last_gate_result,
                last_heartbeat, owner_agent, cost_usd, tokens }
```

Nothing else changes shape. `estate.db` is already the estate's state of record for what `/fleet`
shows, and the Face's backend already reads it.

### 6.4 Monitoring and visibility — /fleet, face, otto, and the bus

The founder asked for two things here: **monitoring** (the estate can see what the layer decided)
and **visibility to other systems like /fleet and face**. The estate already has the vehicle for
both: the live-mind event contract and the two surfaces.

**The bus (monitoring).** Every packet emits `estate.agent.event` rows — the schema's `kind`
vocabulary already covers the whole lifecycle (`phase`, `tool`, `wait`, `done`, `steer`, `gate`),
and its own example names the verb `delegate`:

| Moment | Row |
|---|---|
| packet planned | `kind=phase, phase=planning` |
| worker started | `kind=tool, tool={name: "delegate", target: "<packet id>"}` |
| worker waiting on a gate | `kind=wait` |
| a gate decided | `kind=gate` (pass/refuse) — this is the "safeguard deciding on a real agent action" row AGENTS.md §3 asks for |
| packet done | `kind=done, phase=done` |
| packet blocked or failed | `kind=done, phase=failed` |
| human steer | `kind=steer` |

One schema change is required: the contract's `runtime` enum
(`claude-code | sovereign | cyrus | otto | dagster | github-actions`) has no value for the
orchestrator itself, so a value such as `delegation` is added. That is a one-line schema change
with its CI consequence intact: *an adapter that emits a row this schema refuses fails CI.*

**/fleet (the board).** One new panel beside the existing claims panel:

* **Plans** — one row per plan: state, number of sub-tasks, money spent, elapsed time.
* **Sub-tasks** — one row per packet: harness, model, tier, state, last gate verdict, heartbeat
  age, owner, and *the diff link*. This is where "know exactly where any agent is and where they
  left off" becomes a screen instead of a question.
* **Decisions** — every tier decision with the evidence that justified it (which lane, which
  rule, which prior), so the founder can see the routing *thinking*, not just the result. This is
  also the raw material for §7.2's measurement.
* **Gates** — pass/refuse per packet, streamed live.

**The Face / Otto (voice).** The Face can run 64 arg-free estate intents by name and *cannot*
pass an argument (Face audit §1). That constraint shapes the voice design:

* `plan status` → "Plan 7042: 3 of 5 sub-tasks green, one blocked on the router lane, 40 cents
  spent."
* `where is everyone` → the same rows, spoken, naming each agent, its harness, and what it is
  doing right now.
* `restart plan` → re-drives blocked sub-tasks from their recorded resume token (arg-free: the
  most recent plan with something blocked).
* `why did you use that model` → the recorded decision evidence, spoken in one sentence.

Because the Face cannot take arguments, the arg-free verbs always refer to *the* current plan —
which is exactly the "electricity" property (§6.5): the founder never assembles a command line.
Specific plans are addressed on the board, where the specificity is free.

**A dependency the founder should know about (measured).** The Face's intent execution is
forwarded from the cluster pod to the **laptop** over Tailscale (`FLEET_INTENTS_URL →
fleetview-mac`, Face audit §2). A sleeping Mac therefore silences the Face's hands while its
page survives. Since the delegation layer is also laptop-local (§4.10), the Mac is a
single point of failure for *voice reachability* — not for the work (§7.6 covers the work).

### 6.5 "As seamless and reliable as electricity" — the three testable properties

The founder's bar is not a feeling; the estate already turned it into three requirements
(Battalion spec §10). Applied to this proposal end to end:

* **UX-01 — no visible mode switch.** The founder never chooses a model, a harness or a tier. The
  call shape in is a goal; the response shape out is a plan, whatever cell served it. Only the
  trace shows which lane ran. **Acceptance:** the same goal issued through `plan.delegate` under
  five different tier-table cells produces schema-identical output; only the trace differs.
  (This is why the tier table is a *config* the estate owns, not a parameter the founder sets.)
* **UX-02 — edge cases are enumerated, not discovered in production.** The named list for this
  layer: cold start beyond the JIT budget; mid-request lane eviction; budget breach mid-sub-task;
  verifier timeout; **all lanes down simultaneously**; config hot-reload mid-sub-task; a
  malformed artifact-tier edit that would disable every cheap lane at once; a harness crash
  mid-sub-task; a laptop sleep mid-fan-out; two packets claiming overlapping paths; a reviewer
  pool collapsed onto one model family. Each gets a named, tested degradation path — never an
  unhandled error surfaced to the requester.
* **UX-03 — a floor that cannot be switched off.** The always-on local lane (`ollama`, the
  `ROUTE-06` floor) is the floor the schema itself enforces, not a config choice. Concretely: a
  config write that would leave zero cheap lanes reachable is rejected **at the schema layer**,
  so the write never lands. The cheap tier is the relief valve when the machine saturates
  (§7.6) and it cannot be switched off.

Two consequences the founder should be told plainly: (a) UX-02's honest reading is "the estate
degrades visibly and keeps working, but it is never invisible-and-broken"; (b) the "electricity"
property is a property of the **whole chain** — router, orchestrator, harness, gate, board — and
the 2026-10-21 outage (§7.6) is the estate's own proof that a single front door breaks it. That
is why §7.6 is in this proposal and not deferred.

### 6.6 Compatibility and migration

* **Harness configs are not changed.** `platform/llm/router_catalog.py` already writes the
  router's aliases into every installed harness's picker, so the harnesses already speak the
  router's model names.
* **The router's config is not changed in phases 1–3.** The artifact-tier table only *names*
  aliases that `lanes.json` already serves, and a check refuses an alias the live registry does
  not serve — a check, not a comment.
* **`AGENTS.md` §11 gains one `[artifact_tier]` block**; `sovereign/policy.py` parses it; the
  existing drift test (`sovereign/tests/bdd/test_policy.py`) is extended to it. The policy stays
  in one place, as the law requires.
* **`/fleet` gains a panel; the Face gains four verbs.** No new service, no new deployment, no
  new port.
* **Nothing existing is removed.** If the layer is switched off, the estate is exactly as it is
  today — which is the reversibility argument for Option A.
* **Moving a sphere is a binding change, not a rewrite (§4.11, §7.8).** The packets, the tier
  table, the lanes and the gates are portable; only the binding changes. Two things make that
  true and both are new work: a **config-drift check** that compares the effective policy of every
  live sphere and refuses a divergence, and the harness registry's `where` / `isolation` /
  `transports` / `resumable` fields (the first two already exist in the harness inventory spec of
  2026-10-23), so the binder can refuse a binding the sphere cannot honour.

### 6.7 Integration sequence (no big bang) and acceptance criteria

Each phase is a claim, a lane and a green proof; each phase's acceptance is a measurement.

| Phase | What ships | Acceptance criterion (measurable) | Days |
|---|---|---|---|
| 0 — observe | a read-only shadow mode that *predicts* the tier each real task would have used, and records the prediction | 50 real tasks classified; the prediction log published; **no change to any execution path** | 1 |
| 1 — the contract | `delegation-packet.schema.json`, the artifact-tier table, and their tests | schema test green; **every tier-table alias is present in the live `lanes.json`**; the tier table is parsed by `sovereign/policy.py` and the drift test fails when they disagree | 1 |
| 2 — one adapter | the `opencode` adapter (`invoke`/`capture`/`resume`), in shadow mode beside the normal path | on 10 real `edit_diff` sub-tasks: the cheap diff is produced, its scope gate passes, and its acceptance gate result is recorded — with **no** adoption | 1–2 |
| 3 — one real delegated sub-task | a two-sub-task plan, one per tier, landed through the greenlane with the claim gate live | the plan's acceptance passes; `claim-gate` green; the change lands on `main` via the lane; the state rows and the live-mind rows are visible on /fleet | 1 |
| 4 — fan-out | three or four concurrent sub-tasks, with the measured machine-capacity bound live | a fan-out at the bound completes with no swap pressure above the 2026-10-21 baseline; killing one worker mid-flight leaves the plan completable by resume | 1 |
| 5 — voice and monitoring | the four arg-free Face verbs, the /fleet plan panel, the decision log | the founder can ask "where is everyone" and get the truth from the board's own rows; a tier decision can be explained after the fact with its evidence | 1 |
| 6 — spheres | the config-drift check; the registry's `transports`/`resumable` fields; one packet bound in a second sphere | the same packet body runs in two spheres, both pass the **same** acceptance commands, the bindings differ, no path/binary/key crosses spheres; the drift check is green across the live spheres | 1–2 |

**Total: 6–9 days, one operator, no new always-on cost.** The phases are ordered so that phase 0
and phase 1 are worthless on their own but make every later phase cheap.

---

## 7. The hard problems (the founder's emphasis), each with a mechanism and its proof

### 7.1 Feedback loops between models

**The failure.** A frontier model plans; a cheap model executes; a mid model reviews; the frontier
reads the review and rewrites the plan. That loop is where two things go wrong: (a) **correlated
error** — the reviewer shares the author's blind spot and "confirms" it, and the loop converges on
a wrong answer with high apparent confidence; (b) **budget spiral** — each round costs more than
the last, and the loop stops when money runs out, not when the work is right.

**Why it is hard.** Agreement between models is not evidence, and the estate already has the
measurement to prove it: `sovereign/engine/disagreement_escalation.py` and
`sovereign/consensus/decide.py` exist because a quorum of models can agree and still be wrong.
There is also a specific, citable trap in the current configuration: the fallback chain
`groq → cerebras → sambanova → nvidia → openrouter` serves the **same `gpt-oss-120b` weights**
across several providers (`llm/config.yaml` lists `gpt-oss-120b` under groq, cerebras and
sambanova). **A "five-model quorum" over that chain is one model's opinion counted five times.**
That is precisely the kind of thing "ultra intelligent" instinct is reaching for.

**Mechanism.**
1. **Bound the rounds** in config (`max_rounds`, default 2), and make the stop condition a
   **deterministic gate passing**, never "the models agree".
2. **Diversity by construction**: the reviewer pool is drawn from *distinct model families*, and a
   pool that would collapse onto the same weights (as the `gpt-oss-120b` chain does) is refused by
   a config check, not by good intentions.
3. **Independence of context**: the reviewer sees the artifact and the criterion, not the author's
   reasoning (otherwise it anchors on it).
4. **Escalate on disagreement, do not average**: disagreement between two families is a signal to
   escalate to the frontier tier, not a reason to compute a mean. Jev is the tie-breaker when
   available (§7.2); when it is not, the disagreement escalates to a human — never to a coin flip.
5. **Cost bound**: each round's spend is charged against the packet's budget; the loop stops when
   the budget is spent and the state becomes `blocked`, visibly.

**Proving measurement.** Take one real plan; run the loop with the reviewer pool deliberately
collapsed onto one model family, and again with two families; record the false-accept rate on the
deterministic gate. The claim "diversity matters" is only true if the collapsed pool's
false-accept rate is measurably higher.

### 7.2 Deciding which model to route to

**The failure.** "Ultra intelligent routing" invites a classifier that picks the model per request.
The estate already tried this and named the gap: `filter_depth` (semantic intent routing) in
`platform/llm/routing-matrix.yaml` is **off by default and labelled a named gap** (`ROUTE-05`),
with the reason written in the file — *misclassification ships a wrong answer on the cheap path, a
real cost, not a free filter*. The anticipatory router's own incident stands behind it: on
2026-10-01 a raw vendor model group (`moonshot/kimi-k3`) with no fallback chain took two retries to
fail with `429 … account suspended due to insufficient balance`.

**Why it is hard.** (a) **Cold start** — before any outcome data exists, the routing policy is a
prior; (b) **fitness is task-class-specific** — a model good at mechanical edits may be bad at
schema design, and one global score hides that; (c) **the feedback is delayed and confounded** — a
failure may be the model's fault, the gate's fault, the harness's fault or the context's fault, and
attributing it wrongly poisons the policy; (d) **the router already has a strong prior**: the alias
fallback chains encode operational knowledge (which vendor dies how) that a learned policy would
have to relearn, badly.

**Mechanism — a prior, a posterior and an arbiter, in that order.**
1. **Prior (deterministic, always available)**: the artifact-role table (§4.2). Not a guess: it is
   the founder's own rule expressed as config, and it is *safe by construction* — the cheapest tier
   only ever does work whose acceptance is a machine command.
2. **Posterior (measured, never assumed)**: per lane, per artifact class, the outcome table read
   from the existing `platform/llm/action_ledger.py` (which already attributes spend and outcomes
   by harness and model) and from the gate results recorded per packet. Only lanes with a
   *measured* success rate move off the prior. The policy is a **bandit over the prior**, and the
   estate already has the discipline for it in `sovereign/engine/flip.py` and
   `candidate_selection.py`.
3. **Arbiter (Jev, when available)**: only for the genuinely ambiguous cases, and only as an
   *override with a recorded confidence*. Because Jev is currently unavailable (§2.7), the policy
   must work without it — and must record, for each decision, what it *would* have said, so the
   estate can measure the arbiter's value when the key lands.
4. **Never route to a lane whose health is unknown**: the lane registry's state (`ready`,
   `cooling`, `dead`) is a hard gate, not a hint. This is the anticipatory router's doctrine
   applied at the task level.

**Proving measurement.** A routing decision log: for every packet, {artifact class, chosen alias,
the evidence that chose it, the gate outcome, the cost}. After N packets the table "cheap-tier
success by artifact class" is a measurement, not a belief — and it is the input to the first
policy change.

### 7.3 Models running out of credit, mid-session

**The failure.** The estate has already lived this: on 2026-10-01 a lane's account was out of
balance "long before that request"; the router did not know, spent two retries finding out, and
had nowhere to send the work because a raw vendor model group has no fallback chain (anticipatory
router spec §1). Today a *plan* can start on a metered lane and die at step 7 with an empty
account, taking the plan's continuity with it.

**Why it is hard.** Credit is not a property of the request; it is a property of the *account*, and
it can change between the plan and the seventh step. It is also invisible: an HTTP 402 arrives
after the work is done. And there is a second-order failure — **half-funded plans**, where some
steps are paid for and the paid-for work is lost.

**Mechanism.**
1. **Pre-flight**: before a plan starts, the lanes it will use are probed for *credit and health*
   (the lane registry already distinguishes `402 / insufficient balance / suspended → dead
   (credit)` from `429 → exhausted` — the classes exist; the pre-flight does not).
2. **Reservation**: the plan reserves its total budget up front, and each sub-task's reservation is
   drawn against it. A plan whose remaining steps cannot be funded **does not start** — the
   anti-half-funded-plan rule.
3. **Degradation ladder, with declared minimums**: each artifact class declares the *minimum
   viable tier* (an `edit_diff` may fall to the local Ollama model; a `plan` may not fall below the
   frontier tier without re-planning). When a lane dies mid-plan, the sub-task falls to the next
   rung of its own chain and the event is recorded — the founder sees "step 3 re-routed from
   `groq` to `ollama`" on /fleet, not a failure.
4. **Checkpoint and hand back (a terminal state, not a crash)**: if no rung can serve the class, the
   sub-task stops at `blocked` *with its state, its diff and its session key intact*, so the work
   resumes when credit returns — it is not lost.
5. **Cost-bounded retries**: a retry after a credit failure only ever goes to a *different* lane
   (the chain), never the same one; and a credit failure is never counted as a model-quality
   failure, so it never pollutes the outcome table of §7.2. This is the estate's own law: *a
   skipped leg is not a failed leg* (`docs/decisions/2026-09-04-a-skipped-leg-is-not-a-failed-leg.md`).

**Proving measurement.** Drain the credit of one lane (or point one alias at a dead account), run
a plan that uses it, and show the plan completing on the next rung with the re-route recorded.

### 7.4 Continuity and ownership

**The failure.** The estate's own history: the continuity layer was keyed to one vendor's private
transcript format, so "an agent that is not Claude Code has no Stop hook, no JSONL and no
session_id, so it gets no checkpoint, no ticket binding, and is invisible" — the exact words of
`bin/estate-checkpoint`'s docstring, which exists because 55 commits of a *non-Claude* agent's work
were invisible to it.

**Why it is hard.** Continuity has three independent clocks — the harness session, the estate's
state, and the git worktree — and they can disagree. Ownership has a second problem: the claim
system is issue-scoped and one-claim-per-issue (§2.5), so the moment work is divided, ownership
must be divided too.

**Mechanism.**
1. **One state of record per sub-task**, in `estate.db` (§4.7), written on every transition — not
   in a vendor file, not in a runtime's private directory.
2. **The resume token** = (issue, claim, worktree path, harness, session_key, last passed gate).
   Every harness supports resumption natively (§2.8) — measured, not hoped for.
3. **Ownership = claim = issue = packet paths** (§4.8), enforced by the existing `bin/claim-gate` in
   `ci-success`.
4. **Heartbeats** refresh the claim; a stale heartbeat releases the claim and the sub-task is
   re-drivable by anyone (the estate's existing rule, unchanged).
5. **Position is derived, not narrated**: "where is agent X" is a query over the state rows, so it
   cannot drift from reality the way a prose report can.

**Proving measurement.** Kill a harness mid-sub-task (SIGKILL the process), restart the plan, and
show: the same sub-task resumes (same issue, same claim, same worktree, same session key), the
already-passed gates are not re-run, and the plan finishes without a second claim.

### 7.5 Driving to completion despite setbacks

**The failure.** Agents stop. They stop at the first hard step; they report a green CI as done;
they re-run a failing command hoping for a different answer; they hand back a half-finished
thing. The estate already has the law against each of these (ADR 0029's five checks, AGENTS.md §3's
"proof, not assertion", §6's one-of-each-layer) and the failure is not knowing the law — it is
having no *mechanism* that makes stopping impossible without a human.

**Why it is hard.** "Retry until success" is unbounded and can burn the budget on a deterministic
failure. "Escalate on the first failure" is the opposite extreme and stalls on the first setback.
The right answer is a *budgeted, cause-aware* loop, and cause-aware needs the failure to be
classified — which is what the estate's error-class discipline (`402 → dead (credit)`,
`429 → exhausted`, `401 → dead (auth)`, `timeout → degraded`) already does for lanes and does not
yet do for tasks.

**Mechanism.**
1. **Cause classification before reaction.** Every gate failure is classified into:
   *environmental* (lane dead, machine saturated, network) → re-route or fan-in, no re-planning, no
   budget charge; *plan defect* (the sub-task was wrong) → re-plan with the frontier tier;
   *execution defect* (the model did the wrong thing) → re-plan with a different tier or a
   different harness; *gate defect* (the gate itself is wrong) → raise a defect against the gate,
   do not re-run the task.
2. **Setback budget**: per sub-task, a bounded number of re-plans (default 2) and a bounded number
   of re-routes (default: the length of the lane's fallback chain). Exceeding either escalates
   *visibly* to a human with the full state — it never loops.
3. **The done-bar is the estate's, not the agent's**: a sub-task is done when its acceptance
   command exits 0 **and** the parent plan's criterion is satisfied **and** the change is landed
   through the greenlane and observed in production (AGENTS.md §3: "a real production log line is
   the only done").
4. **No silent no-op**: every state transition is written; a sub-task that ends without an
   acceptance result is `failed`, never `done`.
5. **The plan's completion is a first-class state**: `plan.state ∈ {planned, running,
   partially_blocked, landed, operating}` — so "is it operational?" is a query, not a narrative.

**Proving measurement.** Run a plan whose step 2 fails the gate twice with a deterministic cause.
Show: attempt 1 → classified → re-planned (not blindly retried) → attempt 2 → if it still fails, the
sub-task escalates with its state, and the *plan* continues with the remaining independent
sub-tasks instead of stalling.

### 7.6 Resiliency routing

**The failure, measured.** On 2026-10-21 every agent session on the founder's Mac (Claude Code and
pi) stalled or timed out. The local LiteLLM router at `127.0.0.1:4000` was the single path for
every harness. Its health check took 4.2 s, and for 2 h 20 min the watchdog logged repeated
`probe slow curl=28` timeouts. The router was **starved, not crashed** — and because `front.py`
fails over only on *connect refused* or a 5 s connect timeout, **a starved router that still
accepts connections was never skipped**. Load average peaked at 95 on 4 cores with 8 GB RAM and
3.3–4 GB of swap in use.

**Why it is hard.** Health checks that ask "can I connect?" cannot see saturation. Failover that
switches on connection error cannot see a slow-but-alive upstream. And a single front door is
exactly what "ultra resilient" must not be.

**Mechanism.**
1. **Health is latency-and-saturation, not connect-refused.** A lane is `degraded` when its p95
   latency or its queue depth crosses a threshold, and `degraded` lanes are not chosen for new
   fan-out. This is the anticipatory router's `degraded` class, applied to the *front* door that
   failed in 2026-10-21.
2. **A warm standby door.** The OKE router (`https://llm.mumchimp.com`) answers in ~0.6 s but
   currently has **no `claude-*` passthrough lane and does not accept the laptop caller key** — so
   today nothing can fail over to it. Making it a real standby (a keyed lane that accepts the
   laptop's key, plus a `claude-*` passthrough) is a small, concrete piece of work with a large
   payoff, and it is *already the design* in `docs/specs/2026-09-24-llm-routing-cost-layer.md`.
3. **Load-shedding to the free/local tier.** When the laptop's measured headroom falls below the
   floor (the 2026-10-21 numbers are the baseline: load, swap, RSS of the harness processes), the
   orchestrator moves new work to `ollama`/free lanes and *stops* starting new fan-out. This is
   the tier ladder's most valuable property: the cheap tier is not only cheaper, it is the
   **relief valve** when the machine is saturated.
4. **No single front door for the executor**: each harness may be pointed at the local router or
   the OKE router; the orchestrator's health view covers both, and the harness's config is
   rewritten by the existing `router_catalog.py` mechanism rather than by hand.
5. **Circuit breaker, with the estate's own precedent**: `platform/llm/request_ceiling.py` and the
   lane registry's `allowed_fails`/`cooldown_time` are the pattern; the orchestrator reads them
   rather than duplicating them.

**Proving measurement.** Saturate the primary door (or stop it) while a plan is running with three
sub-tasks in flight, and show: the in-flight sub-tasks finish (or are re-routed and finish), the
plan completes, and the /fleet plan panel shows the re-route with its cause.

### 7.7 Portability — the same intelligence in any sphere

**The challenge.** The estate's brain and hands are laptop-bound today: the router is a local
process, the harnesses are local binaries, the worktrees are local directories, the Face executes
its intents by forwarding to the laptop over Tailscale. The founder's requirement is that **the
core engine and the intelligence are portable**: they must work in any sphere — the laptop, the
cluster, a cloud sandbox, a CI runner, a just-in-time cloud box — and **the lanes available
(free / cheap / frontier) must be discoverable per sphere**, not hardcoded.

**Why it is hard.** Portability is usually attempted by moving the *implementation* everywhere and
hoping the behaviour follows. Here it fails for a specific reason: the implementation is
**bound early** — a packet that names `opencode` and `groq/gpt-oss-120b` is only meaningful on a
machine that has that binary and that lane key. Change sphere and the packet is meaningless, even
though the *intent* of the packet ("add the retry budget to the watchdog, these paths, this
acceptance") is portable.

**Mechanism — bind late, discover lanes, carry state in the portable medium.**
1. **A packet declares requirements, not bindings.** `artifact_class`, `paths`, `acceptance`,
   `capability_requirements` (needs: file-edit, needs: long-context, needs: local-fs, needs:
   network-egress, needs: git) — and *never* a machine-specific path, binary or key. The
   `harness` and `model` fields in §4.1 become **optional hints**, resolved at bind time. A packet
   with an absolute path from sphere A is a schema violation, refused by the schema.
2. **Each sphere advertises its lanes.** A *lane descriptor* = (sphere, provider, alias, price,
   health, capabilities, tools). The estate already has most of this: `lanes.json` is a lane
   registry with health, error classes and fallbacks; the sphere adds the identity of where it is
   running and what it can reach. Discovery is a **probe**, exactly as this session probed the
   harnesses (§11 A2): on the laptop the probe finds `claude`, `opencode`, `pi`, `ollama` and the
   router's 35 aliases; in a cloud sandbox it finds whatever that sandbox has, and the binder
   refuses to promise a capability it cannot verify.
3. **The binder is the only place that knows the sphere.** It resolves (packet, sphere) → (harness,
   lane, worktree, price). The *same* packet resolves differently in different spheres — that is
   the design, not a defect. The artifact-tier table (§4.2) expresses **capability tiers**
   (frontier / mid / cheap); the *lanes* behind each tier are whatever the sphere advertises, and
   the price comes from the sphere's advertisement, so the same policy spends differently in a
   metered cloud sphere than on the free laptop tier — which is exactly Decision 0034's ladder
   made explicit.
4. **The floor is portable.** UX-03's floor — the always-on local tiny model — becomes "the
   cheapest *available* lane in this sphere", and it may never be switched off. In a cloud sphere
   the floor is the cloud's cheapest always-on lane (or a local model on the box); on the laptop it
   is `ollama`.
5. **State travels in a portable medium.** The estate already has one: **the GitHub issue**. The
   claim, the plan, the sub-task state and the resume token are all representable as issue
   content, which is why the estate's continuity survived a dead laptop before. The local
   `estate.db` is a *cache and index* of the portable record, never the only copy — this is the
   exact lesson of `bin/estate-checkpoint` (state keyed to a vendor format became invisible).
6. **Spheres are peers.** A packet can be bound in sphere A and, if that sphere dies mid-flight,
   resumed in sphere B from the same issue and the same resume token — provided the worktree can
   be recreated (a git worktree is recreated from the branch; the *diff* is the durable artifact,
   which is why the estate's checkpoint DAG stores diffs and never snapshots).
7. **The estate's existing doors already span spheres.** The cluster has `estate-mcp` ×2 (ns
   `mcp`) and the Face pod forwards intents to the laptop over Tailscale; the laptop has
   `fleetview-backend` (launchd `ai.estate.fleetview-backend`, `127.0.0.1:18790`). A portable
   orchestrator must therefore be **reachable through the intent door in every sphere**, with the
   same three intents (`plan.delegate`, `subtask.run`, `plan.status`).

**Proving measurement.** Two spheres, one plan: run the same three packets on the laptop and in a
cloud sandbox (or a GitHub Actions runner — the sphere the estate already has), and show:
(a) both produce diffs that pass the **same acceptance commands**; (b) the recorded bindings
differ (harness and lane), while the packet bodies are byte-identical; (c) no path, binary or key
from sphere A appears in a packet executed in sphere B (a schema check, not a convention); and
(d) killing the laptop mid-plan leaves the plan resumable from the issue in sphere B.

### 7.8 Interoperability of routing and local harness — moving the estate to the cloud

**The challenge, stated by the founder (2026-10-23).** Everything the estate has built — the
sub-goal machinery, the intelligent routing, the claims, the verifier — works, and works well,
**on the laptop**. But the brain and hands are laptop-bound: the router is a local process
(`platform/llm/front.py` → `127.0.0.1:4000` → a local LiteLLM slot), the harnesses are local
binaries, the isolation rung available locally is `temp_tree` (none), and the cloud-side pieces
built so far — the cluster's LiteLLM in ns `llm` and the **ZeroEdge** cost gateway in front of it —
are a *second* router-side layer that the local harness does not and cannot share. "What if we need
to move to cloud? How does this all pay out? We can't be fully coupled to the current situation."

**Why it is hard.** Portability is usually attempted by moving the implementation everywhere and
hoping behaviour follows. Here it fails for three specific reasons, each of which the estate has
already measured:

1. **Bound-early packets.** A packet that names `opencode` and `groq/gpt-oss-120b` is only
   meaningful on a machine that has that binary and that lane key. Move the sphere and the packet
   is meaningless, although its *intent* ("add the retry budget to the watchdog, these paths, this
   acceptance") is portable.
2. **Two routers, two policies.** The laptop's router and the cluster's router are separate
   deployments with separate configurations, and ZeroEdge adds a second cost/routing layer in the
   cluster whose presence is "off unless `ZEROEDGE_URL` is set". The harness-inventory spec
   (2026-10-23) calls ZeroEdge "a second cost/routing layer next to the platform's own router" and
   leaves the one-of-each-layer question unresolved. Unresolved is not neutral: it means a cloud
   harness can be billed and routed differently from a laptop harness for the same alias — which is
   exactly "coupled to the current situation".
3. **Evidence is not comparable across substrates.** A laptop `temp_tree` run (no isolation) is not
   the same claim as a `gvisor` run (registered on the cluster, currently used by **0 pods**), and
   neither is the same as a greenlane proof on `main`. A plan that accepts a cheap laptop gate as
   "done" has quietly lowered its own bar.

**Mechanism.**
1. **Bind late (§7.7):** packets declare capability requirements; the binder resolves harness,
   lane, isolation and price per sphere. The packet body is sphere-neutral by schema.
2. **One policy, many renderers (§4.11 rule 1):** the lane namespace, health classes, fallback
   chains, tier table and budgets are the portable policy; each sphere's router is a renderer of
   that policy. A **config-drift check** compares the effective policy of every live sphere and
   refuses a divergence — the same discipline the estate already applies between `AGENTS.md` §11's
   toml and `sovereign/policy.py`.
3. **ZeroEdge is resolved, not deferred (§4.11 rule 2, decision D9):** one optimizer, in the
   cluster renderer, configured by the same policy; never a second optimizer beside the platform's
   router, and never a different policy in the other sphere.
4. **Transport extension, never a second implementation (§4.11 rule 4):** the `runtimes.json`
   precedent — a runtime that cannot speak MCP gets its tools from a link to the same bridge, not
   from a bespoke integration. A cloud harness that cannot be driven by CLI flags gets an
   MCP/ACP bridge; the delegation contract does not change.
5. **Isolation-aware evidence:** every gate verdict records `sphere`, `isolation`, `harness` and
   `lane`; the plan's "operating" state still demands the estate's own bar (landed, five checks,
   production observation).
6. **Dual-plane operation during any migration.** A plan may have sub-tasks in the laptop and in
   the cloud at the same time, because the plan's state travels in the issue (§7.7 rule 5) and the
   claims are per-issue and path-scoped — so the two spheres cannot collide on a path. This is what
   makes the move a *migration* rather than a *cutover*, and it is the concrete answer to "how does
   this all pay out" if the estate moves: nothing is rewritten, sub-tasks are re-bound.

**Proving measurement.** (a) The same three packets are executed in two spheres (laptop and a
cloud sandbox or a GitHub Actions runner); both produce diffs that pass the **same** acceptance
commands, the recorded bindings differ, the packet bodies are byte-identical, and no path, binary or
key from one sphere appears in the other's packets (a schema check, not a convention).
(b) The config-drift check runs green across the live spheres — same alias→lane resolution, same
tier policy, same budget ceilings. (c) With the laptop's router stopped, a plan already running in
the cloud continues and completes, and a plan started in the cloud binds to cloud lanes without a
config change on the laptop. (d) ZeroEdge, when enabled in the cluster, changes *cost*, never
*which tier a role gets* — asserted by the artifact-tier table, not by a comment.

---

## 8. Cost, risks, non-goals

### 8.1 Cost model

Per the house rules, prices are referenced from `platform/llm/cost-ladder.yaml` and never
restated; the estate's daily caps live in `AGENTS.md` §11.

| Tier | Lane | Price | Where it is used | Calls per typical task |
|---|---|---|---|---|
| frontier | `claude-*`, `minimax_m31f`, `deepseek-v4-pro` | rung 1 metered: $0.0000003 in / $0.0000012 out per token | planning, re-planning, ambiguous review | 1–3 |
| mid | `minimax`, `glm`, `gemini`, `deepseek` | rung 1 metered, same rate | new files, semantic review, re-plan after a plan defect | 0–2 |
| cheap | `groq` (`gpt-oss-120b`), `cerebras`, `sambanova`, `nvidia`, `openrouter` free models, `ollama` local | **$0** (free tier / local) | edits, diffs, tests, mechanical fixes | 5–50 |
| none | deterministic gates (`bin/idp-ci`, claim-gate, greenlane) | $0 | verification, landing | every |

**A worked example (arithmetic, not a measurement):** a task whose plan is 8,000 input + 2,000
output tokens of frontier planning costs ≈ 8,000×$0.0000003 + 2,000×$0.0000012 ≈ **$0.0048**; the
same task executed today at frontier for 50,000 input + 10,000 output tokens costs ≈ **$0.027**.
The saving is small in absolute money — **the real cost being optimised is founder attention,
machine saturation and wall-clock, not tokens.** The proposal should be judged on those three, and
the /fleet plan panel should report them (money, wall-clock, machine headroom).

**Honest counter-argument, for the consultant.** If the founder's time is the scarce resource,
spending a frontier call to *avoid* a cheap-tier mistake is often right; if machine capacity is
scarce (it was, on 2026-10-21), the cheap tier is right. The default should therefore be **the
cheapest tier whose acceptance gate is deterministic**, with the frontier tier bought deliberately
rather than by default. That is the trade-off the founder is actually making (decision D2).

### 8.2 Risks

| # | Risk | Likelihood (evidence) | Impact | Mitigation | Who decides |
|---|---|---|---|---|---|
| K1 | The cheap tier produces a plausible wrong diff that passes a weak gate | high in general; the estate's own `filter_depth` note names misclassification as "a real cost" | a wrong change lands | scope gate + the estate's real gate + mid-tier review for semantic criteria; never the model's own word (§4.6) | D2 |
| K2 | Fan-out reproduces the 2026-10-21 saturation (load 95, swap 3.3–4 GB, 473M swapouts) | high — the measurement exists | every session stalls; the estate goes dark | the measured machine-capacity bound; load-shedding to `ollama`; the fan-out bound is a gate, not a hint (§4.4) | D3 |
| K3 | Issue noise: one sub-task = one issue | certain (design) | five issues per plan; `/fleet` clutter | meta-issue per plan; the panel groups by plan; D6 offers the multi-claim-per-issue alternative | D6 |
| K4 | A second router-side layer (ZeroEdge) re-introduces duplicated routing policy | present now | two policies, two bills, "one of each layer" broken | D9: one optimizer, inside the cluster renderer, same policy; the config-drift check refuses divergence (§4.11, §7.8) | D9 |
| K5 | The layer is laptop-local, so a dead Mac loses in-flight work | certain today | plan interrupted | every packet is re-runnable from its issue; state travels in the issue; cloud spheres can bind the same packets (§7.7) | D8 |
| K6 | Jev stays unavailable, so the arbiter never speaks | measured today (`TYPESAFE_API_KEY` unset) | ambiguous routing decisions stay low-confidence | the deterministic table is the primary; every decision records what Jev *would* have said, so the value is measurable when the key lands (§7.2) | D4 |
| K7 | The plan's fan-in waits on a sub-task that is stuck | possible | the plan stalls | the setback budget (§7.5); blocked sub-tasks are visible on /fleet and spoken by the Face; the plan continues with independent sub-tasks | D5 |
| K8 | Scope creep into "build the whole matrix" (Option B) | real — the Battalion spec already asks for it | 30+ days, a paid rung, and a second selection layer | Option A first; the artifact-tier table is designed as the axis B wants, so B is a superset, not a rewrite | D1 |
| K9 | The proposal is read as "the estate already does this" | possible | the gap is dismissed | §3's six gaps, each with a citation; the gap is a *unit of work*, not the absence of capability | — |
| K10 | Voice reachability dies with the Mac (the Face forwards intents to the laptop over Tailscale) | measured (Face audit §2) | the founder's hands go quiet | the cluster already runs `estate-mcp`; make the plan verbs reachable from the cluster door (D8) | D8 |

### 8.3 Non-goals (so the scope is not read larger than it is)

* Not a new router. The router exists and works; the proposal adds a *task-level* policy on top.
* Not a new verifier, a new claim system, a new scheduler, a new memory plane or a new secrets
  path. Each of those is a "one of each" layer that already exists (AGENTS.md §6).
* Not a replacement for the greenlane. Every packet lands through it.
* Not a claim that the cheap tier can do everything. It can do the classes whose acceptance is a
  machine command — that boundary is the design's core safety property.
* Not a new Always-On deployment. Net new always-on resources: zero (Decision 0034).

---

## 9. BDD scenarios (the acceptance suite for this proposal)

These are the scenarios a consultant and the founder can check the design against. Each maps to a
requirement.

| # | Given | When | Then |
|---|---|---|---|
| B1 | a goal and a live claim for the paths involved | `plan.delegate` runs | a plan is returned whose sub-tasks have **disjoint** path sets, each with exactly one deterministic acceptance command, and one issue + one claim per sub-task |
| B2 | a plan with an `edit_diff` sub-task and the cheap tier live in `lanes.json` | `subtask.run` runs | the packet names a cheap alias; the executor runs it on the cheap lane; the estate runs the acceptance; the model is never asked whether it passed |
| B3 | a sub-task whose diff touches a path outside the packet's `paths` | the scope gate runs | the gate **refuses**, the packet is `blocked` with the offending path named, and no change is offered for landing |
| B4 | a cheap-tier sub-task that fails the same acceptance twice | the driver reacts | the failure is classified, the sub-task is **re-planned** (not retried), the frontier tier is asked for a new decomposition, and the plan's other sub-tasks continue |
| B5 | a harness process killed mid-sub-task | the plan is restarted | the same sub-task resumes with the same issue, claim, worktree and session key; already-passed gates are not re-run; no second claim is opened |
| B6 | a lane whose account has no credit, in the middle of a plan | the next sub-task starts | the sub-task falls to the next rung of its own chain (or to the local floor), the re-route is recorded and visible on /fleet, and the plan completes |
| B7 | all lanes of the preferred tier unavailable | the planner runs | it binds the cheapest available lane that satisfies the packet's capability requirements; if none does, the plan does not start and says why (§7.3's anti-half-funded rule) |
| B8 | a plan running on the laptop and the same packets bound in a cloud sandbox | both execute | both pass the **same** acceptance commands; the packet bodies are byte-identical; the bindings differ; no path, binary or key crosses spheres |
| B9 | the laptop's router is stopped mid-plan | the plan continues | in-flight sub-tasks finish or are re-routed to the standby door; the plan completes; /fleet shows the re-route and its cause |
| B10 | a reviewer pool that would collapse onto one model family (e.g. `gpt-oss-120b` under groq, cerebras and sambanova) | the loop config is loaded | the config is **rejected** (diversity rule), and the run falls back to a distinct-family pool |
| B11 | the founder asks "where is everyone" by voice | the Face answers | the answer is read from the same state rows the /fleet panel reads, naming each agent, its harness, its state and its heartbeat age — with no argument required |
| B12 | a plan whose sub-tasks all pass their gates | the fan-in runs | the change lands through a lane on `main`; the plan state becomes `landed` and then `operating` only after the estate's five checks; never before |

---

## 10. Decisions taken (numbered, each with its recommendation and its owner)

These are the decisions the founder and the consultant are being asked to settle. The
recommendation is the proposer's; the owner is who must sign.

| # | Decision | Options | Recommendation | Owner |
|---|---|---|---|---|
| D1 | Which option to build | A (delegation layer) / B (full tier matrix) / C (voice-first orchestration) | **A**, with B's axis (the artifact-role tier table) designed in from the start so B is a later superset, and C's Face verbs as a surface over A | founder + consultant |
| D2 | How cheap by default | always cheapest / cheapest-that-passes-a-deterministic-gate / tier chosen per role | **cheapest-that-passes-a-deterministic-gate**, with frontier bought deliberately (cheap tokens are not the scarce resource; attention and machine capacity are) | founder |
| D3 | The fan-out bound | fixed number of parallel sub-tasks / measured capacity ceiling | **measured ceiling** (the 2026-10-21 saturation is the evidence), with the plan panel showing headroom | founder |
| D4 | Jev's role | primary arbiter / override when available / deterministic only | **override when available, deterministic table as primary**, and every decision records what Jev would have said so its value is measurable when the key lands | founder + consultant |
| D5 | The setback budget | 1 re-plan / 2 re-plans / unlimited | **2**, after which the plan is blocked and reported (the estate's "report only done or seriously blocked" rule) | founder |
| D6 | Ownership granularity | one issue per sub-task / one issue per plan with multiple disjoint claims | **one issue per sub-task now** (the fleet panel groups them by plan); the multi-claim variant is D6-alt and the `bin/claim-open` docstring already notes a claim covers only one issue | founder + consultant |
| D7 | Reviewer independence | any reviewer / family-diverse pool / no review on deterministic criteria | **family-diverse pool, required only for semantic criteria** — never the same family as the author, never the model's own verdict as acceptance | consultant |
| D8 | Where the engine runs | laptop only / laptop + cluster dual-plane / cloud only | **dual-plane** (laptop now, cloud as a peer sphere), with plan state carried in the issue so the estate can move without a cutover; **no new always-on deployment** (Decision 0034) | founder |
| D9 | ZeroEdge, the second router-side layer | keep it beside the platform router / fold it into the cluster renderer under one policy / retire it | **fold it in** (one policy, many renderers) — the one-of-each-layer law decides this; a second optimizer with its own routing policy is what "coupled to the current situation" looks like | founder + consultant |
| D10 | Budget posture for delegation | keep the current caps / raise the frontier cap / reserve per plan | **keep the caps** and have each plan *reserve* from them, so a plan cannot spend the estate's daily frontier budget twice over | founder |

---

## 11. Appendices

### A. Raw measurements (2026-10-23, this session, laptop)

Every number below was produced by the command shown. Nothing is estimated except where the row
says "not re-measured".

| # | Measurement | Command | Result |
|---|---|---|---|
| A1 | Which harnesses exist here | `command -v claude opencode pi ollama aider gemini codex` | `claude`, `opencode`, `pi`, `ollama` present; `aider`, `gemini`, `codex` absent |
| A2 | The harness CLIs' own capability flags | `claude --help`, `opencode --help`, `pi --help` | `claude`: `--allowedTools`, `--disallowedTools`, `--permission-mode`, `--mcp-config`, `--session-id`, `--resume`; `opencode`: `run`, `serve`, `acp` (ACP), `--model`, `--agent`; `pi`: `--model`, `--session`, `-p`, `--extension` |
| A3 | Which router slot is live | `cat ~/.estate/router-state/active` | `4002` (the primary 4001 with the fallback 4002) |
| A4 | The free tier answers | `curl -m 40 http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_LAPTOP_KEY" -d '{"model":"groq",...,"max_tokens":5}'` | `http=200 time=5.695s` (measured earlier this session with the vault-loaded laptop router key). Re-measured without the key: `http=401` with the body naming the vault entry (`secrets/dev/LITELLM_LAPTOP_KEY.yaml`) and stating that lanes carrying your own credential need nothing. No key value is recorded anywhere |
| A5 | The local floor | `curl -s http://127.0.0.1:11434/api/tags` | `['moondream:latest', 'llama3.2:latest']` — a text model and a vision model, both free and offline |
| A6 | The live lane registry | `python3 -c "…json.load(~/.estate/router-state/lanes.json)"` | `at 2026-10-22T22:02:28Z`, `served` = **35** aliases, `dropped` = **0**; per-alias fallback chains exist, e.g. `groq → [cerebras, sambanova, nvidia, openrouter]`, `minimax → [minimax_m31f, gemini, groq]`, `default → [gemini, groq]` |
| A7 | Jev (the arbiter) is unavailable | `estate_invoke jev.decide` | `escalated: true`, `_fallback: "jev_unavailable"`, `confidence: null` — the deterministic table carries the decision; `TYPESAFE_API_KEY` is unset |
| A8 | The isolation actually in use (laptop) | `detect_backend()` in `platform/executor/sandbox.py`; `/dev/kvm`; `command -v runsc`; `docker info` | `temp_tree`; `/dev/kvm` absent; no `runsc`; the Rancher Desktop socket absent — so the ladder has no rung above `temp_tree` here |
| A9 | The isolation registered but unused (cluster) | harness inventory spec (2026-10-23, on `main`) | the `gvisor` RuntimeClass is registered and **0 pods** carry a `runtimeClassName`; `agent-workforce` CronJob `Running 0/1` after 21 minutes, previous `Failed` |
| A10 | ZeroEdge's role | `platform/llm/zeroedge.yaml`, `platform/llm/zeroedge_gateway.py` docstring | "provider-agnostic, drop-in LLM cost-optimization gateway"; "off unless `ZEROEDGE_URL` is set"; **budget is advisory**; the shim fails open with a 2 s timeout; `PDB maxUnavailable: 1` |
| A11 | The Face's reachability | the Face audit spec (2026-10-23) | live at `https://catalogue.mumchimp.com/face/` (HTTP 200, 10,835 bytes); **64 arg-free intents**; the Face **cannot pass arguments**; `FLEETVIEW_INTENTS_URL` points at the laptop's fleetview-mac over Tailscale; the laptop backend is `127.0.0.1:18790`; the voice router is `8091` |
| A12 | The runtime-parity precedent | `platform/estate/memory/runtimes.json` | pi has `mcp.reads: false` and takes its tools from "tools" links pointing at the same bridge every other runtime runs; "a new runtime is a new entry under runtimes, not a new integration" |
| A13 | The claim model | `backstage/plugins/fleetview-backend/src/fleetview_backend/claims.py:109`, `:192` | "Newest claim per issue. A refresh is a new comment, not an edit, so the newest wins."; `claims_snapshot(now)` returns the live claims |
| A14 | The runner registry | `sovereign/engine/runners.py:159` | `REGISTRY: dict[str, RunnerFn]` — the estate's registry pattern this proposal follows |
| A15 | The 2026-10-21 saturation (the fan-out evidence) | the estate's own incident record — **not re-measured this session** | 4 cores / 8 GB; load average **95**; swap **3.3–4 GB** of 4–5 GB; **473M** swapouts; `front.py`'s health check took **4.2 s**; 2 h 20 m of "probe slow curl=28"; `front.py` fails over only on connect-refused or a 5 s connect timeout — a starved router does **not** fail over |

### B. Citations (every load-bearing claim in this document points at one)

* Routing and lanes: `platform/llm/front.py`, `platform/llm/lanes.json`, `platform/llm/cost-ladder.yaml`, `platform/llm/routing-matrix.yaml`, `platform/llm/availability.yaml`, `platform/llm/zeroedge.yaml`, `platform/llm/zeroedge_gateway.py`, `~/.estate/router-state/lanes.json`, `~/.estate/router-state/active`
* Policy: `AGENTS.md` §11 (the single toml block), `sovereign/policy.py`, `sovereign/config.py`, `sovereign/tests/bdd/test_policy.py`
* Claims and landing: `bin/claim-open`, `bin/claim-gate`, `backstage/plugins/fleetview-backend/src/fleetview_backend/claims.py`, `greenlane/engine.py`, `.github/workflows/greenlane.yml`, `docs/runbooks/greenlane.md`
* Verification: `sovereign/verifier.py`, `sovereign/engine/`, `bin/idp-ci`, `bin/verify`, `sovereign/tests/bdd/`
* Execution and isolation: `platform/executor/sandbox.py`, `factory/sandbox.py`, `platform/sandbox/vcluster/`
* Harnesses and portability: `docs/specs/2026-10-23-harness-inventory-and-how-a-harness-is-swapped.md` (on `main`), `platform/estate/memory/runtimes.json`, `docs/synthesis/factory-inventory.md`
* Voice and visibility: the Face audit spec (2026-10-23), `platform/llm/availability.yaml`, the Fleet board (`backstage/plugins/fleetview-*`), `bin/idp-brief`
* Prior art for the desired behaviour: `docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md` (Status: PROPOSED — the same proposal genre, and the source of the "like electricity" language in its §10), `docs/specs/2026-10-22-*.md` (the idp-mode/voice/workforce series), `docs/diagnoses/*.yaml` (the hypothesis-race genre used for the gap analysis)
* Placement: `docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`

### C. Glossary

* **Packet** — the unit of delegated work: one goal, one scope, one acceptance, one owner.
* **Lane** — one named route to a model through one provider (`groq`, `ollama`, `claude-*`, …).
* **Alias** — the stable name a packet asks for (`cheap`, `frontier`), resolved per sphere.
* **Tier** — the cost band a role is assigned (cheap / mid / frontier / none).
* **Binding** — the resolution of a packet to (harness, lane, isolation, price) at dispatch time.
* **Sphere** — a place the estate runs: the laptop, the cluster, a cloud sandbox.
* **Harness** — the runtime that executes an agent's turns (`claude`, `opencode`, `pi`, …).
* **Substrate** — where the work is isolated while it runs (`temp_tree`, `docker`, `gvisor`, `firecracker`).
* **Floor lane** — the always-available free lane (local `ollama`) that never switches off.

---

*Status: PROPOSED — for the founder and an external consultant to evaluate. Not approved, not built.*
*Nothing in this document has been implemented. Every "will" is a proposal; every "is" is measured
and cited in §11.*
