# Research that is driven by objectives, and experiments that follow from it

Founder, 2026-10-19, live. This is the ticket's spec and its requirement ledger (idp#6603).
Every line in the ledger is a thing the founder asked for in that session, in their words, and
each carries the proof that closes it. A line is closed by a measurement on the real path, never
by a merge (AGENTS.md §3).

## Requirement ledger

| # | Founder asked for | Closes when (measured, on the real path) | State |
|---|---|---|---|
| R1 | "what is the status of our research engines? what exactly are they researching?" | Answered with live cluster and database numbers | **Done 2026-10-19**: one engine live; 943 admitted and 704 rejected claims over 98 runs; subjects are five fixed lines in `platform/research-engine/cronjob.yaml` |
| R2 | "we have other research engines not operational" | One research layer remains (AGENTS.md §6); the crew research lane is retired, ironcage is parked with its reason written down, `factory-inventory.md` is true | Open |
| R3 | "this engine is useless and not researching anything worthwhile" | The engine's input is objectives, not trivia; the share of admitted claims that cite an objective is measured and above 95% | Open |
| R4 | "we need a way to give it objectives" | An objective filed as a GitHub issue is picked up by the engine within one hour and its result is posted back to that issue | Open |
| R5 | "we need to be able to run autonomous experiments based on research" | `estate-execute experiment.run` runs a hypothesis in the gVisor cell under a USD cap and writes a Forge-format record, refused runs included | Open |
| R6 | "industry leading in our autonomous capabilities" | At least one kept change per week reaches production from objective to measured delta with no human edit; the count is on /fleet | Open |
| R7 | "a clever way to drive research objectives" | Objectives are mined from measured pain and drift signals, ranked by pain per USD, with a baseline recorded before any experiment | Open |
| R8 | "components, capabilities and services ... keep upgrading, improving, researching better ways, experimenting, shipping" | Each Flux component can declare `idp.estate.io/metric` and `idp.estate.io/watch`; drift and frontier-scout objectives are opened for them | Open |
| R9 | "track every requirement in a ticket and get all done" | This ledger, kept current on the issue; the issue closes only when R2 to R8 each carry a proof comment | In progress |
| R10 | (found on the way) the hourly run died on `source_index: "all"` | The next hourly job on the cluster completes and `research-engine` logs a delivery line | Fix pushed (research-engine `fix/source-index-not-a-number`); pin not landed |

## Design

An **objective** is a measured problem: a signal, a baseline measured now, a target, a USD cap
and a deadline. No baseline, no objective. It is a GitHub issue labelled `objective`, because the
issue is already the estate's claim of record (AGENTS.md §5); there is no second queue.

Three sources feed it, and one pipeline follows it.

| Source | Question | Found by | Needs an LLM |
|---|---|---|---|
| Pain | what is failing or costing us | red and cancelled Greenlane lanes, incident reports, Flux rows not Ready, work-audit LOST, the engine's own rejection reasons | no |
| Drift | are we behind | pinned images, charts and dependencies against upstream releases and CVEs | no |
| Frontier scout | is there a better way | a standing question per component, answered by the research engine with cross-provider verified claims | yes, capped per component |

Pipeline: objective -> the research engine decomposes it into questions and hypotheses, each with
a pre-registered gate (`crew/EXPERIMENTS.md`) -> `experiment.run` in the gVisor cell, with a
per-experiment cap drawn from the sovereign budget -> `platform/eval/pareval_layer.py` decides
keep or discard -> a kept change goes to Greenlane as a `lane/` branch -> it counts only when
/fleet shows the metric moved in production.

Ranking is measured pain divided by budget: failures in 30 days times minutes lost each, over
the USD cap. Nobody types a priority.

Autonomy tiers. Auto-ship: version bumps, config tuning and prompt changes, with a green gate and
a measured non-regression. Founder or 2/3 consensus: architecture swaps, new dependencies and
anything destructive (`sovereign/consensus/decide.py`, the capabilities block in AGENTS.md).

## Reuse, so this is not the eleventh copy (AGENTS.md §6)

| Layer | Used | Not built |
|---|---|---|
| research | `research-engine` (chidionyema/research-engine) | a second engine; crew `science/research_*` is retired into it |
| intake | GitHub issues | a queue |
| execution boundary | `estate-execute` intents, the `otto-gvisor-sandbox` cell | a new runner |
| budget | `sovereign/engine/budget.py`, Forge `cost_gate` | a new meter |
| record | Forge `experiment_record.py` | a new format |
| keep or discard | `platform/eval/pareval_layer.py` | a new statistics module |
| landing | Greenlane | a second path to main |
| scheduling | `scheduler/` | Dagster (no Flux row) |
| registry | the Flux-generated Backstage catalog (`bin/catalog-platform`) | a second registry |

What does not exist and is built here: the signal miner, the objective-to-hypothesis
decomposer, `experiment.run`, the baseline-versus-candidate runner, the candidate-to-pareval
wiring, and the /fleet experiments view.

## Cost and placement (AGENTS.md §8)

Deterministic miners run on a GitHub Actions schedule, which is the free rung. The LLM work stays
inside the existing $0 to $150 a month contract. Nothing here adds to the node's 1.8 CPU request
budget in the first checkpoint; any later workload states its requests in its own change.

## Related

idp#3139 (conscience: research is red; "relentless research, always know what is out there and
adopt the best") is the same ambition measured by a gate; this work is what would make it green.
