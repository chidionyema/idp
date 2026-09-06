---
experiment: 0002-ci-flake-triage-plan
task: ci-flake-triage
status: pre-registered, not yet run
---

# Pre-registration 0002: is this red CI run a flake?

Written 2026-09-06 before any GPU minute is spent. The run's record will be filed beside this file
by the forge-train workflow and will not edit this plan.

## In plain English

When a check on GitHub goes red, someone has to read it and decide: did something break, or did the
check just stumble and it would pass if run again? Today a session reads every one, and a run through
a paid model is the usual first read. Between 16 August and 6 September the estate had 2,000 red runs.

This experiment trains a small model, on the estate's own history, to make that first read. The label
is free: for every red run we already know what happened next. If the same commit later went green on
the same check with nothing changed, it was a stumble; if not, it was real. The model reads the end of
the failed step's log and says which. When it is not sure it says nothing and a person or the paid
model takes over, so a wrong guess cannot slip through as an answer. If it passes the gate, the estate
stops paying for the red runs the model answers.

## For engineers

**Question.** Can a 1.5B student, trained on outcome labels only (no teacher model, no hand labels),
classify a failed GitHub Actions run as `flake` or `real` from the failed step's log tail at the
shipping gate, with abstention as the safety valve?

**Hypothesis.** A LoRA (r=16, alpha=32, 3 epochs, lr 2e-4) on `unsloth/Qwen2.5-1.5B-Instruct`,
trained on the 80% train split, agrees with the recorded outcome on at least 95% of the held-out rows
it answers and abstains (top-two margin under 0.80) on at most 20% of them.

**Label.** `forge/collect_ci_runs.py` lists every failed and every successful run of the repository
since 2026-08-09 and marks a failure `1` (flake) when a later successful run of the same workflow
carries the same `head_sha`, else `0` (real). Scheduled workflows (estate-state, the verdict drills)
sit on main's commit, so for them the label reads "cleared itself before main moved", which is the
same operational question.

**Input.** `workflow`, `job`, failed `step`, `event`, then the last 40 cleaned lines of that step's own
log from the run archive (timestamps and ANSI stripped, `##[group]` markers dropped, token shapes
redacted), capped at 2,400 characters. Each row carries the run URL so a label can be re-derived.

**Measured before writing this plan (2026-09-06).** 2,000 failed runs 16 Aug to 6 Sep; in the latest
500, `estate-state` 125, `ci` 112, verdict drills 120, `otto-parity` 39. A 60-run hand sample of
failed `ci` runs split 15 flake / 45 real by the same rule.

## What the run is graded against

| gate | value | source |
|---|---|---|
| minimum rows | 500, split 80/20 with seed 0 | `forge/common.py` |
| abstain_below | 0.80 margin | `forge/tasks/ci-flake-triage.yaml` |
| min_agreement | 0.95 on answered held-out rows | `forge/tasks/ci-flake-triage.yaml` |
| max_abstain | 0.20 of held-out rows | `forge/tasks/ci-flake-triage.yaml` |
| compute | T4, 3600 s, budget 1.00 USD | `forge/tasks/ci-flake-triage.yaml` |

## What would make us stop

- Under 500 rows after collection: the run is refused by `split`; widen `--since`, never lower the floor.
- Class balance worse than 1:9: report it and add a balanced sample before training.
- Agreement inside ±4 points of the gate: the held-out count cannot settle it; label more rows.
- Any token shape surviving redaction in the committed dataset: pull the file, fix the regex, recollect.

## Rejected

Trunk Flaky Tests and BuildPulse do the same job as a service that receives the estate's CI logs.
Rejected for sovereignty: the logs stay in the repository and the model runs on the laptop.
