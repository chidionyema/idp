# Mission Continuity Kernel v1: Production Specification & Operating Contract

## 1. Executive Summary & Non-Negotiable Boundary

The **Mission Continuity Kernel v1** is a self-contained runtime engine providing durable, cross-surface execution continuity for missions across the Genesis Estate. It guarantees that critical missions survive LLM context limits, token exhaustion, network partitions, and worker crashes without losing progress, without routine Founder intervention, and without creating dual execution authorities.

### Operational Boundaries & Guarantees
- **Pure Self-Contained Implementation**: Implements pure TypeScript runtime logic importing only Node.js standard libraries (`node:crypto`, `node:sqlite`). Zero third-party runtime package dependencies.
- **Single Source of Truth**: Adds tables to the existing `estate.db` SQLite database using `DatabaseSync` in WAL mode with `BEGIN IMMEDIATE` compare-and-swap transactions. It does not open separate databases, duplicate ledgers, or create daemons.
- **Injected Clock**: Time is strictly injected via `now(): number` to guarantee deterministic repeatability in verification trials and prevent clock drift vulnerabilities.
- **Cryptographic Tamper-Evidence**: Row-level SHA-256 digests and HMAC-SHA256 signatures over RFC 8785 canonical JSON, coupled with an append-only cryptographic event hash chain. Any tampering fails with `INTEGRITY_ERROR`.
- **Proposal Demarcation**: AI Studio output is a candidate assurance harness and proposal. It does not assert production operating or deployment status without live upstream receipts.

---

## 2. Type System & Data Model

### Literal Unions
```ts
export type MissionKind = 'code' | 'research' | 'operations';

export type MissionPhase =
  | 'QUEUED'
  | 'CLAIMED'
  | 'EXECUTING'
  | 'CHECKPOINTING'
  | 'HANDOVER_PENDING'
  | 'TAKEN_OVER'
  | 'VERIFYING'
  | 'REPAIRING'
  | 'OPERATING'
  | 'BLOCKED';

export type AvailabilityState =
  | 'AVAILABLE'
  | 'DEGRADED'
  | 'EXHAUSTED'
  | 'DISCONNECTED'
  | 'UNKNOWN'
  | 'DENIED';

export type FailureClass =
  | 'EXHAUSTED'
  | 'DISCONNECTED'
  | 'STALLED'
  | 'HOST_LOST'
  | 'PROVIDER_DOWN'
  | 'CAPACITY_DENIED'
  | 'SECURITY_DENIED';

export type ContinuityErrorCode =
  | 'INVALID_INPUT'
  | 'WEAK_RECEIPT_KEY'
  | 'MISSION_NOT_FOUND'
  | 'LEASE_HELD'
  | 'STALE_FENCE'
  | 'INVALID_TRANSITION'
  | 'CHECKPOINT_REQUIRED'
  | 'CHECKPOINT_CONTAINS_SECRET'
  | 'INVALID_EFFECT_KEY'
  | 'INELIGIBLE_WORKER'
  | 'INTEGRITY_ERROR';
```

### Core Records
- `CapacityOffer`: Published by workers declaring execution host, failure domain, capabilities, availability, quota, context remaining, verified success rate, p95 latency, and TTL.
- `MissionCheckpoint`: Captures goal, subgoals, verified facts, decisions, constraints, attempted actions, failed evidence references, next action, branch, commit SHA, and context digest.
- `MissionRecord`: Persistent state of the active mission in `continuity_missions`.
- `EffectPermit`: Cryptographic token permitting execution of an irreversible side effect.
- `EffectCompletion`: Idempotent completion receipt for authorized effects.

---

## 3. Deterministic State Machine

The mission lifecycle strictly follows this transition digraph:

```
QUEUED -> CLAIMED
CLAIMED -> EXECUTING | HANDOVER_PENDING | BLOCKED
EXECUTING -> CHECKPOINTING | HANDOVER_PENDING | VERIFYING | BLOCKED
CHECKPOINTING -> EXECUTING | HANDOVER_PENDING
HANDOVER_PENDING -> TAKEN_OVER | BLOCKED
TAKEN_OVER -> EXECUTING | VERIFYING | BLOCKED
VERIFYING -> OPERATING | REPAIRING | BLOCKED
REPAIRING -> EXECUTING | BLOCKED
```

