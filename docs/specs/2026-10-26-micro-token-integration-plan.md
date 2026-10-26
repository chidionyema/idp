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
3. **Tier-0 latency floor (small EXTEND) — DONE.** The spec wants <2 s local responses. Measured
   2026-10-26 through the cluster router (`POST https://llm.mumchimp.com/v1/chat/completions`,
   `model=ollama`): **1.008617 s** warm, HTTP 200, `cost_usd: 0.0` in the cluster's own ledger. The
   first call after the pod started was 155.4 s while the 1.5B weights loaded into RAM; with
   `keep_alive: 24h` the warm number is the one to hold the line on. If it ever misses 2 s, the
   lever is the 1.5B model's prompt, not a new service. The number is recorded in §5.
4. **Everything else: adopt by use, not by build.** The workflow integration is a routing rule for
   agents, written down here: reviews go through `code-review` (never a hand-rolled LLM prompt);
   efficiency claims go through `bin/estate-token-proof` (never an estimate); context goes through
   the graph + memory + read shunt (never a raw file dump); Tier-0-shaped tasks (formatting, import
   sorting, regex refactors, classification) name the `ollama` alias explicitly.
5. **FILE THE DEFECT: m7 shadow fold — FIXED IN THIS LANE.** The compactor's shadow probes were
   failing on deepseek (`fold returned an empty state`; **1,369 failing rows** measured on the
   laptop ledger, every one of them `model: deepseek`) — the safety arm of epoch compaction was
   testing nothing while it errored. Cause: deepseek is a reasoning lane, it spends its whole
   budget on `reasoning_content` and returns an EMPTY `content`, and an empty completion is a
   200, so LiteLLM's fallback chain never engaged. Fix in this lane: the fold's default lane is
   `minimax_m27` (the lane that answers), a `reasoning_content` answer is used when `content` is
   empty, and an empty fold now names the lane that failed. Graded by
   `tests/test_efficiency_shadow_fold_answers.py` (6 tests). The treat-arm chain was never
   affected — shadow failures never touch the request path by design.

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
- **Bloop, or any self-hosted code-search/index service** — the estate already owns the same
  information as a DETERMINISTIC ARTIFACT, not as a service: `bin/catalog-projection` emits one
  `dependsOn` edge per import (TOT) as a pure function of the tree (DET); the capability registry
  is defined the same way, with a drift check; the cross-repo view is the growmos graph. A
  self-hosted indexer would be a second copy of a layer that exists (AGENTS.md §6), and the worst
  kind of copy: an unsynchronised one whose answers to "who calls this" would drift from the
  bytes CI grades, with no drift check and no proof of freshness. If the query ergonomics are
  needed, the sanctioned extension is a thin QUERY INTENT over those committed artifacts.
- **Vendoring Aider** — its repo-map idea is already here in estate-native form (§6): a symbol
  map for LLM context (`symbol_slicer.py`), an import-edge graph (`catalog-projection`), and an
  impact map (`idp-affected-graph`). Vendoring Aider would add a second, differently-behaving
  map of the same tree.

## 5. Proof status of this document

