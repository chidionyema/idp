# DSPy: where it fits in the estate (characterization, not an adoption)

Status: tracked founder request, characterized 2026-09-08. NOT adopted. No code changed.
Founder asked (verbatim intent): "ensure all agents use DSPy ... turns prompt engineering into
rigorous software engineering ... even telegram agents". After scoping, the founder selected:
DSPy for **one-shot classify/extract** tasks only, and scope = **characterize + write up as a
tracked request**.

## Why the blanket mandate is not adopted

The request rests on a mis-map of the estate.

1. **Agentic tool loops are not DSPy's home.** DSPy compiles a *single-shot / few-shot text
   prompt* against a labeled dataset and a metric. The live agents (otto, sovereign intake,
   consensus, council) are multi-turn tool-calling loops with an FSM
   (`init -> planning -> tool_use -> synthesis -> terminal`), multi-model quorum votes, and
   budget caps. There is no dense per-turn metric to compile against, and auto-rewriting prompts
   in a regime that pins prompts behind measured-cost routing, spend caps and empirical-proof
   change control (Laws 2, 15, 21, 29) would fight the architecture, not help it.

2. **Telegram is not an agent.** In this estate Telegram is the outbound alert / mirror channel
   (`platform/otto-gateway/telegram-mirror.yaml`, JIT broker `telegram.py`). The decisions are
   made *in* by otto / sovereign agents through the LiteLLM proxy; Telegram only carries them
   out. There is no "telegram agent" to convert.

3. **No DSPy footprint exists anywhere** in the tree. This is greenfield, not a repair: no Rule 1
   fire is lit, and nothing was broken that a framework mandate would fix.

## Where DSPy genuinely fits (single-shot, structured, metric-scorable)

Two seams already match DSPy's exact home turf — one system prompt, one call, strict structured
output, and a **deterministic native metric**, all injected through a callable seam and already
routed through the LiteLLM proxy (so a compiled module would respect budget, tracing and routing
rather than bypass them).

1. **Photo intake extraction** — `sovereign/intake/vision.py` and `pipeline.py` (spec 2.3).
   Single system prompt -> one call -> strict JSON `{markdown, slug, tags, title}`. The metric
   already exists: `parse()`'s `ExtractionError` on any shape deviation and slug sanitation.
   Soak it against real ingested photos; keep the `VisionCall` seam and the LiteLLM backend.

2. **Consensus vote** — `sovereign/consensus/models.py` (cp30, spec 4.2). One prompt fanned to
   N models, each returning a single normalized tool call; agreement decided by quorum on the
   normalized-equal proposal. The metric is quorum agreement. DSPy could compile the proposal
   prompt so N models converge on a canonical call more often — fewer re-quorum/retry cycles.

## Recommended next step (not started)

A **bounded pilot on exactly one of the two seams** — photo-intake extraction is the cleaner
target because its metric is strict and offline, and the forge/ dataset tooling
(`forge/generate_teacher_dataset.py`, `forge/train.py`) already exists to build the labeled
soak. Prove the compiled prompt beats the current static prompt on a measured metric over real
data before anything wider. Do not touch the agent loops or the routing layer.

## Why Telegram / agent loops are excluded from any pilot

Same reason the mandate is not adopted: those are not single-shot metric-scorable prompts, so a
DSPy compile there cannot be measured and would only obscure the pinned-prompt, budget-capped,
Langfuse-traced controls the estate already runs on judgment.

## The value DSPy advertises is already delivered by the Forge (added 2026-09-08)

DSPy's pitch - "define the desired outputs, it automatically compiles, tests and optimises" - is
not absent from the estate. `forge/` already runs the exact discipline: every run is an experiment
with a recorded file (`forge/experiment_record.py`), pre-registered hypothesis and gates read from
the same task file the trainer read (`forge/experiments/*-plan.md`), labels that are recorded
outcomes a teacher cannot argue with (`forge/collect_ci_runs.py`), a hard `cost_gate` refusing any
run over its `budget_usd` (`forge/common.py`, founder 2026-09-06), dataset-hash provenance and
exact unlearning by re-running on a smaller JSONL. Criterion by criterion this is the "prompt
engineering becomes rigorous software engineering" the founder asked for - already in place, with
LoRA fine-tunes on small models (Qwen2.5-1.5B, T4, ~$1/run) as the optimiser instead of a frontier
prompt-compiler.

Why the one live classify task is not a DSPy target (crew#885, `forge/tasks/ci-flake-triage.yaml`):
the task's own plain-English goal is that the estate "stops paying a frontier call" for answered red
CI runs. A DSPy compile on top spends frontier calls during compilation - the exact cost the
small-model LoRA lane was chosen to eliminate. DSPy is therefore the wrong optimiser for this
task's stated economics, and the fork is owned by a live crew line.

**Standing recommendation (changed 2026-09-09):** no agent-loop, routing, or live-task change. Any DSPy
adoption should be a bounded experiment against a *new* one-shot estate task that has no cheaper
lane already chosen - so a DSPy result is the first answer, not a challenger to a cheaper one that
already won on economics.

## 2026-09-09 move: make the Forge actually run (the gate for any DSPy work)

Because a DSPy experiment can only be *measured* by the Forge's gated record loop, the founder
directed the Forge be made fully operational first (active goal this session). Findings:

- The Forge's only training run (2026-09-06, run 34056121643) never trained: the launcher died at
  `ModuleNotFoundError: No module named 'common'` in `/root/modal_app.py` (Modal stages the entrypoint
  at `/root` while `add_local_dir` copies the forge dir to `/root/forge`), then the CI job spun to the
  90-minute ceiling. Root cause read from the live run log. Fixed in `forge/modal_app.py` (append both
  module dir and `REMOTE` to `sys.path`), guarded both-ways in `forge/tests/test_forge.py` (16 forge
  tests green). Recorded in `docs/reference/forge/2026-09-09-forge-launcher-common-import-defect.md`.
- Collection is real (799 outcome-labelled ci-flake rows, 639/160 split). Training is NOT yet proven
  end-to-end.
- Founder approved a second GPU road: Kaggle free GPUs (spec line 256, LAW 34). Spec at
  `docs/specs/2026-09-09-forge-kaggle-second-launcher.md`; the build is COMPLETE at the code level
  (20 forge+kaggle tests green): `forge/kaggle_app.py` (plan gate + real kaggle push/poll/pull, shared
  common.cost_gate, never fabricates eval), the committed `forge/kaggle/notebook.ipynb` (runs the
  unchanged forge/train.py via a git clone of the pinned repo), and `.github/workflows/forge-train-kaggle.yml`
  (files the record through the unchanged forge/experiment_record.py). An earlier delegated Builder
  output that hardcoded a fake 0.96 agreement was rejected and removed (Empirical Proof Rule).
  Both the Modal path and the Kaggle path still need one real dispatch (Modal root / KAGGLE root + a
  fired run) to file the first graded record.

Until `forge/experiments/<stamp>-ci-flake-triage.md` exists from a real GPU run, the Forge is
wired-but-not-fired, and the standing DSPy recommendation stays unpiloted.

**Standing recommendation (unchanged, not started):** no agent-loop, routing, or live-task change.
Any DSPy adoption should be a bounded experiment against a *new* one-shot estate task that has no
cheaper lane already chosen - so a DSPy result is the first answer, not a challenger to a cheaper
one that already won on economics.
