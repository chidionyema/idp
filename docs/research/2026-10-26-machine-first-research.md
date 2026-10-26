# Machine-first: what the evidence says about replacing an agent's judgement with a machine or a decision model

**Date:** 2026-10-26 · **Author:** pi (agent runtime) · **Claim:** chidionyema/idp#7222
**Harvest:** `docs/research/2026-10-26-machine-first-harvest.json` (103 records, 12 queries, arXiv API)
**Instrument:** `scripts/harvest-arxiv.py` (stdlib only, re-runnable). `scripts/harvest-arxiv.py --verify
docs/research/2026-10-26-machine-first-harvest.json` fails when a digest cites an id the harvest does not hold.

---

## 0. The question, in the founder's words

> "deep research on current process, way of working, CI, and anything that agents do that can be
> done by machine or decision model like jev, the goal is to drastically reduce agent friction and
> decision making … we also need this to be a first class principle architecturally across estate and
> processes, anything an agent does needs to be justified why it can't be done by jev or machine."

Three claims are being tested, not assumed:

1. **H1 — automation is the cheaper default.** Most of what agents do in this estate is mechanical;
   the evidence says machinery should take it.
2. **H2 — a decision model is a second tier, not a first.** Where a rule can be written down, a model
   is the wrong tool; the evidence says deterministic verification beats probabilistic adjudication.
3. **H3 — what remains is a small, named residue.** Human judgement is irreducible for a few decisions
   only, and the failure mode of pushing too far is automation bias, which is measurable.

Every row below is a record in the harvest file. Every estate number in §3 is a command and its output.

---

## 1. H1 — the external evidence: risk-stratified automation is the working pattern

The strongest result is not "AI reviews code" but **"a machine decides which cases a machine may
decide"**. Meta's RADAR is a multi-stage funnel — classify by authorship and source type, eligibility
gates, static heuristics, a learned Diff Risk Score, LLM review, then deterministic validation — and
the question it answers is explicitly the trade-off between automation yield and safety, tuned by a
risk threshold (2605.30208). That is the estate's principle, already validated at scale: *low-risk
volume is automated; the threshold is data; the risky residue keeps a human.*

The sobering counterweight is 2604.03196: industry reports claim code-review agents can handle 80% of
open-source PRs without human involvement, and the empirical study of 19,450 AIDev PRs (3,109
commented, 98 closed CRA-only) finds the signal-to-noise ratio of agent-only review low enough to
contribute to abandonment. **Automation yield is not automation quality.** A gate that automates the
easy 90% and silently drops the hard 10% produces a green pipeline and a worse estate — which is why
the estate's own rule is proof, not assertion, and why the automation ratio must be published next to
the defect rate.

Industrial studies agree on the mechanism, with measured effect sizes: 2412.18531 (238 practitioners,
10 projects) and 2510.02634 both find LLM-assisted review works when it is embedded in a pipeline with
retrieval and deterministic checks, not when it is a chat box a human consults.

**Estate consequence.** The automation decision is a *risk classification* problem, and the estate
already has the classifier: `bin/idp-ci`'s rungs, `bin/registry-gate`'s invariants, the operating
model's rego rules. Anything already provable by a rung must never be decided by an agent. Anything
not provable must be escalated rather than guessed.

---

## 2. H2 — where the rule is knowable, a model is the wrong tool

This is the part the founder's phrasing gets right for the wrong reason. "Can it be done by jev or
machine" is one question; the evidence says it is two, with a clear order.

**Deterministic verification wins when the property is formalisable.** 2604.01483 (Lean 4) treats
every proposed agentic action as a conjecture permitted iff the kernel proves it satisfies
pre-compiled axioms, and names the incumbent it replaces: probabilistic guardrail classifiers that
are "fundamentally inadequate" for multi-variable regulatory constraints. 2605.29251 makes the same
argument for agent guardrails — probabilistic adjudicators "fail to provide deterministic security
lower bounds" — and adds a proof-constrained execution layer. 2605.10901 concedes that guardrail
classifiers have no formal guarantee and obtains one by verifying in pre-activation space instead of
input space. 2511.09008 (ARc) does the pragmatic version: LLMs *propose* the formalization of a
natural-language policy, humans guide it, and redundant formalizations are checked against it —
i.e. the model writes the rule, the machine proves it, the human owns the policy.

