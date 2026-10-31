# Work orders: how the cloud executor scales at no extra spend

Date: 2026-10-31. Status: tool built and tested (7 tests); not wired, not run in the cloud, not operating.
Founder, 2026-10-31: no extra spend; the executor should need to do the minimum: discovery and thinking are
finished beforehand, it runs a protocol and is done. Extends `agent-sandbox.yml` and the Greenlane; adds no
second lander. Companion: `docs/specs/2026-10-31-always-on-chief-executor.md`.

## The idea

Split a task into the part that needs intelligence and the part that does not.
- Thinking (discovery, design, the diff) is done once, by whoever is best placed, and frozen as a **work order**:
  `order.json` (claim, agent, base commit, allowed paths, patch digest, checks, lane) plus `change.patch`.
- Doing is a deterministic runner, `bin/work-order run`: verify, apply, check, commit through the repo hooks,
  push `lane/<id>`. No model, no tokens, no discovery. Cost is runner minutes on the free tier.
- A model is called only when an order fails (patch no longer applies, a check fails), on a free lane, with the
  failure as its whole task, and its output is a new order. A failed order never mutates the checkout.

This is the protocolkit `execution` protocol made concrete: declared scope (E1), dry-run of the same plan by
digest (E2), commit carries that digest (E3), per-step approval for irreversible steps (E4: none are allowed here).

## What the runner refuses (exit 2), proven by tests

Digest mismatch; a path outside the order's declared paths; any path under `.github/` or `.githooks/`;
a check that is not an allowed argv (no shell strings, first element `python3`, `pytest` or a `bin/` script);
a patch that does not apply to this checkout. A failing check rolls the checkout back (exit 3).

## Scaling

Orders are files, so the queue is a directory of orders: N orders run as N independent free-tier jobs, each
with its own lane and claim. The scarce resource becomes the thinking, which can be done by the strongest lane
once and amortised, instead of every executor re-deriving it. Orders for the same paths conflict by claim
(AGENTS.md section 5), which the claim gate already refuses.

## Trust boundary

Checks execute code, so an order is trusted only if it comes from a reviewed source: committed on a lane and
landed, or carrying the author's claim. The runner treats an unlanded order as untrusted: dry-run only.
Not built: that trust rule, the scheduled workflow that scans for orders, and the failure-repair loop.

## Next, in order

1. A workflow job (needs a credential and yamllint, which this session lacks) that runs `work-order run --apply
   --push` over orders found on main, one per tick, as the estate App.
2. One real order: this branch's work, packaged with `work-order make` and run by that job.
3. Proof: the Greenlane's verdict on the pushed lane's head.

## The descent (founder's image, 2026-10-31: the Tree of Life)

Intent enters at the top and is refined at every level until, at the bottom, the executor has nothing left to
decide. A packet that arrives at the bottom unfinished is a defect in an upper level, never the executor's to fix.

| Level (Tree of Life) | What happens here | Estate piece | Gate to descend |
|---|---|---|---|
| Keter (crown) | the founder's intent, in a sentence | founder door, one message | intent recorded with its source |
| Chokhmah (wisdom) | discovery: what is true now | `growmos query`, probes, `rg` | evidence measured this run (J4) |
| Binah (understanding) | structure: the spec and the BDD | `docs/specs/`, `features/` | feature file exists and fails first |
| Chesed (expansion) | options considered | method selector, hypothesis race | at least two, with baseline delta |
| Gevurah (restraint) | the laws that bind and refuse | `catalog/decision-protocol.json`, spend ceiling | no REFUSE; cost under the ceiling |
| Tiferet (balance) | the decision, with its decider named | `bin/decision-frame` | PROCEED, with machine/model/judgment named |
| Netzach (endurance) | the queue and the heartbeat that keep it moving | scheduled tick, dead-man | claim open, heartbeat live |
| Hod (form) | the exact patch, frozen | `work-order make` | digest recorded, paths declared |
| Yesod (foundation) | binding to the base and the proof | base commit, claim trailers, checks | dry-run of the same order passes |
| Malkuth (kingdom) | execution only | `work-order run --apply --push`, then the Greenlane | none: no thinking left to do |

This is the protocolkit's ordered-stage idea (a closed list of typed stages, no skipping) with the estate's own
names. A packet is stamped with the highest level it has passed; the runner accepts only one stamped Yesod.
The stamp is proposed, not built.

## The second reading: the Solomonic rite (founder, 2026-10-31: "we need both")