| Claim | Proof |
|---|---|
| OKE ollama revived | **PROVEN, end to end, 2026-10-26 13:42–14:05Z.** The cure landed through the estate's own path: lane `lane/oke-ollama-free-floor` → Greenlane PR **#7228** (merged 13:42:37Z, commit `b1c95512f`) → Flux `kustomization/llm` applied `main@sha1:b1c95512f` (Ready=True, `ReconciliationSucceeded`). The `ollama-models-local` claim was **pruned** (no claim at all now), the Deployment's volumes are `emptyDir` 3Gi + 256Mi, and the pod `ollama-74784f44f7-xh67t` is **1/1 Running** on arm64 node `10.0.148.221` after the init container pulled `qwen2.5-coder:1.5b` (986 MB) in 81 s. **Served inference:** `POST https://llm.mumchimp.com/v1/chat/completions` with `model=ollama` → HTTP **200** in **1.008617 s**, body `{"model":"ollama", "content":"ready"}`; the cluster's own ledger row for that call carries `model: ollama`, `cost_usd: 0.0` — a local answer, no paid-vendor fallback. Cold latency was 155.4 s (the model loading into RAM); warm is 1.01 s. The causal chain that got it there: the OCI block-quota was exhausted (`LimitExceeded`), then the `local-path` provisioner was refused by Kyverno's `restrict-volume-types` (it creates `hostPath`), and the cure was the one volume type the policy allows and no provisioner needs — `emptyDir` |
| Shadow fold fixed | The last `fold returned an empty state` row is **2026-10-26T13:58:34Z** (`model: deepseek`, `ok: false`, `state_chars: 0`). After the fix reached the runtime, **11 consecutive shadow folds succeeded**: `model: minimax_m27`, `ok: true`, `state_chars: 6000/5794`, `covered_msgs: 114–297`. Zero empty-state failures since. The cure was the lane's `minimax_m27` default plus the `reasoning_content` fallback: deepseek spends the whole budget on reasoning and returns an empty `content`, and LiteLLM counts that as HTTP 200, so the fallbacks never engaged |
| Tier-0 latency | **Measured 2026-10-26**: the OKE free floor answered a real completion in **1.008617 s** (warm; 155.4 s cold, while the 1.5B weights loaded into RAM). The cluster ledger row for that call: `model: ollama`, `cost_usd: 0.0`. Floor served by `platform/llm/ollama.yaml` on the always-free arm64 pool |
| Efficiency numbers | `bin/estate-token-proof --since 7d`, this turn, output in §2; attribution estimate, control arms empty — stated as such |
| Sessions coverage | ledger joins in §2: 100% of laptop client rows chained (steps m1–m10 present); cluster rows chained and live |
| Symbol slicer | `tests/test_symbol_slicer.py` green on this lane; **live Tier 2 run this turn: `context_mode: sliced`, 6,914 bytes, 11 findings judged, 11/11 false_positive, Tier 3 → 0 verified / 11 rejected** |
| Four tiers actually run | `tests/test_code_review_pipeline_wiring.py` (10 tests) + the live run above: the hand-off files exist, Tier 2 reads them, Tier 3 reads Tier 2's verdicts, Tier 3 disposes of a false positive |
| THE RUNTIME PATH, not the worktree | The real `code-review` intent, through the estate's own door, on the DELIVERED runtime (`~/.estate/libexec`): Tier 0 → 5 findings (4 `unreachable-after-return`, 1 `empty-catch`); Tier 1 → 0; Tier 2 → `context_mode: sliced`, `context_bytes: 2999`, `model: minimax_m27`, 5 findings judged, answer `["false_positive","false_positive","false_positive","false_positive","real"]`; Tier 3 → **0 verified, 5 rejected** — the four false positives disposed on Tier 2's verdict, and the one "real" verdict DISPOSED AGAINST the model, because the deterministic re-check did not confirm the pattern. "Stochastic judgment proposes; deterministic verification disposes", measured, not asserted |
| Runtime delivery | `~/.estate/runtime/idp` advanced `06953453 -> 4b2ecd88` (main) and `stage()` copied the tree's `platform/estate/{intents,libexec}` into `~/.estate`: `~/.estate/libexec/symbol_slicer.py` present, `code-review-t2.py` at `MODEL = minimax_m27`, `~/.estate/intents/code-review.yaml` writing `$HOME/.estate/review/latest/t{0,1,2,3}.json`. The laptop router carried no lane bound to `host.docker.internal` (the Mac ollama lanes are gone). Router health: `:4000/health/liveliness` 200 in 0.06 s; `minimax_m27` answered a live call in 4.3 s with non-empty content. Re-delivered after the merge: runtime tree `06953453 -> 4b2ecd88 -> b1c95512`, `SHADOW_MODEL = minimax_m27` in the runtime copy, router `:4000/health/liveliness` 200 in 0.255 s after the estate's slot-swap restart (the new router boots beside the live one and takes over only once it answers, so no caller is refused) |
| Why the runtime had been stale for 2h40m | MEASURED CAUSE, not a mystery: the laptop's load average was 94–153 and the fleet's load-gate skipped every job — 2,011 skips logged on 2026-10-26 — so `ai.estate.runtime-sync` (a 300 s launchd job) had not run since 10:15:53Z. The gate was right to refuse; the estate's own sync was then run once by hand to deliver main, and the router survived the restart (`:4000` 200 afterwards) |
| Symbol map + cross-file graph | `bin/catalog-projection` (every import → one `dependsOn` edge), `bin/idp-affected-graph` (three-layer impact map), `symbol_slicer.py` (LLM-context map). Invariants: `bin/test-catalog-projection` (run by `bin/idp-ci`) |
| Impact map in the PR path | **NOT ENFORCED — measured gap.** No workflow references `idp-affected-graph` (`rg -l "idp-affected-graph" .github/` → no hits); fast-gate runs `IDP_CI_FAST=1 bin/idp-ci`, verifier runs `bin/idp-ci-verify`. The selector works — live on this lane's own diff: `changed=3 file(s)`, `selected 1 test file(s)` — but nothing in CI runs it. Recorded as the next piece of work, not smuggled into this lane |
| The laptop's rendered config had DRIFTED from its source | **Measured defect, found and fixed in this lane.** `bin/idp-vendor-render --check` was RED on main: `FAIL vendor-render llm/config.yaml does not match a render from the registry`. The cause: the three Mac ollama lanes had been removed from the RENDERED `llm/config.yaml` but not from its SOURCE `llm/config.base.yaml`, so the next render by anyone would have put `host.docker.internal` back into the laptop router — undoing the founder's ruling. Fixed source-first: `llm/config.base.yaml` and `platform/llm/config.base.yaml` edited, then the estate's own renderer regenerated both rendered files; `bin/idp-vendor-render --check` is green for both. The rendered file had also carried a duplicated comment line and a stale "ollama is last because it is local" note, both of which the re-render removed |
| The render check is not wired into CI | **Measured gap.** `rg -ln "idp-vendor-render" bin/ .github/workflows/` returns only the script itself: nothing runs `--check`, even though the header of both rendered files promises "bin/idp-ci fails when this file and a fresh render differ". That is how the drift above reached main. The rung belongs in `bin/idp-ci`; it is not in this lane's claim, and a claim is the price of touching that file. Recorded, not smuggled |