**Formality has a cost the industry is now pricing.** 2606.21339 and 2604.10392 both show
LLM-generated formal specifications failing on syntax or faithfulness, and both answer with the same
architecture: verifier feedback in the loop (KBSpec distils verifier feedback into a knowledge base;
VeriSpecGen attributes each requirement to a targeted test). 2605.14968 (GraphFlow) makes the
compounding argument numerically: ten steps at 90% per-step reliability complete only ~35% of the
time, so a workflow's *specification* must be the artifact that is verified, not its prose.

**Estate consequence.** The order is fixed and it is not "model or machine", it is:

| tier | what decides | when | proof |
|---|---|---|---|
| **machine** | a deterministic program | the property is expressible as a check | the check runs, exit code, receipt |
| **model** | a decision model (JEV, a router, a judge) | the property is statistical and a calibrated model beats a person per unit cost | confidence + held-out agreement rate |
| **judgment** | a person | the property is irreducibly contextual | the reason, recorded, per decision |

The evidence says the middle tier is a *second* tier, not a first: 2407.18370 (Trust or Escalate)
gives the right shape for a judge — assess the judge's confidence and **selectively** decide when to
trust it, with cascaded escalation from cheaper to stronger models — and its guarantee is *human
agreement at a specified level*, not correctness. 2510.09738 measures 54 judges against human
agreement and finds only 27 at Tier 1, split between human-like and *super-consistent* judges, the
latter being a warning sign rather than a win. 2508.06225 names the failure directly: LLM judges are
systematically overconfident, so accuracy-centred evaluation is the wrong metric; confidence
calibration is what makes the judge safe to route on.

**And model consensus is not human agreement.** 2606.03043 is the sharpest result in the harvest:
judges may agree because they capture quality or because they share blind spots, and agreement
statistics cannot tell these apart; on subjective rubrics the judges agree with each other as much
as humans do yet reach only 58–66% of human agreement, while on the rubric with a verifiable answer
the gap closes. 2603.06594 shows the same collapse under distribution shift — judge performance
degrades to near random chance under red-team distribution shift, and attacks succeed by exploiting
judge insufficiency. 2606.07874 shows judges are steerable by in-context information and carry rigid
priors that do not move with the safety definition they are given.

**Estate consequence.** A model verdict is never a terminal verdict; it is a verdict with a confidence,
and below a calibrated floor it escalates (JEV's own `jev.decide` contract already says exactly this:
below the confidence floor the answer comes back `escalated: true` and the caller must not treat it as
a decision). The estate must measure its judges' agreement on a held-out set (R-63 already asks for
this) before routing anything to them.

**Routing is the cost lever.** 2502.00409 surveys routing strategies for exactly this: one
general-purpose model for every query is wasteful when queries differ in required reasoning. 2603.26796
adds the operational constraint that matters for a fleet: per-query routing fails to control
*batch-level* cost under non-uniform batching, so routing must be resource-aware at the batch.

---

## 3. H3 — what is left for humans, and how it fails

The residue is real but small, and the failure mode of over-automating is named and measured.

- **2103.02381** (public-sector decision-making, three experimental studies): humans exhibit
  *automation bias* — over-reliance on algorithmic advice even against warning signals — and
  *selective adherence*, adopting advice only where it matches a stereotype. Automation does not
  remove judgement from the loop; it makes the loop's judgement **worse** when the human rubber-stamps
  a machine's verdict. This is the reason the estate's "judge the judges" rule (R-63) and the
  founder's "go/no-go" ceiling are not merely governance.
- **2608.08601** maps 8,356 risk scenarios over 2,078 job tasks and separates *automation* from
  *augmentation* deployment modes: the same task can be safely automated in one mode and unsafe in the
  other. A capability's decision mode is therefore a property of the *decision*, not of the tool.
- **2411.12924** (HULA, deployed at Atlassian) is the constructive version: humans refine and guide
  the agent at the plan and code stages, and the value comes from the *stage* where they intervene —
  which is precisely a decision-register entry with a stage.
- **2506.06576** introduces the Human Agency Scale: workers' preferred level of human involvement
  differs by task, so "how much judgement" is itself a measured quantity with a distribution, not a
  constant.
- **2609.30863** (embedded software organisation) is the honest organisational result: moving from AI
  as assistant to AI as executor changes the *evidence* a team must produce — quality, traceability,
  verification — not just its headcount.

