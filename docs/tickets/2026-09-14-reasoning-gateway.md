# The Reasoning Gateway — a "PhD cold military surgeon" control plane

**Status:** open
**Opened:** 2026-09-14
**Laws:** LAW 2 (proof before action), LAW 9 (stay on the job), THE EMPIRICAL PROOF RULE, R38 (a guard that refuses correct work is an outage), R42 (the most capable agent works only multipliers)
**Source:** founder essay, 2026-09-14 (excerpt below; full text archived with this ticket)
**Spec:** TBD — written once a design is chosen
**Module:** `platform/reasoning/` (new subtree; no second bus, no second server)
**Binding:** `sovereign/tests/bdd/test_reasoning_gateway.py` (new), `rules.yaml` (new rows)

## The founder's words, verbatim (2026-09-14)

> "ok o achieve that 'PhD cold military surgeon' level of rigorous problem-solving—without
> falling into the trap of endless 'overthinking'—you must shift away from standard prompt
> engineering and implement three architectural patterns across your estate: Process Reward
> Models (PRMs), Test-Time Compute Budgeting, and Epistemic Guardrails."

> "No 'Blind' Assumptions: If the agent says 'I assume the database is up,' the control
> plane blocks the reasoning step until the agent explicitly runs a check_db_connection tool."

> "You buy or use open source for the underlying graph logic and math engines. You build
> the strict Process Reward Model and the gating mechanisms that force the agents to
> verify their assumptions at every single step."

## The failure this removes

Standard agents are generation-only: they produce an answer and grade the final outcome.
Reasoning without instrumentation has three named failures that turn the estate from
"answering" into "guessing", and each is measured on main today:

1. **No step-level supervision.** A wrong turn halfway through reasoning stays wrong; only
   the final answer is graded. Hallucination spirals before any signal fires. The
   `bin/idp-epistemic` rule stops a finished transcript — it cannot stop a wrong step
   while it is happening.
2. **No compute budget.** Reasoning is unbounded. Analysis-paralysis loops eat tokens
   and time, and there is no signal "good enough" has arrived. `bin/idp-trajectory` and
   the 60-second execution boundary catch two failure modes; information-gain stops are
   absent.
3. **No epistemic grounding at the action.** The agent asserts, the system believes.
   Pre-conditions and post-conditions are absent, so an agent can declare success on
   state it never measured.

## The fix, in one sentence

**A Reasoning Gateway that supervises every step (PRM), budgets every branch (compute +
information gain), and gates every action (pre-/post-condition contracts), so a wrong
step is caught at the step, an exhausted budget ends the loop, and an unverifiable action
is refused.**

## What already exists, so we do not build twice

The estate already has three quarters of this — measured, not asserted, and named here so
no session duplicates it:

- **Epistemic Gate** (`rules.yaml` row "epistemic", grader `bin/idp-epistemic`): "three
  independent pieces of evidence, at least one from state the agent did not author."
  This is half of the Epistemic Guardrails pattern, anchored at the final transcript.
- **Trajectory Gate** (`bin/idp-trajectory`): "an agent's action is refused when it
  serves no goal the agent itself declared." Half of the Compute Budgeting pattern,
  anchored at goal-relevance.
- **Execution Boundary** (`bin/idp-execution-boundary`, merged 2026-09-13): the 60-second
  ceiling is applied by a daemon outside the agent's process tree. A hardware-level
  budget that already covers the worst overthinking.
- **Deterministic Verifier** (`sovereign/verifier.py`, 745 lines, merged 2026-09-14):
  `propose_patch` → `verify` → `seal` → `admit`. The PATTERN of "no action without
  verification" — but inside the patch lane only.
- **BDD Proof Gate** (`bin/idp-bdd-proof-gate`): a PR body without a BDD proof block is
  refused. A second epistemic fence, anchored at merge time.
- **Circuit Breaker** (`bin/idp-circuit-breaker`): the same finding on three targets
  locks. A budget analogue at the fleet level, not the reasoning level.
- **No-second-bus, no-second-server rule (THE HEADLINE).** Every new layer lands on the
  Sovereign Bus and the executor daemon. Second stores are the stitching THE HEADLINE
  forbids; that rule binds this ticket.

## The three deliverables

### D1 — Process Reward Model sidecar (`platform/reasoning/prm.py`)

A deterministic grader (NOT another frontier LLM — that would reproduce the failure
mode) that scores every reasoning step on three vectors:

- **Factual correctness** — does the step reference state the agent actually read?
- **Relevance** — does the step serve the declared goal?
- **Efficiency** — does the step buy information gain > the cost of computing it?

Below threshold (default 0.8 per vector), the branch is killed and the agent is forced
to backtrack. The PRM grades BYTES (a transcript, a log, a tool return), never the
agent's own claim about them.

### D2 — Test-Time Compute Budget (`platform/reasoning/budget.py`)

A governor sitting on the agent loop with three controls:

