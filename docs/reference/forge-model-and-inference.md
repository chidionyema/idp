# The Forge's Modal contract and the serving-endpoint question (2026-09-08)

A durable record so the "how is Modal authenticated / can we host a model" question is answered
once, with file:line, and never re-derived per session. Verified from the repo and a peer session
on 2026-09-08.

## The two claims that keep being repeated, and their ground truth

1. **"We already use Modal in our stack"** — TRUE, but with a narrow meaning. Modal is in the
   stack for the **Forge's ephemeral GPU training runs** only.
   - CLI: `modal` present on this Mac (`modal client version 1.5.5`).
   - The one Modal app is `modal.App("model-forge")` in `forge/modal_app.py`, documented as an
     **"Ephemeral GPU launcher"**: `modal run forge/modal_app.py --task ...`. It trains, pushes to
     GHCR, files an experiment record. There is **no `modal serve`/`modal deploy` and no
     `web_endpoint`** anywhere in `forge/`. It is training-only.
   - Cost model in `forge/common.py`: `GPU_USD_PER_HOUR` = {T4, L4: $0.80, L40S: $1.95, ...}; every
     run passes `cost_gate()` vs a task `budget_usd`. Paid GPU is budget-gated.

2. **"Modal is authenticated / it's a frictionless one-root problem"** — Modal auth in this estate
   is **CI-only by design** (R52 "one root per provider"; the whole `forge-train.yml` comment says
   "no terminal, no token on a laptop"):
   - The Modal one-root is the **GitHub repository secret pair** `SEED_MODAL_TOKEN_ID` +
     `SEED_MODAL_TOKEN_SECRET`, set once via `bin/idp-set-root modal`
     (`bin/idp-set-root` lines ~126-127; `platform/vendors/consoles.yaml:29`).
   - `.github/workflows/forge-train.yml` exports them as `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`
     and proves the pair with `modal secret list` before any `modal run` (forge-train.yml:38-39,58-60).
   - **No local/mac session authenticates Modal with the repo secrets.** A laptop session with no
     token fails (`modal app list` -> "Token missing"). `modal token new` on a laptop is what the
     estate rules forbid. So an agent session runs Modal authenticated only inside CINODE, with the
     secret pair in env — there is no recorded local invocation.

## The serving-endpoint question (Qwen-14B / your "$penny open-model" idea)

The proposal repeated in several sessions — host Qwen-2.5-14B-Instruct-AWQ on a Modal
L4, scale-to-zero, exposed as an OpenAI-compatible endpoint wired as a LiteLLM lane — is a
**brand-new pattern this estate has never deployed**:
- It needs an `@app.cls` + `@modal.web_endpoint` (or an ASGI/HTTP serving class) with
  `scale_to_zero`, NOT the existing `@app.function` `modal run` training shape.
- It is PAID GPU kept reachable (warm-or-scheduled), so it is a forge `cost_gate`/budget decision,
  and under the CI-only rule a deploy would go through a new CI workflow (`modal deploy`), not a
  laptop `modal deploy` with a local token.
- The estate's one model ROUTER is LiteLLM (`llm/config.yaml`); a self-hosted lane would be added
  there, not as a second inference system (one-platform rule).

DECISION OPEN (founder, 2026-09-08): whether to stand up a paid Modal serving deployment of an
open model as a LiteLLM lane. Until then: Modal = ephemeral training only; inference stays on the
managed lanes in `llm/config.yaml`. This record exists so the "can we host our own model for
pennies" question is answered with the real constraint (CI-only auth, training-only forge, paid GPU
gated) rather than re-explored each time.

## Concrete facts a future session needs

- Run a training task authenticated: do it in CI or export `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`
  from the repo secrets into env, then `modal secret list` to prove, then `modal run forge/modal_app.py --task <task>`.
- Pricing (forge/common.py `GPU_USD_PER_HOUR`): T4, L4 = $0.80/hr; L40S = $1.95/hr.
- Files: `forge/modal_app.py`, `forge/common.py`, `bin/idp-set-root`, `platform/vendors/consoles.yaml`,
  `.github/workflows/forge-train.yml`.

## Why vLLM is the right engine if we ever self-host (PagedAttention / KV cache paging)

A self-hosted serving lane, if stood up, should use vLLM — because of how it solves KV-cache
memory waste, which is what makes a multi-lane fleet on one GPU viable:
- The old way pre-allocated one giant contiguous VRAM block per user at max context, wasting
  ~60-80% of GPU memory (space reserved for 2k tokens when a call uses 10).
- vLLM borrows OS virtual-memory paging (PagedAttention): the KV cache is broken into small pages
  mapped dynamically, cutting waste to under ~4%, and continuous batching interleaves many agents'
  token streams onto the same GPU cores.
- Net: a single L4/L40S can carry the whole small+moE+heavy tiered fleet without renting many
  machines; scales to zero when idle.

## A model on THIS MacBook (local inference alternative — founder note 2026-09-09)

Cloud/Modal is not the only host. This MacBook is an Intel i7-8850H with a Radeon Pro 560X
(**4 GB VRAM only**) and 16 GB RAM — NOT Apple Silicon, so no unified-memory advantage:
- It can run a small model locally (e.g. a ~1-3B Q4 via llama.cpp/Ollama on CPU) for trivial Tier-1
  work with zero cloud cost and full privacy.
- It CANNOT run a 14B (needs ~10 GB VRAM / >16 GB free RAM; 4 GB VRAM and a 16 GB machine don't fit
  it, and CPU-only a 14B is single-digit tok/s on an i7). Same OS/managed cap would hold.
- If a Mac-native model is wanted, it needs the machine to become Apple Silicon (M-series, 32GB+)
  — a CapEx decision, out of scope of the current paid-GPU path. Until then: local small model for
  Tier-1 trivia at most; heavy tiers stay on managed lanes or a future Modal/self-host serving lane.

- **Quantization makes 14B-on-24GB viable** (AWQ/INT4): a 14B is ~14GB full precision, ~8GB at
  INT4/AWQ — on a 24GB L4 that leaves ~16GB for the 5-lane KV caches. This is the concrete reason
  the tiered fleet fits one L4. (Lighter than L4 won't hold a 14B; 8-bit needs ~16GB.) For the L4
  (forge/common.py $0.80/hr), a 4-bit 14B with 4-8k contexts carries the 5 concurrent lanes.