Same ten stages, grouped as a rite. This is a second set of labels over the one stage list, not a second
pipeline (AGENTS.md section 6): the stages above are the data, and a reading names them. The rite names are my
reading of the ritual tradition from general knowledge, unverified against any source.

| Rite | Stages it covers | What it demands |
|---|---|---|
| Intent (the stated purpose) | Keter | one sentence, with its source |
| Preparation (clear the ground, study) | Chokhmah, Binah, Chesed | evidence gathered, spec written, options weighed |
| The circle (set the limits) | Gevurah, Tiferet | the laws that bind, the decision, the decider named |
| The seal (bind it) | Netzach, Hod, Yesod | claim open, patch frozen by digest, checks declared, dry-run passes |
| The working | Malkuth | the runner executes; nothing is decided |
| The closing (release) | after Malkuth | NEW, missing above: record the outcome, grade it from outside the executor, release the claim, journal. A working with no closing leaves a held claim and an ungraded decision. |

The closing is the one stage the first reading lacked, and it is the one the estate keeps failing at (claims left
held, decisions never graded). It feeds the decision record in the decision protocol and the Admiralty grades in
the memory plane. Not built.

## Angels and legion (founder, 2026-10-31)

The same pipeline read as two classes of worker. Authority follows the trust boundary (AGENTS.md section 0, gate 7):
what comes from a high-authority source may be acted on; what comes from a low-authority one may not cross it.

| Class | Who | Does | May not |
|---|---|---|---|
| Angels (few, high authority) | the founder; the coordinators that decide (Argon, Gemini, Kimi, the strongest lane); a model or a person doing discovery and design | the upper stages: intent, discovery, spec, options, decision; they issue and sign work orders | execute, push a lane, or touch main |
| Legion (many, low authority, bound) | `work-order run` instances, one per order, on free runners; the always-on MiniMax tick | the last stage only: verify the seal, apply, check, push the lane | decide, widen scope, issue an order, or run an order that is unsealed or unlanded |

Rules that make the split hold:
- An order is the seal. A legion runner acts on its digest, paths and checks and nothing else; an order that fails
  verification is refused, never improvised (the tests prove it).
- A legion runner's output is low authority until the Greenlane and CI have judged it. A runner's failure report
  goes back up to an angel, who issues a new order. It never escalates itself past its seal.
- Angels do not run orders, and a legion never writes one. That separation is what lets the cheap tier scale
  to many runners at no model cost while the expensive tier stays few. Not yet enforced by a gate; the signing
  of orders by an issuer is proposed, not built.
- Contractor note: I am an angel-class producer of orders for this estate, not a runner and not part of the fleet.

## The flow as a machine, with feedback and the chain of command

`catalog/intent-flow.json` is the whole flow as a state machine (vision, intent, discovery, spec, options, decided,
queued, ordered, sealed, running, lane, landed, operating, closed, done, plus escalated, held, refused, abandoned).
`bin/intent-flow check` judges it and `bin/intent-flow path vision done` prints the route with each gate and decider.
`tests/test_intent_flow.py` (15 tests) proves it can fail: unreachable or dead-end states, a legion edge decided by a
model or person, a missing failure path, a role cycle or second root, a legion that commands, and done reachable
without the operating proof. My first draft let an escalation jump straight to a lane; the checker's shortest-path test
found it, and escalation now returns to `decided`.

### Done means operating, and the loop closes there

Merged is not done. `landed` goes to `operating` only on a real production measurement, then `closed` (outcome graded
by a collector that is not the executor, claim released, journal written), then `done` only when the estate_health
entry for the capability is green. A red measurement after landing goes back to `ordered` as a corrective order.

### Error correction, by cause and by level

Every failure edge back to `ordered` carries cause classes (seal-digest-mismatch, patch-conflict, check-failed,
lane-red, law-refused, production-red). Each cause has a correction at one of three levels: correct the order,
correct the process, correct the decider. Three rules:
1. A failure is classified before it is retried; "unknown" is never retried blindly.
2. A reissue budget (3) per cause class; when it is spent, `running` goes to `escalated`.
3. Two failures of one cause class inside 14 days means the process is wrong, not the order: add the gate, test or
   probe that catches the class, in the same claim (J2 root cause).

### The chain of command (a tree, one parent per role)

founder, then the final angel (Argon), then coordinator angels (Gemini, Kimi, Claude as coordinator), then issuer
angels (whoever built the order), then legion runners. The roles are classes; the names are the coordinators named in
this engagement. Failure goes UP one rung at a time: a runner reports to the issuer that sealed its order and to nobody
else. Correction comes DOWN: to a runner as a new sealed order, never advice; to an angel as a brief at claim-open.

