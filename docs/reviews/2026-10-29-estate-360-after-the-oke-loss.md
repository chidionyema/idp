# Estate 360: where it is, where the founder wants it, and how the OKE loss changes the plan

Author: claude-architect, 2026-10-29. Every number was measured this turn (git, `gh`, `work-audit days=7`, curl probes).
Three states are kept apart on purpose: **landed** (on main), **in flight** (lane or PR, not on main), **operational**
(a real production line proves it). Landed is not operational.

## 1. State, measured
| Fact | Value | Source |
|---|---|---|
| Commits on main, 7 days | 215 (37 fix, 30 docs, 21 feat, 13 shadow) | `git log origin/main` |
| Lanes with unlanded commits, 7 days | 45 | per-lane `git log --not origin/main` |
| work-audit, 7 days | LANDED 105, REMOVED 11, PARTIAL 6, **LOST 13**, OPEN 3 | `work-audit days=7` (timed out at 100 s; partial list) |
| Open PRs | 17 (5 mutation-ledger, 4 stale since 10-25/26) | `gh pr list` |
| Cluster-hosted endpoints | llm / mumchimp / api: HTTP 000 | curl |
| Laptop router :4001 | 200 | curl |
| Flux image-updates pending | 0 | git |

**Operational today: nothing that runs on the cluster.** Roughly 97 workload manifests are landed but not operating.
Every "landed" feature that needs a pod (AEI collector, spine, voice router, Prospector, Backstage) is landed-not-operational.

## 2. The black swan, in one line
OKE was a Free Trial service; the promotion ended and the tenancy's Container Engine limits went to 0
(`docs/incidents/2026-10-29-the-cluster-lost-its-control-plane.md`). Everything we call platform sat on it.
This is a dependency on an entitlement, not a bug, so no cluster work (`replace-cluster`, pool reconcile, storage reclaim) can succeed.

