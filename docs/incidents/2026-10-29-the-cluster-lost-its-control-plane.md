# Incident: the cluster lost its control plane (2026-10-27 to 2026-10-29)

Status: OKE cannot be rebuilt. ROOT CAUSE (measured 2026-10-29 02:07 UTC, read-only OCI): the
tenancy's Container Engine limits are `cluster-count=0`, `enhanced-cluster-count=0`,
`node-count=0`. `replace-cluster` (run 40802847943) failed at CreateCluster with
`400 LimitExceeded: cluster-count`. Oracle removed the OKE entitlement; the control plane was
removed, not broken. The A1 compute allowance is intact. Everything below this paragraph
(stale pools, 250 GB volumes, detached VNIC) was real but secondary. Path forward on #7387:
single-node k3s on one A1 VM (50 GB boot), Flux bootstrapped to it; alternative is PAYG upgrade.
Founder approved releasing the three legacy volumes.

## What happened
- Node-pool records went stale: both pool nodes TERMINATED while OKE listed them ACTIVE. OKE's
  `NODEPOOL_RECONCILE` failed, so it refused to create replacements ("nodes-per-node-pool limit").
- A replacement node could not be built anyway: 5 x 50 GB CSI volumes = 250 GB live against a
  200 GB Always Free allowance (`LimitExceeded`).
- Later finding (#7387): the control plane itself is gone (`kmi count is 0`). Every pool work
  request fails and the API endpoint is closed. The pool-reconcile door became moot.
- Knock-on: llm.mumchimp.com down, the laptop router dropped 19 lanes (keys only came from the
  dead cluster), the memory door was unreachable and its hook refused writes, codex stalled.

## The real problem
Not data volume. The data is tiny: Prospector's whole shop is a 7 MB SQLite file with a verified
daily offsite copy; Backstage moved into estate-db. The problem is **allocation granularity**: the
CSI minimum is 50 GB per volume, so the 200 GB allowance is 4 volumes. Megabytes of data consumed
whole 50 GB slots, and nothing counted slots against the allowance. The boot volume needs one of
those four.

## The bottleneck
Slots, not bytes: 200 GB / 50 GB = 4 volumes, shared by boot volumes and every oci-bv PVC. Anything
that creates a fifth volume (a node surge, a new PVC, a replacement node) fails.

## Weaknesses in the setup
0. **Platform dependency on an entitlement nobody monitored.** No check read the tenancy's service
   limits; the estate learned OKE was gone from a failed create, two days late. Add a daily limits probe.
1. Capacity was never budgeted in slots (gate now exists: `bin/idp-storage-budget`, #7349; hard gate P1 #7370).
2. Lifecycle leaks: dead PVs and TERMINATED volumes kept counting; no scheduled reclaim (#7367).
3. Doors trusted control-plane records over the resource's own lifecycle state (#7368).
4. Single cluster, single control plane: no degraded mode for the router, memory or keys (#7366, #7369).
5. Passive detection: a receipt was 1711 minutes stale before anyone acted (#7365).
6. Shallow doctors: router-doctor checked 3 lane names (fixed, #7352).
7. **Backups are uneven.** Shop DB: daily, verified, current. estate-db: the newest object in
   `estate-db-backups` is 2026-09-08; no running backup job was found in `platform/estate-db`.
   Backup freshness is not alarmed. This is the real data risk and is the next item to fix.
8. Uncoordinated lanes and ownership: several agents on the same file set; decisions that needed
   the founder were asked late.

## Decisions
- Release the 3 legacy volumes (150 GB): founder, 2026-10-29. Backups checked first: Prospector
  recoverable from `estate-shop-backups/shop/`; Backstage data lives in estate-db.
- New cluster: one node, one boot volume (#7378), then at most 2 oci-bv PVCs, enforced by the gate.

## Follow-ups
Reliability plan `docs/specs/2026-10-28-estate-reliability-plan.md`; tickets #7365-#7370, #7388.
Add: estate-db scheduled backup with a freshness alarm; move low-value PVCs off block storage.
