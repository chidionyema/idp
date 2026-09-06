---
experiment: 0001-example-classify-plan
task: example-classify
status: pre-registered, not yet run
---

# Pre-registration 0001: first Forge run

Written 2026-09-06 before any GPU minute is spent. The record of the run itself will be filed
beside this file by the forge-train workflow and will not edit this plan.

## Question

Can a 1.5B student, trained only on labels the estate's own teacher produced, take a
binary classification task off the paid router at the gate we set, with abstention as the
safety valve instead of a lower bar?

## Hypothesis

A LoRA (r=16, alpha=32, 3 epochs, lr 2e-4) on `unsloth/Qwen2.5-1.5B-Instruct`, trained on 400
teacher-labelled rows, agrees with the teacher on at least 95% of the 100 held-out rows it answers
and abstains (top-two margin under 0.80) on at most 20% of them.

If it passes, the Edge Runtime serves this task and every abstained row falls through to the
router; the saving is the answered share of that task's router spend.

## What the run is graded against

| gate | value | source |
|---|---|---|
| minimum rows | 500, split 80/20 with seed 0 | `forge/common.py` |
| abstain_below | 0.80 margin | `forge/task.yaml` |
| min_agreement | 0.95 on answered held-out rows | `forge/task.yaml` |
| max_abstain | 0.20 of held-out rows | `forge/task.yaml` |

Both gates are graded before export; a run that clears agreement by abstaining is refused.

## Data plan

1. Raw inputs: one JSONL of real texts for the task (ours from router traffic, or a client's
   file). No public benchmark. The example task's labels `class_0` / `class_1` carry no
   definitions, so the first real run replaces `forge/task.yaml` labels with real ones first;
   the teacher marks undefined classes unsure by design (proved 2026-09-06 on two rows: one
   labelled, one unsure).
2. Teacher: `forge/generate_teacher_dataset.py` through the router's default lane, structured
   output, one label plus a reason per row, `--batch` for the full set.
3. Persistence, all three before training: Langfuse datasets `<task>` and `<task>-unsure`,
   `forge/datasets/<task>.jsonl` in git, and `dataset.jsonl` plus its sha256 inside the model
   artifact.
4. Size: 500 rows minimum; 1000 preferred, because 100 held-out rows resolve the 0.95 gate only
   to about ±4 points.

## Procedure

```
# label
uv run --with anthropic --with pyyaml --with 'langfuse<3' forge/generate_teacher_dataset.py \
    --task forge/task.yaml --input raw.jsonl --output forge/datasets/example-classify.jsonl --batch
# commit the dataset, then a dry run first (gates graded, nothing pushed)
gh workflow run forge-train.yml -f task_file=forge/task.yaml -f dry_run=true
# a real run
gh workflow run forge-train.yml -f task_file=forge/task.yaml -f dry_run=false
```

## What we do with each outcome

- **Shipped**: record filed, GGUF on GHCR, Runtime rollout is the next experiment (latency and
  abstain rate on live traffic against the same gates).
- **Refused on agreement**: round two. Take the rows the student was least sure about
  (margin-sampled), have the teacher label those, retrain. Do not lower the gate.
- **Refused on abstain rate**: the task is under-specified or the base is too small. Check the
  unsure set first, then the label definitions, then the base, in that order.

## Cost

Recorded in the run record (`train wall time` on a T4), never estimated here.
