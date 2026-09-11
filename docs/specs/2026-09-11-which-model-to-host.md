# Which model to host, and why the biggest one is not the answer

2026-09-11. **Read this before proposing a model for the estate.** It exists because two sessions
spent hours arguing about model size when the constraint was arithmetic and the decision was already
half-measured.

## The constraint, in exact numbers

| | |
|---|---|
| **One OCI node, allocatable** | **19 GiB** (VM.Standard.A1.Flex, ARM, **no GPU**) |
| **Nodes owned** | 2, both at **99% and 91% reserved** |
| **CPU inference speed** | **~6–10 tokens/s** for a 30B class model |
| **Cost** | £0 forever, on hardware already paid for |

No GPU anywhere in this estate. That is not a limitation to work around; it is the ground.

## The best models we could host

| Model | RAM (Q4_K_M) | Quality | Fits today? |
|---|---|---|---|
| **DeepSeek-R1-Distill-Qwen-32B** | **~19 GB** | 94.3% MATH-500, 72.6% AIME 2024, MIT, beats o1-mini on several reasoning benchmarks | **only on a node with nothing else on it** |
| **Qwen3-30B-A3B (MoE)** | ~17–20 GB | strong | yes, with the trap below |
| **DeepSeek-R1-Distill-Qwen-14B** | **~9 GB** | 93.9% MATH-500, 69.7 AIME24 | **yes, today, with room for KV cache** |
| **Qwen3 1.5B + a task LoRA** | **~1.1 GB** | **97.7% on a real binary task — measured in this estate** | yes, trivially |

### The MoE trap, stated because it gets proposed

**`Qwen3-30B-A3B` does not use 3B of RAM because it activates 3B.** All 30B weights must be
resident; only the routing is sparse. "A3B" describes compute per token, not memory. Anyone
proposing it to save RAM has the wrong number.

## The decision, and it is not "the biggest one"

**A 32B is the ceiling of this hardware. A 14B is what fits alongside the estate. A 1.5B expert
beats both on the work it was trained for — 97.7%, measured.**

So the architecture is three tiers, and the tier is chosen by the DECISION, not by ambition:

| Tier | Model | RAM | What it is for |
|---|---|---|---|
| **Expert** | Qwen3 1.5B + LoRA | ~1.1 GB | one narrow question, answered or abstained. **The default.** |
| **Resident brain** | DeepSeek-R1-Distill-Qwen-14B | ~9 GB | reasoning that is not one narrow question |
| **Heavy** | DeepSeek-R1-Distill-Qwen-32B | ~19 GB | the hard calls, **on a dedicated node**, loaded on demand |

**The rule: start at the expert tier and go up only when the expert abstains.** That is not an
optimisation — it is the same abstain signal `platform/edge-runtime` already computes, and it is what
makes the whole thing affordable in the only currency that matters here, which is RAM on two nodes.

## What was measured in this estate, not quoted from a leaderboard

```
binary expert (2 labels)  : 97.7% agreement, 17.5% abstain   PASSES
7-way expert  (7 labels)  : 100% agreement, 93.6% abstain    REFUSED
```

**Both are in `forge/experiments/`.** The second refused because a model that is never wrong because
it almost never speaks is not useful — and the lesson is that **an expert must be narrow.** Seven
lanes in one head is a generalist, and a 1.5B cannot be one.

**Prefer many binary experts to one multi-class expert.** The narrow shape is the measured one.

## How to get any of these

**A model is a download, not a purchase.** `platform/edge-runtime` loads one GGUF per process on
ARM64 via candle. There is nothing to buy and nothing to negotiate:

1. Get an artifact — `platform/model-forge` trains it, or pull a GGUF from Hugging Face.
2. Put it where the pod can read it (the artifact volume, or an `oras` pull by digest).
3. Deploy it. `/v1/health` proves it.

**No ClickHouse need be destroyed for any tier above.** The expert tier fits in memory that is
already free; the 14B needs ~9 GB freed, and 7.2 GB of measurable waste exists across 174
containers (`hermes-agent-gateway` reserves 1088 Mi and uses **57 Mi**).

**The 32B is the only one that needs a node to itself, and that is a real cost — say so rather than
quietly displacing a service.**

## What this decision replaces

Two arguments that keep recurring, both answered here:

- **"We need a 70B to replace the frontier lane."** No: a 1.5B expert measured 97.7% on a real
  estate task, and 70B does not fit any node in this estate at any quantisation.
- **"Smaller models rival GPT-4 for architecture."** They do not. **An expert answers the question it
  was trained on; it does not notice that the question was wrong.** The paid lane is the seat that
  notices, and nothing in this estate's hardware replaces it.

## The one-line summary for any agent reading this

> **Choose the tier by the decision, not by ambition: expert (1.1 GB) by default, 14B (~9 GB) when
> the expert abstains, 32B (~19 GB) only on a dedicated node. A binary expert beats a multi-class
> one. A model is a download, not a purchase.**
