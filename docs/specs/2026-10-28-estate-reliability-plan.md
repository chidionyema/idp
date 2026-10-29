# Reliability plan: eliminate the failure class behind the 2026-10-28 outage

Issue idp#7362 (child of #7343, tracker #7359). Incident: `docs/incidents/2026-10-28-the-router-lost-every-model.md`.

## What happened, as a chain (every link measured in #7343)

1. The Always Free tenancy allows 200 GB of block storage. Nothing checked demand before applies.
2. Node replacements left CSI volumes behind. Reclaiming them was a manual door (`oci-reclaim`).
3. Volume and node creates answered `LimitExceeded`. The pool's node records went stale (2 records, 2 TERMINATED instances).
4. OKE's `NODEPOOL_RECONCILE` failed, so OKE would not create a replacement. The endpoint VNIC detached.
5. The cluster went dark. Cloud router, memory door, Backstage and the site all lived only there.
6. Dependents failed closed: the memory write gate refused every write (#7351), the laptop router had dropped 19 lanes (#7352) and its doctor said healthy, codex pointed at a lane no router defines.
7. Nobody was told for roughly 28 hours (door receipt 1711 min old against a 20 min limit).

## Root causes (the thing to eliminate, not the symptom)

| # | Root cause | Evidence |
|---|---|---|
| R1 | Capacity is a vendor-side surprise, not a budgeted quantity | no pre-apply check existed; 14 volumes / 700 GB vs 200 GB |
| R2 | Resource lifecycles leak (volumes outlive nodes) and nothing reconciles them | 14 orphaned CSI volumes; manual reclaim only |
| R3 | The estate trusts control-plane records over resource state | stale pool nodes; surge-node and reclaim both read the record, not the instance |
| R4 | One cluster is a single point of failure for every shared service, on a free tier with no headroom | router, memory, catalog, site all behind one endpoint |
| R5 | Detection is passive: a stale receipt is a red row, not a page | 1711 min stale |
| R6 | Consumers have no degraded mode: they refuse instead of degrading | memory gate deadlock; router lane drop |
| R7 | Health checks test for presence of a name, not for the contract | router-doctor looked for 3 of 22 lanes |
| R8 | Concurrent lanes solve the same problem without one design | capacity-guard, capacity-convergence, storage-budget, oci-reclaim, continuity all touch capacity |

## Plan: prevent, detect, survive, recover

Each item names an owner lane (reuse before build, AGENTS.md section 6) and the binary test that proves it.

### Prevent (R1, R2, R3)
- P1 **Capacity is gated before apply.** `lane/capacity-guard` (`bin/idp-estate-capacity`) is the estate's guard; `bin/idp-storage-budget` (landed, #7349) folds into it as the block-storage check rather than living beside it. Test: a PR that raises demand over 200 GB fails `ci-success` (hard block, not report-only).
- P2 **The free tier is asked for what it gives.** `lane/the-capacity-convergence` (#7142): one node, one boot volume. Test: tofu plan at that shape fits the budget.
- P3 **Lifecycle reconciliation is scheduled, not remembered.** A scheduled GitHub Actions job (ADR 0034 ladder) runs `oci-reclaim` and `oci-nodepool-reconcile` in plan mode daily and files an issue on any finding; apply stays gated (destructive = quorum, AGENTS.md section 11). Test: injected phantom node produces an issue within one schedule tick.
- P4 **Instance state is the truth.** Both doors read each resource's own lifecycle state. `oci-reclaim` fixed (#7318); `oci-nodepool-reconcile` built (#7343); `idp-oke-surge-node` still reads the pool record (defect reported on #7318) and needs the same fix.

### Detect (R5, R7)
- D1 **Staleness pages.** A door receipt older than its limit (20 min) raises a push to the founder (voice/Telegram path already in the estate) and a /fleet red tile within one interval. Test: stop the CronJob; the page fires inside 2x the limit.
- D2 **Doctors test the contract.** `router-doctor` now names every declared lane that is not served (#7352, lane cdb069e76). Same rule for every doctor: compare served to declared, never presence of a sentinel.
- D3 **Budget burn is visible.** /fleet shows block-storage and A1 headroom as a gauge with the 200 GB / 4 OCPU limits.

### Survive (R4, R6)
- S1 **Memory has a degraded mode.** The write gate fails open and ledgers it when the door is unreachable (#7351, lane f7e23c64f). Still to do: the gate must not depend on one harness's transcript; local cache of the last brief so pi, codex and opencode behave identically.
- S2 **The router is multi-homed.** Cloud router is primary, laptop router is a fallback and must not be production: it is exposed to machine load (founder, 2026-10-28). Move the second home off the laptop to a free-tier home from ADR 0034 (Cloudflare Workers free as a thin fail-over front). Test: kill the cluster endpoint; a `default` call still answers within 5 s.
- S3 **Vendor keys have a second source.** Laptop render falls back to the vault when kubectl is unreachable (lane 6539e0e14, #7352).
- S4 **Shared services are placed, not defaulted onto the cluster.** Re-run the ADR 0034 ladder for memory and router; anything that can sit off-cluster on a free tier moves.

### Recover (R2, R3)
- C1 **Pool reconcile door** (`oci-nodepool-reconcile`, #7343): plan, then apply deletes only phantom nodes with the size decremented.
- C2 **Rebuild is drilled.** `bin/idp-oke-rebuild` and the continuity/rescue job (`lane/continuity`) are exercised on a schedule with a receipt. Target RTO: 60 min from a dark cluster to node pools ACTIVE (not met today: ~28 h measured).
- C3 **Runbook**: `docs/runbooks/cluster-recovery.md`.

## Gate review (AGENTS.md section 0)

- **Baseline delta:** detection lag from 1711 min to under 40 min (D1); manual recovery from days to a planned door (C1).
- **Trade-offs:** hard-blocking on capacity will stop some PRs that would have worked on a clamped shape; the guard must read the clamp rules (R1). A second router home adds one more thing to keep in sync; mitigated by rendering both from `platform/llm/config.yaml` and a drift doctor (D2).
- **Second-order:** the daily reconcile job needs an OCI identity with delete rights; it is limited to plan mode, and apply stays a gated intent so a bug cannot delete PV data.
- **Verification:** each item above has one binary test; nothing is done until /fleet shows it deciding on real events (AGENTS.md section 3).

## Order (what unblocks the most first)

1. Cluster back: C1 apply (founder-approved), P2 landing, pipeline apply. Unblocks memory, router, catalog, codex.
2. D1 paging and S2 off-laptop fail-over. Removes the laptop as production and the silent-outage window.
3. P1 hard gate, P3 scheduled reconcile, P4 surge-node fix.
4. S1 harness-agnostic memory, S4 placement review, C2 drill.
