# Machine-first: every agent action justified against a machine or a decision model

**Date:** 2026-10-26 · **Author:** pi · **Claim:** chidionyema/idp#7222 · **ADR:** `docs/decisions/0044-machine-first-agent-action.md`
**Research:** `docs/research/2026-10-26-machine-first-research.md` (+ the 103-record harvest it cites)

---

## 1. The principle (T-7)

> **T-7 — Machine-first.** Every action an agent takes is classified into exactly one of three
> modes, and the classification is checked against the estate's own capabilities, not asserted:
>
> - **machine** — a deterministic program decides. The agent executes a verdict it did not form.
> - **model** — a decision model (JEV, a router, a judge, a Bayesian racer) decides and returns a
>   typed value with a confidence. Below the calibrated floor the answer escalates.
> - **judgment** — a person decides. This mode carries a **named irreducibility** and a written
>   justification of why no machine and no decision model can decide it.
>
> An action with no classification, or a judgment without an irreducibility, is refused. The estate
> publishes the **automation ratio** — the share of agent actions decided by a machine or a model —
> and drives it up.

This is the founder's rule, made architectural: *anything an agent does needs to be justified for why
it cannot be done by jev or machine*. The words "jev or machine" are not two synonyms, and the
research (`docs/research/2026-10-26-machine-first-research.md`) is explicit about the order —
deterministic verification first, a calibrated model second, a human last, and a small named residue
of irreducibility in between.

