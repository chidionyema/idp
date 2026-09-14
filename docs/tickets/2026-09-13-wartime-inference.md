---
id: wartime-inference-2026-09-13
title: Wartime multidimensional AI inference routing
status: proposed
opened: 2026-09-13
owner: pi-session
ledger_kind: spec
links:
  - docs/specs/2026-09-13-wartime-multidimensional-plan.md
  - docs/evidence/wartime-inference/PROOF-OF-WORK.md
  - https://gist.github.com/chidionyema/e95c9a06ec79743ba68677310fc1cd3e
---

# Wartime Multidimensional AI Inference Routing — Ticket

## Why now

The founder framed on 2026-09-13:

> "we are not yet commercial when we are we can drop it now now we need to surviv e and
> dont have the luxury to be dropping flippantly"

> "i need war time multidimensional planning and ultra intelligent well designed routing
> seamless and frictionless and the naths nees to nath"

The estate runs one router (LiteLLM, single gateway per THE HEADLINE). Free direct lanes
(Groq, Cerebras, OpenRouter, NVIDIA NIM, Gemini free tier) head every chain since
2026-09-10. The router is now a middle rung where spend accounting and tracing live.

This ticket captures the routing plan for the wartime period: 24/7 lights-on, $50/month
operational target inside the $150/month contract envelope, the best reasoning models
online, every staged path held (TwIL-LM3, Vast.ai, RunPod, llama.cpp, mistral.rs,
TurboQuant), nothing dropped flippantly. Commercial cutover drops staged tiers; the
founder names the cutover date.

## What this ticket owns

- Three live rings: paid frontier, free metered floor, cluster Ollama (proposed).
- Three staged tiers: TwIL-LM3 dev-only, burst GPU, llama.cpp / mistral.rs / TurboQuant.
- Four founder blockers (A/B/C plus the implicit Escalation OCI for GPU shape).
- A 5-step PR that lands the cluster Ollama Deployment + the model lane repoints.
- Empirical proof rule for any "WORKING" / "MEASURED_OK" claim on cluster Ollama.

## What this ticket does NOT own

- No second router (THE HEADLINE binds).
- No console-step credential minting (R52 binds).
- No drop of staged tiers (wartime framing binds).
- No 24/7 GPU (the pool has no GPU shape; escalation needed).
- No commit to the working tree (currently dirty — see blocker C).
- No push to a remote branch (pending founder permission per LAW 11).

## Acceptance

This ticket is DONE when:

1. The canonical spec at `docs/specs/2026-09-13-wartime-multidimensional-plan.md` matches the gist at the pinned URL byte-for-byte.
2. The estate twin (`bin/estate-twin-runtime --once`) reports three rings + three tiers.
3. `bin/idp-otto-homes` reports all three homes `MEASURED_OK`.
4. Blockers A/B/C are off the founder-action list.
5. The 5-step optimised PR merges green and the empirical proof rule has produced a quoted log line for an end-to-end Ollama-served turn.

Until all five are true, status remains `proposed`. Status moves to `in-progress` only when blocker A is greenlit; status moves to `merged` only when `bin/idp-otto-homes` reports `MEASURED_OK` for the cluster Ollama home and a real `router.outcome` event names `default=ollama-coder-7b`.

## References

- `docs/specs/2026-09-13-wartime-multidimensional-plan.md` — the plan.
- `docs/evidence/wartime-inference/PROOF-OF-WORK.md` — what was measured.
- The pinned web URL (gist): https://gist.github.com/chidionyema/e95c9a06ec79743ba68677310fc1cd3e
- `AGENTS.md` — the rules this ticket holds to.
