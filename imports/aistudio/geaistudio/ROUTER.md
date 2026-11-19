# ROUTER.md — Canonical Estate Router & Model Actuator Contract

## 1. Authoritative Routing Endpoints (`LAW_SYSTEM_FIRST_IOC_RECONCILER`)
- **Local Canonical Gateway**: `pennyd` on `http://127.0.0.1:4200/v1` (single local listener across `dsh`, `opencode`, `argon`, and CLI workers).
- **Cloud Lane 2 Gateway**: `https://llm.mumchimp.com/v1` (admitted **only** when `bin/estate-live-probe` returns `MEASURED_OK`; held fail-closed while HTTP `530` / Cloudflare `1033` persists).
- **Interchangeable Stateless Model Actuators**: `gemini`, `glm-5.3`, `deepseek`, `kimi`, `claude`, `chatgpt`. No operational truth lives inside model chat memory; all workers hydrate state from `AGENTS.md`, `ROUTER.md`, `GENESIS_SPORE.dna`, and the canonical OMNIFLOW bus.

## 2. Credential & Probe-Before-Use Law (`INS-00018` / `ac497a97f`)
- **Canonical Credential**: `PENNYD_API_KEY` validated by a live `max_tokens: 0` pre-flight probe before worker dispatch, with deterministic `keys.toml` fallback if a vault credential is stale (`dsh-web-launchd` probe-before-use).
- **Boundary Compatibility Alias Only**: `LITELLM_API_KEY` is retained strictly as a thin compatibility alias at the `dsh` process boundary and must never be referenced as a primary router credential in new code, workflows, or manifests.

## 3. Permanently Retired / Tombstoned Router Artifacts (Deterministic Admission Defect)
- **Retired Ports**: `:4000`, `:4001`, `:4002` (`LiteLLM` proxies — `0` listeners permitted on `4000–4002`; `46` files swept by `estate-router-sweep`).
- **Retired Launchd Plists**: `com.estate.litellm-*` (replaced by Dagster durable orchestration + `pennyd` `:4200` WAL checkpointing).
- **Enforcement**: Any prompt, diff, or manifest referencing `:4000`–`:4002` or `com.estate.litellm-*` is rejected at `0` tokens spent (`HTTP 422 ANTI_CONFUSION_RETIRED_GHOST_BLOCKED`).
