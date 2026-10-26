# 0044 — Machine-first: an agent action is justified, or it is a machine's job

- **Date:** 2026-10-26
- **Claim:** idp#7222 · agent `pi`
- **Gate:** `bin/registry-gate` (invariant I-6) · **Spec:** `docs/specs/2026-10-26-machine-first-agent-action.md`
- **Research:** `docs/research/2026-10-26-machine-first-research.md` (103-record harvest, 29 cited sources)
- **Proposal page:** the spec's §1, read alone.

## Context

The founder, 2026-10-26: *"deep research on current process, way of working, CI, and anything that
agents do that can be done by machine or decision model like jev, the goal is to drastically reduce
agent friction and decision making … we also need this to be a first class principle architecturally
across estate and processes, anything an agent does needs to be justified why it can't be done by jev
or machine."*

The estate already runs the machinery this asks for, in three places, and each of them is invisible to
the founder because it works:

- `policy/operating_model.rego` refuses a PR that creates an identity without a grant, asks for a GUI
  step, or raises the secret ceiling without capacity approval.
- `bin/claim-gate` refuses a change with no live claim.
- `bin/idp-pr-risk-gate` refuses a risky diff.

Those are machine decisions about the estate, made by machines. Everything the founder is complaining
about is the residue where no such machine exists — and the residue is not a small list. Measured on
2026-10-26 (instruments in the spec §6):

- **3,618 agent actions** in the executor's own ledger over 32 days, across 570 distinct intents;
- **1,619 of the window's runs were machine-triggered** (46.9%) — the greenlane's own `unconverged`
  (1,597) and `unmerged` (22) loops — and 1,831 carried no trigger name at all;
- **1,927 door calls over 122 sessions**, of which **484 (25.1%) were the agent asking the door how to
  use the door** (`estate_show`) — friction with a receipt;
- **189,738 model calls** over 22 models in the action ledger in the window: the deciding itself,
  ~6,300 a day;
- the three most-used actions are state fetches (`lane-submit` 747, `gh-api` 320, `ci.status` 208) —
  fetching state a machine already holds is a cost, not a decision.

Two failures the estate has already paid for, and which this decision is a response to:

1. **Paperwork that measures nothing.** The operating-model rules that graded PR-body wording were cut
   on 2026-09-04 because they "checked nothing against the running estate". A principle that asks a
   human to fill in a form is the same failure wearing a better hat.
2. **Automation without quality.** The research is explicit (RADAR at Meta, 2605.30208, against the
   empirical PR study, 2604.03196): automating the easy 90% and dropping the hard 10% produces a
   green pipeline and a worse estate. Yield is not quality, and the ratio must be published next to
   the defect rate.

## Decisions

**D1. Three modes, one of them per action: `machine`, `model`, `judgment`.**
`machine` — a deterministic program decides. `model` — a decision model decides and returns a typed
value with a confidence; below the calibrated floor it escalates. `judgment` — a person decides.

**D2. The mode is derived wherever it can be derived.**
An intent whose steps call no model and need no person is `machine` by its own source. An intent whose
steps — or the libexec script those steps call — reach a model is `model`. Only the judgement residue
and the estate-level decisions are written down, in one file: `policy/agent-decisions.json`. 344 live
intents are classified by reading their own YAML; a human writes down the handful that cannot be.

**D3. `judgment` requires a named irreducibility and a written justification.**
One of four kinds — `value-tradeoff`, `irreversible`, `novel`, `low-confidence-escalation` — and at
least 40 characters of reason. "I was not sure" is not an irreducibility.

**D4. "A machine could do it" is a capability id, not a belief.**
A `machine` entry names the capability that decides, and the gate checks it against the registry. A
`model` entry names a decision model the estate actually runs (`model:jev`, `model:code-review.tier2`,
`model:llm`). A capability is not a decision: `hypotheses.race` is `machine` (the probes are commands
and the posterior is arithmetic) while the *proposal* of hypotheses is a model — two decisions, and
the register says so.

