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

**Amendment 2 (2026-10-23, later the same day).** After the founder read the first version, three
requirements were added and are answered here: **R17** — a *discovery plane*: "a super accurate mega
oracle that can answer any question, super accurately, in real time", with "nothing can escape it";
**R18** — every source of estate knowledge redesigned into **one place**, with agents **forced** to
use one source; **R19** — a **console surface**, answerable from any terminal in any harness. The
new material is §0.1 (the whole picture), §0.2 (the requirements ledger), §2.10 (the measured
review of every data source), §3.7 (the seventh gap), §4.12 (the Discovery Plane), §6.8–§6.10
(integration, the discovery-first contract, the console surface), §7.9 (the oracle, with seven
proving measurements) and decisions D11–D16. The first version's content is unchanged; this
amendment only adds.

**Amendment 3 (2026-10-23, later still).** Two more founder requirements: **R20** — *real-time
communication between models and harnesses*, estate-wide, with broadcast, peer-to-peer channels and
the founder inside them; and **R21** — *integrate and operationalise the Quad (DROS) so agent
identity is solved*. The new material is §3.8 (the eighth gap), §3.9 (the ninth gap — the Quad is
built, deployed and idle: zero ledger rows), §4.13 (the message plane: one bus, one envelope, three
channel kinds, a deadline plus a documented default on every escalation, per-copy cost on
broadcast), §4.14 (the Quad inside the delegation plane: one URN, one registry, one signed chain,
two attestation tiers), §6.11–§6.13, §7.10–§7.11, §8.1.2–§8.1.3, the roadmap's phases 0.5, 0.75 and
1.5, B20–B27, D17–D22 and the measurements A29–A33 (taken live against the cluster this
session). The founder's three surfaces — **/fleet, the Face, and the console on the Mac** — are
named explicitly wherever identity or messages reach the founder.

---

## 0. One page

**The wish.** Frontier models plan and reason and decompose a goal into sub-goals; mid models
create new files; the cheapest/free tier produces the diff; the plan is executed in parallel,
one sub-task per worker, across models *and* harnesses (Claude Code, opencode, pi); every
agent's position and ownership is known at all times; a session that dies mid-flight is resumed
without redoing work; the estate keeps driving until the work is operating; the routing is
"ultra intelligent" and "ultra resilient"; the whole thing must work like electricity — the
founder never chooses a model, never sees a mode switch, never waits on a laptop door; and
everything must be visible on **/fleet** and spoken on **face**, with monitoring. **And every
agent must be able to ask the estate anything, through one door, in real time, with an answer that
carries its evidence** — "a super accurate mega oracle", with "nothing can escape it".

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

**And three more gaps the founder named in the same session.** Real-time communication *between*
models and harnesses, with broadcast and the founder inside it (§4.13) — the transport exists, the
contract does not. An estate-wide **discovery plane** that answers any question about the estate
with its evidence (§4.12) — nine sources, no cross-source answer, agents that poll. And **agent
identity**: the Quad (DROS) is built, deployed and *idle* — its ledger runs and verifies green with
**zero** rows, its registry tables do not exist, its signing proxy and kernel enforcer are not
deployed (§4.14, A29–A33) — so the estate has an identity substrate with no identities in it.

**The hard problems the founder named** (§7) — six at first, then portability, real-time
communication and identity — and the short answers:

| Hard problem | Why it is hard | Mechanism | Proving measurement |
|---|---|---|---|
| Feedback loops between models | agreement is not evidence; loops burn budget; a "five-model" quorum can be one model counted five times | bounded rounds, **family-diverse reviewers**, a deterministic gate between rounds, stop on gate-pass not on agreement (§7.1) | false-accept rate of a collapsed reviewer pool vs a diverse one, on the same packets |
| Which model to route to | cold start; fitness is task-class-specific; failure attribution is confounded | deterministic role→tier prior → measured per-lane posterior → Jev as arbiter **only when available** (§7.2) | a routing decision log; per-lane, per-class success table read from the action ledger |
| Credit running out mid-session | credit is an account property that changes between plan and step 7; half-funded plans lose paid work | pre-flight, budget reservation, a **degradation ladder** (frontier→mid→free→local), and "checkpoint and hand back" as a terminal state (§7.3) | a plan that loses a lane mid-flight and *finishes* on the next rung |
| Continuity and ownership | three clocks disagree (harness session, estate state, worktree); claims are issue-scoped and one-per-issue | one state row per sub-task in `estate.db`, the resume token, one issue = one claim = one packet (§4.7, §4.8) | SIGKILL a harness mid-sub-task; restart; the same sub-task resumes without redoing passed gates |
| Driving to completion despite setbacks | blind retry burns budget on deterministic failures; stopping early is the default failure | cause classification before reaction (environment / plan / execution / gate defect), a bounded setback budget, the estate's five-check "done" (§7.5) | a gate that fails twice is re-planned, not retried, and the plan's other sub-tasks continue |
| Resiliency routing | health checks that ask "can I connect?" cannot see saturation | latency/saturation health (not connect-refused), a warm standby door, load-shedding to the free tier (§7.6) | stop the primary door mid-plan; the plan completes on the standby |
| Portability and interoperability (the last challenge) | the estate's brain and hands are laptop-bound; the cloud side already runs a *second* router-side layer (ZeroEdge) that the local harness cannot share | late binding, **one policy and many renderers**, per-sphere lane discovery, transport extension instead of a second implementation, isolation-aware evidence (§4.11, §7.7, §7.8) | the same packet runs in two spheres with identical acceptance and different bindings; a config-drift check proves the spheres share one policy |
| Real-time communication between models and harnesses (broadcast, peer-to-peer, founder inside) | every message that reaches a model is a paid call; a silent timeout is worse than a slow answer; the laptop cannot reach the bus; a broadcast that wakes everyone is the 2026-10-21 saturation | one bus, one envelope, three channel kinds (point-to-point, role, broadcast); **a deadline plus a documented default on every escalation**, so no wait is unbounded and no answer is guessed; per-copy cost on broadcast; the founder as a channel participant (§4.13) | an escalation answered inside its deadline; a broadcast acked by every live subscriber with the cost charged per copy; the founder's note visible in the plan's row |
| Agent identity (the Quad, operationalised) | an agent that says who it is is an assertion; a laptop agent can never have kernel attestation; an empty ledger is not evidence | one registry with URNs; one signed-action chain and its external anchor; **two attestation tiers recorded honestly** (kernel, door); the URN in every packet, message, claim and plan row (§4.14) | `agent_actions` goes from 0 to ≥1 with the verify door green; a planted fault turns it red; a cheap executor is refused a frontier-only action |

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

**Twenty-two decisions are recorded** in §10, each with options, a recommended default and what
the choice costs: **D1–D10** start the delegation layer, **D11–D16** the discovery plane,
**D17–D18** the message plane, **D19–D22** identity. D1–D10 alone are sufficient to begin; the
rest are decided with the consultant. This document is written so that a reader with no prior
context can choose Option A, B or C without asking a question this document fails to answer.

---

### 0.1 The whole picture — every problem of this session, and the one architecture that answers them

This section is the map for a reader who has followed none of the reasoning and wants the shape
before the detail. Everything below is argued, cited and measured in the sections it points to.

```
                      ┌────────────────────────────────────────────────────────┐
  founder ──voice──►  │  ONE SURFACE: /fleet (the board) · the Face (tap-to-talk)│
                      └───────────────────────────┬────────────────────────────┘
                                  reads the same rows, never a second truth
  ┌───────────────────────────────────────────▼────────────────────────────────────┐
  │ DISCOVERY PLANE (§4.12) — "the oracle": one place, one door, nothing escapes     │
  │  ingest → canonical entity resolution → index → query planner → cited answer     │
  │  every answer carries source · locator · as-of · epistemic state (confirmed /     │
  │  corrected) · a "the estate does not know this" is a valid, required answer       │
  └──┬────────────┬───────────────┬──────────────┬──────────────┬───────────────┬───┘
     │            │               │              │              │               │
 event spine   estate-memory   knowledge      action ledger   git (code)    live state
 (NATS, the    (the MCP door:   graph          (estate.db     + claims,     (claims, lanes,
  epistemic     brief/recall/    (growmos,      step_runs)     specs, ADRs)   runs, pods)
  states)       remember)        10,772 nodes
     │
  ┌──▼──────────────────────────────────────────────────────────────────────────────┐
  │ DELEGATION PLANE (§4.1–§4.10) — packets · role→tier table · adapters · task graph│
  └──┬───────────────┬───────────────┬──────────────┬──────────────┬──────────────┘
     │               │               │              │              │
  the router     the verifier     the claims     the greenlane   the harnesses
 (tiers, lanes,  (deterministic,   (one owner     (prove green,   (claude · opencode ·
  fallbacks)      a gate, not a      per path)      then land)      pi) in any sphere
                 vote)                                                    (laptop · cluster)
```

**The problems of this session, each with the mechanism that answers it and the measurement that
proves it.** This is the founder's "are we tracking all the requirements?" answer, in one table.

| # | The problem as it was stated | The mechanism | Where | The proving measurement |
|---|---|---|---|---|
| 1 | Routing must be "ultra intelligent" and "ultra resilient" | a role→tier table (a *policy*), a measured per-lane posterior, Jev as arbiter only when available, health classes that see saturation | §4.2, §7.2, §7.6 | a routing decision log; per-lane, per-class success; a plan that completes after the primary door dies |
| 2 | "the cheapest models and harnesses if necessary" | artifact-role tiering: the cheapest tier that can produce this artifact class, with the acceptance owned by a deterministic gate | §4.2, §4.6 | a diff produced by the free tier that passes the acceptance |
| 3 | "the most intelligent models should plan and reason" | frontier tier plans, decomposes, assigns; the mid tier writes files; the cheapest tier emits diffs | §4.3, §4.4 | a plan whose decomposition was produced by the frontier tier and whose artifacts came from the cheap tier |
| 4 | "invoke parallel per sub-task" | a task graph with fan-out and join, one packet per sub-task, one owner each | §4.4, §4.8 | N sub-tasks running at once, joined, one result |
| 5 | "agents and harnesses can fail mid-session for any reason" | one state row per sub-task, a resume token, a checkpoint, and rewind | §4.7, §7.4 | SIGKILL a harness mid-sub-task; restart; no passed gate is redone |
| 6 | "models running out of credit mid-session" | pre-flight reservation + a degradation ladder + "checkpoint and hand back" as a terminal state | §4.9, §7.3 | a plan that loses a paid lane and *finishes* on the next rung |
| 7 | "driving to completion despite setbacks" | cause classification before reaction, a bounded setback budget, the estate's five-check "done" | §7.5 | a gate that fails twice is re-planned, not retried |
| 8 | "feedback loops between models" | bounded rounds, family-diverse reviewers, a deterministic gate between rounds | §7.1 | the false-accept rate of a collapsed reviewer pool vs a diverse one |
| 9 | "coordination and ownership fully operational" | one issue = one claim = one packet; the claims reader keeps the newest claim per issue | §4.8 | two agents cannot touch the same file; the claim is always live |
| 10 | "should know exactly where any agent is and where they left off" | the same state rows drive /fleet, the Face and the plan-level verbs | §4.7, §6.4 | "where is everyone" answered from the board's own rows |
| 11 | "smoothly and seamlessly like electricity" | UX-01 no visible mode switch, UX-02 every edge case has a named degradation, UX-03 a floor lane config cannot switch off | §6.5 | the founder never chooses a model and never sees a mode switch |
| 12 | "portable across spheres", "not coupled to the current situation" | one policy, many renderers; late binding; transport extension, not a second implementation | §4.11, §7.7, §7.8 | the same packet runs in two spheres with the same acceptance |
| 13 | "monitoring and visibility to other systems like fleet and face" | every plane writes the same event kinds; the surfaces read the same rows | §6.4 | a decision on /fleet explains itself from its evidence |
| 14 | **"discovery": one place, one source, real time, super accurate, nothing escapes it** | the **Discovery Plane**: one adapter per source, canonical entity resolution, a tiered query planner, mandatory provenance, retraction on correction, and a gate that makes discovery the only door | **§4.12, §7.9** | a question answered with citations in one call; the estate's "I don't know" counted and correct; a retracted fact never served again |
| 15 | **"the executor model needs to communicate in real time with the mid or frontier model … enterprise peer-to-peer realtime comms with broadcast, and also founder inclusive"** | the **message plane**: one bus, one envelope, three channel kinds (point-to-point, role, broadcast), deadline+default on every escalation, the founder as a channel participant, every message a live row on /fleet and in the Face | **§4.13, §6.11, §7.10** | an escalation answered inside its deadline; a broadcast delivered to every live subscriber with the cost charged per copy; the founder's note visible in the plan's row |
| 16 | **"integrate and operationalise the quad solution so agent identity is solved"** | the **Quad inside the delegation plane**: one URN per agent, one registry, one signed-action ledger; two attestation tiers (kernel, door); the registry as the resolver for role channels | **§4.14, §6.12, §7.11** | the first signed action lands in `agent_actions` and the chain verifies against its anchor; a tampered row turns the verify door red; every packet, message and claim is attributable to a URN on /fleet, the Face and the Mac console |