**Why a tenet and not a paragraph.** The estate has already been here: the operating-model rego rules
were cut on 2026-09-04 because they graded the *wording* of PR bodies and "nothing they check is
measured against the running estate". This principle is the opposite of that failure: it is measured
against the running estate (the executor's own ledger of what agents actually did), it is enforced by
a gate that can fail, and it produces a number the founder can watch.

---

## 2. What is classified

**The unit is an agent action, not a document.** The estate already records every action: the
executor's ledger (`~/.estate/estate.db`, table `intent_tickets`) holds one row per intent
invocation, and the door log (`~/.estate/logs/mcp.jsonl`) holds the MCP-mediated calls with their
session. So the classification is attached to *capabilities the agent invokes*, and the estate's own
telemetry says how often each one is used.

Three tiers of classification, cheapest first:

| tier | how the mode is decided | who maintains it |
|---|---|---|
| **derived** | the capability's own source: an intent whose steps call no model and need no person is `machine`; an intent whose steps (or the libexec script they call) reach a model is `model` | nobody — it is derived from the artifact |
| **declared** | a decision that is not one capability: the register entry in `policy/agent-decisions.json` | a human, once, with an irreducibility |
| **residue** | a capability that needs a person and is therefore `judgment` | a human, with an irreducibility and a justification |

The rule that keeps this from becoming paperwork: **the estate derives the mode wherever it can.**
344 live intents are classified by reading their own YAML. A human writes down only what cannot be
derived — the judgement residue and the estate-level decisions.

---

## 3. The decision register (`policy/agent-decisions.json`)

One file, one record per decision, in the shape the gate reads:

```json
{
  "id": "dec:which-failure-next",
  "decision": "Which failure in the estate gets the next unit of work?",
  "mode": "judgment",
  "irreducibility": "value-tradeoff",
  "justification": "The order is a trade-off between the founder's wellbeing, the blast radius of the failure and what the estate can carry in parallel ...",
  "decided_by": "founder",
  "surfaces": []
}
```

For `machine` entries, `decided_by` names the capability that decides (`cap:intent/ci.status`,
`cap:intent/lane-submit`). For `model` entries it names a decision model the estate runs
(`model:jev`, `model:code-review.tier2`, `model:llm`). The gate checks that name against the
registry: a machine entry that names a capability the estate does not have is refused, because
"a machine could do it" is a capability id, not a belief.

**A decision is not a capability.** `hypotheses.race` is the sharpest case: the model *proposes*
the hypotheses and the race *disposes* of them, so those are two decisions, not one — the
proposal is `model:llm`, the race is `machine` (the probes are commands, the posterior is
arithmetic). Reading an intent's name and calling it one thing is how a register goes stale.

**Why the irreducibility must be one of four kinds.** "I was not sure" is not an irreducibility. The
four kinds are the ones the research supports and the estate can name:

| irreducibility | what it means | who decides |
|---|---|---|
| `value-tradeoff` | two goods the estate cannot rank without a human (founder wellbeing vs. blast radius) | the founder |
| `irreversible` | the action cannot be undone (an outward-facing or destructive act) | the founder, or the owner of the blast radius |
| `novel` | no precedent in the estate and no rule that covers it | a person, with the reason recorded |
| `low-confidence-escalation` | a decision model returned below its calibrated floor | the person the model escalated to |

---

## 4. The gate (`bin/registry-gate`, invariant I-6)

The registry gate already refuses a malformed record, a duplicate writer and a stale read. I-6 is the
decision invariant, and every clause has the case that trips it (a gate that cannot fail is not a
gate):

| clause | what it refuses | the trip case (a fixture) |
|---|---|---|
| **I-6a** | a register entry with no mode, or a mode outside `machine`/`model`/`judgment` | an entry with `mode: vibe` |
| **I-6b** | a `judgment` entry with no irreducibility, or one outside the four kinds | `judgment` with `irreducibility: i-was-not-sure` |
| **I-6c** | a `judgment` entry whose justification is shorter than 40 characters | `irreducibility: novel` and a one-word justification |
| **I-6d** | a `machine` entry whose `decided_by` names a capability that is not in the registry | `cap:intent/does-not-exist` |
| **I-6e** | a `model` entry whose `decided_by` is not a decision model the estate runs | `model:the-committee` |
| **I-6f** | a `judgment` entry whose `decided_by` is not a role the register names | `decided_by: the intern` |
| **I-6g** | a duplicate decision id | the same id twice |

**What is a finding, not a refusal.** Two things are reported rather than refused, because a gate
that refuses correct work is an outage:

- **the undeclared judgement residue** — a capability that is `judgment` by derivation and has no
  register entry (`create-repo` was the one the estate had);
- **derivation drift** — a declaration that contradicts the source it claims to describe
  (`gh-api` declared `machine` while its source derived `model`, because a *comment* in its steps
  named another intent; the derivation reads code, not prose, after that finding).

Both appear in `bin/registry-gate` output as `note registry-gate I-6 finding: ...` and in
`bin/capability-index decisions`.

**BLIND tolerance.** On a CI runner there is no `~/.estate`, so live capabilities are invisible. A
`machine` entry whose decider is a live-only capability is reported BLIND, not refused — the same
honesty rule the rest of the gate uses. `--strict` turns every BLIND into a failure, which is the
founder's question asked as a verdict.

---

## 5. The query contract (`bin/capability-index decisions`)

The registry is the one store, so the measurement lives there too, under the same query contract
(`bin/capability-index query|get|prove|reconcile|emit`):

```
bin/capability-index decisions              # the register, the derived modes, the ratio
bin/capability-index decisions --json       # machine-readable
```

What it prints, per decision and per capability:

- the mode (`machine` / `model` / `judgment`) and who decides, with the irreducibility and the
  reason for every judgement entry;
- the observed runs in the window, from the executor's own ledger;
- the **automation ratio** — `(machine + model runs) / all runs the estate can see`, the judgement
  residue in runs, and the BLIND count of runs whose source is not in the registry;
- **who woke the work** — machine-triggered runs against agent-chosen runs, read from the ledger's
  own `harness` column. This is the number that answers "how much of the estate is a machine's
  decision?" and it is not the same number as the ratio: the ratio says what decided an action,
  this says what *started* it;
- **model turns** — how many model calls the estate made in the window, from the action ledger.
  Each one is a decision turn a rule or a calibrated decision model could have made;
- the **friction column**: how many of the door's calls were spent *asking the door how to use the
  door* (`estate_show`), because that is friction with a receipt.

---

## 6. What the estate measures today (2026-10-26)

Measured, with the instrument named, from `docs/research/2026-10-26-machine-first-research.md` §4:

| fact | number | instrument |
|---|---|---|
| live intents / repo intents | 344 / 99 | `ls ~/.estate/intents/*.yaml`, `ls platform/estate/intents/*.yaml` |
| tools in `bin/` / workflows | 444 / 76 | `ls bin`, `ls .github/workflows` |
| agent actions in the executor ledger (32 days) | 3,618 over 570 distinct intents | `sqlite3 ~/.estate/estate.db 'select count(*) from intent_tickets'` |
| **runs in the window that a machine woke** (30 days) | **1,619 = 46.9%** — the greenlane's own `unconverged` (1,597) and `unmerged` (22) loops | `sqlite3 ~/.estate/estate.db 'select harness, count(*) from intent_tickets group by 1'` |
| runs in the window with **no trigger named** (`direct`) | 1,831 | same |
| **model calls** (the deciding itself, 30 days) | **189,738 over 22 models** | `~/.estate/action-ledger.jsonl` |
| MCP door calls / sessions | 1,927 over 122 sessions | `~/.estate/logs/mcp.jsonl` + `plan-mcp.jsonl` |
| **door calls spent re-learning the door** | **484 of 1,927 = 25.1%** (`estate_show`) | same |
| judgement residue in runs (30 days) | 1 run (`create-repo`) | `bin/capability-index decisions` |
| I-6 violations on the committed register | 0 | `bin/registry-gate` |

Three consequences the principle names:

1. **A quarter of the door's traffic is a schema lookup.** The door's contract is not self-describing
   at the moment of use. That is friction, and it is machine-fixable: the registry's query contract
   (`get`, `prove`) already answers "what does this intent take and what does it return" in one call.
2. **The three most-used actions are state fetches** (`lane-submit` 747 runs, `gh-api` 320,
   `ci.status` 208). Fetching state that a machine holds is not a decision; it is a cost. Those are
   `machine` by derivation, and the ratio counts them.
3. **The estate already runs machine-triggered at scale, and it is not the interesting part.**
   46.9% of the window's runs were woken by the greenlane's own loops; the interesting number is
   the **189,738 model calls** — a decision turn each, at ~6,300 a day, and the whole of the
   friction the founder is pointing at. That is where the work is, and T-7 is what makes it
   countable.

---

## 7. The migration (what changes, in order)

1. **Now (this change).** The register exists, the invariant exists, the gate refuses, the ratio is
   published. Nothing in the estate's behaviour changes yet — the register *describes* what agents
   already do, so the first reading is a baseline, not a policy.
2. **Next.** The residue: every intent that is `judgment` by derivation gets a register entry, and
   every `estate_show` in the door's traffic either disappears (the door answers it) or becomes a
   machine decision.
3. **Then.** The judgement residue in *runs* is driven down: each entry in the register names the
   machine that could take it, and the work item to build that machine is the follow-up. The ratio is
   the scoreboard; the epic's autonomy ratio (R-23) is the same number at a different altitude.
4. **Never.** A judgement entry is not deleted when a machine appears — it is *replaced*, and the
   replacement carries its own irreducibility or none at all.

---

## 8. The greenlane and the spine: the machine trigger, made general

T-7 says an action must name its decider. The spine (EFDA: Flux → NATS JetStream → a Temporal
signal → a workflow that verifies the outcome) says **who wakes the action**. The two are one
mechanism, and the estate already holds both halves:

| the spine's part | what the estate already has | what is missing |
|---|---|---|
| the event fabric | NATS with JetStream, file store and a PVC, deployed in `event-bus` (`platform/event-bus/nats.yaml`), and `bin/bus-ensure` to keep it answering | a `FLUX_EVENTS` stream with a dedup window, and a DLQ stream |
| the wiring | the Flux notification-controller, with `telegram` and `github` providers | a `nats` provider and an Alert that selects Kustomization/HelmRelease/GitRepository |
| the bridge | Temporal (chart 1.6.0) with the `sovereign-worker` in `temporal` | the NATS→Temporal signal bridge: routing, idempotency from `Nats-Msg-Id`, DLQ on exhausted retries |
| the workflow | the sovereign Temporal worker | one workflow that suspends on a signal, verifies a Flux reconciliation, and writes a receipt |

**How the greenlane fits.** The greenlane is already the estate's machine trigger: `lane-submit`
lands a change, CI runs, `merge-when-green` merges, Flux converges, and the ledger records the
loop as `unconverged` and `unmerged` — 1,619 machine-triggered runs in the window. The spine
generalises it: **the event that wakes the work is a fact, not a poll.** A Flux reconciliation
becomes a NATS message; the message becomes a Temporal signal; the workflow verifies the outcome
and emits a receipt. An agent is woken only when the signal carries a decision it must make.

**What that means for T-7, concretely:**

- a spine-woken verification is `machine` — a deterministic check against a Flux status;
- a spine-woken *judgement* (a reconciliation failed in a way with no precedent) is `judgment`,
  and it is the only case that costs a person;
- **the anti-pattern to refuse** is a poll: an agent asking "is the deploy done yet?" is an
  action with no decider, and the spine deletes it rather than classifying it.

This is also the answer to the friction the door measures: a quarter of the door's traffic is the
agent asking the door how to use the door, and the spine's receipts replace the *other* half of
it — the agent asking the estate what just happened.

---

## 9. What would prove this wrong

Falsifiers, each with its instrument, are in `docs/research/2026-10-26-machine-first-research.md` §6.
The sharpest one: **if raising the automation ratio raises escaped defects, the principle is wrong**
— and that is measurable, because the estate records both numbers today.