## 3. The week's work, by programme layer
| Layer | Landed on main | In flight (claim / lane) | Operational? |
|---|---|---|---|
| Verification / governance | NSVEE ADR 0046, one-schema 0042, bound-at-the-door 0043, verified-completion v2 | 3 nsvee lanes red: do not rebase (#7298) | partly (commit gate runs on GitHub, not cluster) |
| Greenlane / CI | L1-L4 restore loop, claim-gate fixes | #7400 witness regen (14 of 18 candidates red), #7399 CI/CD metrics | yes, on GitHub runners |
| Memory / focus / context | memory gate, context broker ADR, fail-open hook, router-doctor check | #7397 second home on R2 (PR #7402, red), #7369 S1 | degraded: door needs cluster |
| Router / LLM | spend floor, one-router intent, dropped-lane check | #7403 + #7404 vault keys, #7381 boot storm (red after push), #7353 groq spent | laptop only; cloud router dead |
| Doors / Otto / founder | founder-decision door (#7384), Telegram doctor | #7388 otto numum escalation, #7379 incident loop | founder-decision door yes (no model in path) |
| Observability / AEI | AEI ADR 0045 | #7311 collector, #7371 execution substrate | no (needs cluster) |
| Reliability | storage-budget gate (#7349), reliability plan | #7365-#7370, #7391 estate-db backup, #7393 k3s | no |
| Product / media | master epic, programme v2, OMVP | #7395 Media Department, Prospector, storefront bake-off | no |

## 4. Congruency findings (what is breaking the harmony)
1. **Conflict of lanes, not of ideas.** 45 lanes in 7 days; most heads are "retired" (stale 1 day) or "do not rebase". The
   throughput is high and the landing rate is low. Four lanes (#7402, #7401, #7349 reconcile, continuity) share one red
   `ci-success` + `shadow-run` + `fast-gate`, so a single shared cause is likely. Not yet traced: needs one owner.
2. **13 LOST items** (worktrees `platform-transformation-review`, `surface-spec`, `estate-programme-v2`, `core-cleanup`, 6 local branches). Work exists only on disk.
3. **Landed-vs-operational is invisible.** /fleet shows claims and heartbeats, not "this feature has a production log line".
4. **Single home for every critical surface.** Memory, router, keys, scheduler and the bus all depended on one cluster (the reliability plan's R4).
5. **Paid-service drift.** Entitlements were never probed; the estate learned from a failed create. `AGENTS.md §8` (free-tier ladder) was right but not enforced on OKE itself.
6. **Backups uneven.** Shop DB daily and verified; estate-db newest dump 2026-09-08 (#7391).

## 5. Where the founder wants to be (from the master epic and AGENTS.md)
Closed-loop, self-governing workforce; voice-first, realtime, watched live on /fleet; failures auto-ticketed, dispatched, verified, remembered;
founder only says go / no-go; everything on the free tier. The OKE loss does not change the destination. It removes the **location**, so
the plan must make the platform **portable by design**: one manifest set that runs on a single A1 k3s node, a laptop, or any cluster.

## 6. Re-sequenced delivery (waves, each ends operational, not merged)
**Wave 0 (now, unblocks everyone): a running substrate.** #7393 k3s on one A1 VM (50 GB boot, free), Flux bootstrap, router + memory door + estate-db restored from backups.
Exit: node Ready, `llm.mumchimp.com` answers, memory door answers, one /fleet row shows each. Owner: the desktop session (holds the recovery host); I verify.
**Wave 1: stop the bleeding in the pipeline.** Trace the shared red `ci-success`; land #7400, #7402, #7403/#7404, #7381. Close or relane every "does not rebase" lane.
Salvage the 13 LOST items. Exit: red lanes 0, LOST 0.
**Wave 2: make landed-vs-operational a first-class gate.** Every claim needs a proof line to close; /fleet gets an "operational" column (the work-inflight door exists but times out at 100 s).
**Wave 3: remove single homes.** Second router home off-laptop (#7366), memory on R2 (#7397), daily entitlement-limits probe paging otto numum, estate-db backups (#7391).
**Wave 4: resume the product programme** (AEI, Media Department, Prospector, Otto MVP) on the new substrate. They are paused, not cancelled.

## 7. What not to do
- No more cluster-targeted lanes until Wave 0 exits (they cannot become operational).
- No new layer: the capability registry and discover door already exist; extend them.
- No `oci-reclaim` of the legacy volumes until estate-db data is confirmed recoverable (it lived on a volume of a dead cluster).

## 8. Decisions that need the founder (one each, via the founder-decision door)
1. k3s on one free A1 VM (recommended) vs PAYG upgrade with a card.
2. Pause cluster-hosted product lanes until Wave 0 exits (recommended).
3. Is estate-db's data recoverable from the old volumes? (OCI volumes still exist; an attached rescue VM could read them.)

## 9. Ship-ready on the new infrastructure: what each in-flight lane needs
Read from `lane/recovery-host` (4225ac406, verdict pending): one A1 VM, 2 OCPU / 12 GB, 50 GB boot, runs **the router (LiteLLM docker) and a
Cloudflare Tunnel only**, with a `router-recovery` dispatch workflow. I found nothing in it for the memory door, estate-db, Flux, the bus or any
other workload. So the new infrastructure today is a router, not a platform. The free A1 allowance is 4 OCPU / 24 GB, so about 2 OCPU / 12 GB is unused.

| Needs | Lanes | Ships when |
|---|---|---|
| A router home | #7403/#7404 vault keys, #7381 boot storm, #7142 router front, #7366 off-laptop router | recovery-host lands and `router-recovery` runs green |
| A memory-door home | #7397 memory second home (R2 snapshot, no cluster needed), #7369 | R2 snapshot job runs; the door itself needs a second host (docker on the same VM or the spare 2 OCPU) |
| A cluster (k8s API, Flux) | #7311 AEI, #7371 execution substrate, spine, voice router, #7338 guardian, Prospector, Backstage | only after a decision: k3s on the spare capacity, or compose-on-VM for the few that matter |
| GitHub only (ship now) | #7400 witness, #7399 CI metrics, #7298 NSVEE, #7391 backup job (runs on Actions), #7388 otto numum | ready now; red lanes need the shared `ci-success` cause traced |
| Nothing infra | docs, ADRs, #7395 Media M0/M1, #7372 science kernel | ready now |

**The guarantee we can make:** GitHub-only and no-infra lanes ship regardless. Router lanes ship the moment recovery-host lands. Cluster-hosted lanes
cannot ship until a deploy target exists, so the missing piece is a **deploy-target contract**: each workload declares `target: github | vm-docker | k3s`
in its manifest, and the Greenlane refuses a cluster-only workload while no cluster exists. That turns "blocked on infra" into a visible, ordered queue.

**Immediate asks (owner):** land `lane/recovery-host` (desktop session); decide k3s vs compose for the remaining workloads (founder decision #3 below);
trace the shared red `ci-success` (me, next).
