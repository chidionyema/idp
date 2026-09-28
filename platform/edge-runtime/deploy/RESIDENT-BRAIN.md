# The resident brain: a 14B on one node, and how to reclaim the room for it

**Read `docs/specs/2026-09-11-which-model-to-host.md` first.** This is the deployment half.

## What we are putting where

| Tier | Model | RAM | Runs on |
|---|---|---|---|
| **1 — expert** | Qwen3 1.5B + a task LoRA | ~1.1 GB | the `edge-runtime` pod, already deployed |
| **2 — resident brain** | DeepSeek-R1-Distill-Qwen-14B Q4_K_M | **~9 GB** | one node, as its own pod |
| **3 — hard calls** | 32B on free cloud | £0 | Kaggle / Tencent, when tier 2 abstains |

**Tier 1 is measured: 97.7% agreement at 17.5% abstain.** It is the default and it is nearly free.

## The arithmetic, so nobody re-argues it

- 2 nodes, **19 Gi allocatable each**, **no GPU**.
- **33.2 Gi is RESERVED** across running pods. The estate actually uses **~20 Gi**.
- **A 32B Q4_K_M is ~19 GB plus KV cache: it does not fit** alongside anything. At Q3 it is
  "noticeably" degraded. Do not force it onto a node and call it architect-grade.
- **A 14B Q4_K_M is ~9 GB and fits comfortably** once 9 Gi of REQUEST is reclaimed.
- **The 32B belongs on free cloud for the rare escalation**, not on a node we do not have.

## Reclaiming 9 Gi WITHOUT deleting a service

Every one of these keeps running; each stops reserving memory it never touches. Measured
2026-09-11 from `kubectl top` against `resources.requests`:

| Pod | Reserves | Uses | Reclaim |
|---|---|---|---|
| `hermes-agent-gateway` | 1088 Mi | 206 Mi | **882 Mi** |
| `langfuse-web` | 2048 Mi | 901 Mi | 1147 Mi — **but see the trap below** |
| `robusta-holmes` | 1024 Mi | 502 Mi | 522 Mi |
| `dagster-dagster-webserver` ×2 | 512 Mi each | ~130 Mi | 768 Mi |
| `agent-workforce` | 768 Mi | 466 Mi | 302 Mi |

**THE TRAP, and it is why this is a decision rather than a script:** `langfuse-web` is in the
**radio-room set** — the pods the kubelet evicts *last* — and the estate's `require-priority-class`
rule **refuses any container whose request differs from its limit** (Guaranteed QoS). The same is
true of `hermes-agent-gateway` and `robusta-holmes`. **Admission will reject the obvious edit.**

So a Kustomize patch must change request AND limit together, and the reclaim is bounded by what the
service needs at boot rather than by its steady state.

## How to do it

1. Edit the manifest that owns each workload (`platform/<area>/...`, never the live object — Flux
   reverts a `kubectl edit` and the change becomes invisible).
2. Change `requests` and `limits` to the SAME smaller number, or the Guaranteed rule refuses it.
3. `flux reconcile` the path, or wait for the interval.
4. Confirm: `kubectl describe node | grep -A2 "Allocated resources"` shows the freed memory.
5. Then apply `platform/edge-runtime/deploy/resident-brain.yaml`.

## What is NOT reclaimable, and should not be

- **ClickHouse** sits on both its ceilings servicing 395 pods. Its 4 Gi is real.
- **Prometheus** is the estate's alerting. Deleting it deletes the evidence the empirical-proof rule
  depends on — "quote a live log line" becomes impossible.

**A change that destroys the instrument cannot be verified. That is the rule that makes this a
right-sizing exercise and not a demolition.**
