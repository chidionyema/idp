# Private Inference Stack

> The bundle for any company that wants narrow-task inference on their
> hardware, with the frontier model as the fallback — examples in,
> distilled model out, abstain signal on the router.

## The story the buyer tells their board

> "We pay frontier rates for judgment, cents per hour for narrow
> classification, and we hold the artifacts. The router decides which
> call goes where. The auditor gets one log file."

That is the Private Inference Stack. Four products, one bundle, one
story.

## What you get

The Private Inference Stack is the Model Forge + Edge Runtime + LLM
Gateway + spend-bounded LiteLLM, configured as a single deployment.
Every component is a product on its own; together, they are the
answer a buyer's platform team wants to hear when the model bill is
on the agenda.

| Component | What it does | Why it is in the bundle |
|---|---|---|
| **Model Forge** | A tiny-model factory for narrow tasks | Examples in, distilled model out, eval gate refuses to ship a regression |
| **Edge Runtime** | A Rust service on cheap hardware that loads a GGUF and answers one task | The artifact is rendered; the abstain signal is on the wire |
| **LLM Gateway** | A model router with per-lane budgets and a spend breaker | The router decides which call goes where; the fallback is the frontier model |

## What the buyer sees

- **One task schema.** A task is a YAML file. The schema names the base,
  the prompt template, the labels, the abstain threshold, the eval
  gate. *Benefit: a task is a file, not a meeting.*

- **One registry.** The OCI artifact lands in the buyer's GHCR, alongside
  every image. *Benefit: the registry is the registry; one place to
  govern.*

- **One router.** The router decides which call goes where. The
  Edge Runtime is the local lane; the frontier model is the fallback.
  *Benefit: the buyer does not pick a model per call; the router picks
  per call.*

- **One abstain signal.** Below confidence, the Edge Runtime returns
  the abstain token. The router routes to the frontier. *Benefit: a
  low-confidence answer is a fallback, not a hallucination.*

- **One trace.** Every call — local or frontier — lands in the
  collector. *Benefit: the auditor gets one log file.*

## How it works

The buyer writes `task.yaml`. The buyer collects a dataset. The buyer
pushes. The Forge trains a LoRA, evaluates on the held-out set, and
either pushes the OCI artifact or refuses with a reason.

The Edge Runtime picks up the artifact. The LLM gateway routes calls
to the Edge Runtime when the task matches; to the frontier model when
it does not (or when the Edge Runtime returns the abstain token). The
buyer's client never sees the abstention; the router hides it.

The drill runs hourly. The drill proves the eval gate is the eval
gate; a gate that could not run is a fail-closed FAIL, never a pass.

## Why us

- **The eval gate is the product.** The Forge refuses to ship a
  regression. *Benefit: a buyer does not have to write the gate; the
  gate is shipped.*

- **The abstain signal is the contract.** The Edge Runtime exposes an
  OpenAI-compatible endpoint with an abstain signal. *Benefit: a buyer
  does not have to write the fallback; the fallback is on the router.*

- **The trace is yours.** Every call lands in the buyer's collector.
  *Benefit: a vendor change is a router change, not a trace change.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $200/month, up to 5 tasks | One tenant, the Forge, the Edge Runtime, the router, the abstain signal |
| Team | $2,000/month, up to 25 tasks | Multi-tenant, the trace, Slack alerts, the drill |
| Enterprise | Contact us | Unlimited tasks, custom bases, SOC 2 conversation, dedicated support |

Compute is in addition to the platform fee; the platform fee covers
the Forge, the Edge Runtime, the router, and the trace.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the bundle with
  one example task in 30 minutes. The drill runs hourly.
- **Read the spec.** `docs/specs/2026-09-06-model-forge-edge-runtime.md`
  is the canonical design.
- **See it in action.** The estate runs the bundle; CI flake triage
  is the first task; the trace is in the collector.
- **Call us.** For the Enterprise tier, for a custom base, or for a
  procurement-grade security one-pager.

The Private Inference Stack is the bundle. The frontier is for
judgment. The Forge is for repetition.