## 6. Two ideas the estate already owns: Aider's repo-map, and Bloop

Recorded 2026-10-26 as a decision record (also on chidionyema/idp#7205).

**Aider's repo-map** — a Tree-sitter symbol graph of the whole codebase (symbols, definitions,
cross-file dependencies), run in CI to catch a PR that breaks cross-file boundaries. The estate
has all three pieces already, in its own vocabulary:

| Aider's piece | The estate's equivalent | Where it is proved |
|---|---|---|
| repo-map: symbols + cross-file deps | `bin/catalog-projection` — pure, total, deterministic over Python source; every `.py` → one Component, every import → one `dependsOn` edge or one logged drop; DET/IDP/REF/SCH invariants | `bin/test-catalog-projection`, run by `bin/idp-ci` |
| "does this PR break cross-file boundaries?" | `bin/idp-affected-graph` — three-layer impact map (AST+import edges / prompt+schema / graph-topology closure); fail-open by construction: skipped only on a NO verdict strictly below threshold, equality runs, a missing graph produces RUN | live on this lane's diff: `changed=3 file(s)`, `selected 1 test file(s)` |
| repo-map as LLM context | `platform/estate/libexec/symbol_slicer.py` (FR-1) — touched symbols + dependency signatures; Tree-sitter optional, deterministic fallback otherwise | `tests/test_symbol_slicer.py`; live Tier 2: `context_mode: sliced`, 6,914 bytes |
| **repo-map, already built, in ZeroEdge** | **`~/Documents/code/zeroedge-repo/src/ttcs/ast_manager/`** — `graph.py` builds a `CodeGraph` (`Symbol(name, path, kind, start_line, end_line, imports)`, `called_by`, `reverse_deps(name)`); `slicer.py`'s `slice_symbol(graph, name)` returns "the source of `name` plus the sources of its reverse dependencies" under a 400-line cap; `parser.py` is the optional Tree-sitter parser (python, typescript, tsx, go, rust) whose docstring already states the estate's doctrine: "tree-sitter is an optional dependency of the harness; without it, callers that need a real tree raise here and **the AST slicer falls back to signature-only graphs**" | ZeroEdge repo, `src/ttcs/ast_manager/{graph,slicer,parser}.py`; its tests under `tests/ttcs`; a TLA+ spec for the node lifecycle in `specs/ttcs_node_lifecycle.tla` |

**Enforcement — the one missing piece.** The capability works; nothing in the PR path calls it.
The sanctioned fix is a RUNG, not a service: a rung in `bin/idp-ci` that runs
`bin/idp-affected-graph --plan --base <base>` and FAILS when a changed symbol's dependents are
not in the selected set — a selection-completeness assertion, which is Aider's CI check written
in the estate's safety property (unknown → RUN → FAIL, never skip). It stays a pure function of
the tree, so the same diff selects the same tests everywhere.

