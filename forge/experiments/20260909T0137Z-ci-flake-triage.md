---
experiment: 20260909T0137Z-ci-flake-triage
task: ci-flake-triage
base: unsloth/Qwen2.5-1.5B-Instruct
verdict: refused
refusal_kind: export
exit_code: 1
dry_run: true
held_out: 160
agreement: 0.9847328244274809
abstain_rate: 0.18125
min_agreement: 0.95
max_abstain: 0.2
dataset_sha256: 9517e48d9df50c3402a242e0f59f6be8a761853af256831a7062a39be02fa06f
dataset_rows: 799
usd: 0.1632
budget_usd: 1.0
trace: 6214d318-8fc7-4b1f-9750-c81e6bea3c9b
artifact: null
forge_commit: ae08520bd3f0c798720d731d29501c34317a726a
run_url: https://github.com/chidionyema/idp/actions/runs/34298732378
---

# Forge experiment 20260909T0137Z: ci-flake-triage

PASSED both pre-registered gates, then the run failed after them (exit 1): the GPU was billed, the numbers below are real, and no artifact was published. It was a dry run, which would not have pushed one either way.

## In plain English

A small model reads the end of a failed GitHub check's log and says whether the check merely stumbled (the same code passed on a rerun) or something really broke. When it is not sure it says nothing and a person takes over.
 It got 98% of the ones it answered right and declined to answer 18% of them, which clears the bar we set beforehand -- but the run then failed while packaging the model up, so there is nothing to use yet.

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
| train wall time (s) | 996 |
| cost (USD) | 0.1632 |
| budget (USD) | 1.0 |
| forge commit | ae08520bd3f0c798720d731d29501c34317a726a |
| task file | forge/tasks/ci-flake-triage.yaml |
| CI run | https://github.com/chidionyema/idp/actions/runs/34298732378 |

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
| agreement (answered rows) | 0.9847328244274809 |
| abstain rate | 0.18125 |
| min_agreement met | True |
| max_abstain met | True |
| verdict | refused |
| which refusal | export |
| process exit code | 1 |
| refusal |  |

160 held-out rows resolve agreement to about ±1.9% (95%, normal approximation), so a reading within that band of 95% is not a settled pass or fail; label more rows before trusting it.

## 6. Provenance

| field | value |
|---|---|
| Langfuse trace | https://langfuse.mumchimp.com/trace/6214d318-8fc7-4b1f-9750-c81e6bea3c9b |
| artifact (GHCR) |  |
| dataset sha256 | 9517e48d9df50c3402a242e0f59f6be8a761853af256831a7062a39be02fa06f |
| forge commit | ae08520bd3f0c798720d731d29501c34317a726a |
| CI run | https://github.com/chidionyema/idp/actions/runs/34298732378 |

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
