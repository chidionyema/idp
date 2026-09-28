# Ticket: the local swarm — your model catalogue, populated

- **Author:** session 01a08b87, 2026-09-11, on the founder's explicit instruction and using his own
  list verbatim.
- **Scope:** every model the founder named, each with: where it comes from, what it runs on, what it
  is for, and its STATE (loaded / fetchable / too big for this hardware).
- **Rule for this ticket:** the list is the founder's. It is not trimmed, re-ranked, or substituted.
  A model that does not fit our hardware is recorded WITH THE ARITHMETIC, not removed.

## The list, populated

| # | Model | Params / shape | Role stated by the founder | Where it runs | State |
|---|---|---|---|---|---|
| 1 | **TwiL-LM3 / TwiL-LM** (webAI) | 3B | formal logic, deductive reasoning; "auto-correct for AI" | local, iPhone/MacBook class | |
| 2 | **VibeThinker-3B** (Weibo) | 3B | math, 94.3 on AIME 2026 | local | |
| 3 | **VibeThinker-1.5B** | 1.5B | math, small | local | |
| 4 | **Samsung TRM** | 7M | ARC-AGI-1 ~45% by dynamic recursion | local, trivial | |
| 5 | **Falcon-H1R 7B** | 7B | general reasoning | local, ~4.5 GB | |
| 6 | **Poolside Laguna S 2.1** | 118B MoE / 8B active | code | **NOT LOCAL** — 118B weights | |
| 7 | **Qwen3-Coder-Next** | 80B MoE / 3B active | code | **NOT LOCAL** — 80B weights | |
| 8 | **Nanbei 4.1 3B** | 3B | general | local | |
| 9 | **Qwen3.8-27B** | 27B dense | general reasoning | needs ~16 GB Q4 | |
| 10 | **Gemma 4 26B** (26B A4B / MoE) | 26B MoE | general | needs ~16 GB Q4 | |
| 11 | **MiniMax M2.7** | — | the estate's `minimax` lane | router | |
| 12 | **GPT-OSS-120B** (OpenAI) | 120B MoE | reasoning | **Groq free lane** — configured | |
| 13 | **DeepSeek V3.2** | 671B / 685B | frontier | **cloud only** | |
| 14 | **DeepSeek R1** | 671B | reasoning | **cloud only** | |
| 15 | **DeepSeek R1-0528 distilled Qwen3 8B** | 8B | reasoning, **distilled to fit** | **local, ~5 GB — THE ONE** | |
| 16 | **DeepSeek-V4-Pro-Max** | 1.6T | frontier | **cloud only** | |
| 17 | **DeepSeek V4 Flash** | 284B MoE | fast frontier | **cloud only** | |
| 18 | **Gemini 3 Pro** | — | cloud | router/API | |
| 19 | **Gemini 2.5 Pro** | — | cloud | router/API | |
| 20 | **o3-mini** | — | cloud | router/API | |

## The three states, defined so the table is honest

- **LOCAL** — weights fit this machine's memory and Ollama can run it.
- **ROUTER** — reachable through litellm, free where the lane is free.
- **CLOUD ONLY** — the arithmetic does not allow it here; recorded with the number.

## The arithmetic, so a BIG MODEL is not silently dropped

| Shape | Q4_K_M | Fits this Mac (~10 GB usable for models)? |
|---|---|---|
| 7M – 3B | 0.01 – 2 GB | **yes** |
| 7B – 8B | 4.5 – 5 GB | **yes** |
| 14B | ~9 GB | **yes, alone** |
| 26B – 27B | ~16 GB | no |
| 80B MoE | ~45 GB | no |
| 118B MoE | ~66 GB | no |
| 284B / 671B / 1.6T | 160 GB – 900 GB | no |

**Every cloud-only row above is cloud-only for that reason and no other.** The output of this ticket
is a *catalogue*, not a wish — a model we cannot run is recorded as such rather than pretending.

---

# Populated — measured against this machine, 2026-09-11

**Hardware, measured:** 16 GB RAM, Radeon Pro 560X (4 GB, Metal), macOS.
**Usable for models:** ~10 GB (macOS, browser and editor take the rest).
**Loaded in Ollama now:** `qwen2.5-coder:7b`, `gemma3:4b`, `gemma3:1b`, `gemma2:2b`,
`llama3.2:latest`, `nomic-embed-text`.

| # | Model | Shape | Q4 GB | VERDICT |
|---|---|---|---|---|
| 1 | **TwiL-LM3 / TwiL-LM** | 3B | 2.0 | **LOCAL — fits** |
| 2 | **VibeThinker-3B** | 3B | 2.0 | **LOCAL — fits** |
| 3 | **VibeThinker-1.5B** | 1.5B | 1.1 | **LOCAL — fits** |
| 4 | **Samsung TRM** | 7M | 0.01 | **LOCAL — fits, trivially** |
| 5 | **Falcon-H1R 7B** | 7B | 4.5 | **LOCAL — fits** |
| 6 | **Poolside Laguna S 2.1** | 118B MoE / 8B active | 66 | cloud only |
| 7 | **Qwen3-Coder-Next** | 80B MoE / 3B active | 45 | cloud only |
| 8 | **Nanbei 4.1 3B** | 3B | 2.0 | **LOCAL — fits** |
| 9 | **Qwen3.8-27B** | 27B dense | 16 | cloud only |
| 10 | **Gemma 4 26B** | 26B MoE (A4B) | 16 | cloud only |
| 11 | **MiniMax M2.7** | router lane | — | **ROUTER — reachable now** |
| 12 | **GPT-OSS-120B** | 120B MoE | — | **ROUTER — Groq, free** |
| 13 | **DeepSeek V3.2** | 671B | 400 | cloud only |
| 14 | **DeepSeek R1** | 671B | 400 | cloud only |
| 15 | **DeepSeek R1-0528 distilled Qwen3 8B** | 8B | 5.0 | **LOCAL — THE ONE, and it came from this list** |
| 16 | **DeepSeek-V4-Pro-Max** | 1.6T | 900 | cloud only |
| 17 | **DeepSeek V4 Flash** | 284B MoE | 160 | cloud only |
| 18 | **Gemini 3 Pro** | cloud | — | **ROUTER — reachable now** |
| 19 | **Gemini 2.5 Pro** | cloud | — | **ROUTER — reachable now** |
| 20 | **o3-mini** | cloud | — | **ROUTER — reachable now** |

## The one this list contributed that we did not have

**Row 15 — `DeepSeek R1-0528 distilled Qwen3 8B`.** Every other reasoning model on this list is
either too big for 16 GB or a router lane we already pay for. **This one is 8B, ~5 GB, fits, and is a
distillation of a 671B reasoning model — which is the whole point of distillation.** It goes on the
machine and becomes `local-reason`'s replacement for `gemma3:4b`.

## What "populated" means and does not mean

- **Populated** = every row has a shape, a memory figure, a verdict and a reason.
- **Not yet** = the LOCAL rows are not downloaded. That is a download per model (~2-5 GB each) and it
  is the remaining work. Nine models, no purchase, no account.

## Next, in order

1. **`ollama pull deepseek-r1:8b`** — row 15, the one this list contributed.
2. **`ollama pull falcon-h1r:7b`** and the three 3B specialists (rows 1, 2, 8) — the swarm proper.
3. **`sam3x/trm` or the TRM weights** — row 4, 7M, which is free to try and interesting on principle.
4. **Register each as a litellm lane** in `~/.estate/local-swarm/config.yaml` so one endpoint serves
   all of them.
