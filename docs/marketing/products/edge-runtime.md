# Edge Runtime

> A memory-safe Rust service on cheap hardware — loads a GGUF, answers
> one task, abstains when it should, and falls back to the router when
> it must.

## The problem

You trained a tiny model. You have an OCI artifact. You need to deploy
it on hardware that does not cost a GPU-hour, serve it to a thousand
calls a day, and answer "I don't know" when the task drifts outside the
training distribution. The frontier fallback is on the LLM gateway;
the small model is on your hardware.

You could write the serving code. You could stand up a vLLM cluster. You
could ship a llama.cpp binary and a systemd unit. Or you could ship the
Edge Runtime, which is purpose-built for the Forge's artifact format
and exposes an OpenAI-compatible endpoint with an abstain signal.

## What you get

- **A Rust binary, statically linked.** The Edge Runtime is a single
  binary that loads a GGUF, runs the inference, and answers. No GC, no
  runtime, no Python. *Benefit: the binary fits in a container that
  fits on an ARM64 node.*

- **OpenAI-compatible endpoint.** `/v1/chat/completions` is the wire.
  The buyer does not change a client to use it; they change a URL.
  *Benefit: a buyer can swap a frontier call for a local call without
  rewriting a line of code.*

- **An abstain signal.** When the model is below confidence, the Edge
  Runtime returns a special token. The LLM gateway's `abstain_below`
  flag routes the call to the frontier model. *Benefit: a low-confidence
  answer is a fallback, not a hallucination.*

- **OCI artifact pull.** The Edge Runtime reads the model card, pulls
  the GGUF, and validates the hash. The registry is the source of
  truth; the binary is the renderer. *Benefit: a model update is a
  registry update, not a deploy.*

- **ARM64 native.** The image pipeline already builds `linux/arm64`. The
  Edge Runtime reuses it; an Oracle A1 node (4 CPU, 16 GB) is the
  standing target. *Benefit: the hardware is cheap; the inference is
  cents per hour.*

- **Single-task inferences.** The Edge Runtime is purpose-built for the
  Forge's artifact format: one task, one prompt template, one output.
  No agentic loops; no chat history; no tool calls. *Benefit: the
  binary is small, the latency is bounded, the cost is predictable.*

## How it works

The Edge Runtime is a Rust service. It reads a model card from an OCI
artifact, loads the GGUF into memory, and serves it on an
OpenAI-compatible endpoint. The endpoint is one task per model — the
model card names the task, the prompt template, the labels, and the
abstain threshold.

The LLM gateway sits in front. When a call comes in for the task, the
gateway routes it to the Edge Runtime. When the Edge Runtime returns an
abstain signal, the gateway falls back to the frontier model. The
buyer's client never sees the abstention; the gateway hides it.

The binary is on the same plane as the rest of the platform — same
identity, same secrets, same audit log. There is no second runtime.

## Why us

- **Purpose-built for the Forge's artifact format.** Ollama and
  llama.cpp are general-purpose; the Edge Runtime is one task, one
  model, one binary. *Benefit: the binary is small, the latency is
  bounded, the cost is predictable.*

- **The abstain signal is the contract.** Most small-model serving
  stacks do not have one. The Edge Runtime does. *Benefit: a buyer
  does not have to write the gate.*

- **ARM64 native, cheap hardware.** An Oracle A1 node is the standing
  target. *Benefit: the inference is cents per hour, not dollars per
  GPU-hour.*

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $30/month, up to 1 model | One tenant, one model, the OpenAI endpoint, the abstain signal |
| Team | $300/month, up to 5 models | Multi-tenant, multi-model, the LLM gateway integration, the audit log |
| Enterprise | Contact us | Unlimited models, custom bases, dedicated support, on-prem |

The Enterprise tier is required for any deployment with regulated
workloads.

## Get started

- **Run the install wedge.** `idp/quickstart` brings up the Edge
  Runtime with one sample task in 30 minutes. The drill runs hourly.
- **Read the spec.** `docs/specs/2026-09-06-model-forge-edge-runtime.md`
  is the canonical design. Section 3 is the artifact contract.
- **See it in action.** The estate's CI flake triage task is the first
  Forge + Edge Runtime deployment. The trace is in the collector.
- **Call us.** For the Enterprise tier, for a custom base, or for a
  procurement-grade security one-pager.

The Edge Runtime is the renderer. The Forge is the writer. The
registry is the source of truth.
