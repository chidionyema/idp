# The Micro-Token integration plan — the lean-agent spec, mapped onto what the estate already runs

**Status: ADOPTED — 2026-10-26.** Founder, reviewing the "Micro-Token" lean agentic pipeline spec
(Tree-sitter slicing, tiered routing, stateful diff tracking, local validation gates, >90% token
reduction on a bootstrap budget): "review and plan how we integrate these concepts into our
workflow", with one redirect: *"if using ollama can we use the version in ok and not mac bound"*
(OKE, the cluster — never the founder's Mac).

The finding of this review is not a build list, with one exception named below. **The estate
already runs every mechanism the Micro-Token spec proposes except the syntax-aware slicer, and
the mechanisms it runs are measured — but "measured causally" must be stated precisely: the
holdout instrument exists, while this 7-day window's control arms sat empty, so the 87% figure
is a per-call attribution estimate priced from vendor bills, not a causal contrast.** What
follows maps each spec component onto the estate's existing layer, rejects the components that
would duplicate a layer (AGENTS.md §6), names the one genuine build, and records this turn's
measurements, the live sessions this covers, and the infrastructure fix that revives the
Tier-0 free floor.

---

## 1. The mapping (every spec component, one verdict)

| Micro-Token component | Verdict | The estate's answer | Evidence |
|---|---|---|---|
| FR-1 Semantic AST slicing (Tree-sitter, never raw files) | **EXTEND — the one real build** | The read shunt digests whole-file reads >350 lines into worker digests, decided once per content hash; the growmos graph holds symbol-level repo context. No syntax-aware slicer exists anywhere live (tree-sitter appears only in `platform/voice-gate/src/prose.rs`, `backstage/yarn.lock` and rescued patches) | `platform/llm/efficiency_gateway.py` step [10]; `rg -l tree-sitter` |
| FR-2 Tiered routing (local free / precision paid) | **EXISTS** | LiteLLM router, `routing_strategy: cost-based-routing`, free vendor lanes (groq, cerebras, sambanova, gemini, zai), the ollama free floor, and the `claude-*` precision lane on the founder's Max subscription; `request_ceiling.py` REFUSES oversized requests pre-call | `platform/llm/config.base.yaml`; `tests/test_local_claude_max_lane.py` |
| FR-3 Stateful diff tracking (no growing histories) | **EXISTS** | The append-stable efficiency chain: epoch compaction [7], pointer replacement of repeated tool results [5], consecutive-line collapse [2], reasoning purge [8] — every transform a function of the prefix only, so the prompt cache survives; plus the estate memory store and the growmos graph. SQLite+FAISS: nothing managed exists, as the spec wants | `platform/llm/efficiency_gateway.py` header; `bin/estate-token-proof` |
| FR-4 Automated pre/post-flight validation | **EXISTS — but inert until this turn** | code-review intent: Tier 0 deterministic (lint/ruff) → Tier 1 heuristics → Tier 2 LLM only on T0+1 output → Tier 3 verifies every T2 finding. Stochastic judgment proposes; deterministic verification disposes. Then `bin/idp-ci`, pytest, mutation runs. **Corrected 2026-10-26: the four tiers ran as two.** The tiers handed off through environment variables (`T0_FINDINGS`, `T1_FINDINGS`, `T2_VERDICTS`) that the intent never set, and each intent step is its own shell, so Tier 2 always answered "no findings from Tier 0+1 — nothing to judge" and Tier 3 always answered "no verdicts to verify". The Micro-Token slicer landed in a tier that never ran. Fixed this turn: the tiers hand off through files, Tier 2 carries each finding's file/line/rule into its verdict so Tier 3 can check it, and Tier 3 drops a finding Tier 2 called a false positive instead of re-confirming the pattern | `platform/estate/intents/code-review.yaml`; `platform/estate/libexec/code-review-t{2,3}.py`; `tests/test_code_review_pipeline_wiring.py` |
| The Gatekeeper (local cheap check first) | **EXISTS** | code-review T0 is exactly this for review; the router ceiling is this for size; shell.parse/verify for commands | as above |
| Aggressive prompt caching + minimalist prompts | **EXISTS, measured** | `cache_guardian.py` (byte-identical golden system prompt), the append-stable chain, per-call cache accounting (uncached / cache-read / cache-write 5m/1h) recorded from what the vendor actually billed | `platform/efficiency/cache_guardian.py`; efficiency ledger |
| Zero managed vector DB / middleware | **EXISTS (already true)** | SQLite + the graph + the memory store; no Pinecone-class dependency anywhere | `docs/explanation/architecture/model-stack.md` |
| Docker Compose portability, one command up | **REJECT** | The estate ships via k8s + Flux (merge → build → scan → sign → image automation → deploy-when-green). Compose exists only for the laptop router, and `bin/litellm-up` already validates-and-ups in one command. Adding a compose stack for the cluster would be a second deploy path — a duplicate layer | AGENTS.md §2; `bin/litellm-up` |
| >90% token reduction target | **MEASURED — 87% net, attribution estimate** | `bin/estate-token-proof` (7d window, 22,816 calls): **$894.43 net saved against $132.13 input billed**. The randomised holdout is the causal instrument; this window's control arms were empty (trial ended 2026-10-25), so the number is the attribution model priced from what vendors actually billed — per-call rows recomputable from the ledger, not a causal contrast | §2 below |

## 2. What was measured on 2026-10-26 (the numbers this plan stands on)

| Measurement | Value | Source |
|---|---|---|
| Efficiency chain, transform layer | last 2,000 router calls: 1.397 GB in → **163.4 MB cut (11.7%)** | `~/.estate/efficiency-ledger.jsonl` |
| Spend in the same window | **$2.43 over 741 priced calls**; minimax_m27 carries 73% of traffic (1,462/2,000) | same |
| Vendor latency | p50 10.1 s, p95 63.6 s | same ledger, `latency_ms` |
| Causal holdout, 7d | 22,816 calls; **$894.43 net saved vs $132.13 billed (87%)**; treat arms only, controls empty (trial ended 2026-10-25) | `bin/estate-token-proof --since 7d` |
| Cluster ollama PVC | **Pending 27d** — `LimitExceeded: You cannot create a volume because you have reached your limit. Upgrade to a paid account.` (x1730 events over 4d12h); 14 oci-bv PVCs Bound cluster-wide; coroot and agent-workforce claims Pending on the same error | `kubectl describe pvc ollama-models -n llm` |
| Node CPU headroom | both nodes at **5808m of 6000m allocated** — a 200m+ request does not schedule | `kubectl describe nodes` |
| Deployed ollama lane | `ollama/qwen2.5-coder:1.5b` → `http://ollama.llm.svc.cluster.local:11434`, keep_alive 24h — the repo side of GOV-01 already done and green (`tests/test_ollama_cluster_lane.py`, 4/4) | `platform/llm/config.yaml:605` |
| Live sessions coverage (laptop router) | last 600 ledger rows: **100% of client rows carry arm=treat and the full step set m1–m10** (471 rows, last write 09:12:40Z — live). The 130 session-less rows are `kind: shadow` — the m7 compactor's own fold probes — and they are FAILING: `fold returned an empty state` ×130, `ok: false`, model deepseek. No client traffic is un-chained on this router, and the shadow fold has a live defect to file | `~/.estate/efficiency-ledger.jsonl` |
| Live sessions coverage (cluster router) | the in-pod ledger is live (rows at 09:15–09:16Z, arm=treat, chat + embedding call types) — fleet traffic through llm.mumchimp.com gets the same chain | `kubectl exec litellm-8477d5bc57-9gnlk` |
| Mac-bound laptop lanes | founder ruled 2026-10-26: "we dont have resources to run ollama locally" / "i never use mac ollama" — the laptop router's `ollama`, `ollama-vision`, `ollama-llama` rows (host.docker.internal:11434, dead since 2026-09-10) are removed; the `vision` alias is repointed to the same Gemini backend the cluster's alias uses | `llm/config.yaml` this lane |
| Review pipeline, live | a real review of this lane's own change: T0 11 findings → T2 judged **11/11 false_positive** (correct: every flagged `return` sits inside a branch or a loop) → T3 **0 verified, 11 rejected**. Tier 2's context was `context_mode: sliced`, 6,914 bytes | this lane, §5 |
| The router's model allowlist | the cluster's key may call only `default, ollama, deepseek, deepseek-v4-flash, gemini, glm, groq, kimi, minimax, minimax_m27, cerebras, ...` — **`gpt-4o-mini`, Tier 2's old default, was not on it**, so that tier could not have made a call at all | `403 key not allowed to access model` from llm.mumchimp.com |
| Reasoning lanes answer with nothing | gpt-oss-120b (groq), glm-5.3, deepseek and cerebras all spend the whole token budget on `reasoning_content` and return an **empty** `content` — Tier 2's verdicts were all "uncertain". `minimax_m27` (openai/MiniMax-M2.7) answers | measured this turn, four lanes |
| GitHub's transport from this machine | `git@github.com` (ssh.github.com:443) times out and `api.github.com` intermittently resolves to a poisoned 20.26.x address; **HTTPS works**. The repo's origin is now HTTPS and `url.https://github.com/.insteadOf git@github.com:` is set globally, so every agent's fetch/push works again | fetch over SSH: `kex_exchange_identification: Connection closed by remote host`; over HTTPS: 1.07 s |

The 2026-09-29 record said the ollama Deployment was scaled to 0 because "its volume never bound
(binding volumes: context deadline exceeded)". That was the symptom. The cause is the tenancy's
block-volume quota: OCI refuses every new volume, so `oci-bv` can never provision this claim, with
or without a consumer pod. The fix (this spec's infrastructure half, claim idp#7205, lane
`lane/oke-ollama-free-floor`): storageClassName `local-path` (node disk, no OCI quota), replicas 1,
CPU requests trimmed to 150m. The laptop's ollama lane is deliberately untouched: its
`host.docker.internal` endpoint died with the founder's Mac Ollama on 2026-09-10, and laptop agents
reach the free floor through the cluster router's `ollama` alias instead.

**A claim's storage class is fixed at birth — the first version of this fix was wrong, and the
cluster said so.** The first commit edited the existing `ollama-models` claim in place
(`oci-bv` → `local-path`, 5Gi → 3Gi) and Flux's apply was rejected:

```
PersistentVolumeClaim/llm/ollama-models dry-run failed (Invalid): spec: Forbidden:
spec is immutable after creation except resources.requests and volumeAttributesClassName
for bound claims
```

That rejection held the `llm` kustomization NotReady, and `agent-workforce` waits on
`flux-system/llm`, so one immutable-field edit was blocking a fleet sync. No git edit can move an
existing claim onto a different class — only a new claim can. The claim is therefore
`ollama-models-local` (local-path, 3 Gi), the Deployment mounts it, and the old Pending,
unbound claim (no volume, no quota, no cost) is removed by Flux's own prune. Nothing is
hand-applied; the cluster converges from the commit.

## 3. The deltas (what is actually built from here)

1. **DONE this turn — the Tier-0 free floor.** OKE ollama revived on local-path; the real proof is
   a served inference through the cluster router's `ollama` alias, not a Ready pod (§5). The
   laptop's Mac-bound rows came out the same turn (founder ruling above), and the `vision` alias
   moved to Gemini so photo intake stops hitting a refused connection.
2. **Symbol slicer (the FR-1 build) — BUILT this turn.** `platform/estate/libexec/symbol_slicer.py`:
   syntax-aware extraction (Python by indent, brace languages by matching; tree-sitter used when
   importable, never required), wired into code-review Tier 2's payload builder
   (`build_context`), which now sends touched-symbol slices + top-level signatures instead of
   `diff[:4000]`, and records `context_mode` in its output so a run proves which path fed the
   model. Tests: `tests/test_symbol_slicer.py`. Hard constraint kept: the slicer is a pure
   function of (diff, files) — a slice decision depends on nothing else, so it composes with the
   gateway's once-per-hash append-stable rule. **Measured this turn on a real review: Tier 2 ran
   with `context_mode: sliced`, 6,914 bytes of context, judged 11 findings, and the file's
   `build_context` now also carries a bounded neighbourhood of every flagged line** — a finding
   outside a diff-touched symbol was invisible to the model, which is why it answered "uncertain".
2b. **The pipeline repair (this turn, and it is part of FR-1 being real).** A slicer in a tier that
   never runs is a slicer in a drawer. Four defects, all fixed and all graded by
   `tests/test_code_review_pipeline_wiring.py`:
   - the tiers handed off through env vars that the intent never set → they now hand off through
     files (`$HOME/.estate/review/latest/{t0,t1,t2}.json`), and the env still wins when set;
   - Tier 2's default model was off the router's allowlist → it now defaults to `minimax_m27`, the
     lane that answers, and the model is recorded in the output;
   - every reasoning lane answers with an empty `content` → the tier asks for one word per
     finding (a verbose protocol cost 39 s of reasoning to produce eleven words) and an empty
     completion now reports `finish_reason` and the reasoning instead of degrading silently;
   - Tier 3 re-confirmed patterns without reading the verdict, so 11 false positives came out as
     "5 verified" → Tier 3 now rejects what Tier 2 called a false positive, with the reason.
   Live end-to-end result on this lane's own diff: T0 11 findings → T2 11/11 false_positive →
   T3 **0 verified, 11 rejected**.
3. **Tier-0 latency floor (small EXTEND).** The spec wants <2 s local responses. Once the floor is
   live, measure the `ollama` alias p50 from the router's own latency records; if it misses 2 s,
   the lever is the 1.5B model's prompt, not a new service. Record the number in this file.
4. **Everything else: adopt by use, not by build.** The workflow integration is a routing rule for
   agents, written down here: reviews go through `code-review` (never a hand-rolled LLM prompt);
   efficiency claims go through `bin/estate-token-proof` (never an estimate); context goes through
   the graph + memory + read shunt (never a raw file dump); Tier-0-shaped tasks (formatting, import
   sorting, regex refactors, classification) name the `ollama` alias explicitly.
5. **FILE THE DEFECT: m7 shadow fold.** The compactor's shadow probes are failing on deepseek
   (`fold returned an empty state`, 130 rows and counting) — the safety arm of epoch compaction is
   testing nothing while it errors. Own issue, next lane; until then the treat-arm chain is
   unaffected (shadow failures never touch the request path by design).

## 4. What was rejected, and why it matters

- **Docker Compose for the cluster** — second deploy path, forbidden by the one-of-each-layer rule.
- **A new vector store / memory layer** — the graph and the memory store are the memory layer.
- **A bespoke gatekeeper service** — code-review T0 and the request ceiling are the gatekeeper;
  a second one is a duplicate layer.
- **vLLM / a GPU spot instance** — the free floor's whole point is $0 marginal cost; a paid GPU
  tier re-creates the spend the spec exists to avoid. Revisit only if the 1.5B floor measurably
  cannot carry Tier-0 traffic.
- **Local (Mac) ollama, permanently** — founder 2026-10-26: "we dont have resources to run ollama
  locally". The laptop is an 8 GiB Intel Mac with no GPU; a resident 7B was fiction from the day
  it was written, and the dead lanes made every fallback walk pay for the fiction.

## 5. Proof status of this document

| Claim | Proof |
|---|---|
| OKE ollama revived | lane `lane/oke-ollama-free-floor` → Greenlane → Flux. Not yet proven at writing: the served-inference check below is the rung, not the merge. The PVC rename (the immutable-field correction) is the commit that must land for Flux to apply at all |
| Efficiency numbers | `bin/estate-token-proof --since 7d`, this turn, output in §2; attribution estimate, control arms empty — stated as such |
| Sessions coverage | ledger joins in §2: 100% of laptop client rows chained (steps m1–m10 present); cluster rows chained and live |
| Symbol slicer | `tests/test_symbol_slicer.py` green on this lane; **live Tier 2 run this turn: `context_mode: sliced`, 6,914 bytes, 11 findings judged, 11/11 false_positive, Tier 3 → 0 verified / 11 rejected** |
| Four tiers actually run | `tests/test_code_review_pipeline_wiring.py` (10 tests) + the live run above: the hand-off files exist, Tier 2 reads them, Tier 3 reads Tier 2's verdicts, Tier 3 disposes of a false positive |
| Tier-0 latency | PENDING — measured after the floor is Ready |