**Estate consequence.** A human decision in this estate is legitimate only when it names an
irreducibility: a value trade-off, an outward-facing or irreversible act, a novel situation with no
matching precedent, or a low-confidence model escalation. "I was not sure" is not an
irreducibility.

---

## 4. The estate today, measured (2026-10-26)

The founder asked for the current process and way of working. These are measurements, not opinions,
and each names its instrument so it can be re-run.

**The surfaces.** 344 live intents (`ls ~/.estate/intents/*.yaml`), 99 repo-declared intents
(`ls platform/estate/intents/*.yaml`), 444 tools in `bin/`, 76 workflows in `.github/workflows/`.

**The decision traffic.** The executor's own ledger (`~/.estate/estate.db`, table `intent_tickets`)
holds **3,618 intent invocations over 32 days** (2026-09-24 → 2026-10-26) across **570 distinct
intents**. The MCP door log (`~/.estate/logs/mcp.jsonl` + `plan-mcp.jsonl`) holds **1,873 door calls
across 114 sessions** in the same window: `estate_invoke` 754, **`estate_show` 466**, `estate_list` 95.

Two findings fall straight out of those numbers:

1. **One door call in four is an agent asking the door how to use the door** (`estate_show` = 466 of
   1,873 = 24.9%). That is friction with a receipt: the contract is not self-describing at the moment
   of use, so the agent spends a turn re-learning a schema it already has.
2. **The top three recurring actions are state fetches**: `gh-api` (320 executor runs, 344 door calls),
   `ci.status` (208 runs, 182 door calls), `lane-submit` (747 runs, 107 door calls). Agents are
   spending their decisions on *obtaining state that a machine already holds*. The 43,133 job
   directories under `~/.estate/runs` and 188,922 rows in `~/.estate/action-ledger.jsonl` (LLM calls,
   21 distinct models in the last ten days) are the volume of the deciding itself.

