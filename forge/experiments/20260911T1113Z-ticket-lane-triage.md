---
experiment: 20260911T1113Z-ticket-lane-triage
task: ticket-lane-triage
base: unsloth/Qwen2.5-1.5B-Instruct
verdict: refused
refusal_kind: gate
exit_code: 1
dry_run: true
held_out: 78
agreement: 1.0
abstain_rate: 0.9358974358974359
min_agreement: 0.9
max_abstain: 0.35
dataset_sha256: 27d4a6f033556f37ebed0d17e67fcc09030dd5e14327dc6e8446181d767463c6
dataset_rows: 387
lift_over_untrained: 1.0
lift_over_majority: 0.6794871794871795
answered: 5
wrong: 0
usd: 0.0505
budget_usd: 1.0
trace: 410e1847-0629-4447-af27-acf60bf18694
artifact: null
forge_commit: 789c43eadaa3228abbf8c67e07e7861707431f62
run_url: https://github.com/chidionyema/idp/actions/runs/34592275281
---

# Forge experiment 20260911T1113Z: ticket-lane-triage

REFUSED by the pre-registered gates: held-out abstain rate 0.9359 above 0.35. No model left the Forge.

## In plain English

A small model reads a new ticket and says which lane it belongs in. When it is not sure it says nothing and the ticket waits for a person, which is what happens today anyway.
 It got 100% right and declined 94%, which does not clear the bar, so nothing was published.

## 1. Hypothesis

A LoRA on Qwen2.5-1.5B reads a ticket's title and the top of its body and names the lane the board actually files it under, at 90% agreement with the label a person put on it, abstaining on at most a third of tickets; Linear then stops leaving 171 issues with no lane and no priority for the founder to sort by hand.


## 2. Setup

| field | value |
|---|---|
| base model | unsloth/Qwen2.5-1.5B-Instruct |
| kind | classify |
| labels | `0` = platform, `1` = process, `2` = observability, `3` = agents, `4` = science, `5` = money, `6` = security |
| LoRA | r=16, alpha=32, epochs=3, lr=2e-4 |
| max_steps | -1 |
| GPU | T4 |
| train wall time (s) | 308 |
| cost (USD) | 0.0505 |
| budget (USD) | 1.0 |
| forge commit | 789c43eadaa3228abbf8c67e07e7861707431f62 |
| task file | forge/tasks/ticket-lane-triage.yaml |
| CI run | https://github.com/chidionyema/idp/actions/runs/34592275281 |

Prompt template:

```
Route this ticket to a lane: 0 platform, 1 process, 2 observability, 3 agents, 4 science, 5 money, 6 security.
{input}
Lane:
```

## 3. Data

| field | value |
|---|---|
| rows | 387 |
| train / eval | 309 / 78 |
| sha256 | 27d4a6f033556f37ebed0d17e67fcc09030dd5e14327dc6e8446181d767463c6 |
| per label | {"0": 122, "1": 74, "2": 74, "3": 61, "4": 22, "5": 21, "6": 13} |
| teacher(s) | outcome: the ticket carries lane:agents on the board, outcome: the ticket carries lane:money on the board, outcome: the ticket carries lane:observability on the board, outcome: the ticket carries lane:platform on the board, outcome: the ticket carries lane:process on the board, outcome: the ticket carries lane:science on the board, outcome: the ticket carries lane:security on the board |
| Langfuse dataset | ticket-lane-triage |
| file | forge/datasets/ticket-lane-triage.jsonl |

Labels come from the source each row's `teacher` field names: a teacher model run
(forge/generate_teacher_dataset.py), a gold set, or a recorded outcome (forge/collect_ci_runs.py).
Rows a teacher model marked unsure are in the `-unsure` Langfuse dataset and not here.

## 4. Pre-registered gates

| field | value |
|---|---|
| minimum rows | 500 (80/20 split, seed 0) |
| abstain_below | 0.55 margin between the top two label probabilities |
| min_agreement | 0.9 on answered held-out rows |
| max_abstain | 0.35 of held-out rows |

Both gates are graded before any export. Agreement bought by abstaining is refused by the
second gate.

## 5. Results

| field | value |
|---|---|
| held-out rows | 78 |
| agreement (answered rows) | 1.0 |
| abstain rate | 0.9358974358974359 |
| min_agreement met | True |
| max_abstain met | False |
| verdict | refused |
| which refusal | gate |
| process exit code | 1 |
| refusal | held-out abstain rate 0.9359 above 0.35 |

78 held-out rows resolve agreement to about ±0.0% (95%, normal approximation), so a reading within that band of 90% is not a settled pass or fail; label more rows before trusting it.


