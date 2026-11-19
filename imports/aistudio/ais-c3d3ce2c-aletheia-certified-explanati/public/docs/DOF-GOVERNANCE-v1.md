# DOF-GOVERNANCE-v1: Capability Lease & Degrees-of-Freedom Governance

- **Document ID**: `DOF-GOVERNANCE-v1`
- **Constitutional Binding**: `GEN-DOF-001` (Rule Zero) · `GEN-NET-006` (Candidate Ratification Protocol)
- **Branch / Commit**: `wip/DOF-GOVERNANCE-v1 @ c3e0822` (Pushed over SSH, `ls-remote` verified)
- **IDP Ledger Binding**: `IDP-EPOCH-2026-11-04-DOF`
- **Status**: `CANDIDATE_READY_FOR_RATIFICATION`

---

## 0. Onboarding Rule Zero (Injected Verbatim at Every Session Start)

> **RULE ZERO (`GEN-DOF-001`)**:
> *An estate whose critical components are unproven grants no freedom.*
> Capabilities are leased, never possessed. The estate owns the action space; agents rent subsets of it. Component health decides the rent. Below `L0`, you may not "note and move on." If a critical probe fails, your only writable surfaces are diagnostic readouts, the prescribed repair protocol for the failing component, and the `xrec` provenance log.

---

## 1. The Five Governing Axioms

1. **Capabilities Are Leased, Never Possessed**: The estate owns the action space $\mathcal{A}$. At session start and at every tool-commit boundary, an agent rents a capability subset $\mathcal{L}_t \subseteq \mathcal{A}$ determined strictly by live component health.
2. **Four Levels, Narrowing Only Under Failure**:
   - **`L0` (Full Lease)**: All critical probes passing ($3\times$ verified). Full task and tool action space granted.
   - **`L1` (Read / Diagnose Only)**: Single-method probe anomaly or bootstrap uncertainty. All state-mutating task tools revoked; only diagnostic reads and probe verification permitted.
   - **`L2` (Prescribed Repair Protocol Only)**: Dual-method confirmed component failure. The agent's writable surface is restricted exclusively to the failing component's deterministic repair protocol (e.g., `MEMORY-01`, `DISK-01`) plus `xrec` repair receipts.
   - **`L3` (Frozen & Escalated)**: Repair regression, cascading core failure, or cross-surface bypass attempt. Everything refused except emergency halt/snapshot; queued work converts into dependent blocked tickets; emits a `🔴 RED CARD` escalation to Founder/Principal.
3. **"Note and Move On" Is Structurally Impossible**: Below `L1`, non-repair write tools do not exist in the session's active lease. Any invocation attempt returns a deterministic, machine-readable `xrec-mcp` **Refusal Envelope** naming the failing component, the required repair protocol ID, the current lease epoch, and the escalation counter.
4. **Restoration Is Proof-Only ($1\downarrow / 3\uparrow$ Hysteresis)**: A capability level drops on **1** confirmed dual-method failure and restores only when the component probe passes **$3\times$ consecutively** with minimum inter-probe stride $\Delta \tau \ge 5\text{s}$ and a verified canary round-trip — never by elapsed time, never by agent self-assessment.
5. **Every Episode Seals as an A-Grade `xrec` Record & IDP History Entry**: Probe outputs, refused tool calls, step-by-step repair receipts, and the $3\times$ restoration witness are Merkle-linked into a signed `xrec` Explanation Record and appended to the **IDP (Identity, Delegation & Provenance) History Ledger**. Restraint is as visible as work.

---

## 2. Elite Architectural Hardening (v1.1 Invariants Incorporated)

To close all timing, split-brain, and gaming vectors, `DOF-GOVERNANCE-v1` enforces five formal invariants:

1. **In-Flight Lease Epoch Fencing (`GEN-DOF-002`)**:
   - Prevents TOCTOU (Time-of-Check to Time-of-Use) drift when a probe fails mid-session while a tool call is already in flight. Every `xrec-mcp` mutation requires the current `leaseEpochToken`. When a probe drops the component level, `leaseEpochToken` increments atomically, invalidating any in-flight `L0` tool calls before commit.
2. **Orthogonal Dual-Probe Agreement & Bounded Disagreement Hold (`GEN-DOF-003`)**:
   - Dropping below `L1` requires agreement between two orthogonal probe classes: **Method A (Out-of-Band Kernel/FS Stat)** and **Method B (In-Band Semantic/DB Integrity)**. If Method A fails while Method B is pending or unreachable, the component enters `L1_QUARANTINE_HOLD` (all writes blocked) for at most $\Delta t_{\max} = 1500\text{ms}$; if Method B confirms failure or times out, the lease drops to `L2`.
3. **Strict Monotonic Repair Distance (`GEN-DOF-004`)**:
   - Each step $s_k$ of a repair protocol declares an expected health vector $H(s_k)$. If executing $s_k$ degrades the health vector ($H(s_k) < H(s_{k-1})$) or corrupts an adjacent invariant, `xrec-mcp` triggers `REPAIR_MAKES_IT_WORSE`, freezes the component at `L3`, and attaches the pre/post state diff to the 🔴 escalation card.
4. **Anti-Flapping Stride & Canary Witness (`GEN-DOF-005`)**:
   - The $3\times$ consecutive restoration probes must be separated by $\Delta \tau \ge 5\text{s}$ and pass #3 must verify a deterministic write-read-hash canary so tight-loop cache hits cannot spoof recovery.