**The CI topology.** `bin/idp-ci` is a layered offline gate — rung 1 syntax (`--check`), 1b tests/BDD,
1c schema (every intent's `args` block against the door that runs it), 1d lint/format/types,
1e incident register, 1f `kubeconform`, 1g `flux build dry-run` — then the heavy rungs (kyverno,
conftest, image builds, drills). `bin/registry-gate` adds the registry's invariants on top. The
greenlane (`greenlane/engine.py`, `.github/workflows/greenlane.yml`) proves a lane green, raises the
PR itself and fast-forwards main.

**Where the estate already obeys the principle.** `policy/operating_model.rego` refuses a PR that
creates an identity without a grant, that asks for a GUI step, that raises the secret ceiling without
capacity approval, or that adds a HelmRelease with unbounded history. `bin/claim-gate` refuses a
change with no live claim. `bin/idp-pr-risk-gate` refuses a risky diff. These are machine decisions
about the estate, made by machines, and the founder never sees them — which is the shape the founder
is asking for everywhere else.

**Where it does not.** The `estate_show` quarter of the door traffic, the CI-polling turns, the
"which failure next" judgement that lives only in a model's head, and the decision *not to automate*
are all currently unrecorded, unmeasured and un-refusable.

---

## 5. What the evidence implies for the estate, concretely

1. **Publish the automation ratio, and publish it next to the defect rate.** RADAR's lesson is that
   yield without quality is a trap (2605.30208 vs 2604.03196). The estate's ratio is
   *(machine-decided + model-decided) / (machine-decided + model-decided + judgment)*, per decision,
   weighted by observed runs, with the escalation rate beside it.
2. **Every agent decision gets one of three modes, and the mode is checked against a machine that
   exists.** "A machine could do it" is not a belief; it is a capability id in the registry.
3. **The judgement tier is small and named.** Irreducibility must be stated as one of four kinds
   (value trade-off, irreversible/outward-facing, novel/no precedent, low-confidence model
   escalation). Everything else is machine or model.
4. **Model verdicts are second-order and carry a floor.** Below the calibrated confidence floor the
   answer escalates (2407.18370, 2508.06225) and the judge itself is measured on a held-out set
   (2510.09738, 2606.03043).
5. **Deterministic gates are the target, models are the interim.** The estate should keep moving
   decisions down the ladder: from judgment → model → machine, and only move up when the machine
   provably cannot (formal verification of that impossibility is the strongest form, 2604.01483,
   2605.29251; in practice, a bounded-loop harness proves the *budget*, 2609.27871).
6. **Evaluate the trajectory, not just the outcome.** AgentLens (2607.06624), DynSTEER
   (2609.14637) and ACES (2608.20614) all argue for stage-level evaluation of how the agent worked,
   because a pass/fail bit hides the friction the founder is complaining about.

---

## 6. What would falsify this

The principle is wrong if any of these turn out to be true, and each has an instrument:

| falsifier | instrument |
|---|---|
| Raising the automation ratio raises escaped defects | defect count per merged lane before/after the ratio moves (`~/.estate/logs/`, `estate.db`) |
| Machine decisions are *not* cheaper than the model turn they replaced | cost and wall-clock per decision from the efficiency ledger, per decision id |
| The judgement tier is not small (most decisions claim irreducibility) | the register's own distribution; a register where judgment > 20% of weighted decisions is a finding, not a policy |
| Model verdicts are not calibrated on the estate's own work | held-out agreement rate per judge (R-63), recomputed per release |
| The register is stale — it no longer describes what agents do | the decision register vs. the observed door traffic: any decision id with zero observed runs in 30 days, or any observed intent absent from the register |

---

## 7. Citation index

All ids below are in `docs/research/2026-10-26-machine-first-harvest.json`.

| id | title | used for |
|---|---|---|
| 2103.02381 | Human-AI Interactions in Public Sector Decision-Making: "Automation Bias" and "Selective Adherence" | §3 automation bias |
| 2411.12924 | Human-In-the-Loop Software Development Agents (HULA) | §3 stage-level human intervention |
| 2412.18531 | Automated Code Review In Practice | §1 industrial effect size |
| 2502.00409 | Doing More with Less: routing strategies for LLM systems | §2 cost lever |
| 2506.06576 | Future of Work with AI Agents (Human Agency Scale) | §3 agency distribution |
| 2508.06225 | Overconfidence in LLM-as-a-Judge | §2 calibration |
| 2510.02634 | Automatic Building Code Review: A Case Study | §1 pipeline embedding |
| 2510.09738 | Judge's Verdict: LLM judge capability through human agreement | §2 judge tiers |
| 2511.09008 | A Neurosymbolic Approach to Natural Language Formalization and Verification (ARc) | §2 model proposes, machine proves |
| 2603.06594 | A Coin Flip for Safety: LLM judges fail under adversarial shift | §2 robustness limit |
| 2603.16107 | RepoReviewer: local-first multi-agent repository review | §1 decomposition of review |
| 2603.26796 | Robust batch-level query routing under cost and capacity | §2 fleet routing |
| 2604.01483 | Type-Checked Compliance: deterministic guardrails (Lean 4) | §2 deterministic tier |
| 2604.03196 | From Industry Claims to Empirical Reality: code review agents in PRs | §1 yield ≠ quality |
| 2604.10392 | Intent-aligned formal specification synthesis (VeriSpecGen) | §2 verifier feedback |
| 2605.10901 | Beyond Red-Teaming: formal guarantees of LLM guardrail classifiers | §2 guarantee in pre-activation space |
| 2605.14968 | GraphFlow: formally verifiable visual workflows | §2 compounding error |
| 2605.29251 | Provably Secure Agent Guardrail | §2 deterministic lower bounds |
| 2605.30208 | Automating Low-Risk Code Review at Meta (RADAR) | §1 risk-stratified automation |
| 2606.07874 | Safety is Contextual, LLM-Judges Are Not | §2 judge steerability |
| 2606.21339 | KBSpec: LLM-driven formal specification generation | §2 verifier-in-the-loop |
| 2606.03043 | The Geometry of LLM-as-a-Judge | §2 consensus ≠ human alignment |
| 2607.06624 | AgentLens: production-assessed trajectory reviews | §5 trajectory evaluation |
| 2608.08601 | Unaccountable Delegation, Fading Skills | §3 automation vs augmentation |
| 2608.20614 | Evaluating Skills, Not Just Agents (ACES) | §5 continuous evaluation |
| 2609.14637 | DynSTEER: dynamic stage-wise trajectory evaluation | §5 trajectory evaluation |
| 2609.27871 | Bounded Loops: pre-run spend bounds, proved termination | §2 harness-enforced bounds |
| 2609.30863 | Developing a Roadmap to an AI-first Organization | §3 organisational evidence |
| 2407.18370 | Trust or Escalate: LLM judges with provable guarantees | §2 selective trust, escalation |