## 5a. What it can do

Of 78 held-out rows it had never seen, it answered **5** and declined **73**. Of the ones it answered it was right **5** times and wrong **0**. That is the duty it can take: the declined rows still cost a person or a frontier call.

The same model before a single gradient step scored 0.0% on these rows, so training moved it +100.0% and answering `0` every time would score 32.1%, so it is +67.9% over guessing.

| field | value |
|---|---|
| `0` = platform | 25 rows, answered 5, right 5, caught 100% -- too few rows to judge |
| `1` = process | 15 rows, answered 0, right 0, never answered -- too few rows to judge |
| `2` = observability | 15 rows, answered 0, right 0, never answered -- too few rows to judge |
| `3` = agents | 12 rows, answered 0, right 0, never answered -- too few rows to judge |
| `4` = science | 4 rows, answered 0, right 0, never answered -- too few rows to judge |
| `5` = money | 4 rows, answered 0, right 0, never answered -- too few rows to judge |
| `6` = security | 3 rows, answered 0, right 0, never answered -- too few rows to judge |

## 5b. What it cannot do reliably

- `0` = platform: 25 held-out rows is under 30, so this run says nothing settled about it
- `1` = process: 15 held-out rows is under 30, so this run says nothing settled about it
- `2` = observability: 15 held-out rows is under 30, so this run says nothing settled about it
- `3` = agents: 12 held-out rows is under 30, so this run says nothing settled about it
- `4` = science: 4 held-out rows is under 30, so this run says nothing settled about it
- `5` = money: 4 held-out rows is under 30, so this run says nothing settled about it
- `6` = security: 3 held-out rows is under 30, so this run says nothing settled about it

## 5c. Where the edge is, and how to move it

The task file abstains under a 0.55 margin. That is one point on a curve,
and the curve is the edge: every row of it is the same model, re-read at a different
confidence bar. Lower bars answer more and are wrong more.

| abstain_below | answers | of held-out | agreement |
|---|---|---|---|
| 0.0 | 78 | 100% | 44.9% |
| 0.1 | 30 | 38% | 63.3% |
| 0.2 | 17 | 22% | 64.7% |
| 0.3 | 15 | 19% | 73.3% |
| 0.4 | 12 | 15% | 91.7% |
| 0.5 | 8 | 10% | 100.0% |
| 0.6 | 2 | 3% | 100.0% |
| 0.7 | 1 | 1% | 100.0% |
| 0.8 | 0 | 0% | 0.0% |
| 0.9 | 0 | 0% | 0.0% |
| 0.95 | 0 | 0% | 0.0% |
| 0.99 | 0 | 0% | 0.0% |

Which lever moves it forward, read off the numbers above:

- label `0` has 25 held-out rows, under 30: nothing about `0` is settled either way; label more of it
- label `1` has 15 held-out rows, under 30: nothing about `1` is settled either way; label more of it
- label `2` has 15 held-out rows, under 30: nothing about `2` is settled either way; label more of it
- label `3` has 12 held-out rows, under 30: nothing about `3` is settled either way; label more of it
- label `4` has 4 held-out rows, under 30: nothing about `4` is settled either way; label more of it
- label `5` has 4 held-out rows, under 30: nothing about `5` is settled either way; label more of it
- label `6` has 3 held-out rows, under 30: nothing about `6` is settled either way; label more of it


## 6. Provenance

| field | value |
|---|---|
| Langfuse trace | https://langfuse.mumchimp.com/trace/410e1847-0629-4447-af27-acf60bf18694 |
| artifact (GHCR) |  |
| dataset sha256 | 27d4a6f033556f37ebed0d17e67fcc09030dd5e14327dc6e8446181d767463c6 |
| forge commit | 789c43eadaa3228abbf8c67e07e7861707431f62 |
| CI run | https://github.com/chidionyema/idp/actions/runs/34592275281 |

## 7. Reproduce

```
# 1. label (the teacher through the router; persisted to Langfuse + git)
uv run --with anthropic --with pyyaml --with 'langfuse<3' forge/generate_teacher_dataset.py \
    --task forge/tasks/ticket-lane-triage.yaml --input raw.jsonl --output forge/datasets/ticket-lane-triage.jsonl
# 2. train on Modal from CI (the only road; the root is set once by bin/idp-set-root modal)
gh workflow run forge-train.yml -f task_file=forge/tasks/ticket-lane-triage.yaml -f dry_run=true -f max_steps=-1
# 3. this record
python forge/experiment_record.py --task forge/tasks/ticket-lane-triage.yaml --run forge-run.json --data forge/datasets/ticket-lane-triage.jsonl
```
