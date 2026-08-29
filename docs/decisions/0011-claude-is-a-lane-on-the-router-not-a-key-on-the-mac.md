# 0011. Claude is a lane on the router, not a key on the Mac; the Claude Code subscription stays on the Mac and is not a platform layer

- Status: PROPOSED 2026-08-29 (crew#568 phase 1; the founder's word on the default road comes after the soak in crew#617).
- Date: 2026-08-29
- Deciders: founder (which road is the default after the soak), session f3f21d6e (the research, crew#617)
- Affects: `platform/llm/config.yaml`, `llm/config.yaml`, `platform/vendors/consoles.yaml`, `platform/llm/external-secret.yaml`; every caller that names a model; crew#568, crew#617.

## The day, in plain words

Two things on the estate answer to the word "Claude". One is the Claude Code subscription on the
founder's Mac: a person's tool, signed in with his account, with no API key and no way for a pod
to call it. The other is the Anthropic API, which any workload can call with a key. The spec
(crew#617, "two roads, one router") asked which of these a workload should use, and where the key
lives when it does.

### Road A, the Claude Code subscription

Stays exactly where it is. It is a person's tool on a person's machine; it cannot be a lane on the
router because Anthropic offers no API for it, and a pod that shells out to a laptop is the Mac-
bound infrastructure the founder retired (memory `infra-never-mac-bound`, 2026-08-25). Nothing in
the platform depends on it; nothing in the platform is allowed to.

### Road B, chosen: Claude is two lanes on the one router

`platform/llm/config.yaml` gains `claude` (claude-sonnet-5) and `claude-fast`
(claude-haiku-4-5-20251001), both reading `ANTHROPIC_API_KEY` from the `litellm-upstream` vault
entry. The key is born once, by `bin/idp-bootstrap-vendors`, from the `SEED_ANTHROPIC_API_KEY`
repository secret the founder set (R52; `platform/vendors/consoles.yaml` now lists
`litellm-upstream` as a target). The laptop router carries the same two lanes
(`tests/test_llm_row.py` holds the two files to one hosted set), so a laptop caller and a pod
caller name the same lane and get the same model, the same spend row and the same trace.

A caller that wants Claude asks the router for `claude`. It never holds the key. Rotation is one
vault write; revocation is one deleted key; spend is one Langfuse row per lane.

### Road C, rejected: Claude through OpenRouter

One key already in the vault (`OPENROUTER_API_KEY`) and no vendor onboarding, but the OpenRouter
account has been dry since 2026-08-27 (crew#506 CP1), every OpenRouter lane sits in no fallback
chain, and a middleman on the frontier model is a second bill and a second outage surface for the
one lane the founder will read the most.

## The fallback chain

`claude -> [minimax, deepseek]`, `claude-fast -> [claude, deepseek]`: the same shape as every
other chain (crew#506 CP1), ending in the cheap model (sovereign cp30). A Claude turn that meets a
4xx/5xx does not fail; it degrades to the funded direct lanes.

## Consequences

- Hermes, prospector, KINI and any agent file name `claude` or `claude-fast`; none of them holds
  `ANTHROPIC_API_KEY` for itself. The two direct targets (`prospector-engine-env`,
  `hermes-agent-env`) stay until each product is moved to the router lane (crew#568 phase 2).
- The soak (crew#617) measures the two lanes against MiniMax and DeepSeek on the trustworthy row
  before the founder picks the default road.
- LAW 34 holds: the vendor name appears in one place, the lane's `model:` line; a caller sees a
  lane name.

Matrix: claude-on-the-router (`docs/decisions/decision-matrix.yaml`).