Every transition not explicitly listed in the mapping fails immediately with `INVALID_TRANSITION`.

---

## 4. Fencing, Takeover & Leases

### Monotonic Epoch Invariant
- A mission is created with `leaseEpoch = 1`.
- A successful takeover increments the epoch by exactly 1 (`newEpoch = expectedLeaseEpoch + 1`).
- The former attempt/worker retains read capability, but any mutation, checkpoint, effect authorization, completion, or finish call stamped with an older epoch fails immediately with `STALE_FENCE`.

### Atomic Takeover Protocol
1. Takeover requires current phase `HANDOVER_PENDING`.
2. Must match `current.leaseEpoch === expectedLeaseEpoch`.
3. Evaluates fresh candidate offers using `selectTakeoverCandidate`.
4. Executes atomically inside a `BEGIN IMMEDIATE` transaction.
5. Emits `PHASE_TRANSITION` (`HANDOVER_PENDING -> TAKEN_OVER`) and `MISSION_TAKEOVER`.
6. Sets `recoveryPending = false`.
7. Returns `resumeFrom` bound to the latest immutable checkpoint.

### Effect Gating & Checkpoint Prerequisite
- **The Checkpoint Requirement (Law L4)**: A new owner cannot authorize an irreversible effect until it writes a new checkpoint under its new attempt ID and epoch. Any call to `authorizeEffect` prior to persisting a new-epoch checkpoint fails with `CHECKPOINT_REQUIRED`.
- **Effect Key Binding**: `effectKey` must equal `sha256(missionId + ':' + stepId + ':' + action + ':' + argsDigest)`. Any mismatch fails with `INVALID_EFFECT_KEY`.
- **Duplicate Completion Idempotency**: Repeated calls to `completeEffect` return `{ duplicate: true, receipt, completedAtMs }` without re-executing or erroring.

---

## 5. Checkpoint Triggers & Resource Ratios

Checkpointing is mandated whenever any of the following conditions evaluate to `true`:
1. `irreversibleEffectPending === true` (`IRREVERSIBLE_EFFECT_PENDING`)
2. `knownContextRemainingRatio <= 0.30` (`LOW_CONTEXT_REMAINING`)
3. `knownTokenRemainingRatio <= 0.30` (`LOW_TOKEN_REMAINING`)
4. Turn usage ratio `turnIndex / maxTurns >= 0.90` (`HIGH_TURN_USAGE`)
5. Elapsed time ratio `elapsedMs / maxElapsedMs >= 0.80` (`HIGH_ELAPSED_USAGE`)
6. `providerFaultCount >= 1` (`PROVIDER_FAULT_OCCURRED`)
7. **12-Turn Fallback**: When both context and token ratios are unknown (`null`), checkpointing is mandated once `turnIndex >= 12` (`UNKNOWN_RATIOS_TURN_THRESHOLD_EXCEEDED`).

---

## 6. Capacity Selection & Deterministic Ranking

When recovering from a failed attempt, `selectTakeoverCandidate` applies two filtration passes:

### Hard Rejection Rules
- Unauthenticated (`!offer.authenticated`)
- Stale offer (`observedAtMs + ttlMs < nowMs`)
- Future timestamp (`observedAtMs > nowMs + 5000`)
- Availability not `AVAILABLE`
- Quota not `AVAILABLE`
- Context not `SUFFICIENT`
- Concurrency available `<= 0`
- Cost budget remaining `< remainingCost`
- Missing any required capability
- Same worker ID as failed attempt
- Same failure domain as failed attempt
- Missing verified success rate or p95 latency