**The three invariants that keep this one system and not fourteen:**

1. **One of each layer.** The Discovery Plane is the *only* reader of the raw sources; the router is
   the only model door; the verifier is the only gate; the claims are the only ownership; the
   greenlane is the only landing path. Every addition above is an adapter *into* an existing layer,
   never a second copy of one.
2. **Every fact carries provenance.** An answer without (source, locator, as-of, epistemic state)
   is not an answer. This is what turns "super accurate" from a claim into a measurement, and it
   is why the oracle is allowed to say "the estate does not know this".
3. **Every action goes through a door.** Discovery is an intent and an MCP tool like every other
   capability; the estate's executor refuses what is not an intent, so the discovery plane is
   reachable the same way from every runtime.

Not shown in the diagram, because both cut across every box: the **message plane** (§4.13) is the
wire between the boxes — how an executor talks to a frontier reasoner mid-flight — and the
**identity substrate** (§4.14) is the signature on every line that crosses a box.

### 0.2 The requirements ledger — every founder requirement, and where it is answered

The founder asked (2026-10-23): *"i hope we are tracking all requirements for this epic"*. This is
the ledger. Every requirement the founder stated in this session, in the order it was stated, with
the section that answers it and its state. Nothing here is a new requirement: R1–R16 are the
founder's words decoded in §1; R17–R18 were added during the review when the founder raised
discovery and the single-source mandate, and are argued in §3.7, §4.12 and §7.9.

| Req | The founder's words (abridged) | Answered in | State |
|---|---|---|---|
| R1 | "truly ultra intelligent ultra resilient routing that truly standardises planning, execution and verification" | §4.2, §7.2, §7.6 | designed, not built |
| R2 | "plays well with our goals, subgoals, BDD, edge cases" | §4.1, §9 | designed, not built |
| R3 | "using Jev and ultra intelligent routing" | §4.3, §7.2 | designed, not built |
| R4 | "the most intelligent models should plan, reason, create goals, subgoals to the correct degree of decomposition" | §4.3, §4.4 | designed, not built |
| R5 | "invoke the cheapest models and harnesses if necessary to get it done" | §4.2, §4.6 | designed, not built |
| R6 | "frontier, mid, cheapest/free tier" | §4.2 | designed, not built |
| R7 | "output most of the time should be a diff by the cheapest tier; new files by mid tier" | §4.2, §4.5 | designed, not built |
| R8 | "invoke parallel per sub-task to get things done faster" | §4.4 | designed, not built |
| R9 | "coordination and ownership to fully operational … agents and harnesses can fail mid-session" | §4.7, §4.8, §7.4 | designed, not built |
| R10 | "know exactly where any agent is and where they left off" | §4.7, §6.4 | designed, not built |
| R11 | "restart in interruptions to drive to fully operational" | §4.7, §7.5 | designed, not built |
| R12 | "models running out of credit mid-session", "resiliency routing", "driving to completion despite setbacks" | §4.9, §7.3, §7.5, §7.6 | designed, not built |
| R13 | "smoothly and seamlessly like electricity" | §6.5 | designed, not built |
| R14 | "monitoring and visibility to other systems like fleet and face" | §6.4 | designed, not built |
| R15 | "the core engine and intelligence needs to work across spheres and be fully portable anywhere" | §4.11, §7.7 | designed, not built |
| R16 | "cloud harnesses like zero edge don't work with our local harness" | §7.8 | designed, not built |
| **R17** | **"one last problem we need to solve once and for all … discovery of anything happening in the estate of source code seamlessly, without having to search different sources"; "super accurate mega oracle that can answer any question, super accurately, in real time"; "nothing can escape it"** | **§3.7, §4.12, §7.9, §6.8** | **designed, not built** |
| **R18** | **"these sources should be designed so everything that can be known about the estate is in one place and every agent is forced to use one source"; "radical and deep research on discovery … uniformly forcing it across platform and agents"** | **§2.10, §4.12, §6.8, §7.9** | **designed, not built** |
| **R19** | **"another surface should be direct from console like i am doing now, from any harness if possible"** | **§6.10** | **designed, not built** |
| **R20** | **"the executor model needs to communicate in real time with the mid or frontier model or vice versa … any communication real time across models and harnesses … estate-wide … including broadcast, enterprise peer-to-peer realtime comms with broadcast, and also founder inclusive"** | **§4.13, §6.11, §7.10** | **designed, not built** |
| **R21** | **"integrate and operationalise the quad solution so agent identity is solved"** | **§4.14, §6.12, §7.11** | **measured idle; integration designed, not built** |

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
| R5 | "invoke the cheapest models and harnesses if necessary to get it done" | Live aliases include free Groq (`gpt-oss-120b`), free OpenRouter (`nemotron-3.5-lightning:free`) and local Ollama (`llama3.2`, `moondream` for vision) — all in `~/.estate/router-state/lanes.json` | No **task→tier assignment**: the router picks a model per *request*, not per *artifact role* |
| R6 | "frontier, mid, cheapest/free tier" | `platform/llm/cost-ladder.yaml` rungs 0–3 and `platform/llm/routing-matrix.yaml` axes (resource tier × candidate volume × selection method × escalation pattern) | The matrix's `resource_tier` is a **compute** tier (local / router / flat-rate box / GPU), not a **capability** tier (frontier reasoner / mid author / cheap executor). The two are conflated |
| R7 | "the output most of the time should be a diff by cheapest tier; new file creations can be done by mid tier; frontier plans, reasons, assigns, invokes" | — | This rule exists nowhere. It is the sharpest and cheapest win in the whole message (§4.2) |
| R8 | "invoke parallel per sub-task to get things done faster" | Greenlane batches lanes (§2.6); `sovereign/engine/dag.py` is a **content-addressed diff DAG**, not a task DAG | No task-graph fan-out. `sovereign/engine/runners.py:159` `REGISTRY` = `echo, sleep, ask, burn, llm` — one runner, one repo, sequential steps (`workflow.py`) |
| R9 | "coordination and ownership to fully operational, considering agents and harnesses can fail mid-session for any reason" | Claims (`bin/claim-open`, `bin/claim-gate`), the `/fleet` claims panel, `bin/estate-checkpoint`, `platform/estate/libexec/work-audit.py` (the `work-audit` intent) | Ownership is **per issue**, and the claims reader keeps the **newest claim per issue** (`backstage/plugins/fleetview-backend/src/fleetview_backend/claims.py:106-109`) — two agents cannot hold disjoint path claims on one issue. No per-sub-task owner, no "where is everyone", no resume token |
| R10 | "should know exactly where any agent is and where they left off" | `bin/estate-checkpoint` writes branch/HEAD/dirty files/open PR to the issue; `/fleet` shows claims with heartbeat age | Live *position* is visible per issue only, not per running sub-task, and not while the agent is mid-flight |
| R11 | "should be able to restart in interruptions to drive to fully operational" | `sovereign/engine/checkpoint.py` (rewind/recover/audit), Temporal session durability, `bin/estate-checkpoint` | Nothing joins a *delegated sub-task* to a resumable token. All three harnesses can resume (measured: `claude --resume`, `opencode -s/--session`, `pi --resume/-r`) — nobody uses it |
| R12 | "models running out of credit mid-session", "resiliency routing", "driving to completion despite setbacks" | Lane registry with error classes (`402/429/401` → dead/exhausted) and per-alias fallback chains | The **plan** has no funding model: a plan may start on a metered lane and die at step 7 with no credit and no rung to fall to |
| R13 | "smoothly and seamlessly like electricity" | The Battalion spec §10 already turns this into UX-01/02/03 with acceptance criteria | The bar has never been applied to the *end-to-end* path (router → orchestrator → harness → gate → /fleet → face) |
| R15 | "the core engine and intelligence needs to work across spheres and be fully portable anywhere"; "we can't be fully coupled to the current situation" | The estate's policy is already portable in principle (`AGENTS.md` §11 one block; `platform/estate/memory/runtimes.json` — "a new runtime is a new entry, not a new integration"); the cluster already runs `estate-mcp` (ns `mcp`) and the harness inventory already specifies `where: laptop \| cloud \| both` plus an `isolation` field | The *implementations* are bound early: local router (`front.py` → `127.0.0.1:4000`), local binaries, local worktrees, and a second cost/routing layer in the cluster (ZeroEdge) that the local harness does not share. There is no sphere-neutral unit of work and no per-sphere lane discovery |
| R16 | "cloud harnesses like zero edge … don't work with our local harness" | The estate's own interop law: a runtime without an MCP client gets a transport extension, never a second implementation (`runtimes.json`); opencode already speaks ACP | The harness registry has no `transports` or `resumable` field, and the "one of each layer" question for ZeroEdge is explicitly unresolved (harness inventory, 2026-10-23) |
| R14 | "monitoring and visibility to other systems like fleet and face" | `/fleet` claims panel; the Face at `catalogue.mumchimp.com/face/`; the live-mind event contract `estate.agent.event` (kinds `phase/tool/wait/done/steer/gate`) | The Face can run 64 **arg-free** intents by name but "cannot pass an argument to anything … cannot choose or steer or stop an agent, cannot start a fleet session, cannot claim work or land it" (Face audit §1). The plan layer has no voice/board surface, and no delegated decision is emitted as a live-mind row |
| R17 | "one last problem we need to solve once and for all … discovery of anything happening in the estate of source code seamlessly, without having to search different sources"; "a super accurate mega oracle that can answer any question, super accurately, in real time"; "nothing can escape it" | nine sources exist, each authoritative for one thing (§2.10); `rg`, memory recall, the graph and the ledger are four partial answers to one question | there is **no single door** that answers across all sources with a citation, a freshness stamp and a retraction state — §3.7, §4.12, §6.8, §7.9 |
| R18 | "these sources should be designed so everything that can be known about the estate is in one place and every agent is forced to use one source" | the enforce gate already exists and writes every decision to a ledger (717 rows) | the gate enforces *writes*; nothing enforces *knowledge* — the plane and its enforcement rules are the answer (§4.12 L7, §6.9) |
| R19 | "another surface should be direct from console like i am doing now from any harness if possible" | the estate already has zero-config console doors: `bin/estate-brief`, `bin/estate-checkpoint`, `bin/lane-where`, `bin/claim-open` | the discovery plane needs the same kind of console client, beside the MCP tool — §6.10 |
| R20 | "the executor model needs to communicate in real time with the mid or frontier model or vice versa … any communication real time across models and harnesses … an estate-wide, well-thought-out and architected feature including broadcast, enterprise peer-to-peer realtime comms with broadcast, and also founder inclusive" | the transport exists: NATS in the cluster, subjects `estate.agent.{runtime}.{session}.{kind}`; the live-mind contract `estate.agent.event` already carries a `steer` kind | there is **no inter-agent message contract**: no escalation channel from a cheap executor to a frontier reasoner mid-flight, no broadcast with a cost cap, no founder join, no ack/deadline semantics, and the laptop cannot reach the bus at all (A23) — §4.13, §6.11, §7.10 |
| R21 | "integrate and operationalise the quad solution so agent identity is solved" | the Quad (DROS): bootstrapper → registry → Elpis signing proxy → kernel enforcer, plus the layer-4 ledger (`cmd/quad-ledger`), the registry DDL (`schema/identity0_registry.sql`), SPIRE running in the cluster, and four identity intents | **measured idle**: the ledger runs and verifies green but `agent_actions` = **0** and `merkle_anchors` = **0** (A30–A31); the registry tables `agents`/`sessions` **do not exist** (A32); Elpis, the bootstrapper and the kernel enforcer are **not deployed** (A33); ADR 0035 is still PROPOSED — §4.14, §6.12, §7.11 |

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