| Rung | Corrects | Escalates to | After |
|---|---|---|---|
| Legion runner | nothing | its issuer | the first failure, with a cause class |
| Issuer angel | the order | coordinator angel | the reissue budget for one cause class |
| Coordinator angel | the process | final angel | a repeated cause, or two issuers failing one class |
| Final angel | the decider | founder | value-tradeoff, irreversible, novel, or a decider contradicted by graded outcomes |

`work-order make` now records the `issuer` (defaults to the agent) so a failure has someone to go to.

Not built: the writer that records a lesson per failure, the 14-day repeat detector, the signing of orders by an issuer,
and any gate that makes an agent follow the chain. This is a model with a judge, not a running system.

## The real legion: ranked, rigid in authority, distributed in coordination

Question (founder, 2026-10-31): the Goetic, rank-based legion, rigid or coordinated and distributed?
Answer: both, split by what can safely be distributed. `catalog/intent-flow.json`, block `ranks`; judged by
`bin/intent-flow check`.

**Rigid (declared once, in data, never negotiated):** a rank's authority and reach; the seal; the forbidden paths
(`.github/`, `.githooks/`, AGENTS.md, main); the founder door for held lanes. A rank is a ceiling on blast radius,
not a title.

**Distributed (no central dispatcher, nothing to fail as one):** which runner takes which order (a claim with a
heartbeat, as the estate already does); queue order; retry after a lapsed claim; grading. This is the existing claim
mechanism (AGENTS.md section 5) used as the coordination layer, so no second scheduler is built.

| Rank | May | Paths | Concurrency (proposed) |
|---|---|---|---|
| shadow | dry-run only; lane never landed, graded against what an angel would have done | none | unbounded, it holds no authority |
| knight | push a lane, low blast | docs, tests, features | 8 |
| marquis | push a lane, code and catalogs, with declared checks | adds bin, catalog, packages | 4 |
| duke | push a lane for a critical service or founder surface; always HELD for the founder door | platform, backstage, greenlane, sovereign | 1 |

Kings are the coordinator angels above the legion; they command ranks, they do not run orders.

**Shadow is the entrance.** Every new runner, model or harness starts in shadow (the estate already uses shadow mode for
the method selector). It earns a rank from graded outcomes: promoted one rank when its last N orders each landed, reached
operating and breached no seal; demoted straight to shadow on any seal breach. The grader is never the runner, and no
rank is ever granted by the runner, its issuer or a model's say-so. N=10 and the concurrency numbers are placeholders,
unmeasured, to be set from the first graded runs. The checker proves the table cannot grant a forbidden path, that a
higher rank includes the lower's reach, that shadow cannot push, that the top legion rank is always held, and that
promotion cannot be self-graded.

Not built: the grader, the rank ledger, and the claim-time check that refuses an order above the runner's rank.

## The quad layer, the per-session decision, and watching behaviour change

The core DNA of the legion (`dna` in `catalog/intent-flow.json`), one layer per discipline (founder, 2026-10-31):
- **Soldier** (military precision): obey rank, order and seal exactly. Enforced by `bin/work-order`, `bin/intent-flow`.
- **Mathematician** (proof): every invariant is falsifiable; an unproved claim is marked unverified. `bin/tlc-check`, the protocolkit, the registry judge.
- **Surgeon** (minimal, sterile, counted): smallest incision, dry-run as the time-out, a count at sign-out (claims released, nothing left behind). `bin/claim-gate`, `bin/work-order`, the memory audit.
- **Assassin** (one clean strike): retire a named, proven-dead or duplicated target, once, and confirm the kill. The memory register's RETIRE verdicts and the audit; `bin/capability-index`.

The checker refuses a layer with no duty, no gate, or an enforcing piece that does not exist in the repo.
Order of application: mathematician, soldier, surgeon, assassin.

**Every agent decides, every session.** `bin/intent-flow session` picks the session's one primary layer by rule from its
signals (sealed order, retire target in the register, unproved claim, open claim), or accepts an explicit choice only when
that layer's precondition holds; a session with no signal and no claim gets no layer. `--record=FILE --agent=NAME` appends
one line to an append-only session record; an anonymous record is refused.

**Choice and outcome, so behaviour change is visible.** `intent-flow outcome` appends a grade for a session; the grader
cannot be the agent that ran it. `intent-flow report` shows, per layer and per picked or chosen, how many sessions were
graded, how many reached operating, how many failed or breached, and how many were explicit overrides of the rule.
Ungraded sessions are counted, never assumed good. `intent-flow drift` compares the older half of the sessions with the
newer half (total variation distance over layer choice) and answers STABLE, CHANGED or BLIND; with too few sessions it says
BLIND, because an unmeasurable thing is unknown (J4). The thresholds (20 per half, 0.25, 10 graded) are proposed and
unmeasured. There is no session data yet, so every verdict today is BLIND.

