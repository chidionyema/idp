<!-- estate:historical current=platform/router-edge/CONTEXT_GOVERNANCE.md -->
# Meridian Estate-Wide Context Governance & Fleet Adoption Kit (`v1.0.0`)

One-shot, zero-external-dependency, multi-runtime control plane enforcing tight,
cache-coherent context budgets across **all estate surfaces** (`meridian-router-edge`,
Cline, Codex CLI, OpenCode, `agent-sandbox`, Legion 8, `brain-hub`, `lifeboat`) with
zero mid-transaction interruptions.

## Edge Cases Hardened Mechanically (10/10 Covered in Test Suite)

1. **Streaming SSE / Mid-Tool-Call Cutoff:** Budget evaluated strictly at ingress; never truncates mid-stream.
2. **Atomic Critical-Section Interruption:** Bounded, non-renewable `X-Meridian-Critical-Section` lease (+15% headroom, max 2 turns) lets commit/push/rollback finish atomically.
3. **Heterogeneous Provider Tokenizer Drift:** Conservative safety multipliers per model family + exponential moving average calibration from live provider `usage.prompt_tokens`.
4. **KV-Cache Prefix Thrashing:** Computes `prefix_sha256` on Turn 1; flags `ERR_KV_PREFIX_THRASH` on any mid-session prefix/tool mutation; all dynamic directives emit strictly via `X-Meridian-*` headers.
5. **Multimodal / Screenshot Explosion:** Accounts for base64/tile image tokens and externalizes images older than `N=1` turn to hash-addressed pointers.
6. **Sub-Agent / Legion Fan-Out Amplification:** Enforces `<= 4k` compiled brief on sub-agent Turn 1 plus hierarchical `mission_aggregate_cap` across all child sessions.
7. **High-Reasoning Burn on Mechanical Ops:** Router transparently clamps `reasoning_effort` (`low` for `role:ops-dispatch`) and `max_tokens` in `SOFT_ROTATE`/`ENFORCE` phases.
8. **BudgetLedgerDO Storage Outage:** Degrades fail-open (`budget_ledger_unavailable_fail_open`) rather than causing self-inflicted inference downtime.
9. **Compaction Invariant Amnesia & Failure-Trace Erasure:** Externalizes >4 KB tool payloads to recoverable file pointers while pinning the last 15 lines of failure traces verbatim; validates rotation handoff packets for mandatory invariants (`mission_id`, `target_sha`, `acceptance_receipt_contract`).
10. **Memory Probe Pollution & Stale Authority Injection:** Pre-slice filter quarantines `self-test`/`probe` namespaces and restricts recall strictly to `authority_status == CURRENT`.

## Zero-Interruption Delivery & Fleet Adoption

1. **Stage immediately (independent of `idp#8416`):** Land this kit in `chidionyema/idp` with `rollout_phase: "SHADOW"`, run `bin/estate_context_fleet_sync.py --compile` to slim `.clinerules` and `AGENTS.md` below 1,500 tokens, and activate `context-budget-gate.yml` on PRs.
2. **Gateway Gravity (after `idp#8416` HTTP 200):** Wire `ts/context-budget-middleware/index.ts` into `meridian-router-edge` (`BudgetLedgerDO`), remove raw upstream provider keys from client workstations, and issue `MERIDIAN_CLIENT_KEY` only so every fleet surface adopts automatically with zero bypass.
3. **Evidence-Gated Phase Promotion:** `SHADOW` (Days 0-3, observe-only) -> `SOFT_ROTATE` (Days 4-7, role clamping + soft rotation headers) -> `ENFORCE` (Day 8+, gated on 7 days of zero false-positive interruptions and >=75% KV-cache hit ratio).