### 2.10 The estate's data sources, reviewed against reality

The founder asked (2026-10-23) for an architecture review of *all* the estate's data sources and how
they can be streamlined, improved and optimised — "before solutionising". Method: every source was
**measured**, not described, on 2026-10-23 (commands and outputs in Appendix A). The question each
source must answer is: *what is this the authority for, and what does it stop being?*

| Source | What it really is (measured 2026-10-23) | Authoritative for | Where it costs the agent | The improvement |
|---|---|---|---|---|
| **Git** (56 repos under `~/Documents/code`; 9,269 `.py` files at depth ≤4) | the only source whose every fact is signed, versioned and diffable | what the code *is*, and who owns each line | an agent must clone, grep, and read whole files to learn one fact; there is no index of symbols, ownership or history | a **code index** built from the trees (symbol, path, owner, last-change), refreshed on merge, queried by the plane (§4.12) — the code stays the truth, the index is only its address book |
| **`rg`/grep** (the search the estate's own law mandates, AGENTS.md §10) | a fast *text* matcher: <1 s across the tree, no ranking, no provenance, no semantics | raw text presence | the agent reads the match and then the file: two steps, one answer, no citation | keep as the **deep-read fallback** of the plane (tier 3), never as the entry point |
| **Knowledge graph** (`growmos`, `estate-graph`) | 10,772 entities, 14,154 relations; a query returns 636 nodes / 2,469 edges in **15.4 s** | durable, provenance-carrying *relations* between named things | far too slow to be a lookup; it answers "what is related" not "what is true now" | keep as the **durable provenance backbone**; feed the plane from its JSONL; `growmos query` becomes a *tier* inside the planner, not the front door |
| **Estate memory** (the unified memory server behind one MCP door; three live `estate-memory-mcp` processes) | semantic recall over what agents *said*; `bin/estate-brief --task` returns live claims in **3.20 s** | narrative context and shared meaning across surfaces | the brief is a *summary of a summary*: it names claims but not the facts behind them; nothing here knows about code or events | keep as the **meaning tier**; the plane composes it with the code index and the event spine so one call answers "what is true" instead of "what was said" |
| **Action ledger** (`~/.estate/estate.db`, local sqlite) | the estate's own record of what actually happened: `step_runs` **3,828**, `intent_tickets` **2,648**, `policy_decisions` **790** | decisions taken and their verdicts | an agent wanting "what did we decide about X" must know the schema and write SQL; the ledger is local, so it is invisible to the cluster | keep as the **decision tier**; index it, and let the plane answer decision questions without SQL |
| **Event spine** (NATS in the cluster: `estate.agent.*`, `estate.news.story`, `metrics.*`, `epistemic.*`; 3 hard schemas in `platform/event-bus/contract/`) | the estate's real-time nervous system — but it lives **behind cluster DNS**: `nc nats.event-bus.svc 4222` from the laptop fails | live state, at the moment it happened | *the laptop cannot see the estate live at all*; agents reconstruct liveness by polling (1,277 hand-rolled lane/CI polls in 24 h, per the estate's own memory) | run the plane's **ingest beside the bus** and expose a relay/stream to the laptop — the bus stays the spine, the plane becomes the laptop's window onto it |
| **Epistemic layer** (newsroom/epistemic: `reported → confirmed → corrected`) | the estate already has *correction semantics* — a fact can be retracted | whether a claim is true, corrected, or withdrawn | nothing consumes it as a general primitive, so a corrected fact can still be served by every other surface | reuse it as the **retraction primitive** of the plane: a correction tombstones the fact everywhere it was indexed (§4.12 L6) |
| **Claims / lanes / focus** (`~/.estate/memory/focus-register.json`, rewritten live; `claims.py` newest-claim-per-issue; `bin/lane-where`) | the estate's live ownership and CI state | who owns what, and whether a lane is green | agents read ownership from issue comments (slow, lossy) or re-derive it | keep as the **live-state tier**; the plane reads the register directly and never re-derives it |
| **Surfaces** (`/fleet`, the Face at `catalogue.mumchimp.com/face/`, Otto) | *views* over the above — each with its own query path | presentation | each surface re-queries the sources its own way, so two surfaces can disagree | surfaces become **read-only views of the plane's rows**; no surface keeps its own query path |

**What the review says, in four findings.**

1. **Every source is authoritative for something and for nothing else.** No single source can answer
   a cross-source question: *"which agent touched this file, what was decided about it, and was that
   decision later corrected?"* needs git **and** the ledger **and** the epistemic layer. That
   question is unanswerable in one call today, and it is the most common question in the estate.
2. **Real time is cluster-bound; the agents are laptop-bound.** The event spine and the epistemic
   layer are unreachable from the laptop, so the agent's view of the estate is a **poll** — and the
   estate has already measured what polling costs (1,277 hand-rolled polls in 24 h). Any design that
   leaves the plane laptop-bound inherits that cost.
3. **Two sources search without provenance; two carry provenance without speed.** `rg` and memory
   recall answer "where is it"; the graph and the ledger answer "what is related" / "what happened";
   neither pair can answer "what is true, right now, and how do I cite it".
4. **The estate already owns the three hardest parts of the oracle** — a semantic memory with one
   door, an enforcement gate with a decision ledger (717 rows, 524 pass / 169 refuse / 24 unknown),
   and correction semantics in the epistemic layer. The discovery plane is therefore **mostly
   plumbing and an index**, not a new invention — which is the cheapest possible way to buy the
   founder's "super accurate mega oracle".

**What the enforcement ledger shows (measured).** The estate already measures agent friction, and the
ledger is the best evidence in the repo (`~/.estate/memory/enforce-ledger.jsonl`, 717 rows on
2026-10-23):

| Observed | Count | What it says | The mechanism that removes it |
|---|---|---|---|
| `pass — covered by a live claim` | 336 | the gate works; the happy path is the common one | keep |
| `refuse — no live claim covers <path>` | 30+ | agents spend turns discovering they may not write, after the fact | **discovery-first**: the claim surface answers "may I write here?" *before* the agent writes, from the same live register (§4.12, §6.8) |
| `refuse — No plan declared, so Bash is refused` | 21 | the seven-gate plan is discovered by being refused | the plan is **published to the plane** at `declare_plan`, so the agent *reads* its obligations instead of hitting them (§4.1, §6.8) |
| `unknown — claim ledger unreadable` / `transcript unreadable` | 12 + 12 | the enforcement plane itself has **24 blind spots**: it cannot distinguish "refused" from "could not read" | the plane keeps its own health row: a source that is unreadable is reported as *stale*, never as *absent* (§4.12 L5) |
| a turn's context priming | `estate-brief` **3.20 s**; a graph query **15.4 s** | every agent turn pays up to ~19 s before acting | the plane answers in one call, and caches what is stable (§4.12 L4) |

### 2.11 Where the estate already solved this, three times, in pieces

Three doors built on 2026-10-23 are the shape of the oracle, in miniature, and the discovery plane
must **generalise them, not replace them**:

| Door (landed) | What it solved | The generalisation |
|---|---|---|
| `estate-memory-enforce` (claim #6857) | one gate that refuses an unclaimed write, with every decision written to a ledger | the same gate, answering *questions*, not only refusals: "what is true here?" gets the same enforcement and the same ledger |
| `bin/lane-where` (claim #7003) | "where is my branch" in one observation — LANDED/PENDING/GREEN/RED/GONE — replacing 1,277 hand-rolled polls in 24 h | the same idea for *every* liveness question, including the ones with no door yet |
| the skill layer (claim #6984, in flight) | one governed pack layer for every runtime | skills say **how to act**; discovery says **what is true** — adjacent, not duplicate |

---

## 3. What is genuinely missing — the nine gaps

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

### 3.7 The seventh gap: the estate is searchable, but it is not *discoverable*

The six gaps above are all about **doing work**. This one is about **knowing** — and it is the gap
that makes the other six expensive.

Measured, in one afternoon (full table and commands in §2.10 and Appendix A):

- The estate has **nine** data sources, each authoritative for something and for nothing else.
- **No source can answer a cross-source question.** "Which agent touched this file, what was decided
  about it, and was that decision later corrected?" needs git, the ledger and the epistemic layer
  together. Today that is three searches, three mental joins and one uncited answer.
- **Real time is cluster-bound and the agents are laptop-bound.** The event spine and the epistemic
  layer sit behind cluster DNS; the laptop cannot see them, so agents *poll* — 1,277 hand-rolled
  lane/CI polls in 24 h, per the estate's own memory.
- **Two sources search without provenance; two carry provenance without speed.** `rg` finds text,
  memory recall finds meaning, the graph and the ledger carry the truth — and none of them can
  answer "what is true right now, and how do I cite it".
- **The estate pays for its own ignorance in enforcement.** The enforce ledger has **24 `unknown`
  rows** — decisions the gate could not take because a source was unreadable — and **30+ refusals**
  for "no live claim covers this path", i.e. the agent discovered the rule *after* trying.

The founder's requirement is therefore three-part and it is stricter than "add a search box":

> "one place … everything that can be known about the estate is in one place and every agent is
> forced to use one source" · "super accurate mega oracle that can answer any question, super
> accurately, in real time" · **"nothing can escape it."**

The gap, stated exactly: **there is no single door that answers a question across all nine sources,
carries a citation, a freshness stamp and a retraction state for every sentence it returns, and is
forced on every agent without being copied into every runtime.** Everything the estate has today is
a *capability*; what is missing is the *one layer* those capabilities are read through.

### 3.8 The eighth gap: there is no way for one agent to talk to another in real time

The bus exists; the *contract* does not. Today an agent that needs a frontier decision has three
options and all three are bad: guess, hand the work back, or wait for a human. The estate's own
live-mind contract has a `steer` kind, so the *idea* of an agent-to-agent message was anticipated —
but there is no envelope, no channel model, no deadline, no default, no cost rule, no broadcast and
no place for the founder (§4.13). The consequence is the failure mode the founder named: the
executor and the planner cannot talk while the work runs, so every semantic decision either
stalls the plan or leaks into the cheap tier's guess.

### 3.9 The ninth gap: the estate has an identity substrate with no identities in it

The Quad was built (DROS ticket, 2026-09-28; `cmd/identity-bootstrapper`, `cmd/elpis-proxy`,
`cmd/dros-daemon`, `cmd/quad-ledger`; the registry DDL; ADR 0035). Measured on 2026-10-23: the
ledger **runs** (Deployment 1/1, anchor + verify CronJobs every 15 min) and the verify door
**passes** — with **0 rows** in `agent_actions` and **0** in `merkle_anchors` (A30, A31). The
registry tables `agents` and `sessions` **do not exist** (A32). Elpis, the bootstrapper and the
kernel enforcer are **not deployed** (A33), and ADR 0035 is still PROPOSED. So: the machinery to
prove *who did what* is running, and it has never proved anything, because no agent signs.

This is the gap that makes the delegation layer's ownership claims cheap to assert and expensive to
believe. A delegated packet that says `owner: pi` is a string; a delegated packet signed by a URN
whose session is in the anchored chain is evidence (§4.14).

---

## 4. Target design

### 4.1 The Delegation Contract (the one new artifact)

One JSON document, one schema (`docs/schemas/delegation-packet.schema.json` — **to be added**;
it does not exist today), versioned. It is
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
place: `platform/llm/artifact-tier.yaml` (a file **to be added**; the tier table is new, the lanes
it names are not). The router's lanes are the *implementation* of each
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
   sphere is the *policy*: the lane namespace and its aliases (`~/.estate/router-state/lanes.json`), the health classes and
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
   already specifies the shape: `name`, `where: laptop \| cloud \| both`, and
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

### 4.12 The Discovery Plane — one place, one door, nothing escapes

This is the layer that makes the other sections possible: the router's intelligence is bounded by
what it knows (§7.2), a delegation packet's context is only as good as what was found (§4.1), and a
verdict is only as good as its evidence (§4.6). So the discovery plane is specified **first**, and
the delegation plane is specified as its consumer.

**The shape.** A service with one wire contract (`estate.discover`), eight layers, and *no source of
truth of its own*: everything it says is a pointer into a source it did not change.

```
 question ──► L3 planner ──► L2 indexes ──► L0 adapters ──► sources
                  │              │              │
                  │              │              └─ git · graph · memory · ledger · bus · claims
                  │              └─ code · doc · event · semantic · decision · live-state
                  └─ tier ladder: exact → semantic → deep read → synthesis
                                    │
                            L4 answer object ──► L5 verify ──► L6 freshness/retraction
                                    │
                            L7 enforcement (the door every agent uses)
```

#### L0 — Ingest: one adapter per source, read-only, always with provenance

Each adapter is a small, declarative reader for exactly one source, and it is the **only** thing
allowed to read that source raw. Every fact it emits is a **document**:

```json
{
  "source_id": "git:idp:platform/llm/watchdog.py",
  "source_kind": "code|doc|event|memory|decision|live_state|graph",
  "locator": "platform/llm/watchdog.py:88",
  "span": "…the watched text…",
  "as_of": "2026-10-23T20:41:14Z",
  "epistemic_state": "reported|confirmed|corrected|retracted",
  "sha": "…",
  "content_hash": "…"
}
```

Rules, all deterministic: an adapter **never writes** to its source; it **never invents** a fact it
did not read; a document with no `locator` is rejected at ingest (a fact without an address is not a
fact); and a source that cannot be read produces a `stale` marker for that source — never an empty
result, because "unreadable" and "absent" are different answers (this is the defect the enforce
ledger's 24 `unknown` rows show the estate has today).

#### L1 — Canonical entity resolution: one thing, one id, everywhere

The same thing appears under many names: `idp`, `chidionyema/idp`, `the platform repo`; `pi`,
`pi-parity`, `agent pi`; issue `#7001` and `idp#7001`. Discovery requires **one entity id per
thing**, with aliases, so a question can join across sources:

- `discovery.entity(id, kind, canonical_name, created_at)` — kinds: `repo`, `path`, `symbol`,
  `service`, `issue`, `agent`, `runtime`, `model`, `lane`, `decision`, `spec`.
- `discovery.alias(entity_id, alias, source_id)` — every surface name ever seen, and where it was seen.
- Resolution rules: (1) exact alias match wins; (2) a canonical-name normalisation (repo slug,
  issue number, symbol path) wins over free text; (3) **ambiguity is never resolved by guessing** —
  the answer returns both candidates and asks which one, because a wrong join is worse than a
  question.

#### L2 — Indexes: six indexes over one document stream

| Index | Built from | Serves | Baseline today |
|---|---|---|---|
| **code** | git trees + symbol extraction | "where is X defined", "who owns this file" | `rg` + read (two steps, uncited) |
| **doc** | specs, ADRs, decisions, runbooks | "what does the estate say about X" | `rg` over `docs/` |
| **event** | the bus, by subject and kind | "what happened at 20:41" | cluster-only, unreachable from the laptop |
| **semantic** | memory bodies (embeddings) | "anything like X" | `brief`/`recall` (3.20 s, semantic only) |
| **decision** | the action ledger | "what was decided, and with what verdict" | SQL by hand (790 policy decisions) |
| **live_state** | claims, lanes, focus register | "is it green, who owns it" | 1,277 polls / 24 h |

All six are **derived**: delete the index and it is rebuilt from the sources. The plane holds no
truth of its own — that is what makes it portable (§4.12 portability paragraph) and disposable.

#### L3 — The planner: a question class picks a tier ladder, and the ladder stops on sufficiency

| Question class | Example | Ladder (cheapest first) | Stop condition |
|---|---|---|---|
| **what-is / where-is** | "where is the retry budget set?" | code index → doc index → deep read | an exact locator match |
| **who-does / owns** | "who owns `platform/llm`?" | live-state → code index → ledger | an owner with a live claim |
| **what-happened** | "what did we decide about the router?" | decision index → event index → semantic | a verdict + its decision id |
| **why** | "why is the floor lane free?" | doc index → graph → semantic → synthesis | a cited rationale |
| **what-changed** | "what changed in the estate in the last hour?" | event index → live-state → decision | a bounded time window |
| **is-it-true** | "is the claim still live?" | live-state + epistemic | a confirmed/corrected state |

The planner's stop condition is **deterministic**, not a model's opinion: a tier stops when the
answer contains the fields the question asked for (a locator for "where", a claim id for "who", a
verdict for "what was decided"). If no tier produces a sufficient answer, the planner **escalates**;
if the last tier still fails, it returns "the estate does not know this" with the search it performed.
Every escalation is logged with its latency and cost, because the cost of the plane is exactly the
sum of its escalations.

#### L4 — The answer object: prose plus per-sentence evidence

```json
{
  "question": "where is the retry budget set?",
  "answer": "platform/llm/watchdog.py:88, in WatchdogPolicy.retry_budget_usd.",
  "claims": [
    {"statement": "the retry budget is 0.50 USD",
     "source_id": "git:idp:platform/llm/watchdog.py",
     "locator": "platform/llm/watchdog.py:88",
     "as_of": "2026-10-23T20:41:14Z",
     "epistemic_state": "confirmed",
     "content_hash": "…"}
  ],
  "unknowns": [],
  "contradictions": [],
  "searched": ["code", "doc"],
  "elapsed_ms": 240
}
```

The answer is never prose alone: `claims` is the substance, and each claim carries the four things
that make it checkable — **where**, **when**, **what state**, **which exact bytes**. `unknowns` and
`contradictions` are first-class fields, because the two most dangerous answers in an estate are
"it is definitely X" when it is not, and "X" when two sources disagree.

#### L5 — Verification, and the right to refuse

Four deterministic checks, all machine-checkable, no model in the loop:

1. **No citation, no claim.** Every statement in `claims` has a `source_id`, a `locator` and an
   `as_of`. A statement without one is dropped from the answer and counted as a defect.
2. **Locators must resolve.** The locator is re-read from the source at answer time; if the bytes
   changed, the claim is re-labelled `stale` rather than served as fact.
3. **Contradictions surface.** If two claims about the same entity conflict, both are returned with
   their states, and the conflict is ranked by epistemic state and `as_of`.
4. **Refusal is a first-class answer.** "The estate does not know this" is a valid, successful
   result — with the searched sources listed. An oracle that cannot say *no* is a guess generator.

This is the whole accuracy story, and it is worth stating plainly to the founder and the
consultant: **the oracle's accuracy does not come from a larger model.** It comes from (a) mandatory
provenance, (b) the right to refuse, (c) contradiction surfacing, (d) retraction, and (e) a measured
refusal/retraction rate. A model is used only at tier 4, to *phrase* retrieved spans — never to
produce a fact.

#### L6 — Freshness and retraction: the estate's own epistemic semantics, reused

The estate already knows what a corrected fact is: the epistemic layer has
`reported → confirmed → corrected`. The plane reuses it as the retraction primitive:

- each source has a **watermark**; a document is served only with the `as_of` the source gives it;
- a `corrected` fact **tombstones** every index entry that quoted it (`discovery.tombstone`);
- an answer that cited a tombstoned fact is re-issued as `stale` to every caller that received it
  (the query log carries the answer ids, so re-issue is a join, not a broadcast);
- a source whose watermark has not moved in N minutes is served with `freshness: stale` **and** the
  source is reported as unreadable if it cannot be reached at all.

#### L7 — Enforcement: how agents are *forced* to use one source

The founder's word is "forced", so this is not a recommendation; it is a gate, and the estate
already has the machinery for it (the enforce hook and its ledger):

| Rule | Mechanism | Where it is enforced | Failure it prevents |
|---|---|---|---|
| **Discovery-first** | the session brief is a discovery call; the plane's answer is the session's context | the runtime bridge (`bin/estate-brief` already is one) | an agent acting on a stale mental model |
| **Ask before you write** | "may I write here?" is a discovery call against the live-state index | the enforce hook refuses a write whose path has no live claim — **the same rule, answered before the attempt** | the 30+ "no live claim covers …" refusals (friction, not safety) |
| **Cite to finish** | a plan may not be `complete_goal`-ed without at least one discovery id in its evidence | `complete_goal` (the same seven gates that already refuse a missing `add_bdd`) | an uncited conclusion, in the report or in the code |
| **One door, not N doors** | every runtime gets **one** discovery tool from the runtime manifest; a runtime without MCP gets a transport extension | `platform/estate/memory/runtimes.json` + `bin/estate-memory-install` (the estate's existing rule) | a per-runtime bespoke integration (the duplication the estate's law forbids) |
| **Raw reads are visible, not forbidden** | direct source reads are recorded in the query log as "bypassed the plane" | the same ledger | silent divergence between what an agent read and what the estate knows |

The fifth rule is deliberate: blocking the founder's own exploration would be a law the estate
cannot keep. The gate's job is to make the plane the *fast path*, not to imprison the agent.

#### Portability of the plane

The plane is portable because it has no home:

- **No local state.** All six indexes are derived; the plane can be rebuilt from the sources on any
  machine. The laptop copy and the cluster copy answer the same questions, and the cluster copy is
  the fresher one for events.
- **One wire contract, many deployments.** `estate.discover` is a request/response contract over the
  estate's existing door (the same door the memory MCP uses), so a laptop agent, a cluster agent
  and a cloud sandbox agent call the same thing. This is the estate's existing rule — *one bridge
  per runtime*, transport extension, never a second implementation.
- **One policy, many renderers** (§4.11): the tiers, budgets and escalation rules live in the same
  policy file the router reads, so a sphere cannot drift into a different discovery behaviour.
- **Placement by the free-tier ladder** (§4.10): the ingest and the indexer run where the sources
  are (the cluster, beside the bus); the query path runs where the agents are (the laptop, or the
  cloud); the relay between them is one small service, not a new plane.
- **Sphere-local sources are first-class**: a cloud sandbox's own repo and logs are indexed by the
  same adapter contract, so "what is true" means "true in this sphere, plus what the estate knows".

#### The state it owns (four tables, all derived)

| Table | Rows | Written by | Read by |
|---|---|---|---|
| `discovery.document` | every fact ingested | adapters | planner |
| `discovery.entity` + `discovery.alias` | canonical things and their names | resolver | planner, answer layer |
| `discovery.tombstone` | retracted facts | epistemic adapter | answer layer, re-issue |
| `discovery.query_log` | every query: class, tiers tried, latency, cost, answer id, whether the answer was cited | planner | cost model, friction measurement, re-issue |

Plus one **non-table** obligation: the plane answers the estate's own question — *what does the
estate know, how fresh is it, and what does it not know?* — as a first-class query class
("coverage"), because an oracle that cannot measure its own blind spots is decoration.

---

### 4.13 The message plane — real-time communication between models, harnesses and the founder

**The requirement, in the founder's words (2026-10-23).** "The executor model needs to communicate in
real time with the mid or frontier model or vice versa … any communication real time across models
and harnesses … this needs to be an estate-wide, well-thought-out and architected feature,
including broadcast, enterprise peer-to-peer realtime comms with broadcast, and also founder
inclusive."

**What the estate already has.** The transport: NATS in the cluster, subjects
`estate.agent.{runtime}.{session}.{kind}`. The event contract: `estate.agent.event`, whose kinds
already include `steer`. The founder's standing law: *"real-time or invalid. Every agent run, PR,
queue step, CI result, deploy, cluster change and rule refusal is visible live on FleetView, from
the event itself"* (founder rule, 2026-09-30).

**What is missing.** A *message* is not an *event*. Events are broadcast facts about what happened;
messages are addressed requests that expect an answer, with a deadline, a default and a cost. Today
an agent that needs a frontier decision has no door: it either guesses, or it hands work back, or it
waits on a human. So the message plane is specified here, in the same "one of each layer" spirit:
**one bus, one envelope, one policy.**

**The envelope.** One JSON document, one schema (`estate.agent.message`), versioned — the same
discipline as the delegation packet (§4.1):

```json
{
  "message_version": 1,
  "id": "msg-7042-03-0007",
  "channel": "plan:idp-7042",
  "from": {"agent": "pi", "runtime": "pi", "sphere": "laptop", "role": "implementer"},
  "to": {"kind": "role", "role": "frontier_reasoner"},
  "class": "escalate",
  "body": {
    "question": "the retry budget is a per-call or per-plan ceiling?",
    "packet": "idp-7042/03",
    "citations": ["git:idp:platform/llm/watchdog.py:88"],
    "default_if_unanswered": "refuse_and_hand_back",
    "deadline_s": 30
  },
  "reply_to": null,
  "as_of": "2026-10-23T21:04:00Z",
  "expires_at": "2026-10-23T21:04:30Z"
}
```

`citations` are **discovery ids** (§4.12): a message that asserts something carries the same evidence
obligation as an answer. A message without citations is a question, not a claim.

**Three channel kinds, and nothing else.**

| Kind | Who it reaches | Use | Cost rule |
|---|---|---|---|
| **point-to-point** | one named agent | a hand-off, a targeted ask | one wake-up |
| **role channel** | whoever currently holds the role (frontier reasoner, verifier) | escalation, review, arbitration | one wake-up; the *router* picks the lane (§4.2), so a role channel works even when the named model is down |
| **broadcast** | every live subscriber in scope | an estate-wide or plan-wide notice | **per copy**: the publisher is charged N times for N subscribers |

A role channel is the important one: it makes the *role* the address, not the model, so the estate
never hard-codes "ask `gpt-5`" — the same late binding the packets use (§4.11).

**The escalation pattern** — the founder's own example, made deterministic:

1. a cheap executor hits a decision it is not allowed to make (a semantic or architectural choice,
   not a mechanical one);
2. it publishes `escalate` to the plan's **role channel**, carrying the packet id, its citations, a
   **deadline** and a **documented default**;
3. the frontier reasoner (whichever lane is healthy) replies `answer`, and the executor applies it;
4. if the deadline passes with no reply, the executor **takes the default** — normally
   `refuse_and_hand_back` — and records that it did. It never guesses and it never waits forever.

This is the same "no half-funded work" rule as §7.3, applied to a different resource: attention.

**Delivery semantics** (deterministic, not "best effort"):

- **at-most-once with explicit ack** for point-to-point and role messages: an unanswered escalation
  is an *event* ("escalation timed out, default applied"), never a silent loss;
- **per-channel ordering** by sequence number, so a plan's messages read in order;
- **dead-letter** after N delivery attempts, with the dead letter visible on /fleet;
- **expiry**: every message carries `expires_at`; an expired message is never delivered to a
  newcomer (a channel is not a backlog);
- **every message becomes a live row**: the same `estate.agent.event` kinds the estate already
  publishes, so the founder sees the exchange live on /fleet and hears it on the Face, exactly as
  the "real-time or invalid" law requires.

**Founder-inclusive.** The founder is a first-class participant, not an observer of logs:

- **observe**: any live plan channel is visible on **/fleet**, audible on the **Face** ("what is the
  plan saying?" — arg-free, per the Face's constraint, §6.4) and readable from the **console on the
  Mac** (`bin/estate-brief`-style, §6.10);
- **steer**: the founder's note is injected into the channel as a `founder_note` and is bound to the
  plan; a `steer` from the founder interrupts the plan's next decision point (this is what the
  live-mind `steer` kind was for);
- **instruct**: an instruction that changes scope becomes an **issue comment** — the estate's
  existing authority model — not free-form chat, so it is recorded, cited and auditable;
- **cost**: a founder steer wakes exactly the agents in the channel it targets; it never wakes the
  estate.

**Why this is not a second bus, a second workflow engine, or a second event contract:** the bus
carries it, Temporal still sequences plans, `estate.agent.event` still carries the rows, and the
message envelope is the only new artifact — one document, one schema, one policy.

### 4.14 Identity — the Quad inside the delegation plane

**The requirement (founder, 2026-10-23).** "This may be a good time to think about how to integrate and
operationalise the Quad solution, so agents' identity is solved."

**What the Quad already is.** A four-layer identity substrate plus a ledger, written down in the
DROS ticket (2026-09-28) and implemented in `cmd/`:

| Layer | Component | What it does | State, measured 2026-10-23 |
|---|---|---|---|
| 1 | `cmd/identity-bootstrapper` | SPIRE Workload API → JWT-SVID → RFC 8693 token exchange → Ed25519 key in tmpfs, never in the agent's filesystem | code present, **not deployed** (A33) |
| 2 | `schema/identity0_registry.sql` | the registry: `agents` (URN primary key, public key, fingerprint, lineage, authority scope, operator), `sessions` (SPIFFE id, harness, model) | **the DDL was never applied** — `agents`/`sessions` do not exist in any database (A32) |
| 3 | `cmd/elpis-proxy` | signs every request an agent makes (Method + URI + Timestamp + BodyHash + AgentURN + SessionID) and injects `X-Agent-Id`, `X-Agent-Signature` | code present, **not deployed** (A33) |
| 4 | `cmd/dros-daemon` (BPF LSM) | kernel egress enforcement: an unregistered process gets `-EPERM` | code present, **not deployed**; ADR 0035 (one DaemonSet per node) is still **PROPOSED**, founder decides |
| 4′ | `cmd/quad-ledger` | the single writer that turns signed actions into a hash chain in `estate-db`, anchors the chain head outside the cluster, and verifies it | **running** — Deployment `quad-ledger` 1/1, anchor + verify CronJobs every 15 min; the `quad.ledger-verify` intent passes — but with **0 rows** (A29–A31) |

**The honest finding.** The Quad is *built and idle*: the machinery runs, the verification door
passes, and the ledger is empty, because nothing signs an action yet. The estate therefore has an
identity substrate with **no identities in it** — the delegation plane cannot lean on it today.

**The integration, in one rule.** *Every actor in the delegation plane is a URN, and every action it
takes is a signed row.* Concretely:

| Where identity appears | Today | With the Quad |
|---|---|---|
| the delegation packet's `owner` | a free-text agent name ("pi", "claude") | the **agent URN** (`urn:aid:<sphere>:<agent>`), resolvable in the registry |
| the message envelope's `from` / `to` | names, and a role | URNs; a **role channel** resolves to the URNs whose registry `authority_scope` holds that role |
| the claim trailer (`Claim: <owner>/<repo>#<n>`) | an owner name | the URN plus the human-readable owner — the gate checks the URN, humans read the name |
| the discovery answer | prose with citations | the same, plus the **acting URN** and the attestation tier of the answerer |
| the plan row on /fleet | a runtime name | the URN, the role, the attestation tier, and the session id |
| the audit trail | a git history | the ledger's hash chain + the external anchor — **history that cannot be quietly edited** |

**Two attestation tiers, one model.** The Quad's layers 1–4 assume a cluster pod with a SPIFFE
identity. The estate's other half — the laptop agents (pi, claude, opencode, and the executor the
delegation layer adds) — cannot have kernel attestation, and pretending otherwise would be a lie in
the ledger. So:

- **kernel-attested**: a cluster pod with a SPIRE SVID; its requests are signed by the Elpis proxy;
  the kernel refuses unsigned egress. Strength: the strongest available.
- **door-attested**: a laptop agent whose every action goes through the **executor door**
  (`estate-execute`), which signs the request with a device key and writes the same
  `agent_actions` row. Strength: attested at the door, not by the kernel; recorded honestly as such.

Both tiers write the **same** table, the same signature envelope and the same chain. The row
carries the tier, so a reader can always tell how strong an attestation was — the ledger records
what is true, not what is convenient (the Quad's own principle).

**Operationalising it — the order that works** (each step is a claim, a lane and a proof):

| # | Step | What it proves | Why in this order |
|---|---|---|---|
| 0 | apply the registry DDL and **register the estate's agents** with URNs, keys, roles and authority scopes | `agents` and `sessions` exist and hold the estate's real agents | identity must exist before anything can reference it |
| 1 | deploy the **Elpis proxy** as the only egress for the delegation executor in-cluster, with the executor talking to the router through it | the first signed action lands in `agent_actions` | the executor is the first actor the delegation plane adds; identity is proven on the new path, not retrofitted |
| 2 | run the ledger for real: the first signed action, the chain, the anchor, the **verify** | `quad.ledger-verify` passes with **rows > 0** (A30's zero becomes non-zero) | an empty chain is not evidence of integrity |
| 3 | **door-attested tier** for the laptop: the executor signs and writes the same rows | a laptop action appears in the same ledger, tagged `door` | this is how the founder's own agents become attributable |
| 4 | **kernel enforcer** (ADR 0035) as the final closure | an unsigned process gets `-EPERM` | last, because it is the step that can break working agents; 0035 already measured two bypasses (unknown PIDs, IPv6) |
| 5 | **founder-facing identity**: /fleet shows URN + tier + role; the Face names the agent it is talking to; the **console on the Mac** answers "who am I" and "who did that" | the founder can see *who* acted, on the surface they are already using | identity the founder cannot see is identity the founder does not have |

**What identity buys the delegation plane** (why this is not a detour):

1. **attribution** — every diff, message and dollar is attributable to an agent and a session
   (the delegation layer's "who owns this packet", §7.4);
2. **authority** — a packet's `owner` URN and the registry's `authority_scope` decide what that
   agent may do, so a cheap executor *cannot* take a frontier-only action (§4.2's tiering becomes
   enforceable, not advisory);
3. **continuity** — `sessions` + `lineage_parent` prove that a resumed run is the same agent
   (the "continuity and ownership" problem, §7.4);
4. **proof** — the chain and its external anchor make the estate's own history non-editable, so a
   claim's provenance can be *proved* to a consultant or an auditor, not asserted;
5. **cost** — an action row carries the session, so spend is attributable to an agent rather than
   to a token bucket (§8).

---

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
| `platform/llm/front.py` + LiteLLM | the single model door; per-request routing; per-alias fallbacks | asks it for the alias the *packet* names | never choose a model outside `~/.estate/router-state/lanes.json`; never hold a vendor key |
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
  aliases that `~/.estate/router-state/lanes.json` already serves, and a check refuses an alias the live registry does
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
| 0.5 — the discovery plane | the cross-source index and the cited-answer door, in shadow mode beside the existing searches | 30 real questions answered with a citation each; **the estate's "I don't know" answers counted** (currently unmeasurable) | 2–3 |
| 0.75 — the Quad, operationalised | the registry DDL applied, the estate's agents registered with URNs, and the first signed action written by the ledger | `agents`/`sessions` exist; `agent_actions` goes from **0** (A31) to ≥1; `quad.ledger-verify` still exits 0 | 1–2 |
| 1 — the contract | `delegation-packet.schema.json`, the artifact-tier table, and their tests | schema test green; **every tier-table alias is present in the live `~/.estate/router-state/lanes.json`**; the tier table is parsed by `sovereign/policy.py` and the drift test fails when they disagree | 1 |
| 1.5 — the message plane | the message envelope, the role channel, the deadline+default rule and the founder's channel; the bus already carries it | one escalation answered inside its deadline; one broadcast acked by every live subscriber; the founder's note visible in the plan's row | 1–2 |
| 2 — one adapter | the `opencode` adapter (`invoke`/`capture`/`resume`), in shadow mode beside the normal path | on 10 real `edit_diff` sub-tasks: the cheap diff is produced, its scope gate passes, and its acceptance gate result is recorded — with **no** adoption | 1–2 |
| 3 — one real delegated sub-task | a two-sub-task plan, one per tier, landed through the greenlane with the claim gate live | the plan's acceptance passes; `claim-gate` green; the change lands on `main` via the lane; the state rows and the live-mind rows are visible on /fleet | 1 |
| 4 — fan-out | three or four concurrent sub-tasks, with the measured machine-capacity bound live | a fan-out at the bound completes with no swap pressure above the 2026-10-21 baseline; killing one worker mid-flight leaves the plan completable by resume | 1 |
| 5 — voice and monitoring | the four arg-free Face verbs, the /fleet plan panel, the decision log | the founder can ask "where is everyone" and get the truth from the board's own rows; a tier decision can be explained after the fact with its evidence | 1 |
| 6 — spheres | the config-drift check; the registry's `transports`/`resumable` fields; one packet bound in a second sphere | the same packet body runs in two spheres, both pass the **same** acceptance commands, the bindings differ, no path/binary/key crosses spheres; the drift check is green across the live spheres | 1–2 |

**Total: 9–14 days, one operator, no new always-on cost.** The phases are ordered so that phase 0
and phase 1 are worthless on their own but make every later phase cheap. The discovery, identity and
message phases are *cross-cutting*: they can run in parallel with the delegation phases, and each
one makes the delegation layer more trustworthy rather than more complex.

---

### 6.8 The discovery plane in the stack — what plugs in, and what it must not do

The plane is a **reader**, not a writer. It sits beside every source and inside no source's job.

| Existing component | Its role today | What the discovery plane adds | What it must NOT do |
|---|---|---|---|
| **NATS event spine** (cluster) | the estate's live nervous system | the plane subscribes to the same subjects and turns events into documents with `as_of` | not publish, not own a subject, not become a second bus |
| **estate-memory** (the MCP door) | semantic recall of what agents said | the plane *uses* memory as its semantic tier and adds code, event and decision tiers around it | not replace the memory store, not write memories, not fork the bridge |
| **growmos graph** | durable provenance-carrying relations | the plane reads its JSONL as one index; `growmos query` becomes a planner tier | not re-implement extraction, not write `.growmos/` directly |
| **`estate.db` action ledger** | step runs, intent tickets, policy decisions | the plane indexes it as the decision tier ("what was decided, with what verdict") | not own a second decision log |
| **git (56 repos)** | the truth about code | the plane builds the code index (symbol, path, owner, last change) | not modify a tree, not be a second source of truth, not reimplement `git` |
| **claims / focus register / lanes** | live ownership and CI state | the plane serves "may I write here?" and "is it green?" before the agent acts | not decide ownership, not replace `bin/claim-gate` |
| **`sovereign/verifier.py` + the deterministic gates** | acceptance | the plane supplies the *evidence* the verifier reads | not verify, not pass a gate, not vote |
| **greenlane** | prove green, then land | the plane supplies the context a lane needs to avoid re-reading the world | not merge, not push, not raise PRs |
| **`/fleet`, the Face, Otto** | views for the founder | both read the plane's rows and the plane's query log | not query the raw sources their own way |

**New intents (three, all read-only except the last):**

| Intent | Args | Returns |
|---|---|---|
| `discover.query` | `question`, optional `sphere`, `freshness`, `max_escalations` | the answer object (§4.12 L4) |
| `discover.cover` | `subject` | what the estate knows about the subject, from which sources, how fresh, and the blind spots |
| `discover.index.status` | optional `source_id` | per source: last watermark, staleness, last error, document count |

The MCP surface is **one** tool, `discover`, added to every runtime through the existing runtime
manifest (`platform/estate/memory/runtimes.json` + `bin/estate-memory-install`); a runtime without
MCP gets a transport extension to the same door. That is the estate's own one-bridge rule
(Appendix B), applied to discovery.

**Where it sits in the sequence (§6.7 amended):** after the router is live and before the fleet
fan-out is trusted. The delegation plane consumes the plane's answers for context and for
"where is everyone"; the plane consumes the delegation plane's events for the event index. The
dependency is one-way per query and one-way per event — **no cycle**, so the plane can be built
and shipped independently.

### 6.9 The discovery-first contract, in the founder's own terms

The founder asked that agents be "forced to use one source". In practice, for a task, that is five
moments:

1. **Before planning**: the brief *is* a discovery call — it already returns live claims and
   pending work; the plane adds the "what is already known about this" tier.
2. **Before touching a file**: "may I write here?" — one discovery call against the live-state
   index; the claim surface answers instead of the write being refused afterwards.
3. **Before spending**: the pre-flight (§4.9) asks the plane what this lane has cost and what it
   failed on before, so the plan starts from measured history instead of a guess.
4. **Before concluding**: the completion of a goal carries the discovery ids that support it — the
   same rule that already refuses a goal with no `add_bdd`.
5. **Before reporting**: the report's claims cite discovery ids, so a reader can re-ask the plane
   the same question and get the same answer (or its corrected version).

---

### 6.10 The console surface — asking the estate from any terminal, in any harness

The founder asked (2026-10-23): *"another surface should be direct from console like i am doing now,
from any harness if possible."* The estate already has this pattern — `bin/estate-brief`,
`bin/estate-checkpoint`, `bin/lane-where`, `bin/claim-open` — and it works in every runtime because
it needs no MCP client, no configuration and no key in a repository.

So the discovery plane ships with a **console client** as a first-class surface, beside the MCP
tool, not after it:

```
bin/estate-discover "where is the retry budget set?"              # the answer, with its evidence
bin/estate-discover --json "what did we decide about the router?"  # machine form
bin/estate-discover --explain "is the claim still live?"            # the search it performed, tier by tier
bin/estate-discover --cover platform/llm                            # what the estate knows here, and its blind spots
bin/estate-discover --source git --reindex                          # (admin) rebuild one index
```

The rules that make it work "from any harness":

- **no configuration** — it reads the same door the memory bridge reads (the key by name, never in a
  repository), so it works on a laptop, in CI, and in a sandbox;
- **no MCP required** — it speaks the `estate.discover` wire contract directly, so `pi`, `claude`,
  `opencode`, a bare shell, a Makefile, a CI step and the founder's terminal are all first-class
  callers;
- **one implementation** — the console client and the MCP tool are the same call; there is no second
  query path (the same discipline as one bridge per runtime);
- **exit codes carry truth** (the `lane-where` precedent): `0` answered, `3` not found, `4` partial
  (some sources stale), `5` the plane is unreachable — a script can branch without parsing prose;
- **`--explain` is how the founder audits the oracle**: it prints the tiers tried, the documents
  read, each source's freshness, and why the answer stopped where it did.

This is also the answer to "how do agents discover": **the same door from every surface** — a
terminal, an MCP runtime, `/fleet`, the Face. The Face's arg-free verbs ("where is everyone") are
the live-state class with an implicit newest target; the console is the same call with an explicit
question.

---

### 6.11 The message plane in the stack

| Existing component | Its role | What the message plane adds | What it must NOT do |
|---|---|---|---|
| **NATS (cluster)** | the transport for everything live | the message subjects (`estate.msg.{channel}.{class}`) and the ack/dead-letter semantics | not a second bus, not a second event contract |
| **`estate.agent.event`** (live-mind) | the event rows /fleet and the Face read | the message plane publishes its exchanges as the *same* rows (kind `steer`, and the new kinds the contract allows) | not invent a parallel row type the surfaces must learn |
| **the router** (`platform/llm/front.py`) | picks the lane per request | a role channel resolves to a lane through the router, so an escalation to "the frontier reasoner" works when the named model is down | not choose a lane outside the live registry |
| **the delegation packet** (§4.1) | the unit of work | a message references a packet id; the packet stays the only thing that crosses a harness boundary | not carry code or prose blobs in the message body |
| **the discovery plane** (§4.12) | facts with provenance | a message's `citations` are discovery ids; a message may carry an answer object | not be a message bus |
| **Temporal / the sovereign engine** | sequences plans, durable workflows | the message plane is *within* a step, for the parts a workflow cannot express (ask a peer, escalate a decision) | not re-implement durable timers or retries |
| **`/fleet`, the Face** | the founder's surfaces | both show the live exchange: who asked, who answered, what it cost, what the default was | not require a form, a table dump or a report to read later |

**New intents (two):** `msg.send` (channel, class, body, deadline, default) and `msg.listen`
(channel, since) — plus the surface-level verbs the founder uses by voice, which stay **argument-free**
because the Face cannot pass arguments (§6.4): "what is the plan saying", "tell the plan to hold",
"who is waiting on what".

**Where it sits in the sequence (§6.7 amended):** the message plane is **phase 1.5** — it needs the
bus (which exists) and the plan state rows (§4.7); it does not need the delegation layer to be
complete, and the delegation layer becomes far better once escalations have a door. The discovery
plane is phase 0.5 for the same reason: a message with citations needs the plane to be honest.

### 6.12 The Quad in the stack

| Existing component | Its role | What the delegation plane adds | What it must NOT do |
|---|---|---|---|
| **the registry** (`schema/identity0_registry.sql`) | the authoritative agent list (URN → key, role, authority) | the resolver behind every role channel; the source of the packet's `owner` | not duplicate identity in `estate.db` |
| **Elpis** (`cmd/elpis-proxy`) | signs each request (URN, session, body hash, timestamp) | the executor's egress becomes the signing proxy, so every delegated action is attributable | not sign on the agent's behalf without the agent's key |
| **the Quad ledger** (`cmd/quad-ledger`) | the single writer; hash chain; external anchor; verify | the delegation plane's actions, messages and plan transitions are the rows | not become a second audit store; the git history stays the code's history |
| **DROS kernel enforcer** (`cmd/dros-daemon`, ADR 0035) | kernel egress refusal for unregistered processes | the final closure of step 4 — not a prerequisite for the delegation plane | not be switched on before 0035's two measured bypasses are fixed |
| **SPIRE** (spire-server, two agents, CSI driver — running, A33) | the workload identity | the kernel-attested tier's source of truth | not be replaced by the registry's keys |
| **`estate.db`** | the estate's own state | the delegation, plan and message tables (they live here) | not absorb the Quad's tables (they live in `quad_ledger`, A31) |
| **`/fleet`, the Face, the Mac console** | the founder's surfaces | all three render the acting URN, its role and its attestation tier | not show a name where a URN is the fact |

**Founder inclusion, on the three surfaces the founder actually has** (/fleet, the Face, and the
console on the Mac): the identity of every actor is visible on all three, and the Face's verbs stay
**argument-free** (§6.4) — "who is running the plan", "what did the executor just do", "who am I".

### 6.13 Where this sits in the sequence

The Quad is **phase 0.75**: it needs only the registry and the ledger, both of which exist as code
and a running deployment. It does not wait for the delegation layer — and the delegation layer
becomes trustworthy because of it.

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
   health, capabilities, tools). The estate already has most of this: `~/.estate/router-state/lanes.json` is a lane
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

### 7.9 The oracle: super accurate, real time, and nothing escapes it

**The difficulty, stated honestly.** "A super accurate oracle that answers any question about
anything, in real time" is not a search problem; it is a *truthfulness* problem under three
adversaries: a **stale** estate, a **partial** estate (a source that cannot be read), and a
**model** that will confidently fill a gap with something plausible. Any design that answers from
one index, without provenance, without the right to refuse and without retraction, will be wrong
often and *will not know it is wrong* — which is the failure mode that actually hurts an estate.

**The mechanism** is §4.12 in full. Its five load-bearing parts, restated as the oracle's contract:

1. **Provenance is mandatory** — every claim carries source, locator, `as_of`, epistemic state.
2. **Refusal is a success** — "the estate does not know this" is a first-class answer, with the
   search performed.
3. **Contradictions are surfaced, not smoothed** — two claims about one entity are returned with
   their states and times.
4. **Retraction propagates** — a `corrected` fact tombstones every index entry that quoted it and
   re-issues the affected answers as stale.
5. **Nothing escapes the door** — every agent's reads are recorded; every write is preceded by a
   live-state answer; every conclusion cites a discovery id.

**The proving measurement.** Seven numbers, all measurable, none of them "the model felt good":

| # | Measurement | How | Target | Failure it catches |
|---|---|---|---|---|
| M1 | **citation coverage** | of every answer's claims, the fraction with a locator that re-resolves to the same bytes | 100 % | the planner answering from the model's head |
| M2 | **stale detection** | replay a labelled question set against a snapshot, then mutate 5 % of the source facts; re-query | 100 % of mutated facts re-labelled stale within one watermark interval | a plane that serves yesterday's truth |
| M3 | **refusal correctness** | 100 questions about things that never existed, hand-labelled | 0 fabricated answers; ≥95 % correct refusals | a confident guess engine |
| M4 | **retrieval sufficiency** | 50 questions with a known gold locator; compare top-1 | ≥90 % exact locator match; report p50/p95 latency and cost | a plane that finds *a* thing rather than *the* thing |
| M5 | **real-time lag** | publish an event on the bus, ask the plane, measure the lag | p95 < 2 s | a "real-time" claim that is really a poll (the 1,277-polls failure mode) |
| M6 | **coverage and blind spots** | the `discover.cover` query per source | every source either indexed with a live watermark or explicitly marked stale/unreadable — never silently absent | the 24 `unknown` rows in the enforce ledger repeating at a larger scale |
| M7 | **answer cost** | per answer: tiers tried, escalations, wall-clock, tokens, and the cost of the sources read | p95 latency inside the tier budget; escalations logged per class (the plane's cost *is* its escalations) | a plane that is slower or dearer than the searches it replaces |

M1–M4 and M6 are deterministic and belong in CI (they are a test suite, not a judgement). M5 is a
property of the deployment (it needs the cluster-side ingest), and M7 is the number that decides
whether the plane earns its keep.

---

### 7.10 Real-time communication between models and harnesses

**The difficulty.** Real-time agent-to-agent communication is easy to demo and hard to make
*correct*, because four things go wrong at once: (1) **a wake-up costs money** — every message that
reaches a model is a paid call, and an estate-wide broadcast is N paid calls; (2) **a silent
timeout is worse than a slow answer** — an executor that waits forever on a frontier decision is a
stalled plan; (3) **the laptop cannot reach the bus** (A23: the spine is cluster-only today), so
"real time" for a laptop agent is currently a poll; (4) **a broadcast that wakes everyone is the
2026-10-21 saturation waiting to happen** — load average 95, 473M swapouts (A15).

**The mechanism** (§4.13): one bus, one envelope, three channel kinds; role channels so the address
is a role and the router picks the lane; a **deadline plus a documented default** on every
escalation, so no wait is unbounded and no answer is guessed; explicit acks, dead letters and
expiry, so nothing is silently lost; **per-copy cost** on broadcast with a cap; every exchange
published as live rows, so the founder watches the estate talk to itself.

**The proving measurement.**

| # | Measurement | How | Target | Failure it catches |
|---|---|---|---|---|
| M8 | **publish → ack latency** | publish on a role channel from inside the sphere, measure to the ack | p95 < 200 ms in-sphere; < 2 s across spheres via the relay | "real time" that is really a poll |
| M9 | **escalation round-trip** | force an escalation with a 30 s deadline and a default | p95 round-trip < 30 s; **100 % of timeouts apply the documented default and record it** | a stalled plan waiting on a model that never answered |
| M10 | **broadcast delivery** | broadcast to N live subscribers, count acks | 100 % of live subscribers ack within 1 s; the cost charged per copy | a broadcast that reaches some agents and starves others |
| M11 | **loss under failure** | kill a subscriber mid-broadcast; kill the publisher mid-escalation | the publisher sees the ack gap and the dead letter; the plan's state row shows the default applied | a message that vanishes with no trace |
| M12 | **cost per message** | tokens and dollars per class | an escalation ≤ the packet's `max_usd`; a broadcast ≤ its cap; every spend visible on /fleet | a messaging layer that spends the estate's daily budget on chatter |

M8 is a **baseline this proposal does not have**: the bus pod carries no NATS client CLI (A23), so
the in-sphere latency must be measured from a pod that links the client, and that measurement is a
precondition of phase 1.5. Inventing a number here would be exactly the failure this document
refuses (§7.9, D14).

### 7.11 Agent identity, solved

**The difficulty.** Identity is easy to *claim* and hard to *believe*: an agent that says who it is
is an assertion; an agent whose every request is signed by a key only it can read, whose actions are
chained and anchored outside the cluster, and whose unregistered egress is refused by the kernel, is
evidence. And the estate is half in the cluster and half on a laptop — a laptop agent can never have
kernel attestation, so a design that pretends otherwise produces a ledger full of claims.

**The mechanism** (§4.14): one registry with URNs as primary keys; one signing path per attestation
tier, both writing the same signed rows; the chain anchored outside the cluster and verified on a
cron; the tier recorded on every row so the strength is visible; the delegation plane's `owner`,
`from`, `to` and claim trailers all resolving to URNs; and the founder seeing the URN, the role and
the tier on /fleet, the Face and the Mac console.

**The proving measurement.**

| # | Measurement | How | Target | Failure it catches |
|---|---|---|---|---|
| M13 | **the first signed action** | run one delegated action through the signing path | `agent_actions` goes from **0** (A31) to ≥ 1, and the verify door still passes | an identity story with no identity in it |
| M14 | **tamper detection** | plant the fault the Quad's own chain test uses (altered row, deleted-and-relinked row, truncated chain) | `quad.ledger-verify` exits non-zero on each | a chain that cannot fail is not a chain |
| M15 | **attribution end-to-end** | take a landed change and follow it to the agent | the URN, session id and attestation tier are readable on /fleet, in the ledger row and in the commit's claim trailer | attribution that stops at the git author |
| M16 | **authority enforcement** | give a cheap executor a frontier-only packet | it is refused by `authority_scope`, and the refusal is a ledger row and a live event | tiering that is advisory only |
| M17 | **cross-sphere continuity** | resume a laptop run after a crash | the resumed session carries the same URN and `lineage_parent`, and the ledger shows both sessions | a resumed plan that nobody can attribute |

M13–M14 are the gates for step 2 of the operationalisation table; M15–M17 are the gates for the
delegation layer's phase 3. ADR 0035's measured bypasses (unknown PIDs allowed; IPv6 unchecked)
mean the kernel tier is **not** claimed until they are fixed.

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

### 8.1.1 The discovery plane's cost

Three cost centres, and the honest answer that the plane is *cheaper* than the searches it
replaces only if it is actually used:

| Cost | What it is | Measured by | Order of magnitude, from the measured baselines |
|---|---|---|---|
| **Index build** | one pass per source: git trees + symbol extraction, doc text, event replay, memory embeddings, ledger scan, claims snapshot | minutes of CPU per source, once per change | the code index is the expensive one (56 repos, 9,269 `.py` files at depth ≤4); the others are seconds |
| **Storage** | the six indexes plus the query log | bytes per document | roughly an order of magnitude above the raw text (embeddings + entity links), plus the query log — the only unbounded table, so it needs a retention rule (D16) |
| **Query** | per answer: the tiers tried, the documents read, the embedding, and (at tier 4) one synthesis call | p50/p95 latency and tokens per answer | the plane's own budget is the same policy file the router reads (one policy): a discovery call is capped like any other model call, and the free local floor serves the exact tiers |

The arithmetic that matters: a graph query costs **15.4 s** and returns 636 nodes / 2,469 edges
that the agent must then read; `estate-brief` costs **3.20 s**; a `rg` sweep is fast but returns
text the agent must read before it can cite it. The plane's claim is therefore **not** "one call is
free" — it is that one call replaces two to five reads with one cited answer, and that every
escalation it performs is logged, so its cost is visible instead of hidden in an agent's context.

### 8.1.2 The message plane's cost

Every message that reaches a model is a paid call, so the cost model is about *waking*, not about
bytes:

| Cost centre | What it is | Measured by | Rule |
|---|---|---|---|
| **escalation** | one frontier wake-up per unresolved decision | tokens/dollars per escalation, by class | bounded by the packet's `max_usd`; the plan's budget reserves for it (§4.9) |
| **broadcast** | N wakes for N subscribers | cost per copy × copies | a per-publisher cap and a max fan-out (D17); a broadcast that no one acts on expires |
| **idle standing by** | an agent that waits to be messaged | open sessions × duration | the plan layer wakes an agent **only** on a message; it never polls (this is what replaces the 1,277 hand-rolled polls, A22's context) |
| **transport** | the bus | messages/sec, bytes | free tier: the cluster's own NATS; no new always-on resource (Decision 0034) |

The honest statement for the consultant: **real-time messaging does not reduce token spend; it
replaces polling and human latency with explicit, capped, measurable wake-ups.** The saving is in
*elapsed time* and in *fewer stalls*, and the cost is bounded by construction (per-copy cost, caps,
deadlines, defaults).

### 8.1.3 The Quad's cost

The identity substrate is the cheapest of the three new layers, because it is mostly code that
already exists and a workload that already runs:

| Cost | What it is | Measured by | Order of magnitude |
|---|---|---|---|
| **ledger** | one writer Deployment + two CronJobs every 15 min, already running | `kubectl get deploy -n quad` (1/1, 20d) and the CronJob history | **zero new cost** — it is already deployed; the change is rows, not resources |
| **signing** | one Elpis sidecar per agent pod | sidecar CPU/memory and added latency per request | one process per pod; the request adds one Ed25519 sign (microseconds) |
| **registry** | one table set in the Quad's own database | rows (agents, sessions) | tens of rows today, thousands later; negligible storage |
| **kernel enforcer** | one DaemonSet per node (ADR 0035) | node CPU/memory and the risk of refusing a working agent | **deferred to step 4** precisely because it is the only part that can break running work |
| **door tier** | signing inside the existing executor | one signature + one row per action | no new process — the executor is already the only door |

The honest line for the consultant: **identity is the cheapest layer to operationalise and the most
expensive to get wrong.** Its cost is not money; it is the risk of a ledger that says more than it
proves, which is why §7.11's gate M14 (a planted fault must turn the verify door red) comes before
any claim that history cannot be quietly edited.

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
| K9 | The proposal is read as "the estate already does this" | possible | the gap is dismissed | §3's seven gaps, each with a citation; the gap is a *unit of work*, not the absence of capability | — |
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
| B2 | a plan with an `edit_diff` sub-task and the cheap tier live in `~/.estate/router-state/lanes.json` | `subtask.run` runs | the packet names a cheap alias; the executor runs it on the cheap lane; the estate runs the acceptance; the model is never asked whether it passed |
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
| B13 | a question whose answer spans code, a decision and a live event | `discover.query` runs | one answer object returns claims from all three, each with source, locator, `as_of` and epistemic state, plus the list of tiers tried |
| B14 | a question about something the estate never recorded | `discover.query` runs | the answer is "the estate does not know this", with the searched sources listed and no claim returned (exit code 3) |
| B15 | a fact the epistemic layer has marked `corrected` | the same question is asked again | the claim is labelled `stale`, the tombstone is shown, and no un-retracted variant of that fact is served |
| B16 | a source that cannot be read | `discover.index.status` runs | the source is reported `unreadable` with its last watermark and last error — never as empty — and answers depending on it are `partial` (exit code 4) |
| B17 | an agent about to write a path with no live claim | the pre-flight discovery call runs | it answers "may I write here?" **before** the attempt, and the enforcement ledger records the discovery id that answered it |
| B18 | the founder asks a question in a terminal, from any harness | `bin/estate-discover "<question>"` runs | the answer is identical to the MCP tool's answer for the same question (one implementation), exit codes 0/3/4/5, and `--explain` prints the tiers tried and each source's freshness |
| B19 | a goal with no discovery id in its evidence | `complete_goal` runs | it refuses — the same refusal shape as a goal with no `add_bdd` |
| B20 | a cheap executor blocked on a semantic decision it may not make | it escalates to the plan's role channel | the frontier reasoner receives it with the packet id and citations, replies within the deadline, and the executor applies the answer |
| B21 | no reply by the deadline | the deadline passes | the executor takes the **documented default** (`refuse_and_hand_back`), records that it did, and the plan's state row shows the timeout — it never guesses and never waits unbounded |
| B22 | an estate-wide broadcast with a token cap | it is published | every live subscriber receives and acks it within 1 s, the cost is charged **per copy**, and the spend appears on /fleet |
| B23 | the founder speaks to the Face while a plan is running | the note is issued | the note lands in the plan's channel as a `founder_note`, appears in the plan's row on /fleet, and steers the plan's next decision point |
| B24 | the registry has no row for the agent that is about to act | the agent tries to open a session | it is refused with a named reason ("unregistered URN"); no session, no action, no row |
| B25 | an agent signs an action and the chain is later tampered with | `quad.ledger-verify` runs | it exits non-zero and the fault is named — the ledger is not decorative |
| B26 | a cheap executor is handed a packet its authority does not cover | it tries to act | the registry's `authority_scope` refuses it, and the refusal is a ledger row and a live row on /fleet |
| B27 | the founder asks "who did that" from the Mac console | the console is asked | it answers with the URN, the role, the attestation tier and the session id — the same facts /fleet and the Face show |

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
| D11 | Where the discovery plane runs | laptop only / cluster only / split (ingest beside the bus, query by the agents) | **split** — the ingest must sit beside the bus (the only way to see events in real time: the laptop cannot reach NATS today, A23); the query path runs where the agents are; one relay between them | founder + consultant |
| D12 | May the plane answer *from* a model | never (index only) / model synthesis over retrieved spans / free-form model answer | **model synthesis only at tier 4, over retrieved spans, always cited** — the model phrases retrieved facts and is never the source of one | consultant |
| D13 | What happens when two sources disagree | pick the newest / pick the most authoritative / surface both | **surface both**, ranked by epistemic state then `as_of` — an estate answer must be auditable, not silently chosen | consultant |
| D14 | Which measurements must exist before anyone says "accurate" | none / M1–M7 | **M1–M7 first** (§7.9) — the estate has no such numbers today, and a proposal that invents them is exactly what this document refuses to report | founder + consultant |
| D15 | The plane's own budget | uncapped / capped by the router policy / a fixed per-call ceiling | **capped by the same policy file the router reads**; when the cap is hit, the plane returns the best partial answer and states what it did not do | founder |
| D16 | The query log's retention | forever / 30 days / sampled | **30 days**, with the answer ids and citations kept in the estate's evidence store — the log is the only unbounded table | founder |
| D17 | Broadcast scope and cap | estate-wide by default / plan-scoped by default / founder-requested only | **plan-scoped by default**; an estate-wide broadcast requires an explicit intent with a per-publisher token cap and a max fan-out (D17) — an estate-wide wake of N agents is N times the cost and is the 2026-10-21 saturation waiting to happen (A15) | founder + consultant |
| D18 | The founder's power in a channel | observe / observe + steer / observe + steer + instruct | **observe + steer**; an instruction that changes scope becomes an **issue comment** — the estate's existing authority model — so it is recorded, cited and auditable | founder |
| D19 | Which attestation tier the laptop agents get | kernel only (no laptop agents) / door-attested (signed at the executor) / claim-only | **door-attested**: the executor signs every laptop action into the same ledger, and the tier is recorded honestly; the laptop is where the founder's own agents run | founder + consultant |
| D20 | Whether identity gates the delegation layer from day one | identity optional / identity required for in-cluster delegation only / identity required everywhere | **required for in-cluster delegation** (it is already there), **advisory for the laptop** until the door-attested tier lands (step 3) — a hard gate the estate cannot yet meet would stall the work | founder + consultant |
| D21 | Where the registry lives | in `estate.db` / in the Quad's own database | **the Quad's own database** (`quad_ledger`, measured A31): one registry, one chain, one place; no second copy of identity in `estate.db` | founder |
| D22 | Whether the kernel enforcer gates the launch | yes / no, ADR 0035 first | **no**: 0035 measured two bypasses and is still PROPOSED; the kernel tier is step 4, after the ledger proves itself with real rows | founder |

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
| A16 | The size of the estate's source tree | `ls -d ~/Documents/code/*/ \| wc -l` | **56** repositories |
| A17 | The volume of code to index | `find ~/Documents/code -maxdepth 4 -name "*.py" -not -path "*/node_modules/*" \| wc -l` | **9,269** Python files at depth ≤ 4 |
| A18 | The knowledge graph's size | growmos entity/relation counts over `~/Documents/code/estate-graph` | **10,772** entities, **14,154** relations |
| A19 | What a graph query costs | `growmos --root ~/Documents/code/estate-graph query "discovery plane"` | **15.4 s**, returning 636 nodes / 2,469 edges — a summary, not a lookup |
| A20 | What the brief costs | `/usr/bin/time -p bin/estate-brief --task "discovery plane design"` | **real 3.20 s** (user 0.31 s, sys 0.24 s) |
| A21 | What the action ledger holds | `sqlite3 ~/.estate/estate.db` counts | `step_runs` **3,828**, `intent_tickets` **2,648**, `policy_decisions` **790** |
| A22 | What the enforcement ledger holds | a python pass over `~/.estate/memory/enforce-ledger.jsonl` | **717** rows — **524** pass, **169** refuse, **24** unknown; top reasons: 336 "pass — covered by a live claim", 186 "pass — wrote back", 21 "refuse — No plan declared, so Bash is refused", 30+ "refuse — no live claim covers …", 12 "unknown — claim ledger unreadable", 12 "unknown — transcript unreadable" |
| A23 | Whether the laptop can see the event spine | `kubectl exec -n event-bus nats-0 -- nats stream ls`; `nc nats.event-bus.svc 4222` | the bus pod has **no `nats` CLI** ("executable file not found in $PATH"), and the laptop **cannot reach** the cluster's NATS service by cluster DNS — the spine is cluster-only today |
| A24 | The bus's hard contracts | `ls platform/event-bus/contract/` | **3** schemas: `estate.agent.event.json`, `estate.commerce.order_paid.json`, `estate.news.story.json` |
| A25 | The live memory service | `ps ax \| rg estate-memory-mcp`; `ls ~/.estate/memory` | **3** live `estate-memory-mcp` processes (`~/.estate/memory/bin/estate-memory-mcp`); `~/.estate/memory/` holds `bin/`, `enforce-ledger.jsonl` (207 KB, live), `focus-register.json` (12,975 bytes, rewritten 21:49), `claims-noted.json`, `platform/` |
| A26 | The console-door precedent | `bin/estate-brief`, `bin/estate-checkpoint`, `bin/claim-open` | the zero-config CLI pattern §6.10 follows (no MCP required, key read by name) |
| A27 | The `lane-where` door in this checkout | `bin/lane-where` | "No such file or directory" here — the door landed on `main` under claim #7003 while this worktree sits behind it; the console design does not depend on it |
| A28 | The event bus's in-sphere latency | publish → ack from inside the cluster | **not measured this session** — the bus pod has no NATS client CLI (A23) and the laptop cannot reach the service, so the baseline must be taken from a pod that links the client; it is a precondition of phase 1.5 and is marked **[unverified]** rather than estimated |
| A29 | The Quad ledger, live | `kubectl get deploy -n quad` | `quad-ledger` **1/1 Ready**, 20d; pod age 19h; `anchor` and `verify` CronJobs every 15 min, last runs 13m and 7m ago, both `Completed` |
| A30 | The Quad ledger's content | intent `quad.ledger-verify` (exit 0) | `quad-ledger: 0 rows verified, head 000000000000 matches anchor` — **the chain verifies and it is empty** |
| A31 | The Quad's tables, live | `kubectl exec -n estate-db estate-1 -- psql -d quad_ledger` | database `quad_ledger` exists in estate-db and holds exactly `agent_actions` and `merkle_anchors`; `agent_actions` = **0**, `merkle_anchors` = **0** |
| A32 | The identity registry, live | `psql -d estate -c "select … from sessions"` | `ERROR: relation "sessions" does not exist` — and no `agents` table in any database: the registry DDL was never applied |
| A33 | The Quad's other layers, live | pod list across all namespaces | no `elpis-proxy`, no `identity-bootstrapper`, no `dros-daemon` pod anywhere; SPIRE **is** running (`spire-server-0`, two `spire-agent`s, two CSI drivers, 27d/45d); ADR 0035 (kernel enforcer as a node DaemonSet) is still **PROPOSED** |

### B. Citations (every load-bearing claim in this document points at one)

* Routing and lanes: `platform/llm/front.py`, `platform/llm/cost-ladder.yaml`, `platform/llm/routing-matrix.yaml`, `platform/llm/availability.yaml`, `platform/llm/zeroedge.yaml`, `platform/llm/zeroedge_gateway.py`, `~/.estate/router-state/lanes.json`, `~/.estate/router-state/active`
* Policy: `AGENTS.md` §11 (the single toml block), `sovereign/policy.py`, `sovereign/config.py`, `sovereign/tests/bdd/test_policy.py`
* Claims and landing: `bin/claim-open`, `bin/claim-gate`, `backstage/plugins/fleetview-backend/src/fleetview_backend/claims.py`, `greenlane/engine.py`, `.github/workflows/greenlane.yml`, `docs/runbooks/greenlane.md`
* Verification: `sovereign/verifier.py`, `sovereign/engine/`, `bin/idp-ci`, `sovereign/tests/bdd/`
* Execution and isolation: `platform/executor/sandbox.py`, `factory/sandbox.py`, `platform/sandbox/vcluster/`
* Harnesses and portability: `docs/specs/2026-10-23-harness-inventory-and-how-a-harness-is-swapped.md` (on `main`), `platform/estate/memory/runtimes.json`, `docs/synthesis/factory-inventory.md`
* Voice and visibility: the Face audit spec (2026-10-23), `platform/llm/availability.yaml`, the Fleet board (`backstage/plugins/fleetview-*`), `bin/estate-brief`
* Prior art for the desired behaviour: `docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md` (Status: PROPOSED — the same proposal genre, and the source of the "like electricity" language in its §10), `docs/specs/2026-10-22-*.md` (the idp-mode/voice/workforce series), `docs/diagnoses/*.yaml` (the hypothesis-race genre used for the gap analysis)
* The data sources reviewed in §2.10: `~/.estate/memory/enforce-ledger.jsonl` (717 rows), `~/.estate/memory/focus-register.json`, `~/.estate/estate.db` (`step_runs`, `intent_tickets`, `policy_decisions`), `platform/event-bus/contract/` (3 schemas), `platform/estate/memory/door.py` (the https door the bridge forwards to), `platform/estate/memory/runtimes.json`, `~/Documents/code/estate-graph` (growmos: 10,772 entities), `bin/estate-brief`, `bin/estate-memory-install`, `backstage/plugins/fleetview-backend/src/fleetview_backend/claims.py`, `docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`
* In flight, not relied on: `docs/decisions/0037-the-film-is-a-deterministic-twin-of-the-event-spine.md` (read on disk under claim #7000; **not merged**, so nothing in this proposal depends on it)
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
