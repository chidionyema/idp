# Wartime Multidimensional AI Inference Plan (estate canonical)

> Date: 2026-09-13
> Lead: keep lights on 24/7 within a $50/month operational target (under the $150/month contract ceiling),
>       with the best reasoning models, ultra-intelligent seamless routing, GPU options included,
>       every path held (nothing dropped flippantly — drop at commercial cutover the founder names).
> Status: PROPOSED, not built. Working tree dirty. Founder blockers pending.
> Companion web URL: https://gist.github.com/chidionyema/e95c9a06ec79743ba68677310fc1cd3e (secret gist, same content).
> Mirror formats: `docs/tickets/2026-09-13-wartime-inference.md`, `docs/evidence/wartime-inference/PROOF-OF-WORK.md`.

---

## 0. Executive read

The estate operates one AI inference router (LiteLLM, single gateway per THE HEADLINE).
The router today heads no chain. Free direct lanes (Groq, Cerebras, OpenRouter, NVIDIA NIM,
Gemini free tier) lead every chain ahead of the cluster router since 2026-09-10. The
router is now a middle rung where estate spend accounting and tracing live; Otto's brain
still emits `router.outcome` for every turn regardless of which lane answered.

Three live rings, three staged tiers, every path held. Nothing dropped flippantly.

---

## 1. Verified constraints (numbers from real files, this session)

| Item | Value | Source |
|---|---|---|
| Daily litellm cap | $5.0/day | `llm/config.yaml:417 max_budget: 5.0` |
| Budget reset | 1 day | `llm/config.yaml:418 budget_duration: 1d` |
| Per-virtual-key daily cap | $5 | `estate-defaults.yaml llm.virtual_key_daily_usd: 5` |
| Operational monthly target | $50 | `estate-defaults.yaml budget_monthly_usd: 50` |
| Contract ceiling | $150/month | `AGENTS.md [cost] contract_max_usd_month: 150` |
| Per-agent frontier budget | $3/day | `AGENTS.md [budget.usd_per_day] litellm = 3.0` |
| Main node pool | 2 nodes | `estate-defaults.yaml max_nodes: 2` |
| Main pool burst | 60 hr/mo | `estate-defaults.yaml burst_hours_monthly: 60` |
| Spot pool | 1 node, 30 hr/mo | `estate-defaults.yaml spot_max_nodes: 1, spot_hours_monthly: 30` |
| Spot pool shape | `a1-spot` (AMD Arm CPU) | `estate-defaults.yaml` |
| Retry policy | `allowed_fails: 3, cooldown_time: 60, num_retries: 2` | `llm/config.yaml:399-400` |

Routing policy (read this session):

- `OTTO_ROUTER_LANE_JUDGMENT_MODEL: "gemini"` — `platform/otto-gateway/router-lanes.yaml:74`.
- `OTTO_ROUTER_LANE_VERIFY_MODEL: "deepseek"` — `platform/otto-gateway/router-lanes.yaml:115`.

Family separation holds: judgment vendor ≠ verify vendor.

11 litellm lanes wired today (grep result this session): openrouter, minimax, minimax_json, minimax_m27, gemini, groq, cerebras, nvidia, ollama, ollama-vision, ollama-llama.

Estate identity (this session):

- Region: `uk-london-1` (`clusters/oke/estate-config.yaml` `ESTATE_OCI_REGION`).
- GitHub owner: `chidionyema` (`ESTATE_GITHUB_OWNER`).
- Repo URL: `https://github.com/chidionyema/idp.git` (`git remote get-url origin`).

---

## 2. Three live rings

### Ring 1 — paid frontier (capacity, $5/day ceiling)

- Default lane: `minimax` (MiniMax-M3, 1M context, reasoning depth at the top of the ladder).
- Judgment lane: `gemini` (env: `OTTO_ROUTER_LANE_JUDGMENT_MODEL`).
- Verify lane: `deepseek` (env: `OTTO_ROUTER_LANE_VERIFY_MODEL`).
- Spend: per-agent frontier $3/day (AGENTS.md), router hard ceiling $5/day.
- MiniMax-M3 pricing: $0.30/M in, $1.20/M out.
- Used for: deep reasoning, frontier calls, multi-step plans.
- Daily guard: 8s per-turn budget per the free-lane measurement (router.yaml comment).

### Ring 2 — free metered (the floor, 24/7)