**D5. The invariant lives in the registry gate, not in a new tool.**
`bin/registry-gate` gains I-6 (seven clauses, each with the fixture that trips it). The registry is
the one store; the decision register is read into it; the measurement is a query on it
(`bin/capability-index decisions`). No second registry, no second gate, no second query surface. A
declaration that merely drifts from its source is a **finding**, not a refusal: refusing correct
work is an outage.

**D6. The measurement is the automation ratio, published from the executor's own ledger.**
`(machine + model runs) / all runs`, per decision and estate-wide, with the judgement residue in runs
beside it and the friction column (`estate_show` share of door calls) beside that. This is R-23's
autonomy ratio at the altitude of a single action. **Two numbers, not one:** the ratio says what
*decided* an action, and a second number says what *woke* it (machine-triggered against
agent-chosen, read from the ledger's `harness` column). Reporting only the first would have said
"100% automated" while the estate made 189,738 model calls a month; reporting only the second would
have hidden the judgement residue.

**D7. The order is fixed: machine first, model second, human last.**
The research does not support "jev or machine" as a single alternative. Where the property is
formalisable, deterministic verification beats probabilistic adjudication (Lean 4 guardrails,
2604.01483; provably secure agent guardrails, 2605.29251). A decision model is a *second* tier whose
value is a calibrated confidence and an escalation, not correctness (2407.18370, 2510.09738,
2608.06225) — and inter-model consensus is not human alignment (2606.03043). So a `model` verdict is
never terminal.

**D8. BLIND in CI, honest on the laptop.**
On a runner there is no `~/.estate`, so a live-only decider is invisible. The gate reports it BLIND,
exactly as the rest of the registry gate does; `--strict` turns BLIND into a failure.

**D9. The greenlane is the machine trigger; the EFDA spine is how the rest of the estate's waking
becomes one too.**
The greenlane already wakes the estate's work without a human: `lane-submit` → CI → `merge-when-green`
→ Flux converge, recorded in the ledger as the `unconverged` and `unmerged` loops. The spine (Flux
events → NATS JetStream → a Temporal signal → a workflow that verifies the outcome) generalises it:
the event that starts the work is a fact, not a poll. An action the spine wakes is `machine` until
it needs a judgement, and the anti-pattern to refuse is the poll — an agent asking "is the deploy
done yet?" is an action with no decider, and the spine deletes it rather than classifying it.

## Consequences

- **Good:** the estate can finally answer "how much of what agents do is a decision at all?", with a
  number from its own ledger. The judgement residue becomes a short, named, owned list instead of an
  untracked habit.
- **Good:** a new intent cannot be added without saying what decides it; the gate says so in the same
  place it already says "this record is malformed".
- **Cost:** the register is a file a human maintains. It is kept small on purpose (D2) and the gate
  refuses stale entries, so a register nobody trusts fails loudly instead of quietly.
- **Risk:** the ratio can be gamed by classifying hard decisions as `model`. Mitigated by D7 (model
  verdicts carry a floor and are themselves judged, R-63) and by publishing the escalation rate next
  to the ratio.
- **Risk, stated plainly:** if the ratio rises and escaped defects rise with it, this decision is
  wrong. Both numbers are measured today; the falsifier is in the research digest §6.

## Alternatives rejected

- **A second store for decisions.** The estate has built this kind of store five to ten times
  (AGENTS.md §6). The registry already holds every capability with its owner, plane and cost; a
  decision is a capability's mode of decision. One store.
- **A prose rule in AGENTS.md.** The estate cut prose rules that graded wording, because they measured
  nothing against the running estate. A rule with no gate and no number is that failure again.
- **Ask the model to self-classify.** A model grading its own decisions is the judge-unjudged case
  (2606.03043, 2603.06594). The classification is derived from artifacts and checked by a program.
- **Automate everything with a model.** Automation bias is measured (2103.02381): a human who
  rubber-stamps a model's verdict makes the loop's judgement worse, not better.
