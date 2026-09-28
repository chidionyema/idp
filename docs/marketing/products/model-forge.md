# Model Forge

> A tiny-model factory for narrow tasks — examples in, distilled model
> out, with an evaluation gate that refuses to ship a regression.

## The problem

You have a narrow task. It runs a thousand times a day. The frontier
model handles it well, but every call costs you. After a year, the bill
is a number the CFO wants to talk about.

You could fine-tune a small model. You could stand up a training
pipeline, pick a base, write the LoRA, evaluate the held-out set,
package the artifact, deploy it, monitor it, and roll back when the
quality drifts. You could do all of that. The cost is a quarter of an
engineer for a year.

Model Forge is that pipeline, packaged. You bring the examples; the
Forge brings the launcher, the trainer, the evaluation gate, the
artifact format, and the deployment. The Forge refuses to ship a
regression: the held-out agreement with the teacher labels must meet
the floor you set, or nothing ships.

## What you get

- **A task schema.** A YAML file that names the task, the base model,
  the prompt template, the labels, the abstain threshold, the held-out
  agreement floor, the compute budget. *Benefit: a task is a file, not
  a meeting.*

- **A launcher.** Modal brings the ephemeral GPU; per-second billing,
  scale to zero, zero standing cost. *Benefit: the compute is a row in
  the budget, not a line item.*

- **A trainer.** Unsloth LoRA on Qwen3 0.6B and 1.7B; one library does
  train, merge, and export. GGUF `q4_k_m` output. *Benefit: the
  artifact is a file, not a service.*

- **A evaluation gate.** Held-out eval over the teacher labels; a
  threshold you set in `task.yaml`; a refusal to ship below threshold.
  *Benefit: a regression cannot ship.*

- **An OCI artifact.** The model lands in your GHCR as an OCI artifact,
  alongside every image. *Benefit: the registry is the registry; one
  place to govern.*

- **A trace.** Every run lands in Langfuse with the eval table.
  *Benefit: a run is a receipt, not a rumor.*

- **An abstain signal.** The Edge Runtime exposes an OpenAI-compatible
  endpoint with an abstain signal; below confidence, the call falls
  back to the frontier model. *Benefit: a low-confidence answer is a
  fallback, not a hallucination.*

- **Provider-agnostic.** `forge/train.py` runs on any CUDA box. The
  Modal launcher is a separate file; a Kaggle launcher is a separate
  file. *Benefit: the launcher is the buyer's choice.*

## How it works

You write `task.yaml`. You collect a dataset (the Forge ships a
collector for outcome-labeled data — a run is a flake if the same
commit later went green with nothing changed; the label costs nothing).
You push. The Forge launches a Modal job, trains a LoRA, evaluates on
the held-out set, and either pushes the OCI artifact or refuses with a
reason. The Edge Runtime picks it up; the LLM gateway's `abstain_below`
flag routes low-confidence calls to the frontier model.

The first task shipped on the estate is `ci-flake-triage`: a 1.5B model
reads the end of a failed GitHub Actions run's log and says "flake" or
"real," abstains below 0.80 confidence, and pays cents per run on Modal
instead of dollars per call on the router.

## Why us

- **The eval gate is the product.** Modal and Unsloth are tools;
  anyone can stand up a training pipeline. The Forge's product is the
  refusal to ship a regression. *Benefit: a buyer does not have to
  write the gate; the gate is shipped.*

- **The abstain signal is the contract.** A small model that abstains
  on hard cases is more useful than a small model that hallucinates.
  *Benefit: the buyer's accuracy does not drop when the task drifts.*

- **The trace is in your collector.** Every run lands in Langfuse; the
  eval table is a row in the trace. *Benefit: a run is a receipt, not
  a rumor.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $50/month, up to 5 tasks | One tenant, the launcher, the eval gate, the OCI artifact |
| Team | $500/month, up to 25 tasks | Multi-tenant, the abstain signal, the trace, the Edge Runtime |
| Enterprise | Contact us | Unlimited tasks, custom bases, dedicated support, on-prem |

Compute is in addition to the platform fee; the platform fee covers
the launcher, the trainer, the eval gate, the artifact, the trace, and
the deployment.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Forge with
  one example task in 30 minutes. The drill runs hourly.
- **Read the spec.** `docs/specs/2026-09-06-model-forge-edge-runtime.md`
  is the canonical design.
- **See it in action.** The estate's CI flake triage task is a real
  Forge run. The trace is in the collector.
- **Call us.** For the Enterprise tier, for a custom base, or for a
  procurement-grade security one-pager.

The Forge is the tiny-model factory. Examples in, eval gate, OCI
artifact, abstain signal. The frontier model is for judgment; the
Forge is for repetition.
