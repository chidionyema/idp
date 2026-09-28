---
experiment: 20260911T1657Z-ci-flake-triage
task: ci-flake-triage
base: unsloth/Qwen2.5-1.5B-Instruct
verdict: refused
refusal_kind: export
exit_code: 1
dry_run: true
held_out: 160
agreement: 0.9776119402985075
abstain_rate: 0.1625
min_agreement: 0.95
max_abstain: 0.2
dataset_sha256: 9517e48d9df50c3402a242e0f59f6be8a761853af256831a7062a39be02fa06f
dataset_rows: 799
lift_over_untrained: 0.7901119402985075
lift_over_majority: 0.09011194029850755
answered: 134
wrong: 3
usd: 0.1762
budget_usd: 1.0
trace: 61e99cff-3a9f-4913-80c6-6373272f32a9
artifact: null
forge_commit: 31310ca719aee3de1579b7179fe1ee19ec314cf9
run_url: https://github.com/chidionyema/idp/actions/runs/34623164859
---

# Forge experiment 20260911T1657Z: ci-flake-triage

PASSED both pre-registered gates, then the run failed after them (exit 1): the GPU was billed, the numbers below are real, and no artifact was published. It was a dry run, which would not have pushed one either way.

## In plain English

A small model reads the end of a failed GitHub check's log and says whether the check merely stumbled (the same code passed on a rerun) or something really broke. When it is not sure it says nothing and a person takes over.
 It got 98% of the ones it answered right and declined to answer 16% of them, which clears the bar we set beforehand -- but the run then failed while packaging the model up, so there is nothing to use yet.

## 1. Hypothesis

A LoRA on Qwen2.5-1.5B reads the failed step's log tail of a red GitHub Actions run and says whether the same commit later went green with nothing changed (a flake) at 95% agreement with what actually happened, abstaining on at most 20% of runs; the estate then stops paying a frontier call, or a session's attention, for the red runs the model answers.


## 2. Setup

| field | value |
|---|---|
| base model | unsloth/Qwen2.5-1.5B-Instruct |
| kind | classify |
| labels | `0` = real, `1` = flake |
| LoRA | r=16, alpha=32, epochs=3, lr=2e-4 |
| max_steps | -1 |
| GPU | T4 |
| train wall time (s) | 1075 |
| cost (USD) | 0.1762 |
| budget (USD) | 1.0 |
| forge commit | 31310ca719aee3de1579b7179fe1ee19ec314cf9 |
| task file | forge/tasks/ci-flake-triage.yaml |
| CI run | https://github.com/chidionyema/idp/actions/runs/34623164859 |

Prompt template:

```
A GitHub Actions run failed. Decide whether it was a flake (1: the same commit later passed with no change) or a real failure (0: a change was needed).
{input}
Verdict:
```

## 3. Data

| field | value |
|---|---|
| rows | 799 |
| train / eval | 639 / 160 |
| sha256 | 9517e48d9df50c3402a242e0f59f6be8a761853af256831a7062a39be02fa06f |
| per label | {"0": 700, "1": 99} |
| teacher(s) | outcome: same commit later green on the same workflow |
| Langfuse dataset | ci-flake-triage |
| file | forge/datasets/ci-flake-triage.jsonl |

Labels come from the source each row's `teacher` field names: a teacher model run
(forge/generate_teacher_dataset.py), a gold set, or a recorded outcome (forge/collect_ci_runs.py).
Rows a teacher model marked unsure are in the `-unsure` Langfuse dataset and not here.

## 4. Pre-registered gates

| field | value |
|---|---|
| minimum rows | 500 (80/20 split, seed 0) |
| abstain_below | 0.8 margin between the top two label probabilities |
| min_agreement | 0.95 on answered held-out rows |
| max_abstain | 0.2 of held-out rows |

Both gates are graded before any export. Agreement bought by abstaining is refused by the
second gate.

## 5. Results

| field | value |
|---|---|
| held-out rows | 160 |
| agreement (answered rows) | 0.9776119402985075 |
| abstain rate | 0.1625 |
| min_agreement met | True |
| max_abstain met | True |
| verdict | refused |
| which refusal | export |
| process exit code | 1 |
| refusal |  |

160 held-out rows resolve agreement to about ±2.3% (95%, normal approximation), so a reading within that band of 95% is not a settled pass or fail; label more rows before trusting it.


## 5a. What it can do

Of 160 held-out rows it had never seen, it answered **134** and declined **26**. Of the ones it answered it was right **131** times and wrong **3**. That is the duty it can take: the declined rows still cost a person or a frontier call.

The same model before a single gradient step scored 18.8% on these rows, so training moved it +79.0% and answering `0` every time would score 88.8%, so it is +9.0% over guessing.

| field | value |
|---|---|
| `0` = real | 142 rows, answered 123, right 122, caught 99% |
| `1` = flake | 18 rows, answered 11, right 9, caught 82% -- too few rows to judge |

## 5b. What it cannot do reliably

- `1` = flake: 18 held-out rows is under 30, so this run says nothing settled about it

## 5c. Where the edge is, and how to move it

The task file abstains under a 0.8 margin. That is one point on a curve,
and the curve is the edge: every row of it is the same model, re-read at a different
confidence bar. Lower bars answer more and are wrong more.

| abstain_below | answers | of held-out | agreement |
|---|---|---|---|
| 0.0 | 160 | 100% | 93.8% |
| 0.1 | 160 | 100% | 93.8% |
| 0.2 | 160 | 100% | 93.8% |
| 0.3 | 160 | 100% | 93.8% |
| 0.4 | 159 | 99% | 94.3% |
| 0.5 | 158 | 99% | 94.3% |
| 0.6 | 155 | 97% | 96.1% |
| 0.7 | 147 | 92% | 96.6% |
| 0.8 (this run) | 134 | 84% | 97.8% |
| 0.9 | 109 | 68% | 100.0% |
| 0.95 | 86 | 54% | 100.0% |
| 0.99 | 41 | 26% | 100.0% |

Which lever moves it forward, read off the numbers above:

- label `1` has 18 held-out rows, under 30: nothing about `1` is settled either way; label more of it
- the threshold is set conservatively: at abstain_below 0.6 the model would answer 97% of rows instead of 84% and still hold 96.1% agreement, over the 95% floor


## 6. Provenance

| field | value |
|---|---|
| Langfuse trace | https://langfuse.mumchimp.com/trace/61e99cff-3a9f-4913-80c6-6373272f32a9 |
| artifact (GHCR) |  |
| dataset sha256 | 9517e48d9df50c3402a242e0f59f6be8a761853af256831a7062a39be02fa06f |
| forge commit | 31310ca719aee3de1579b7179fe1ee19ec314cf9 |
| CI run | https://github.com/chidionyema/idp/actions/runs/34623164859 |

## 7. Reproduce

```
# 1. label (the teacher through the router; persisted to Langfuse + git)
uv run --with anthropic --with pyyaml --with 'langfuse<3' forge/generate_teacher_dataset.py \
    --task forge/tasks/ci-flake-triage.yaml --input raw.jsonl --output forge/datasets/ci-flake-triage.jsonl
# 2. train on Modal from CI (the only road; the root is set once by bin/idp-set-root modal)
gh workflow run forge-train.yml -f task_file=forge/tasks/ci-flake-triage.yaml -f dry_run=true -f max_steps=-1
# 3. this record
python forge/experiment_record.py --task forge/tasks/ci-flake-triage.yaml --run forge-run.json --data forge/datasets/ci-flake-triage.jsonl
```