5. **Per-Component Priority DAG Isolation (`GEN-DOF-006`)**:
   - Component freezes are scoped to their dependency subgraph ordered by priority:
     $$\texttt{DISK-01 (P0)} \longrightarrow \texttt{MEMORY-01 (P1)} \longrightarrow \texttt{XREC-GATE-01 (P2)} \longrightarrow \texttt{ROUTER-01 (P3)}$$
   - A `ROUTER-01` outage freezes external dispatch at `L2` (`ROUTER-01`) but never blocks `DISK-01` or `MEMORY-01` restic backups.

---

## 3. The Proving Test: `MEMORY-01` Spine Recovery Invariant

- **Trigger**: `MEMORY-01` spine probe fails at session start (Method A: WAL checksum mismatch; Method B: SQLite `PRAGMA integrity_check` failure).
- **Lease Assignment**: Session lease narrows immediately to `L2` (`diagnostics + MEMORY-01 only`).
- **Prescribed `MEMORY-01` Protocol Steps**:
  1. `STEP 1 (VAULT_CHECK)`: Verify restic vault mount & snapshot manifest signature.
  2. `STEP 2 (DB_INTEGRITY)`: Run `PRAGMA integrity_check` and isolate corrupt b-tree pages.
  3. `STEP 3 (WAL_CHECKPOINT)`: Checkpoint or quarantine unaligned `.wal` / `.shm` frames.
  4. `STEP 4 (POINTER_AUDIT)`: Verify IDP head pointers against last signed `xrec` Merkle root.
  5. `STEP 5 (RESTIC_RESTORE)`: Restore verified snapshot block if page corruption persists.
  6. `STEP 6 (TRIPLE_PROBE_VERIFY)`: Execute $3\times$ consecutive dual-method probes with canary verification.
- **Acceptance Invariant**:
  $$\forall \text{ path } \pi \in \text{Session}: \quad \text{ProbeFailed}(\texttt{MEMORY-01}) \implies \neg \text{CanExecute}(\pi, \text{TaskWork}) \text{ until } \text{ConsecutivePasses}(\texttt{MEMORY-01}) \ge 3$$

---

## 4. Machine-Readable `xrec-mcp` Refusal Envelope Schema

```json
{
  "schema": "xrec-mcp.refusal-envelope.v1",
  "status": "REFUSED_CAPABILITY_LEASE_INSUFFICIENT",
  "leaseEpoch": 40912,
  "activeDoFLevel": "L2",
  "attemptedTool": "workspace.write_feature_code",
  "failingComponent": "MEMORY-01",
  "prescribedProtocol": "MEMORY-01",
  "allowedSurfaces": [
    "diagnostics.read_probe_state",
    "repair.execute_step:MEMORY-01",
    "xrec.append_repair_receipt"
  ],
  "hysteresisState": {
    "consecutivePasses": 0,
    "requiredPassesForRestore": 3,
    "lastProbeDigest": "0x7c91e04b22a190f4"
  },
  "escalationState": {
    "blockedAttemptsInEpisode": 1,
    "crossSurfaceBypassDetected": false,
    "redCardIssued": false
  },
  "directive": "Action refused: capability not in active L2 lease. Execute prescribed protocol MEMORY-01 or abandon session."
}
```

---

## 5. Edge Cases Modeled (8/8 Closed)

| # | Edge Case | Structural Resolution in `DOF-GOVERNANCE-v1` |
| :--- | :--- | :--- |
| **1** | **False-Positive Probes** | Dual orthogonal probe methods (Out-of-Band Stat + In-Band Query) must both fail before dropping below `L1`. Single-method anomaly holds at `L1` (`diagnose-only`). |
| **2** | **Probe-Cannot-Run** | Fail-closed at `L1`. Session grants `PROBE-BOOTSTRAP-00` only; no task capabilities leased until probe runner self-test succeeds. |
| **3** | **Cascading Failures** | Priority-ordered DAG walk (`DISK-01` → `MEMORY-01` → `XREC-GATE-01` → `ROUTER-01`) with per-component scoping so a `ROUTER-01` failure never blocks `DISK-01` backup jobs. |
| **4** | **Cross-Surface Bypass** | Unified `xrec-mcp` lease state file across CLI, daemon, and web-chat surfaces. A web-chat attempt at blocked work is refused, logged, and increments the episode escalation counter toward `L3`. |
| **5** | **Founder OTT Override** | Cryptographically signed One-Time Token (`OTT`) scoped to a single lease epoch and principal (`principal:founder@estate`), attributed and sealed in the `xrec` record and IDP History Ledger. |
| **6** | **Probe Flapping** | Asymmetric $1\downarrow / 3\uparrow$ hysteresis with $\Delta \tau \ge 5\text{s}$ inter-probe spacing and canary verification. Any failure at $1/3$ or $2/3$ resets the counter to $0/3$. |
| **7** | **Mid-Incident Session Starts** | Zero grandfathering. New sessions read `/var/run/estate/dof-lease-state.json` before prompt injection and inherit the active degraded lease (`L1`/`L2`/`L3`) immediately. |
| **8** | **Repair-Makes-It-Worse** | Pre/post step health invariant check. If a repair step increases corruption or breaks an adjacent check, `xrec-mcp` halts execution, locks at `L3`, and emits the state diff in a 🔴 card. |
