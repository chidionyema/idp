# Asymmetric compute leverage — research record

Date: 2026-09-15, revised same day after a direct gap audit against the source material
(the founder's own buffet: two blog posts plus two personal emails, `chidionyema@gmail.com`,
2026-09-14, pasted in full this session). Every claim below carries a source. A claim taken
from the buffet itself (not independently checked by me) is marked **founder-supplied,
unverified** — a weaker receipt than an arXiv/vendor citation, and stated as such, not hidden
among the stronger ones. Nothing here is a build recommendation; it is the evidence one would
rest on.

The first version of this file covered 5 of roughly 14 distinct items in the buffet. This
revision closes the gaps found on audit — it does not just note them.

## 1. JIT / point-of-use compute — verified, with a real floor

Claim: a rented Apple Silicon node can be billed only while running, not as a standing monthly
lease — "point of use" instead of "24 hours standing."

- Verified true, with a real constraint: Scaleway's Apple silicon-as-a-Service bills €0.17/hr
  (Mac mini M2) or €0.21/hr (M2 Pro) on demand, and "billing pauses if you power off the
  instance and resumes when you power it on"
  ([Scaleway Apple silicon concepts](https://www.scaleway.com/en/docs/apple-silicon/concepts/)).
- The floor: "due to license constraints, the minimum lease for Apple silicon-as-a-Service is
  24 hours" — a Mac mini can only be released after that minimum allocation
  ([same source](https://www.scaleway.com/en/docs/apple-silicon/concepts/)).
- Same constraint independently confirmed on AWS: EC2 Mac instances bill per second but carry a
  mandatory 24-hour minimum Dedicated Host allocation "to comply with the Apple macOS Software
  License Agreement"; billing continues even if the instance itself is stopped, until the host
  is released
  ([AWS EC2 Mac instances docs](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-mac-instances.html)).
- Reading: this is an Apple licensing term, not a vendor policy choice — it applies to every
  Apple-Silicon-as-a-service vendor, not just the two checked. True point-of-use billing (no
  minimum floor at all) exists for GPU rental (Vast.ai-class), not for rented Apple Silicon.
  The two are not interchangeable on this axis.
- **Not yet reconciled**: the buffet's own email separately quotes flat *monthly* Mac Mini
  rental — Hetzner ~€64/mo (£54/mo) and Scaleway ~€80/mo (£68/mo), both for a 32GB M2 Pro
  (**founder-supplied, unverified**) — against Scaleway's own *hourly* Apple-silicon-as-a-
  Service product above. These may be two different product lines from the same vendor
  (dedicated monthly lease vs. metered-hourly-as-a-Service) rather than the same offer priced
  two ways; that distinction has not been checked against Scaleway's own product pages and
  should be before any cost model treats them as substitutes.

## 2. Small / efficient models beating much larger ones — current findings

Ranked by source strength (paper/vendor-docs first, buffet-supplied figures flagged as such).

**Strong sources (arXiv / vendor):**

- **SGS — Self-Guided Self-Play** (Stanford, [arXiv:2604.20209](https://arxiv.org/pdf/2604.20209),
  Apr 2026): applied to DeepSeek-Prover-V2-7B, after 200 rounds / 6.3M generations the 7B
  fine-tune surpasses the pass@4 of the 671B DeepSeek-Prover-V2 on D3k. **Caveat stated by the
  authors' own framing**: D3k is that run's own training-target set, not a held-out public
  benchmark like miniF2F or PutnamBench — evidence for the self-play + verifier-guided
  mechanism, not a clean "7B beats 671B" claim in general.
- **BFS-Prover / Goedel-V2**: both beat the 72B Kimina (84%) at 95% and 90.4% respectively on a
  theorem-proving benchmark, with 32B named as the sweet spot for this class of reasoning task.
- **Phi-4-Reasoning** (Microsoft, 14B): reported to outperform models 50x its size on
  Olympiad-grade mathematics. Note: the buffet names a different SKU, **Phi-4 Mini Reasoning
  4B**, at ~2.3GB under Q4 quantization (**founder-supplied, unverified**) — not confirmed to be
  the same benchmark claim as the 14B model above; treat as two distinct Phi-4 variants until
  reconciled.
- **Qwen3-Coder-Next** (Feb 2026, 80B total / 3B active MoE, distilled from Qwen3-Coder-480B as
  teacher): outperforms its own 480B parent on CRUXEval and Codeforces-rating benchmarks. Named
  limitation from the same research pass: 3B active parameters is not enough for complex
  multi-step reasoning or long agentic loops. Already in the buffet's own model zoo list; this
  is its first receipt-backed benchmark claim plus its first stated limitation.
- **SmolLM3-3B** (Hugging Face) — **not in the buffet at all** — outperforms Llama-3.2-3B and
  Qwen2.5-3B at the 3B scale, competitive with several 4B-class models across 12 benchmarks.
  Fully open. A genuine addition, not a repeat of supplied material.
- **1.3M-parameter specialized model vs. LLMs on real-time game control** ([arXiv:2604.07385](https://arxiv.org/pdf/2604.07385),
  "Playing DOOM with 1.3M Parameters"): an extreme, receipt-backed instance of the
  specialist-beats-generalist principle the buffet itself argues for — the outer bound of how
  far task-narrowing can be pushed.
- **GPT-OSS-120B** (OpenAI, MoE, 116.83B total / 5.13B active): near-parity with o4-mini on core
  reasoning; requires a single 80GB GPU (H100/MI300X) to self-host — confirms it belongs in the
  "route to it via a free/cheap API" tier (Pillar 1), never the "rent hardware to run it
  ourselves" tier ([OpenAI](https://openai.com/index/introducing-gpt-oss/),
  [HF](https://huggingface.co/openai/gpt-oss-120b)).
- **Poolside Laguna S 2.1** (MoE, 118B total / 8B active, top-10-of-256 experts + 1 shared,
  256K context): the buffet's own "118B MoE/8B active" figure is exactly right, confirmed against
  the vendor's own model card ([Poolside](https://poolside.ai/blog/introducing-laguna-s-2-1),
  [vLLM recipes](https://recipes.vllm.ai/poolside/Laguna-S-2.1)).
- **Nanbeige4.1-3B** (buffet spelled it "Nanbei 4.1"; 3B dense): the first open small language
  model to unify agentic behavior, code generation and general reasoning in one 3B checkpoint,
  and it beats 30–32B class models on most benchmarks — a real arXiv paper, not a press claim
  ([arXiv:2602.13367](https://arxiv.org/abs/2602.13367), Apache 2.0).
- **Gemma 4 26B A4B** (Google, MoE, 25.2B total / 3.8B active, 262K context): near-31B quality at
  4B-class latency and cost ([Google](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/),
  [OpenRouter](https://openrouter.ai/google/gemma-4-26b-a4b-it)).
- **MiniMax M2.7** (MoE, 230B total / 10B active): SWE-Pro 56.22%, near-Opus-class on that
  benchmark — but released under a **non-commercial license**, a real blocker for any product
  use of this model specifically, separate from and in addition to its cost line
  ([Artificial Analysis](https://artificialanalysis.ai/models/minimax-m2-7)).
- **Falcon-H1R 7B** (TII, hybrid Transformer+Mamba2, 256K context): AIME-2025 83.1%, beats the
  15B and 32B class on the same benchmark; ~1,500 tok/s per GPU at batch 64
  ([MarkTechPost](https://www.marktechpost.com/2026/01/07/tii-abu-dhabi-released-falcon-h1r-7b-a-new-reasoning-model-outperforming-others-in-math-and-coding-with-only-7b-params-with-256k-context-window/)).

**Correction, TwiL-LM3's headline figure**: the 96.4-vs-65.2 rule-induction claim (TwiL-LM3 vs.
GPT-OSS-120B) that the buffet cites belongs to **TwiL-LM3\*, an unreleased internal variant named
in webAI's own model-card comparison table — not the shipping 3B checkpoint**. Citing "the 3B
model beats a 120B model" without that caveat overstates what is actually deployable today
([MarkTechPost](https://www.marktechpost.com/2026/08/10/webai-releases-twil-lm-a-1-7b-and-3b-formal-logic-model-family-for-autoformalization-on-local-hardware/),
[HF](https://huggingface.co/webAI-Official/TwIL-LM3)).

**Founder-supplied, unverified — named in the buffet, not yet checked against a primary source:**

These were missing from the first version of this file entirely; that was the single biggest
gap on audit. Listed here honestly as unverified, not silently dropped and not silently
promoted to "confirmed."

- **Samsung TRM (7M parameters)**: claimed ~45% on ARC-AGI-1, "outperforming models thousands of
  times its size" via dynamic recursion (looping its own reasoning 1–10 times rather than
  scaling width). Buffet's own stated limits: no broad world knowledge, rigid/supervised-only,
  cannot generate open-ended text.
- **VibeThinker-3B (Weibo)**: claimed 94.3 on the AIME 2026 math benchmark.
- **VibeThinker-1.5B**: named in the buffet's model zoo, no benchmark figure attached.
- **DeepSeek-R1-Distill family**: 1.5B (~2GB at 4-bit), 7B (~4.0GB at Q4), 14B (~7.8GB at Q4),
  32B (unspecified footprint, named as the OCI-cluster / Mac-Mini reasoning-engine candidate).
- **Qwen3.8-27B (dense)**, **DeepSeek V3.2 (671B/685B)**, **DeepSeek R1 (671B)**,
  **DeepSeek R1-0528 distilled Qwen3 8B**, **DeepSeek-V4-Pro-Max (1.6T)**,
  **DeepSeek V4 Flash (284B MoE)**, **Qwen3-32B** — named in the buffet's model zoo list with no
  benchmark figures attached to check.

None of the above should enter a cost or capability decision until at least the two headline
figures (TRM's 45% ARC-AGI-1, VibeThinker's 94.3 AIME) are found in a paper or an official model
card, the same bar every claim in the "strong sources" list above already clears.

## 3. MoE active-vs-total-parameter economics — the mechanism, not just examples

- General finding, multiple sources: total parameters represent knowledge, active parameters
  represent cost — MoE architectures deliver a large model's quality at a small model's
  inference speed, because only a fraction of parameters fire per token
  ([howaiworks.ai](https://howaiworks.ai/blog/mixture-of-experts-explained)).
- Nearly every frontier open-weight model released in 2026 is MoE for this reason — this is now
  the default architecture pattern, not an exotic choice.
- Direct relevance: the buffet names DeepSeek-R1-Distill-32B (*dense*) as the model to load onto
  a rented Mac Mini's unified memory. An 80B-total/3B-active MoE model (Qwen3-Coder-Next class)
  is a much lighter resident-memory commitment for the same or better output quality on the
  tasks that model is good at — a real alternative to re-examine before committing to the
  buffet's specific dense-model recommendation, not yet checked against real memory/bandwidth
  numbers for either model on that hardware.

## 4. The buffet's four architecture pillars and its Z3/CEGIS pillar — checked against the actual repository, not asserted

This is the second-biggest gap the audit found: the buffet's core architecture proposal (four
named "Pillars" plus a Z3/CEGIS formal-verification design) was discussed in conversation
earlier this session but never entered this record. Checked directly against `idp` on disk
just now, not from memory:

- **Pillar 1 — "Hollow Model": LiteLLM routing to cheap/free APIs + a local CPU-quantized
  gatekeeper model for deterministic tasks.** Already built, confirmed by reading
  `platform/llm/config.base.yaml` and `platform/llm/ollama.yaml` directly: `cost-based-routing`
  picks the cheapest healthy deployment automatically (the three free vendor pools price at
  $0.0000 by convention and win whenever healthy), and a local `qwen2.5-coder:1.5b` model runs
  on the cluster's own free Ampere pool as the "ollama" lane — the same gatekeeper role the
  buffet describes, on the buffet's own suggested model family. Real, not aspirational.
- **Z3/CEGIS formal verification pillar.** Already built, and more rigorous than the buffet's
  own sketch: `sovereign/verifier.py` runs a three-stage pipeline — structural (`compile()`),
  symbolic (Z3 over the patch's own declared contract), execution (tests in a sterile throwaway
  tree) — and only mints an attestation, bound to the SHA-256 of the verified bytes, if all
  three pass. The file's own docstring is explicit that Z3 proves a property of a function for
  all inputs in its domain, and does *not* by itself prove "the tests pass" — that is stage 3's
  job, a distinction the buffet's sketch does not make. Confirmed by reading the file, not by
  trusting its docstring alone.
- **Semantic routing (buffet's "Traffic Cop": LiteLLM semantic routing via nomic-embed-text,
  RouteLLM's weak/strong classifier, vLLM Semantic Router).** **Not built. A real, named gap.**
  `cost-based-routing` in this estate routes on live price and health, never on the meaning or
  difficulty of the prompt — there is no intent classifier anywhere in the routing path. If the
  founder wants the buffet's "traffic cop" specifically, it does not exist yet.
- **Pillar 2 — CPU sandbox / `execute_python` token-offload tool** (agent writes code, an
  ephemeral Alpine-Python container on the free Ampere CPUs runs it, the result — not the raw
  data — returns to the model). Searched the repository directly for `execute_python` and any
  ephemeral-sandbox tool definition: **nothing found. A real, named gap**, not a rediscovery of
  something already there.
- **Pillar 3 — "Grind Tool": a CronJob worker forced to keep working a queued task until a
  deterministic test passes or a 4-hour wall-clock limit is hit.** Searched for `grind` and for
  a job-queue-plus-hard-timeout pattern: the one match (`platform/jit/broker/broker.py:661`) is
  unrelated prose ("the offline grind that would need the full [key]"), not this mechanism.
  **A real, named gap.**
- **Pillar 4 — "Darwin Machine": a weekly meta-optimizer that generates prompt/tool-definition
  variants, evals them, and auto-deploys the winner via CI.** `sovereign/shadow/distill.py` and
  `sovereign/shadow/branching.py` are the closest plausible analog — branching.py already runs
  concurrent candidate branches via Temporal — but I have not opened either file's actual logic
  closely enough to confirm they implement the specific weekly-generate/eval/auto-deploy loop
  the buffet describes. Stated as a plausible analog, not a confirmed match — the distinction
  the founder has been explicit about wanting kept clean (DoD v3: verified, not asserted).
- **Orchestration frameworks named in the buffet (CrewAI, LangGraph).** Not checked against the
  repository. The estate's actual orchestration primitive for concurrent branches is Temporal
  child workflows (`branching.py`), a different mechanism than either named framework — whether
  it is a sufficient substitute for what CrewAI/LangGraph would add is an open question, not
  answered here.
- **Differentiable Execution Graphs / do-calculus counterfactual fault isolation.** Real,
  established technique (Judea Pearl's do-calculus for counterfactual inference over a causal
  DAG) — not fabricated by the buffet. Nothing in this repository implements it as a repair
  mechanism. A genuine, uncosted gap, distinct from the Z3/CEGIS pillar above.
- **Refinement types / proof-carrying actions (Liquid Haskell, typed Rust).** Also a real,
  established technique — an illegal action becomes a compile failure, not a runtime check.
  Nothing in this repository does this; the repo's actual enforcement (`sovereign/verifier.py`)
  proves properties and runs tests at verification time, which is weaker on "syntactically
  impossible to write" but stronger on "proves the tests actually pass."
- **LLMRouter via ComfyUI.** Real, confirmed tool — [ulab-uiuc/LLMRouter](https://github.com/ulab-uiuc/LLMRouter)
  shipped a drag-and-drop ComfyUI front end for its routing pipeline in Feb 2026. Not fabricated,
  not in use anywhere in this repository.

## 5. Hosting matrix — real receipts, no rented Mac in it (none procured yet)

Correction on the record: no Mac has been rented. Every hosting row below is a candidate with a
real per-unit cost, not built or committed infrastructure. "Rented Mac" is one candidate row, not
a standing fact of the design.

| Tier | Real unit cost | Activation floor | Source |
|---|---|---|---|
| OCI Ampere A1, free | $0/mo, 2 OCPU / 12 GB | none, always-on | `docs/reference/oci-tenancy.md:18`; cut from 4 OCPU/24GB confirmed independently by [InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) |
| OCI Ampere A1, paid overflow | $0.01/OCPU-hr + $0.0015/GB-hr | none, per-second | [Oracle Ampere A1 pricing](https://www.oracle.com/cloud/compute/arm/pricing/) — doubling the free allotment (+2 OCPU/+12GB) costs roughly $28/mo run continuously |
| OCI GPU, VM.GPU.A10.1 | ~$1.27/hr on-demand | none, per-second | [Thunder Compute OCI GPU pricing survey](https://www.thundercompute.com/blog/oracle-cloud-oci-gpu-pricing) |
| OCI GPU, A100 | ~$4/hr on-demand | none, per-second | same source |
| Rented Apple Silicon, hourly (Scaleway, candidate only) | €0.17/hr (M2) or €0.21/hr (M2 Pro) | **24-hour minimum per activation**, Apple licensing term | [Scaleway](https://www.scaleway.com/en/docs/apple-silicon/concepts/) |
| Rented Mac Mini, flat monthly (Hetzner, candidate only) | ~€64/mo (~£54/mo), 32GB unified memory | none named, standing monthly lease | founder's email, 2026-09-14 — **founder-supplied, unverified against Hetzner's own pricing page** |
| Rented Mac Mini, flat monthly (Scaleway, candidate only) | ~€80/mo (~£68/mo), 32GB unified memory | none named, standing monthly lease | founder's email, 2026-09-14 — **founder-supplied, unverified**; possibly a different Scaleway product line than the hourly row above, not reconciled |
| Vast.ai, RTX 3090 (24GB), continuous | $73–$146/mo (24/7 @ $0.10–$0.20/hr) | none, native point-of-use | founder's email, 2026-09-14 — **founder-supplied, unverified against Vast.ai's live marketplace** |
| Vast.ai, RTX 3090 (24GB), 2hr/day | ~$9/mo | none | same source |
| Vast.ai, RTX 4090 (24GB), continuous | $180–$330/mo (@ $0.25–$0.45/hr) | none | same source |
| Vast.ai, A100/H100, continuous | $600–$1,400/mo (@ $0.80–$2.00/hr) | none | same source |
| Vast.ai, persistent storage | $0.10–$0.20/GB/mo (billed even when the instance is stopped, unless destroyed) | n/a | same source |
| Frontier paid pool (MiniMax, default floor) | $0.30/1M input, $1.20/1M output tokens | none | `platform/llm/config.yaml`, capped near $139.50/mo by the AGENTS.md budget block |
| Free vendor pool (groq/cerebras/sambanova) | $0 while healthy | none | `cost-based-routing`, priced $0.0000 by convention |

Correction from the first version of this file: it stated "Vast.ai — no receipt yet, needs the
founder's own pricing email." That was wrong — the founder's email with exact Vast.ai figures
was already in the material pasted this session; the first pass of this record simply failed to
use it. The rows above are those figures, marked as **founder-supplied, unverified** because I
have not yet cross-checked them against Vast.ai's live marketplace myself, not because they
were unavailable.

## 6. The choreography — reusing what's real, naming the one gap that must close first

Not a new framework. Three existing pieces, one real hardening:

1. **The matrix above becomes data**, in the same shape AGENTS.md's `[routing]` TOML block
   already uses for model aliases — one row per hosting tier, machine-readable, not prose.
2. **`sovereign/shadow/branching.py`'s Temporal child-workflow mechanism is the choreographer** —
   it already runs N branches concurrently; pointed at hosting-tier rows instead of candidate
   answers, it is the automated switch, not a new orchestrator.
3. **The live signal already exists**: the router's `cost-based-routing` + `enable_pre_call_checks`
   + breaker (`allowed_fails`/`cooldown_time`) is what a tier-switch decision should read, not a
   new health check.
4. **The one real gap that makes "metered hard" false today**: `request_ceiling.proxy_handler_instance`'s
   own comment states it plainly — "it reports and warns; it does not sever the router" — proven
   by the 86,525,924-token/hour incident going through with every existing guard reporting and
   nothing stopping it. Any claim of hard metering is false until this becomes an actual breaker,
   not an alert. This is the one prerequisite, named specifically, not a vague caveat.
5. **Visibility belongs in the real catalog, not a new dashboard** — this estate already generates
   Backstage entities from data (`bin/catalog-gen`, `backstage/templates/`). The hosting matrix
   becomes one new catalog entity generated the same way every other one is, per THE HEADLINE
   ("never script what a proven platform already solves"). Not a bespoke UI.
6. **Autonomous switching that can spend money is governed by the capabilities already defined**
   in AGENTS.md's `[capabilities]` block — a tier-switch that provisions a paid GPU sits closer to
   `destructive` than `nondestructive` in spend terms, so it inherits the existing quorum +
   hardware-signature requirement rather than getting new, separately-invented authority.

## 7. Open items — do not treat as settled

- **The Mac-Mini hourly-vs-flat-monthly reconciliation** (§1, §5): whether these are genuinely
  two different Scaleway/Hetzner products or the same offer described two ways has not been
  checked against either vendor's own product pages.
- **TRM (45% ARC-AGI-1) and VibeThinker-3B (94.3 AIME 2026)** need a primary source — paper or
  official model card — before either figure enters any capability decision. Same bar for
  the DeepSeek-R1-Distill family's exact footprints, VibeThinker-1.5B, Qwen3.8-27B, and the rest
  of §2's founder-supplied list. (TwiL-LM3 is now resolved above: its headline figure belongs to
  an unreleased variant, not the shipping model — closed, not still open.)
- **MiniMax M2.7's non-commercial license** (§2) rules it out for any product use regardless of
  its SWE-Pro score — a licensing fact, not a benchmark question, and it should not be reused as
  a candidate anywhere downstream without that caveat attached.
- **No semantic-intent router exists in this estate** — the buffet's "Traffic Cop" pattern
  (LiteLLM semantic routing / RouteLLM / vLLM Semantic Router) is a real gap against
  `cost-based-routing`, which routes on price and health only.
- **No CPU-sandbox / `execute_python` token-offload tool exists** — Pillar 2 is unbuilt.
- **No Grind-Tool overnight worker-queue-with-hard-timeout exists** — Pillar 3 is unbuilt.
- **Pillar 4's match to `sovereign/shadow/distill.py`/`branching.py` is unconfirmed** — plausible
  analog only; their actual logic has not been read closely enough to say they do the
  weekly-generate/eval/auto-deploy loop the buffet describes.
- Whether an MoE model (e.g., Qwen3-Coder-Next class) fits the rented-Mac unified-memory profile
  better than the buffet's own dense-32B recommendation has not been checked against real
  memory/bandwidth numbers — flagged here, not yet answered.
