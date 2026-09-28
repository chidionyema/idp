# Forge second GPU launcher: Kaggle (spec, 2026-09-09)

Status: spec for a delegated build. Founder asked to add "Kaggle infra" as the free second road
to a GPU, sanctioned by `docs/specs/2026-09-06-model-forge-edge-runtime.md` line 63-64 and 256:
"forge/train.py is a plain script that runs on any CUDA box. forge/modal_app.py is only the
launcher. A second launcher (Kaggle, a rented box) is a file, not a rewrite." And line 256 names
Kaggle explicitly as the fallback above Modal's free tier: 30 GPU hours a week, about 120 runs a
month, zero cost.

## Contract the launcher must honor (identical to `forge/modal_app.py`)

The point of a second launcher is that everything downstream of the GPU run is unchanged. A
Kaggle run must produce the same artifacts `modal_app.run_forge` produces, so
`forge/experiment_record.py` and `forge-train.yml`'s record/PR steps are NOT rewritten:

1. **Inputs** `(task, task_file, data_jsonl, dry_run, max_steps)`.
2. **Pre-launch cost gate**: run the same `cost_gate(task)` from `forge/common.py`. A GPU that has
   no price in the Kaggle-aware budget table, or a worst-case bill over `budget_usd`, is refused
   BEFORE any Kaggle session starts, and the refusal is returned as a `verdict: refused` record
   identical in shape to Modal's refusal. Nothing may bill for a refused run.
3. **Run** `forge/train.py` on the remote GPU exactly as Modal does:
   `python train.py --task <task_file> --data <dataset.jsonl> --max-steps N`. `train.py` is BYTE
   UNCHANGED (LAW 34 portable core; it must stay a plain script runnable on any CUDA box).
4. **Return** a JSON record with the keys `modal_app.run_forge` returns when reachable:
   `task, task_file, dry_run, max_steps, gpu, seconds, usd, budget_usd, trace, artifact,
   eval{held_out, agreement, abstain_rate, dataset{rows, train, eval, sha256,...}}, verdict`.
   For a Kaggle **dry-run**, `artifact` is null and `verdict` is `dry-run`. For a **shipped** run
   the record also has the GHCR `artifact` ref — but shipping is a LATER milestone; v1 ships the
   dry-run path only (the graded-record proof), because the goal needs a `dry-run` graded record
   and GHCR push from inside a Kaggle notebook adds `oras` auth in a foreign sandbox.
5. **Refusal / failure** must still leave a record the workflow can file (a run that dies silently
   is the 2026-09-06 failure mode we are not repeating).

## Kaggle facts the launcher is built on (verified 2026-09-09)

- Fire a notebook non-interactively: `kaggle kernels push -p <dir>` where `<dir>` holds
  `kernel-metadata.json` + the `.ipynb` + any local data to bundle.
- Poll with `kaggle kernels status <slug>` (returns running/complete/error) or the API.
- Set the GPU via `kernel-metadata.json` `enable_gpu: true` and `accelerator: nvidiaT4/nvidiaP100`
  (the Launcher should read the accelerator from the task's `compute.gpu` block and map T4->nvidiaT4,
  P100->nvidiaP100; an unmappable GPU is a pre-launch refusal, not an attempt).
- `train.py` writes `eval.json` under the notebook CWD (`/kaggle/working`); fetch it back with
  `kaggle kernels output <slug> -p <dir>`; read `<dir>/eval.json`.
- The dataset JSONL must reach `/kaggle/working/dataset.jsonl` (mount via a Kaggle Dataset at
  `/kaggle/input`, or bundle into the pushed folder and copy). The launcher passes `--data
  dataset.jsonl` relative to the notebook CWD.
- Free tier: P100/T4, 30 GPU-hours/week. Fast internet, so the base-model download per run is
  accepted for v1 (no warm volume on Kaggle) — note this in the record's `seconds`.

## File scope (what the Builder may create)

- `forge/kaggle_app.py` — the CLI launcher: `kaggle_app.py --task <task_file> --data <file.jsonl>
  --max-steps N [--dry-run] [--record forge-run.json]`, mirroring `modal_app.py main()`'s inputs &
  record-write, calling `cost_gate` from `forge/common.py` (import it the SAME robust way the
  Modal fix enforces — via a local dir/`sys.path` append — because Kaggle CLI context may also
  stage it away from `common.py`; do not reintroduce the 2026-09-06 import bug).
- `forge/kaggle/kernel-metadata.json` template + a generated notebook (`.ipynb`) that: installs
  `unsloth langfuse pyyaml datasets`, accepts the task/data via env or embedded args,
  runs `subprocess.run(["python","train.py","--task",...])`, and relies on cwd=/kaggle/working.
- A `forge/tests/test_kaggle_app.py` guard (see FAILING test below).
- A `forge-train-kaggle.yml` workflow mirroring `forge-train.yml`'s record/PR tail, reading
  `KAGGLE_USERNAME`/`KAGGLE_KEY` from repo secrets, that: pushes the kernel, polls to completion,
  pulls `eval.json`, and files the record through the UNCHANGED `forge/experiment_record.py`.

## Not in scope for v1 (state explicitly)

- GHCR artifact push from inside Kaggle (ship milestone) — dry-run graded record only.
- Langfuse trace wiring from inside Kaggle (record `trace: null`; acceptable for the graded-record
  proof).
- Editing `forge/train.py`, `forge/common.py`, `forge/experiment_record.py`, or the Modal path.

## FAILING test that defines done (Builder must make it pass; it must NOT require Kaggle creds)

`forge/tests/test_kaggle_app.py`:
1. `test_kaggle_app_reuses_the_same_common_import_guard` — structural: `kaggle_app.py` must add
   both its own module dir and (if it stages a remote copy) that remote to `sys.path` before
   importing `common`, mirroring the Modal guard. Assert via AST (R76), exactly the pattern in
   `test_modal_app_imports_common_after_module_reads_both_dirs`.
2. `test_kaggle_refuses_unmappable_gpu_before_any_session` — calling the launcher's planning fn
   with a task `compute.gpu` that maps to no Kaggle accelerator returns a `verdict: refused`
   record with a refusal message, and does NOT touch the network (pure local).
3. `test_kaggle_cost_gate_agrees_with_common` — the Kaggle launcher's refusal logic must be the
   SAME `cost_gate` from `forge/common.py` (no second, driftable copy): assert the launcher calls
   the imported common.cost_gate, and that for the shipped `forge/tasks/ci-flake-triage.yaml` it
   returns None (task fits its own budget) exactly as the Modal path decides.
4. `test_kaggle_record_shape_compatible_with_experiment_record` — feed a canned Kaggle dry-run
   record (eval + dataset metadata shaped as above) through the REAL `forge/experiment_record.py`
   renderer and assert it produces a valid `<stamp>-ci-flake-triage.md` with front matter and the
   gate rows — proving the SECOND launcher feeds the SAME record loop unchanged.

## Verify command (must exit 0; SQL-free; local-only, no Kaggle token needed)

`cd /Users/chidionyema/dev/code/idp && python3 -m pytest forge/tests/test_forge.py forge/tests/test_kaggle_app.py -o addopts="" -p no:cacheprovider -q`

## Live proof (founder-gated, NOT part of this build's verify)

After the build is green, the founder mints `KAGGLE_USERNAME`/`KAGGLE_KEY` (R52 root) into repo
secrets, then one real `forge-train-kaggle.yml` dispatch on `forge/tasks/ci-flake-triage.yaml`
must return a graded record under `forge/experiments/`. That is the Empirical-Proof-rule end-state;
a Builder cannot and must not fake it with synthetic output.