- Lanes: `groq`, `cerebras`, `nvidia`, `openrouter`, `gemini` (free tier).
- Measured: Groq 0.48s, Cerebras 0.25s from the router pod (`platform/otto-gateway/three-homes.yaml` comment, 2026-09-10).
- Since 2026-09-10 these free lanes head every chain ahead of the cluster router.
- Spend table impact: Groq/Cerebras answers do NOT touch LiteLLM spend (they never enter the router).
- Otto's brain still emits `router.outcome` for every turn.
- Last entry of every fallback chain is `cheap` = `groq` (daily-metered, prepaid budgets can reach zero, daily meters can't).
- Durable free floor — git history commit `3e5c7bad` ("cheap finally means free").

### Ring 3 — cluster Ollama (proposed, NOT BUILT)

- File: `platform/llm/ollama.yaml` — new Flux-managed Deployment (none exists today).
- Image: `ollama/ollama`. CPU first pass (cluster pool is `a1-spot` AMD Arm — no GPU shape).
- Models staged: `qwen2.5-coder:7b` first, then `VibeThinker-3B` (HF card MIT confirm pending), then `prism-ml/Ternary-Bonsai-4B-2bit` (Apache 2.0, ternary quant).
- Lanes currently target `host.docker.internal:11434` (Mac, dead since 2026-09-10). Cluster Ollama would repoint these to `ollama.llm.svc:11434`.
- Pre-pull: init container pins models so reconciliation is idempotent.

---

## 3. Three staged tiers (NOT WIRED — held, not dropped)

### Tier 4 (staged, dev-only) — TwIL-LM3

- webAI Non-Commercial License v1.0 (2026-08-10): 3B params, ~300 tok/s M2 MacBook, post-trained on webAI's beenote dataset.
- When adopted: only as `webai-3b` model_name entry, gated dev-only while the licence holds.
- Drop at commercial cutover the founder names.
- Status: NOT in `llm/config.yaml`.

### Tier 5 (staged) — burst GPU (Vast.ai, RunPod)

- Per-task off until cluster Ollama P50 > 8s budget AND AMD Arm spot saturated.
- Market-rate dynamic pricing. NOT persistent. NOT in `llm/config.yaml`.
- Drop at commercial cutover if/when reserved capacity is cheaper.

### Tier 6 (staged, on-Ollama-ship) — llama.cpp, mistral.rs, TurboQuant

- llama.cpp PR #26622 `--n-cpu-ffn`: measured on Qwen 2.5-27B at 130K, ~20 tok/s. Cuts FFN offload overhead; one row added when Ollama ships `--n-cpu-ffn`.
- mistral.rs v0.9.3: supports Qwen3.5/3.8, Gemma4, LFM 2.5, Hunyuan v1, Muse Glimmer. Adopt when one lands in Ollama's lib distribution.
- TurboQuant (ICLR 2026): ≥6× KV compression, ~3-bit quant; Ollama support unmeasured.
- Drop at commercial cutover if/when proprietary kernels beat Ollama.

---

## 4. Corrected GPU priority order (current pool has NO GPU)

1. Cluster Ollama on existing OKE pool — CPU first pass; only GPU-class option that ships today. ~$0 marginal.
2. AMD Arm spot (`a1-spot`) — 1 node, 30 hr/mo, ~$15/mo ceiling. Useful for batch jobs that don't need 24/7 GPU; NOT persistent GPU.
3. Vast.ai / RunPod burst GPU — STAGED; activated only when steps 1 + 2 saturate and P50 exceeds 8s.
4. Reserved A100 — STAGED, dropped at commercial cutover. Only when frontier reasoning truly needs >24 GB VRAM for sustained bursts.

> Prior drafts named "spot A10 24/7 idle ~$43/mo" — that pool does not exist on this estate. `a1-spot` is AMD Arm CPU, capped 30 hr/mo.

---

## 5. Cost math (corrected)

- Realistic monthly: $5–15/mo (free lanes head chains; frontier calls rare).
- Litellm hard ceiling at full burn: $5/day × 31 days = $155/mo — $5 over the $150 contract envelope, but unreachable because free lanes lead chains.
- AMD Arm spot hard ceiling: 30 hr/mo × ~$0.50/hr ≈ $15/mo.
- Cluster Ollama marginal: $0 (runs on existing `max_nodes: 2`).
- Staged tiers marginal: $0 while staged.
- Headroom under $150 envelope: $135–$145/mo at realistic burn.

---

## 6. Optimised: line (LAW 51 — for any execution that changes the world)

Naive steps:

1. Write `platform/llm/ollama.yaml` (Flux-managed Deployment, image `ollama/ollama`).
2. Repoint `llm/config.yaml` ollama* lanes to `ollama.llm.svc:11434`.
3. Repoint `platform/otto-gateway/router-lanes.yaml` home 2 to the cluster Ollama Service.
4. Run `bin/idp-otto-homes` to grade all three homes.
5. Run `bin/estate-twin-runtime --once` to land new lanes in the catalog.

Bottleneck: step 1 (LAW 11, founder blocker; new Flux Deployment is not undoable without a PR).
Memoize: pre-pull init container pins models so reconciliation is idempotent.
Parallelise: NONE (sequential by dependency).
Lazy: stage `qwen2.5-coder:7b` first; `VibeThinker` / `Bonsai-Ternary` only after HF card verify and Ollama support measured.
Batch: all 5 in ONE PR.
Recount: 5 sequential, 1 PR, 1 founder blocker, 0 parallel wins.

Optimised: 5 in 1 PR (saves 4 round trips); pre-pull avoids 1–2 Flux empty-pod retries; `bin/idp-otto-homes` and `bin/estate-twin-runtime` are existing estate automation (no new operator to babysit).

---

## 7. Founder blockers (LAW 11)

A. Greenlight `platform/llm/ollama.yaml` as a new Flux-managed Deployment, or kill it.
B. OCI GPU shape is not in the current pool (`a1-spot` is AMD Arm CPU only). If a true GPU shape is required, founder escalation to OCI capacity planning.
C. Clean the working tree before any grading pass. Current state has `M .githooks/pre-push`, `M backstage/plugins/fleetview-backend/src/sessions.py`, `?? features/fleetview/cp6_readable.feature`, `?? sovereign/tests/bdd/test_fleetview_cp6.py`, `?? tests/fixtures/verifier-hooks/`. `bin/idp-clean-tree` would refuse grading from this checkout.

---

## 8. Wartime framing (founder 2026-09-13)

> "we are not yet commercial when we are we can drop it now now we need to surviv e and dont have the luxury to be dropping flippantly"

> "i need war time multidimensional planning and ultra intelligent well designed routing seamless and frictionless and the naths nees to nath"

Tier 4 / 5 / 6 stay staged. Nothing is dropped because commercial cutover has not been named. Adoption happens by adding a `model_name` entry to `llm/config.yaml` with the same fallback chain. Removal is deletion of that row, again gated by founder action.

---

## 9. Honest ledger (what this plan does NOT claim)

- No second router. No Rust Axum, no parallel llama.cpp fleet, no mistral.rs server. THE HEADLINE holds.
- No console-step credential minting. R52 holds.
- No drop of staged tiers. TwIL-LM3, Vast.ai, RunPod, llama.cpp, mistral.rs, TurboQuant all stay staged for commercial cutover.
- No 24/7 GPU. The pool has no GPU shape. Stated up front; founder escalation available.
- No claim that `bin/idp-otto-homes` has been run end-to-end — verified at `--help` and source-declared functions only.
- No claim that `minimax` is the `default:` routing key — wiring under `litellm_settings.model_group_alias` not directly read this session.
- No claim that cluster Ollama exists. `find clusters platform -type d -name ollama` returned empty.

---

## 10. Step-by-step for the founder

1. Pull the latest plan — see the web URL pinned at the top of this doc.
2. Decide on blocker A (cluster Ollama yes/no).
3. Decide on blocker B (GPU shape yes/no — escalation to OCI capacity needed).
4. Decide on blocker C (clean the working tree; or work in a worktree per LAW 27).
5. Greenlight the 5-step optimised PR — or amend first.
6. Drop at commercial cutover only — staged tiers held until then.

---

## 11. References

- `docs/specs/2026-09-12-estate-twin-complete-spec.md` — sibling spec (estate-twin format).
- `docs/tickets/2026-09-12-estate-twin.md` — sibling ticket.
- `AGENTS.md` — the rules; constraints and budget defaults cited above.
- `llm/config.yaml` — litellm model list + caps.
- `estate-defaults.yaml` — pool + budget + ceiling knobs (root, NOT `clusters/oke/`).
- `platform/otto-gateway/three-homes.yaml` — routing philosophy (free-lanes-head-chains).
- `platform/otto-gateway/router-lanes.yaml` — judgment/verify env wiring.
- `bin/idp-otto-homes` — health probe + Cloudflare edge deploy tool.
- `bin/idp-rules` — repo rules registry, BEGIN/END markers.

## 12. The empirical proof rule

Before any future "WORKING" or "MEASURED_OK" claim on the cluster Ollama build (founder 2026-09-05):

1. Read live traffic: `kubectl logs --tail=100` on `litellm-*` and quote a real, end-to-end conversation completing through `ollama.llm.svc:11434`.
2. Check for silent failures: `kubectl get events` for OOMKilled / CrashLoopBackOff on new `ollama-*` pods.
3. Verify the critical path: an actual `router.outcome` emission for an Ollama-served turn.

If a successful production log line cannot be quoted, the system is NOT working.
