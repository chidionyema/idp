# Forge experiments

Every Forge run is an experiment and leaves a record here, named `<UTC stamp>-<task>.md`. Refused
runs and dry runs leave one too. A run with no record did not happen. Records are written by
`forge/experiment_record.py` from the run's `forge-run.json` (what `forge/modal_app.py` returns) and
filed on a pull request by `.github/workflows/forge-train.yml`; nobody writes one by hand except a
pre-registration (below).

Each record has a YAML front matter (verdict, agreement, abstain rate, dataset hash, trace,
artifact, commit) so the folder can be graded by a script, then an **In plain English** paragraph
(what the model does and what happened, for a reader who is not an engineer; a task sets its own
sentence with `plain_english:`), then seven sections for engineers:

1. **Hypothesis**: what the student is expected to reach, stated before the run. Set `hypothesis:`
   in the task YAML to override the default sentence.
2. **Setup**: base model, LoRA shape, steps, GPU, wall time, forge commit, CI run.
3. **Data**: rows, split, sha256, per-label counts, teacher(s), the Langfuse dataset name.
4. **Pre-registered gates**: the numbers from the task YAML the run was graded against. They are
   read from the same file the trainer read; a record cannot quote a threshold the run did not use.
5. **Results**: held-out agreement and abstain rate, whether each gate was met, and what the
   held-out count can actually resolve.
6. **Provenance**: trace, artifact reference, dataset hash, commit, run.
7. **Reproduce**: the three commands, with this run's arguments.

**What a task may try.** Anything. `kind`, `base`, model size and GPU are the task file's choice;
the Forge refuses a run before launch on one ground only, the `compute.budget_usd` in the task
file against the worst case the GPU and `timeout_s` could bill (`forge/common.py` `cost_gate`,
founder 2026-09-06). Every record carries the actual `usd` next to the budget.

**Forgetting.** A model is its hashed dataset plus one recorded run. To remove a client's rows,
delete them from the JSONL, run again, publish the new artifact; the old one is retired by tag.
That is exact unlearning, at the cost of one run, and the two records prove the rows are gone.

**Pre-registration.** Before the first run of a task, a `NNNN-<task>-plan.md` states hypothesis,
data plan and gates, in both registers: an "In plain English" section and a "For engineers" section.
The run's record then sits next to it; the plan is never edited after the run.

**Where they are read.** Every file here is copied into the portal at each docs build
(`bin/mkdocs_hooks/forge_experiments.py`, TechDocs page "Own models, every experiment", with an
index that puts the plain English sentence first). Founder, 2026-09-06: all of it in Backstage.

**Where labels come from.** A teacher model (`forge/generate_teacher_dataset.py`), a gold set, or a
recorded outcome the estate already had, such as whether a red CI run later went green on the same
commit (`forge/collect_ci_runs.py`). An outcome label costs nothing and cannot be argued with.

**Reading a result.** 100 held-out rows resolve agreement to roughly ±4 points at 95%. A reading
inside that band of the gate is not settled either way: label more rows (the second round is
student-margin sampled; spec §5) before trusting it.