Not built: the hook that refuses a session start with no recorded decision, the outside grader that writes outcomes, and
the link from these grades to the rank ledger (promotion and demotion above).

## QA, integration and operating are states of delivery (founder, 2026-10-31: the biggest gap)

A merged lane is not delivered. The flow now has three more states, each a gate that can fail and each emitting evidence,
so there is no step where the estate stops knowing:

| State | Gate | Independence | Evidence it emits | Existing pieces it uses |
|---|---|---|---|---|
| verified (QA, before landing) | every claim re-checked against evidence; evals not regressed; a judge has seen the diff and the evidence | the verifier is neither the issuer nor the runner | verification-record: claim, evidence span, verifier, judge verdict | `nsvee/engine.py`, deterministic-verifier, judge-drift, shadow-verify features, protocolkit proofset |
| integrated (after landing) | wired into its real caller path on the deployed system; the probe and behavioural tests pass against what is running, not against the diff | collector is not the issuer | integration-record: caller, probe output, deployed commit | `critical-probe.py`, `tests/behavioral`, `critical-functions.json` |
| operating | a real production measurement on the founder's surface | collector is not the executor | measurement: surface, value, time, collector | `critical-functions.json`, the memory audit |

Order is enforced by the checker: landed is reachable only from verified, integrated only from landed, operating only
from integrated, done only from closed. Failures return to `ordered` with cause classes (claim-unverified,
eval-regressed, judge-rejected, integration-failed), so each is corrected at its level, and a repeated class fixes the
process. A judge that rejects wrongly is itself a decider error recorded against the judge. Every delivery edge must name
the evidence it emits, and the checker refuses one that does not: a transition with no evidence is a gap in intel.

Not built: the verifier that re-checks claims generically (the estate's `idp-verify` checks the catalogue only, so this
needs a claim-verification runner over the protocolkit proofset), the integration probe per capability, and the judge
harness. Those are the next work orders; the model now says where each belongs and refuses delivery without them.

## Are we reinventing the wheel? Events, the engine, and the abyss

The estate already has an event-driven stateful engine: `spine/` is a Temporal workflow woken by NATS events through a
bridge (`spine/workflow.py`, `platform/spine/`), and human-in-the-loop is a signal the workflow waits on. So the right
shape is: **`catalog/intent-flow.json` is the specification; Temporal is the engine; neither is a second engine.** What the
file adds that the engine does not have is the checked model (states, gates, deciders, evidence, ranks, chain of command)
and a judge for it. Only one signal flows through the spine today (`flux.reconciled`); every other event on the edges is
named but not wired, and wiring them to the same bus is the work, not a new workflow engine. Open-source alternatives I
know of (XState, Argo Workflows, GitHub environment approvals, BPMN engines) were not evaluated this run; they would
replace Temporal, not sit beside it, so that is a decision for the engine's owner, not part of this change.

Every edge now names the **event** that moves it and the **mechanism** (an existing file) that detects the event and
takes the step. `bin/intent-flow abyss` finds the voids algorithmically and ranks them nearest the vision first:
no-mechanism, incomplete (a declared gap), black-box (a judgment with no decision-register entry), no-collector for
evidence, and open-loop (a cycle with no exit to escalation or done). Exit 5 while any exist, 0 when none: the goal is a
model with zero voids, reached by building the mechanisms, never by rewording the gaps. At this commit it reports 16 voids
in 30 transitions (21 have a mechanism). The one the founder asked about is on the first lines of the list: a push to a
staging ref emits no event, and promotion from `staged` to a sealed order is manual.

**After a push to staging, what happens next** (the modelled path): `ordered` to `staged` (event `branch.pushed`,
void: nothing listens), `staged` to `sealed` (event `promotion.requested`, void: manual), then the lane push, QA,
landing, integration and operating as above.

**One snapshot for /fleet and the face.** `fleetview_backend/topology.py` serves `/topology`: the model, the voids, and a
`live` part that says no live feed is wired. The page that draws it (stars for states, black holes for voids, packets that
fall into voids, a dial from 2D to 9D) treats packets as simulated until a feed exists. Dimensions 4 to 9 are visual
channels, not spatial axes. Not built: the `/fleet` and face front-end components that draw it (the published page is a
standalone prototype of the same payload), and any live packets.