**The estate ALREADY OWNS THE BLOOP ANALOGUE, AND IT IS DEPLOYED: ZeroEdge's TTCS.** ZeroEdge
is a provider-agnostic LLM cost-optimization gateway that the estate already runs as a
Deployment in the `llm` namespace (`platform/llm/zeroedge.yaml`; the router reaches it over a
flat shim, `GET /health` and `POST /optimize`, failing open with a 2 s timeout). Its `src/ttcs/`
tree is a tree-sitter code-search harness: `ast_manager/parser.py` (multi-language Tree-sitter,
optional), `ast_manager/slicer.py`, `ast_manager/graph.py`, `git_ops/`, `memory/`, `state/`,
`models/`, `verification/prm.py`, with a formal node-lifecycle spec in TLA+. So "a self-hosted
Rust code-search engine that parses codebases into AST code graphs" is not a gap to fill — it
exists, in Python, inside a component the estate already ships. The one thing Bloop would add
that TTCS does not expose is QUERYABILITY from an agent: the deployed ZeroEdge HTTP surface is
`/health` and `/optimize` only, and the graph is not served.

**What to incorporate, concretely (and what NOT to build).**

1. **Do not write a fourth code-graph implementation.** The estate now has three code-graph
   shapes in play — `catalog-projection` (Python, pure, deterministic → Backstage `dependsOn`
   edges), TTCS `ast_manager` (multi-language, Tree-sitter → `CodeGraph` + reverse deps), and
   `symbol_slicer.py` (per-diff slices for the review path). Under AGENTS.md §6 that is one
   layer with three implementations, and it needs ONE declared owner before anything else is
   added. The honest ownership: **whole-repo graph and search = ZeroEdge's TTCS `ast_manager`**;
   **the catalog's edge artifact = `catalog-projection`** (it is a pure function of the tree and
   CI grades its invariants); **per-diff review context = `symbol_slicer.py`**, which must not
   grow a second whole-repo graph.
2. **The bridge to the estate's own packages already exists**: `packages/idp_concurrency/
   src/idp_concurrency/ttcs/__init__.py` today exposes only `ShadowMemory`/`Triplet`. Exposing
   TTCS's graph there (or a thin query over it) is how the review path and the agents consume
   the graph without vendoring a second parser.
3. **The walk engine is the estate's, not Bloop's**: `idp_concurrency.dag.TopologicalDAG`
   (graphlib) proves acyclicity before a single cycle runs, and its own docstring says "every
   request through ZeroEdge and every search through TTCS instantiates a DAG whose acyclicity is
   proven". Any new graph traversal (a compact codebase map, a cross-file impact closure) should
   be a DAG walk on that engine, with the acyclicity check kept as the fail-closed step.
4. **Keep Tree-sitter optional, everywhere, as the estate already decided.** TTCS's parser
   docstring is the doctrine: without Tree-sitter the AST slicer falls back to signature-only
   graphs. `symbol_slicer.py` follows the same rule. The corollary for CI: a gate may not
   require a native parser, and the fallback must be covered by a test — which is why
   `tests/test_symbol_slicer.py` grades the fallback path rather than assuming it.
5. **The one thing still missing is the query surface, and it is an intent, not a service.**
   Bloop's real value is an agent asking "who calls this" before judging a PR. The sanctioned
   shape is a thin intent over the artifacts the estate already commits (the projection's edges,
   the registry, the graph), so the answer is derived from the bytes CI grades. NOT a daemon
   with its own index.
6. **The enforcement gap is unchanged and is the piece worth building next**: the impact
   selector exists and works, and no workflow runs it. A rung in `bin/idp-ci` asserting
   selection completeness is the Aider CI check, written in the estate's safety property.

**Bloop** — a self-hosted Rust code-search engine parsing the codebase into an AST code graph so
local agents can query the wider architecture before judging a PR. **Rejected: do not run it, and
do not run anything like it.** §4 gives the reason in full. The estate's version of "query the
architecture" is a query surface over committed, gated artifacts — the projection's edges, the
capability registry, the growmos graph — not an indexer with its own copy of the tree.

**The future-proofing rules these two ideas leave behind.**

1. **One owner per artifact.** Cross-file edges belong to `catalog-projection`, the symbol map to
   `symbol_slicer`, the capability map to the registry. A new consumer reads them; it never
   recomputes them.
2. **Determinism is the gate.** Every artifact is a pure function of the tree, so drift is a
   diffable fact a gate can refuse. A service breaks this by construction.
3. **Parsers accelerate, they never decide.** Tree-sitter is optional inside `symbol_slicer`, and
   any rung that uses it must fail closed without it — CI must not depend on a native parser.
4. **Enforcement belongs in the PR path** (fast-gate/verifier), not on a laptop. A capability no
   CI runs does not exist — the same defect this lane found in the four-tier review pipeline,
   which advertised four tiers and ran two.
5. **A fork gets a record.** This section is that record.
