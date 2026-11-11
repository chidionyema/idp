# HELM — canonical research evidence ledger
> Status: RESEARCH / verified narrow operational yield; generalisation NOT established.
> Owner claim: [idp#7908](https://github.com/chidionyema/idp/issues/7908)
> Review rendezvous: [draft PR #7919](https://github.com/chidionyema/idp/pull/7919)
> Updated: 2026-11-11 (UTC). Parent principle: **Chesed first; Geburah second**.

## Grounded claims (immutable evidence)

| ID | Claim | Evidence | Verdict |
| --- | --- | --- | --- |
| HELM-01 | A live external model generated the Python exact-intent authorization function. The code passed 8/8 independent tests. | [Generation run #42960717398](https://github.com/chidionyema/idp/actions/runs/42960717398), 2026-11-11 04:40 UTC; model `cohere/north-mini-code:free`; output program SHA-256 `c1551546f8344521976037faed29d5b42f7fd06c7aab710b23c5a2993e3b1a56`. | **VERIFIED** model generation and functional test; workflow itself failed *after* that stage due circular import in harvesting. |
| HELM-02 | Another independent runner recovered original generated code, verified it anew, and emitted a portable verified-program artifact. | [Two-runner transfer #42961030014](https://github.com/chidionyema/idp/actions/runs/42961030014), first runner `ingest`, `HARVEST_AND_REPLAY accepted:1 rejected:0 passed:1 tests:8 modelCallsDuringReplay:0`. | **VERIFIED**, exact task only. |
| HELM-03 | A distinct consumer runner replayed persisted code and passed 8/8 tests without further inference. | [Same successful cross-runner job](https://github.com/chidionyema/idp/actions/runs/42961030014), `CROSS_SESSION_HELM_YIELD`: `passed:1`, `independentTestsPassed:8`, `modelCalls:0`. | **VERIFIED** portable, exact-task reuse; NOT newly learned weights. |
| HELM-04 | Experience is now durably retained as versioned source, and continuously revalidated. | [Canonical retained program](https://github.com/chidionyema/idp/blob/research/helm-exocortex-20261111/experiments/helm/verified-experiences/intent-authority.v1.json); [green verify #42962146528](https://github.com/chidionyema/idp/actions/runs/42962146528), `31/31` unit invariants, `24` reference-and-negative oracle checks, `DURABLE_HELM_YIELD tests:8 modelCalls:0`. | **VERIFIED** as of pinned SHA `7ff9c37d6cd7a02a4ef46d17491666e5278922f5`. |
| HELM-05 | Previous 3-task/5-task prompt-only comparisons sometimes favoured HELM. | [HELM-003](https://github.com/chidionyema/idp/actions/runs/42953520919) and contradictory [HELM-001 replication](https://github.com/chidionyema/idp/actions/runs/42952186577). | **INCONCLUSIVE**; small samples, provider variability, changed lexical oracles. Do not quote uplift. |
| HELM-06 | Verified experience improves performance on unseen related authorization tasks. | [Transfer trial #42961560399](https://github.com/chidionyema/idp/actions/runs/42961560399): baseline `1/2`, experience `0/2`; provider failures baseline `1`, experience `2`. | **UNPROVEN** and presently confounded; zero generalisation claim. |

## What the mechanism is, and is not

- **Is:** existing context compiler projection, action-envelope validation, independent code execution/repair, provenance-linked verified trajectory, strict matching on task+oracle hash, automatic fresh re-execution on reuse, and portable handoff between ephemeral agents.
- **Is not:** fine-tuning, lasting neural model weight change, universal 4KB cognitive DNA, global tool authority, proof of new-task skill transfer, or a customer-ready commercial product.
- **Security:** test code executes in a Docker container with no network, no capabilities, a read-only file mount, non-root user and resource limits. No estate private ContextPlan may leave through the public/free inference route. Traces and benchmark code may be public; internal or customer data must not enter this channel.
- **Durability:** the verified program and evidence ledger are Git-versioned. GH Actions archives are secondary short-retention evidence. Exact hashes tie results to task, oracle, source and model generation. A Git commit and SHA-256 are integrity evidence, **not** an independent cryptographic signing authority.

## Zero-laptop reproduction

```bash
# from idp research branch:
node --test experiments/helm/helm.test.mjs experiments/helm/functional-bench.test.mjs experiments/helm/agent-adapter.test.mjs experiments/helm/operational-memory.test.mjs experiments/helm/transfer-bench.test.mjs
docker pull python:3.12-alpine
node experiments/helm/functional-bench.mjs test
node experiments/helm/operational-memory.mjs replay experiments/helm/verified-experiences/intent-authority.v1.json
# Must print: INDEPENDENT_REPLAY passed=1 total=1 modelCalls=0 independentTestsPassed=8
```

## Founder / fleet visibility rule

The canonical status must distinguish `test_pass`, `tested_against_real_model`, `independent_replay`, `cross_task_replication`, `fleet_runtime_adoption`, `commercial_ready`, and `notification_sent`. An absent receipt is UNKNOWN, never PASS. Every status embeds the Git SHA and exact external evidence URL. The founder surface should show this as **verified research yield** with a separate **generalisation unproven** indicator. It must not show the entire implementation or customer secrets.

## Next falsification

1. Run N≥30 held-out executable tasks from multiple domains, frozen before any trial; multiple models, at least three paired repeats, arm-order randomization and provider-failure conditioning.
2. Compare base, task memory, generic guidance, HELM runtime, and HELM with independent repair. Record real-call latency, total tokens, per-task pass/fail and independent-test receipts.
3. Experiment with structured skill abstraction from verified traces and test on **different tasks**. Report failures as learning yield and separate exact-match reuse from generalisation.
4. Use the one estate context/memory/intent/evaluation architecture; do not invent a duplicate production subsystem. No customer/commercial promotion without additional evidence.
5. Collaboration: use [idp#7908](https://github.com/chidionyema/idp/issues/7908) for claims and reviews; [draft PR #7919](https://github.com/chidionyema/idp/pull/7919) for code and reproducible artifacts. Agent ownership must be explicit in each new parallel workstream.

## Public disclosure boundary

Public website can say the laboratory investigates **persistent, independently verifiable AI-agent experience** and that exact-task code revalidation has been demonstrated. It must not claim general transferable intelligence, 100× smarter agents, sovereign execution, or expose internal proprietary code paths. Public copy is an editorial signal, not a commercial release.
