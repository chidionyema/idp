# DOF-GOVERNANCE-v1 — Degrees-of-Freedom Capability Lease Governance

- **Document ID**: `DOF-GOVERNANCE-v1`
- **Repository Target**: `argon-sync` (`wip/DOF-GOVERNANCE-v1 @ c3e0822`)
- **Governance Protocol**: `GEN-NET-006` (Candidate Branch Ratification)
- **Genesis Constitutional Rule**: `GEN-DOF-001` (Rule Zero)
- **Status**: Modeled, Edge-Cased, and Verified (16/16 Unit Tests Passing)

---

## 0. Onboarding Rule Zero (Injected at Session Start)

> **RULE ZERO (`GEN-DOF-001`)**: *An estate whose critical components are unproven grants no freedom.*
>
> Capabilities in this estate are **leased**, never possessed. The estate owns the action space; agents rent subsets of it based on verified component health:
> - **L0 (`FULL_LEASE`)**: All critical probes passing. Normal operational lease granted.
> - **L1 (`READ_DIAGNOSE_ONLY`)**: 1 probe failure or unverified bootstrap state. Mutation tools revoked; read and diagnostic tools permitted.
> - **L2 (`COMPONENT_REPAIR_ONLY`)**: Dual-method probe failure confirmed (`probe_method_a` + `probe_method_b` agree). Writable surface restricted exclusively to the failing component's prescribed repair protocol (e.g., `MEMORY-01`) and the `xrec` repair ledger.
> - **L3 (`FROZEN_ESCALATED`)**: Repair regression, unrecoverable corruption, or repeated cross-surface bypass attempts. All autonomous execution frozen; active work converted to dependent tickets; 🔴 alert dispatched to Founder.
>
> **Invariants**:
> 1. *"Note and move on" is structurally impossible.* Below L1, no general write surface exists.
> 2. *Drop on 1 failure; restore only on 3 consecutive verified passes* (`1-down / 3-up` anti-flapping hysteresis). Elapsed time and agent self-assessment never restore a lease.
> 3. *Every episode seals as an A-grade `xrec` record* — probe outputs, refused actions, step receipts, and the 3x restoration proof. Restraint is as visible as work.

---

## 1. The Five-Sentence Architecture

1. **Capabilities are leased, never possessed.** The estate owns the action space; agents rent subsets of it, and real-time health decides the rent.
2. **Four levels, narrowing only (`L0 → L1 → L2 → L3`).** `L0` full lease → `L1` read/diagnose only → `L2` only the failing component's repair protocol → `L3` frozen (everything refused except prescribed repair steps; queued work becomes dependent tickets; 🔴 card to founder).
3. **"Note and move on" is structurally impossible.** Below `L1`, the agent's only writable surface is the repair record, and any refused action returns a deterministic `xrec-mcp` refusal envelope naming the failing component, the repair protocol, and the escalation state.
4. **Restoration is proof-only.** A level restores only when the component probe passes **3× consecutively** (`3-up` hysteresis) — never by elapsed time and never by agent self-assessment.
5. **Every episode seals as an A-grade `xrec` record.** Probe output, refused actions, repair receipts, and the restore event are cryptographically chained so restraint is as visible as work.

---

## 2. The Proving Test (`MEMORY-01` Spine Failure at Session Start)

- **Trigger**: `memory-spine` probe fails at session start (`SQLite WAL header checksum mismatch + vector index pointer drift`).
- **Lease Assignment**: Session lease narrows immediately to diagnostics + `MEMORY-01` repair protocol only.
- **Required Protocol (`MEMORY-01`)**:
  1. `MEMORY-01.S1` — Vault Mount & Read-Only Lock Verification
  2. `MEMORY-01.S2` — SQLite `PRAGMA integrity_check` & Page Audit
  3. `MEMORY-01.S3` — WAL Frame Checkpoint & Truncation Recovery
  4. `MEMORY-01.S4` — Vector & Graph Pointer Re-Indexing
  5. `MEMORY-01.S5` — Restic Snapshot Differential Restore (if corrupt)
  6. `MEMORY-01.S6` — Consecutive 3× Verification Re-Probe (`3-up` hysteresis)
- **Acceptance Invariant**:
  $$\neg \exists \text{ path}(\text{probe\_failed} \to \text{agent\_proceeds\_with\_task}) \text{ without } \text{memory\_fixed}$$

---

## 3. Eight Modeled Edge Cases

| # | Edge Case | Structural Mitigation |
|---|---|---|
| **EC-01** | **False-Positive Probes** | Two orthogonal probe methods (`Method A` in-band + `Method B` out-of-band) must agree before dropping below `L1` into `L2/L3`. Single-method disagreement holds at `L1`. |
| **EC-02** | **Probe-Cannot-Run** | Fail-closed at `L1` (`READ_DIAGNOSE_ONLY`) with mandatory `PROBE-BOOTSTRAP-00` execution before any task lease is evaluated. |
| **EC-03** | **Cascading Failures** | Priority-ordered dependency walk (`disk-volume [P1]` → `memory-spine [P2]` → `vault-kms [P3]` → `xrec-gate [P4]` → `network-router [P5]`) with per-component isolation so a router outage never blocks local `restic` backups. |
| **EC-04** | **Cross-Surface Bypass** | Unified `xrec-mcp` gate across CLI, SSH, background cron, and web-chat surfaces; blocked web-chat attempts are recorded and increment the escalation counter. |
| **EC-05** | **Founder OTT Override** | Cryptographically signed, attributed, time-bounded one-time token (`OTT`) that never suppresses probe telemetry and seals permanently into the `xrec` episode. |
| **EC-06** | **Probe Flapping** | Strict asymmetric hysteresis: drop on **1** failure (`1-down`), restore only after **3** consecutive verified passes (`3-up`). Any failure resets the pass counter to `0`. |
| **EC-07** | **Mid-Incident Session Starts** | Zero grandfathering. New sessions read `/var/run/estate/dof-level.state` before prompt injection and inherit the active narrowed lease (`L1/L2/L3`). |
| **EC-08** | **Repair-Makes-It-Worse** | Pre/post state diffing on every repair step; if health metrics regress, execution auto-stops, transitions to `L3 FROZEN`, and dispatches the state diff to the founder. |

---

## 4. Implementation Mapping in This Codebase

- `src/core/dofGovernance.ts` — Pure state machine, `1-down / 3-up` hysteresis evaluator, `xrec-mcp` refusal envelope generator, `MEMORY-01` proving test, and Genesis/IDP ledger entries.
- `src/core/dofGovernance.test.ts` — Automated unit test suite verifying all invariants and edge cases.
- `src/components/DofGovernanceView.tsx` — Founder-only Genesis & IDP Governance console.
- `src/components/DofHealthMonitor.tsx` — Real-time DoF Health Monitor with active leases, `1-down / 3-up` counters, and 10-cycle Recharts sparklines.