- **Per-query budget** (default $0.50 / 5 tree branches, configurable per severity tier —
  a Tier-1 outage gets the deepest budget; a noisy CPU spike gets shallow triage).
- **Expected Information Gain threshold** — a branch must mathematically prove it will
  reduce uncertainty above the threshold before opening.
- **Budget exhaustion → forced termination** — the agent stops thinking and executes
  the best-so-far plan when the budget runs out.

The existing trajectory gate and execution boundary cover two of the three; this ticket
unifies them with an information-theoretic floor.

### D3 — Design-by-Contract executor (`platform/reasoning/contract.py`)

A layer in front of `Handler.handle` requiring every tool call to declare:

- **Pre-condition** — the state the agent expects to find (e.g., "pod uptime > 0s").
- **Post-condition** — the state change the agent expects to occur (e.g.,
  "readiness probe passes within 30s").

A deterministic script (NOT the agent) checks the post-condition against the live
system. If it fails, the PRM penalises the trajectory and the agent is forced to
adapt before continuing.

## The stack — what to buy vs build

| Layer | Choice | Rationale |
|---|---|---|
| Orchestrator | **Temporal.io or Ray** | off-the-shelf execution state + retries/timeouts; buy not build |
| Reasoning engine (MCTS) | **ReST-MCTS\*** or custom LangGraph nodes | open source; use as-is, do not reimplement |
| PRM checkpoint | **small open-source 8B fine-tuned on internal runbooks** | deterministic, fast, fine-grained — NOT a frontier LLM |
| Execution sandbox | **shadow environment or K8s dry-runs** | already partly wired via the Deterministic Verifier's sterile tree |
| Communication | **Sovereign Bus + existing executor daemon** | no second bus, no second server |

## Definition of Done — in commands

1. **PRM sidecar grades a transcript and rejects a hallucinated step before it propagates.**
   `bin/idp-prm --grade <transcript>` names the bad step, the failing vector, and the
   evidence it graded (a tool return, not the agent's claim).
2. **Budget exhaustion terminates the loop.**
   `bin/idp-budget --max-steps 5 --run <agent-loop>` exits at step 5 with the
   best-so-far plan, and `bin/idp-budget --explain <run>` names the exhaustion cause.
3. **Post-condition failure is caught by an external script.**
   `bin/idp-contract --pre "pod uptime > 0s" --post "readiness probe passes within 30s"
   --tool restart_pod` refuses the next step when the probe still fails.
4. **The existing rules.yaml rows (`epistemic`, `trajectory`, `execution-boundary`,
   `bdd-proof`, `circuit-breaker`) are still wired and pass.** The new layers add to
   them, not replace them — proved by `bin/idp-rules run` returning green for all of
   them after the new layers land.
5. **`bin/idp-rules run` and `bin/idp-ci` are green on the branch.**
6. **One end-to-end scenario from the founder's essay passes in practice.** Pick the
   "I assume the database is up" case: an agent that hand-waves the database state is
   blocked by the contract layer until `check_db_connection` is run; the PRM scores
   that check; the budget honours the cycle cost. Measured on a recorded run, not
   asserted in a transcript.

## What "operational" means here, so it cannot be softened later

The Reasoning Gateway is operational when an agent that needs N reasoning steps to
solve a problem **never spends more than its declared budget**, **never has a step
below threshold propagate**, and **never claims success on an unverified action** —
measured on a recorded run, not asserted in a transcript. Until then, the layers are
built, and that is what this ticket says they are.

## Risks to record now, while the architect is sober

- **PRM as a frontier LLM is the failure mode, not the fix.** The whole point is
  determinism; using another generative model as the judge reproduces the
  hallucination at a second layer.
- **Information-gain math needs an actual Bayesian engine.** Without one, the
  threshold degrades to "looks plausible" — which is the trap the founder named.
- **Three independent layers need one mental model.** If the PRM, the budget, and
  the contract disagree about whether to continue, there is no answer; that is
  itself a contract bug and must be designed-in, not designed-out.
- **No new bus, no new server, no second store.** All three layers land on the
  Sovereign Bus and the estate's existing executor daemon; a second Langfuse or a
  second scheduler is the stitching THE HEADLINE forbids.
- **Latency budget.** A PRM call per step is cheap; a Bayesian-engine call per step
  may not be. The 60-second ceiling already covers the worst case; a finer inner
  budget (per-step) is the open question, and must not exceed the existing ceiling.

## A note on file naming, so the next session is not confused

The estate already has `bin/idp-trajectory`, `bin/idp-epistemic`, `bin/idp-execution-boundary`,
`bin/idp-bdd-proof-gate`, `bin/idp-circuit-breaker`. New binaries must NOT reuse those
names. Suggested names: `bin/idp-prm`, `bin/idp-budget`, `bin/idp-contract`. Spec at
`docs/specs/2026-09-14-reasoning-gateway.md`, BDD at
`features/gates/reasoning-gateway.feature`, tests at
`sovereign/tests/bdd/test_reasoning_gateway.py`.