### Deterministic Multi-Tier Ranking
1. **Provider Diversity**: Candidate with a different provider from the failed attempt is ranked first.
2. **Success Rate**: Higher verified success rate (`b.verifiedSuccessRate - a.verifiedSuccessRate`).
3. **Latency**: Lower p95 latency (`a.p95LatencyMs - b.p95LatencyMs`).
4. **Cost**: Lower cost budget remaining (`a.costBudgetRemaining - b.costBudgetRemaining`).
5. **Lexicographic Tie-Break**: `a.workerId.localeCompare(b.workerId)`.

---

## 7. SQLite Schema & Cryptographic Integrity

The kernel manages exactly five tables in `estate.db`:

```sql
CREATE TABLE continuity_missions (
  mission_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  risk_class TEXT NOT NULL,
  goal TEXT NOT NULL,
  phase TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  worker_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  lease_expires_at_ms INTEGER NOT NULL,
  required_capabilities_json TEXT NOT NULL,
  cost_budget_remaining REAL NOT NULL,
  recovery_pending INTEGER NOT NULL,
  failure_class TEXT,
  evidence_ref TEXT,
  checkpoint_sequence INTEGER NOT NULL,
  checkpoint_digest TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  row_digest TEXT NOT NULL,
  row_hmac TEXT NOT NULL
);

CREATE TABLE continuity_attempts (
  mission_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  worker_id TEXT NOT NULL,
  adapter TEXT NOT NULL,
  execution_host TEXT NOT NULL,
  failure_domain TEXT NOT NULL,
  offer_json TEXT NOT NULL,
  stored_lease_ttl_ms INTEGER NOT NULL,
  last_heartbeat_seq INTEGER NOT NULL,
  last_heartbeat_at_ms INTEGER NOT NULL,
  last_availability TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  row_digest TEXT NOT NULL,
  row_hmac TEXT NOT NULL,
  PRIMARY KEY (mission_id, attempt_id, lease_epoch)
);

CREATE TABLE continuity_checkpoints (
  mission_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  sequence INTEGER NOT NULL,
  checkpoint_json TEXT NOT NULL,
  digest TEXT NOT NULL,
  hmac TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  row_digest TEXT NOT NULL,
  row_hmac TEXT NOT NULL,
  PRIMARY KEY (mission_id, sequence)
);

CREATE TABLE continuity_effects (
  effect_key TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  step_id TEXT NOT NULL,
  action TEXT NOT NULL,
  args_digest TEXT NOT NULL,
  token TEXT NOT NULL,
  expires_at_ms INTEGER NOT NULL,
  status TEXT NOT NULL,
  receipt_json TEXT,
  completed_at_ms INTEGER,
  row_digest TEXT NOT NULL,
  row_hmac TEXT NOT NULL
);

CREATE TABLE continuity_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  lease_epoch INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  prev_event_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  row_digest TEXT NOT NULL,
  row_hmac TEXT NOT NULL
);
```

### Row-Level Integrity & Append-Only Hash Chain
- Every row mutation serializes canonical JSON, computes `sha256`, and calculates `hmacSha256(receiptKey, canonicalJson)`.
- On read, the HMAC and digest are verified. Any mismatch throws `INTEGRITY_ERROR`.
- `continuity_events` forms an append-only cryptographic chain:
  $$\text{event\_hash}_n = \text{sha256}(\text{event\_hash}_{n-1} + ':' + \text{mission\_id} + ':' + \text{attempt\_id} + ':' + \text{epoch} + ':' + \text{type} + ':' + \text{payload} + ':' + \text{ts})$$
- Genesis event ($n=1$) uses $\text{prev\_event\_hash} = \text{'0'}^{64}$.
- Snapshot verification traverses the entire chain from event 1 to $N$. Any altered row or broken chain immediately throws `INTEGRITY_ERROR`.

---

## 8. Verification & Test Suite

The test suite consists of 28 deterministic tests covering all 22 required specification scenarios with 0 mocks, 0 stubs, and 0 fake timers.

### Verification Commands
```bash
npx tsx --test src/engine/missionContinuity.test.ts
npx tsx --test src/engine/missionContinuity.sqlite.test.ts
npm run lint
```
