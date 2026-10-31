# Decision protocol: how an agent decides, with the laws and the situation in hand

Date: 2026-10-31. Status: proposed, tool built and tested, not landed, not operating.
Author: external contractor (Claude). Builds on, and does not replace: ADR 0030 (JEV), ADR 0044 (deciders),
the method selector (`packages/method_selector`), the decision register (`policy/agent-decisions.json`),
the protocolkit (`platform/estate/protocolkit/SPEC.md`), and `docs/training/2026-10-30-founder-judgement.md`.

## Why

An agent's work is a stream of decisions: which task next, whether a bug found on the way is its to fix,
whether a blocker is real, whether a reading is an anomaly, which of two goals wins. Today the laws are in
AGENTS.md and the judgement in a training file, and the agent has to remember to apply them. Each repeated
failure in that file is a decision made without the law in view. This protocol puts the situation and the
laws in front of the decision, forces one of four outcomes, and leaves a record that can be graded.

## The loop (situational awareness, Endsley's three levels)

| Level | What the agent does | Where it is enforced |
|---|---|---|
| 1 Perceive | Fill the situation: decision, kind, reversibility, outward-facing, blast radius, novelty, evidence (measured this run?) | `bin/decision-frame`: a missing field is GATHER, never a guess (J4) |
| 2 Comprehend | Match the situation's tags to the laws (`catalog/decision-protocol.json`, `laws`); rank candidates by the registry's priority tiers | the tool returns the matching laws with source and effect |
| 3 Project | Answer the "and then what" questions (the seven gates in AGENTS.md section 0) | the tool returns the seven questions; the record must answer them |

Then exactly one outcome: **PROCEED** (a machine or a calibrated model decides), **GATHER** (take the cheapest
reversible probe inside your scope), **ESCALATE** (a person decides, with a named irreducibility), **REFUSE** (a
law forbids it). The order is machine, then model, then judgment (ADR 0044); "I was not sure" is not an
irreducibility.

## Competing priorities

Lexicographic, highest first, from the catalog's `priority_tiers`: a law that forbids it; irreversible or
outward-facing; a founder-critical function (the registry order in `catalog/critical-functions.json` is the order,
J5); your own claim; estate value; cost. Within a tier the tool breaks ties on value, then cost, then id, and says
so. If the registry does not rank the goals, it is a `value-tradeoff` and goes to the founder door once with both cases.

## Situations the founder named

| Situation | Rule the tool applies |
|---|---|
| Bug found on the way | Outside your claim and not blocking: record a finding and continue (L-only-asked). Blocking: check the owner or widen the claim before touching it (L-claim-first). |
| Blocker | Real only with the intent run, exit status and printed line (L-no-handback). Not irrevocable: try another way. Irrevocable: report once. |
| Anomaly | Probe first; compare to the series' own baseline; measure the goal, not liveness (J3); a series with too little history is BLIND, not normal. |
| Discovery | Probe first, and check the layer does not already exist (L-one-layer) before building on it. |
| Competing goals | Priority tiers above; incommensurable goals escalate. |
| Status or done claim | Needs a measurement this run (L-proof-not-assertion). |

## Which machine-learning and decision approaches, and when

Every row is in `catalog/decision-protocol.json` with its status. "Exists" means the estate has it today;
"proposed" means it does not, and the tool names it only as the method to build when its condition is met.

| Approach | Use when | Do not use when | Status |
|---|---|---|---|
| Ordered rules (lexicographic) | goals have a declared order; a law applies | the order is the open question | exists |
| Value of information (probe first) | evidence is missing and a probe is cheap and reversible | the probe costs more than a wrong reversible guess | proposed as a named method; probes exist |
| Bayesian hypothesis race | several candidate causes, evidence discriminates | one cause already measured | exists (`hypotheses.race`) |
| Method selector with abstention | choosing how to attack a problem | an authorisation is needed | exists (all entries UNVERIFIED) |
| Calibrated model with a confidence floor (JEV, 0.7) | bounded reversible choice, no rule | irreversible, or below the floor | exists |
| Selective prediction or conformal abstention | a model decides repeatedly and outcomes are graded; the floor should be earned | fewer than a few hundred graded outcomes | proposed |
| Independent-model vote, quorum 2/3 | hard-to-undo cross-cutting choice a model may make | voters share evidence and prompt | exists |
| Contextual bandit with exploration budget | the same choice recurs, reward is measured, a bad arm is cheap | one-off, delayed or unmeasured reward, irreversible arm | proposed |
| Robust baseline on health history (median/MAD or control chart) | is this reading abnormal for this series | too little history | proposed |
| Replay and ablation | did a protocol, brief or lane help | no outcome grading exists | proposed |
| Model checking | a protocol must provably never reach a state | the property is empirical | exists (`bin/tlc-check`) |
| Human judgment via the founder door | value-tradeoff, irreversible, novel, low-confidence | a machine or model can decide | exists |

Machine learning is the minority of the table on purpose. Most agent decisions are rules and probes; a learned
component is added only where outcomes are graded, because without grading there is nothing to learn from and
the floor stays a fixed number.

## The decision record (proposed, not built)

Each PROCEED or ESCALATE writes one append-only record: situation, laws matched, decider, method, action, and the
answers to the seven projection questions. Later the outcome is graded by a collector that is not the deciding
agent (an agent writes events, never grades). The record is the training data for the two "proposed" learned rows;
until a few hundred graded outcomes exist, neither is built. The record would go through the same event shape as
the memory plane (Admiralty-style source and content grades); no second store.

## What is built and what is not

Built and tested (17 tests): `catalog/decision-protocol.json` (19 laws, 12 methods), `bin/decision-frame`,
`tests/test_decision_frame.py`. Not built: the record writer, the outcome grader, the claim-open and
lane-submit hook that calls the tool, the Stop-hook check that a decision-bearing turn carries a frame, the
learned methods. Not operating: nothing here has been used by an agent on a real decision, so nothing is
measured. The catalog indexes laws by hand; a test checks that each cited AGENTS.md section exists, not that the
summary matches it.

## Not verified

The Endsley three-level model and the conformal, selective-prediction and bandit approaches are cited from
general knowledge; I searched but did not read the sources this run. The tool does not decide anything the
laws leave open; where it says PROCEED on "a rule decides" it trusts the caller's `rule_decides` flag.
