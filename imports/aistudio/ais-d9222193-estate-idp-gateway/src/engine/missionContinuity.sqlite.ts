import { DatabaseSync } from 'node:sqlite';
import {
  AvailabilityState,
  CapacityOffer,
  ContinuityError,
  ContinuitySnapshot,
  EffectCompletion,
  EffectPermit,
  FailureClass,
  HeartbeatResult,
  MissionCheckpoint,
  MissionCheckpointRecord,
  MissionKind,
  MissionPhase,
  MissionRecord,
  RecoveryPendingResult,
  TakeoverResult,
  canonicalJson,
  hmacSha256,
  isValidTransition,
  selectTakeoverCandidate,
  sha256,
  validateCheckpoint,
} from './missionContinuity.js';

interface MissionRow {
  mission_id: string;
  kind: MissionKind;
  risk_class: 'P0' | 'P1' | 'P2';
  goal: string;
  phase: MissionPhase;
  attempt_id: string;
  worker_id: string;
  lease_epoch: number;
  lease_expires_at_ms: number;
  required_capabilities_json: string;
  cost_budget_remaining: number;
  recovery_pending: number;
  failure_class: string | null;
  evidence_ref: string | null;
  checkpoint_sequence: number;
  checkpoint_digest: string;
  created_at_ms: number;
  updated_at_ms: number;
  row_digest: string;
  row_hmac: string;
}

interface AttemptRow {
  mission_id: string;
  attempt_id: string;
  lease_epoch: number;
  worker_id: string;
  adapter: string;
  execution_host: string;
  failure_domain: string;
  offer_json: string;
  stored_lease_ttl_ms: number;
  last_heartbeat_seq: number;
  last_heartbeat_at_ms: number;
  last_availability: string;
  created_at_ms: number;
  row_digest: string;
  row_hmac: string;
}

interface CheckpointRow {
  mission_id: string;
  attempt_id: string;
  lease_epoch: number;
  sequence: number;
  checkpoint_json: string;
  digest: string;
  hmac: string;
  created_at_ms: number;
  row_digest: string;
  row_hmac: string;
}

interface EffectRow {
  effect_key: string;
  mission_id: string;
  attempt_id: string;
  lease_epoch: number;
  step_id: string;
  action: string;
  args_digest: string;
  token: string;
  expires_at_ms: number;
  status: 'AUTHORIZED' | 'COMPLETED';
  receipt_json: string | null;
  completed_at_ms: number | null;
  row_digest: string;
  row_hmac: string;
}

interface EventRow {
  event_id: number;
  mission_id: string;
  attempt_id: string;
  lease_epoch: number;
  event_type: string;
  payload_json: string;
  created_at_ms: number;
  prev_event_hash: string;
  event_hash: string;
  row_digest: string;
  row_hmac: string;
}

export class MissionContinuityKernel {
  private readonly db: DatabaseSync;
  private readonly receiptKey: string;
  private readonly now: () => number;

  constructor(options: {
    dbPath: string;
    receiptKey: string;
    now?: () => number;
  }) {
    if (!options.receiptKey || options.receiptKey.length < 32) {
      throw new ContinuityError(
        'WEAK_RECEIPT_KEY',
        'Receipt key must be at least 32 characters'
      );
    }
    this.receiptKey = options.receiptKey;
    this.now = options.now ?? (() => Date.now());

    this.db = new DatabaseSync(options.dbPath);
    this.db.exec('PRAGMA journal_mode = WAL;');
    this.initTables();
  }

  private initTables(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS continuity_missions (
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

      CREATE TABLE IF NOT EXISTS continuity_attempts (
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

      CREATE TABLE IF NOT EXISTS continuity_checkpoints (
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

      CREATE TABLE IF NOT EXISTS continuity_effects (
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

      CREATE TABLE IF NOT EXISTS continuity_events (
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
    `);
  }

  private withTransaction<T>(action: () => T): T {
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const result = action();
      this.db.exec('COMMIT');
      return result;
    } catch (err) {
      try {
        this.db.exec('ROLLBACK');
      } catch {
        // Ignored if transaction already ended
      }
      throw err;
    }
  }

  private computeRowHMAC(data: unknown): { digest: string; hmac: string } {
    const cjson = canonicalJson(data);
    return {
      digest: sha256(cjson),
      hmac: hmacSha256(this.receiptKey, cjson),
    };
  }

  private verifyRowIntegrity(data: unknown, rowDigest: string, rowHmac: string): void {
    const { digest, hmac } = this.computeRowHMAC(data);
    if (digest !== rowDigest || hmac !== rowHmac) {
      throw new ContinuityError(
        'INTEGRITY_ERROR',
        'Database row tamper detected: digest or HMAC mismatch'
      );
    }
  }

  private appendEvent(
    missionId: string,
    attemptId: string,
    leaseEpoch: number,
    eventType: string,
    payload: unknown
  ): void {
    const nowMs = this.now();
    const payloadJson = canonicalJson(payload);

    // Fetch the latest event to continue the immutable hash chain
    const lastRow = this.db
      .prepare('SELECT event_id, event_hash FROM continuity_events ORDER BY event_id DESC LIMIT 1')
      .get() as { event_id: number; event_hash: string } | undefined;

    const prevEventHash = lastRow ? lastRow.event_hash : '0'.repeat(64);
    const eventHash = sha256(
      prevEventHash +
        ':' +
        missionId +
        ':' +
        attemptId +
        ':' +
        leaseEpoch +
        ':' +
        eventType +
        ':' +
        payloadJson +
        ':' +
        nowMs
    );

    const eventData = {
      missionId,
      attemptId,
      leaseEpoch,
      eventType,
      payloadJson,
      createdAtMs: nowMs,
      prevEventHash,
      eventHash,
    };
    const { digest, hmac } = this.computeRowHMAC(eventData);

    this.db
      .prepare(`
        INSERT INTO continuity_events (
          mission_id, attempt_id, lease_epoch, event_type,
          payload_json, created_at_ms, prev_event_hash, event_hash,
          row_digest, row_hmac
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .run(
        missionId,
        attemptId,
        leaseEpoch,
        eventType,
        payloadJson,
        nowMs,
        prevEventHash,
        eventHash,
        digest,
        hmac
      );
  }

  private mapMissionRow(row: MissionRow): MissionRecord {
    const rowData = {
      missionId: row.mission_id,
      kind: row.kind,
      riskClass: row.risk_class,
      goal: row.goal,
      phase: row.phase,
      attemptId: row.attempt_id,
      workerId: row.worker_id,
      leaseEpoch: row.lease_epoch,
      leaseExpiresAtMs: row.lease_expires_at_ms,
      requiredCapabilitiesJson: row.required_capabilities_json,
      costBudgetRemaining: row.cost_budget_remaining,
      recoveryPending: row.recovery_pending,
      failureClass: row.failure_class,
      evidenceRef: row.evidence_ref,
      checkpointSequence: row.checkpoint_sequence,
      checkpointDigest: row.checkpoint_digest,
      createdAtMs: row.created_at_ms,
      updatedAtMs: row.updated_at_ms,
    };
    this.verifyRowIntegrity(rowData, row.row_digest, row.row_hmac);

    return {
      missionId: row.mission_id,
      kind: row.kind,
      riskClass: row.risk_class,
      goal: row.goal,
      phase: row.phase,
      attemptId: row.attempt_id,
      workerId: row.worker_id,
      leaseEpoch: row.lease_epoch,
      leaseExpiresAtMs: row.lease_expires_at_ms,
      requiredCapabilities: JSON.parse(row.required_capabilities_json),
      costBudgetRemaining: row.cost_budget_remaining,
      recoveryPending: row.recovery_pending === 1,
      failureClass: row.failure_class as FailureClass | null,
      evidenceRef: row.evidence_ref,
      checkpointSequence: row.checkpoint_sequence,
      checkpointDigest: row.checkpoint_digest,
      createdAtMs: row.created_at_ms,
      updatedAtMs: row.updated_at_ms,
    };
  }

  private getMission(missionId: string): MissionRecord | null {
    const row = this.db
      .prepare('SELECT * FROM continuity_missions WHERE mission_id = ?')
      .get(missionId) as MissionRow | undefined;
    if (!row) return null;
    return this.mapMissionRow(row);
  }

  private mapCheckpointRow(row: CheckpointRow): MissionCheckpointRecord {
    const rowData = {
      missionId: row.mission_id,
      attemptId: row.attempt_id,
      leaseEpoch: row.lease_epoch,
      sequence: row.sequence,
      checkpointJson: row.checkpoint_json,
      digest: row.digest,
      hmac: row.hmac,
      createdAtMs: row.created_at_ms,
    };
    this.verifyRowIntegrity(rowData, row.row_digest, row.row_hmac);

    const checkpointObj = JSON.parse(row.checkpoint_json) as MissionCheckpoint;
    const computedHmac = hmacSha256(this.receiptKey, canonicalJson(checkpointObj));
    const computedDigest = sha256(canonicalJson(checkpointObj));

    if (computedDigest !== row.digest || computedHmac !== row.hmac) {
      throw new ContinuityError(
        'INTEGRITY_ERROR',
        'Checkpoint HMAC or digest mismatch: content tampered'
      );
    }

    return {
      missionId: row.mission_id,
      attemptId: row.attempt_id,
      leaseEpoch: row.lease_epoch,
      sequence: row.sequence,
      checkpoint: checkpointObj,
      digest: row.digest,
      hmac: row.hmac,
      createdAtMs: row.created_at_ms,
    };
  }

  claimMission(input: {
    missionId: string;
    kind: MissionKind;
    riskClass: 'P0' | 'P1' | 'P2';
    goal: string;
    attemptId: string;
    workerId: string;
    offer: CapacityOffer;
    requiredCapabilities: string[];
    costBudgetRemaining: number;
    initialCheckpoint: MissionCheckpoint;
  }): MissionRecord {
    return this.withTransaction(() => {
      const now = this.now();
      const existing = this.getMission(input.missionId);

      const initialCheckpointDigest = sha256(canonicalJson(input.initialCheckpoint));

      if (existing) {
        // Idempotency: same mission, attempt, worker and initial checkpoint digest
        if (
          existing.attemptId === input.attemptId &&
          existing.workerId === input.workerId &&
          existing.checkpointDigest === initialCheckpointDigest
        ) {
          return existing;
        }
        throw new ContinuityError(
          'LEASE_HELD',
          `Mission '${input.missionId}' is already claimed or active under different parameters`
        );
      }

      // Validate capacity offer for initial claim
      if (!input.offer.authenticated) {
        throw new ContinuityError('INELIGIBLE_WORKER', 'Offer is not authenticated');
      }
      if (input.offer.observedAtMs + input.offer.ttlMs < now) {
        throw new ContinuityError('INELIGIBLE_WORKER', 'Offer is stale');
      }
      if (input.offer.observedAtMs > now + 5000) {
        throw new ContinuityError('INELIGIBLE_WORKER', 'Offer is from the future');
      }
      if (input.offer.availability !== 'AVAILABLE') {
        throw new ContinuityError('INELIGIBLE_WORKER', `Worker unavailable: ${input.offer.availability}`);
      }
      if (input.offer.quotaState !== 'AVAILABLE') {
        throw new ContinuityError('INELIGIBLE_WORKER', `Quota exhausted: ${input.offer.quotaState}`);
      }
      if (input.offer.contextState !== 'SUFFICIENT') {
        throw new ContinuityError('INELIGIBLE_WORKER', `Context insufficient: ${input.offer.contextState}`);
      }
      if (input.offer.concurrencyAvailable <= 0) {
        throw new ContinuityError('INELIGIBLE_WORKER', 'Concurrency exhausted');
      }
      if (input.offer.costBudgetRemaining < input.costBudgetRemaining) {
        throw new ContinuityError('INELIGIBLE_WORKER', 'Cost budget insufficient');
      }
      if (input.offer.workerId !== input.workerId) {
        throw new ContinuityError('INELIGIBLE_WORKER', 'Offer workerId mismatch');
      }
      for (const reqCap of input.requiredCapabilities) {
        if (!input.offer.capabilities.includes(reqCap)) {
          throw new ContinuityError('INELIGIBLE_WORKER', `Missing required capability '${reqCap}'`);
        }
      }

      // Validate initial checkpoint
      validateCheckpoint(input.initialCheckpoint, input.kind);
      if (input.initialCheckpoint.sequence !== 1) {
        throw new ContinuityError('INVALID_INPUT', 'Initial checkpoint sequence must be 1');
      }
      if (input.initialCheckpoint.leaseEpoch !== 1) {
        throw new ContinuityError('INVALID_INPUT', 'Initial checkpoint leaseEpoch must be 1');
      }
      if (input.initialCheckpoint.missionId !== input.missionId) {
        throw new ContinuityError('INVALID_INPUT', 'Initial checkpoint missionId mismatch');
      }
      if (input.initialCheckpoint.attemptId !== input.attemptId) {
        throw new ContinuityError('INVALID_INPUT', 'Initial checkpoint attemptId mismatch');
      }

      const leaseExpiresAtMs = Math.min(now + 60_000, input.offer.observedAtMs + input.offer.ttlMs);
      const chkCanonical = canonicalJson(input.initialCheckpoint);
      const chkDigest = sha256(chkCanonical);
      const chkHmac = hmacSha256(this.receiptKey, chkCanonical);

      // Record transitions: QUEUED -> CLAIMED -> EXECUTING
      this.appendEvent(input.missionId, input.attemptId, 1, 'PHASE_TRANSITION', {
        from: 'QUEUED',
        to: 'CLAIMED',
      });
      this.appendEvent(input.missionId, input.attemptId, 1, 'PHASE_TRANSITION', {
        from: 'CLAIMED',
        to: 'EXECUTING',
      });

      // Insert Attempt Row
      const attemptData = {
        missionId: input.missionId,
        attemptId: input.attemptId,
        leaseEpoch: 1,
        workerId: input.workerId,
        adapter: input.offer.adapter,
        executionHost: input.offer.executionHost,
        failureDomain: input.offer.failureDomain,
        offerJson: canonicalJson(input.offer),
        storedLeaseTtlMs: input.offer.ttlMs,
        lastHeartbeatSeq: 0,
        lastHeartbeatAtMs: now,
        lastAvailability: input.offer.availability,
        createdAtMs: now,
      };
      const attemptHMAC = this.computeRowHMAC(attemptData);

      this.db
        .prepare(`
          INSERT INTO continuity_attempts (
            mission_id, attempt_id, lease_epoch, worker_id,
            adapter, execution_host, failure_domain, offer_json,
            stored_lease_ttl_ms, last_heartbeat_seq, last_heartbeat_at_ms,
            last_availability, created_at_ms, row_digest, row_hmac
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .run(
          input.missionId,
          input.attemptId,
          1,
          input.workerId,
          input.offer.adapter,
          input.offer.executionHost,
          input.offer.failureDomain,
          attemptData.offerJson,
          input.offer.ttlMs,
          0,
          now,
          input.offer.availability,
          now,
          attemptHMAC.digest,
          attemptHMAC.hmac
        );

      // Insert Checkpoint Row
      const checkpointData = {
        missionId: input.missionId,
        attemptId: input.attemptId,
        leaseEpoch: 1,
        sequence: 1,
        checkpointJson: chkCanonical,
        digest: chkDigest,
        hmac: chkHmac,
        createdAtMs: now,
      };
      const chkRowHMAC = this.computeRowHMAC(checkpointData);

      this.db
        .prepare(`
          INSERT INTO continuity_checkpoints (
            mission_id, attempt_id, lease_epoch, sequence,
            checkpoint_json, digest, hmac, created_at_ms,
            row_digest, row_hmac
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .run(
          input.missionId,
          input.attemptId,
          1,
          1,
          chkCanonical,
          chkDigest,
          chkHmac,
          now,
          chkRowHMAC.digest,
          chkRowHMAC.hmac
        );

      // Insert Mission Row in EXECUTING phase
      const reqCapsJson = canonicalJson(input.requiredCapabilities);
      const missionData = {
        missionId: input.missionId,
        kind: input.kind,
        riskClass: input.riskClass,
        goal: input.goal,
        phase: 'EXECUTING',
        attemptId: input.attemptId,
        workerId: input.workerId,
        leaseEpoch: 1,
        leaseExpiresAtMs,
        requiredCapabilitiesJson: reqCapsJson,
        costBudgetRemaining: input.costBudgetRemaining,
        recoveryPending: 0,
        failureClass: null,
        evidenceRef: null,
        checkpointSequence: 1,
        checkpointDigest: chkDigest,
        createdAtMs: now,
        updatedAtMs: now,
      };
      const missionHMAC = this.computeRowHMAC(missionData);

      this.db
        .prepare(`
          INSERT INTO continuity_missions (
            mission_id, kind, risk_class, goal, phase,
            attempt_id, worker_id, lease_epoch, lease_expires_at_ms,
            required_capabilities_json, cost_budget_remaining, recovery_pending,
            failure_class, evidence_ref, checkpoint_sequence, checkpoint_digest,
            created_at_ms, updated_at_ms, row_digest, row_hmac
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .run(
          input.missionId,
          input.kind,
          input.riskClass,
          input.goal,
          'EXECUTING',
          input.attemptId,
          input.workerId,
          1,
          leaseExpiresAtMs,
          reqCapsJson,
          input.costBudgetRemaining,
          0,
          null,
          null,
          1,
          chkDigest,
          now,
          now,
          missionHMAC.digest,
          missionHMAC.hmac
        );

      this.appendEvent(input.missionId, input.attemptId, 1, 'MISSION_CLAIMED', {
        workerId: input.workerId,
        checkpointDigest: chkDigest,
      });

      return {
        missionId: input.missionId,
        kind: input.kind,
        riskClass: input.riskClass,
        goal: input.goal,
        phase: 'EXECUTING',
        attemptId: input.attemptId,
        workerId: input.workerId,
        leaseEpoch: 1,
        leaseExpiresAtMs,
        requiredCapabilities: input.requiredCapabilities,
        costBudgetRemaining: input.costBudgetRemaining,
        recoveryPending: false,
        failureClass: null,
        evidenceRef: null,
        checkpointSequence: 1,
        checkpointDigest: chkDigest,
        createdAtMs: now,
        updatedAtMs: now,
      };
    });
  }

  heartbeat(input: {
    missionId: string;
    attemptId: string;
    leaseEpoch: number;
    sequence: number;
    phase: MissionPhase;
    checkpointAgeMs: number;
    lastActionId: string;
    availability: AvailabilityState;
    progressDigest: string;
  }): HeartbeatResult {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.missionId);

      if (!mission) {
        throw new ContinuityError(
          'MISSION_NOT_FOUND',
          `Mission '${input.missionId}' not found for heartbeat`
        );
      }

      // Check for heartbeat rejection conditions
      let rejectReason: string | null = null;
      if (input.leaseEpoch !== mission.leaseEpoch) {
        rejectReason = 'WRONG_LEASE_EPOCH';
      } else if (input.attemptId !== mission.attemptId) {
        rejectReason = 'WRONG_ATTEMPT';
      } else if (input.phase !== mission.phase) {
        rejectReason = 'PHASE_MISMATCH';
      }

      const attemptRow = this.db
        .prepare(`
          SELECT * FROM continuity_attempts
          WHERE mission_id = ? AND attempt_id = ? AND lease_epoch = ?
        `)
        .get(input.missionId, input.attemptId, input.leaseEpoch) as AttemptRow | undefined;

      if (!attemptRow) {
        rejectReason = rejectReason ?? 'ATTEMPT_NOT_FOUND';
      } else {
        const attemptData = {
          missionId: attemptRow.mission_id,
          attemptId: attemptRow.attempt_id,
          leaseEpoch: attemptRow.lease_epoch,
          workerId: attemptRow.worker_id,
          adapter: attemptRow.adapter,
          executionHost: attemptRow.execution_host,
          failureDomain: attemptRow.failure_domain,
          offerJson: attemptRow.offer_json,
          storedLeaseTtlMs: attemptRow.stored_lease_ttl_ms,
          lastHeartbeatSeq: attemptRow.last_heartbeat_seq,
          lastHeartbeatAtMs: attemptRow.last_heartbeat_at_ms,
          lastAvailability: attemptRow.last_availability,
          createdAtMs: attemptRow.created_at_ms,
        };
        this.verifyRowIntegrity(attemptData, attemptRow.row_digest, attemptRow.row_hmac);

        if (input.sequence <= attemptRow.last_heartbeat_seq) {
          rejectReason = rejectReason ?? 'SEQUENCE_NOT_INCREASING';
        }
      }

      if (rejectReason) {
        this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'HEARTBEAT_REJECTED', {
          reason: rejectReason,
          sequence: input.sequence,
        });
        return {
          accepted: false,
          reason: rejectReason,
          observedAtMs: now,
          leaseExpiresAtMs: mission.leaseExpiresAtMs,
        };
      }

      // Accepted heartbeat
      const storedTtl = attemptRow!.stored_lease_ttl_ms;
      const renewedLeaseExpiry = Math.min(now + storedTtl, now + 60_000);

      // Update attempt
      const updatedAttemptData = {
        missionId: attemptRow!.mission_id,
        attemptId: attemptRow!.attempt_id,
        leaseEpoch: attemptRow!.lease_epoch,
        workerId: attemptRow!.worker_id,
        adapter: attemptRow!.adapter,
        executionHost: attemptRow!.execution_host,
        failureDomain: attemptRow!.failure_domain,
        offerJson: attemptRow!.offer_json,
        storedLeaseTtlMs: storedTtl,
        lastHeartbeatSeq: input.sequence,
        lastHeartbeatAtMs: now,
        lastAvailability: input.availability,
        createdAtMs: attemptRow!.created_at_ms,
      };
      const updatedAttemptHMAC = this.computeRowHMAC(updatedAttemptData);

      this.db
        .prepare(`
          UPDATE continuity_attempts
          SET last_heartbeat_seq = ?, last_heartbeat_at_ms = ?, last_availability = ?,
              row_digest = ?, row_hmac = ?
          WHERE mission_id = ? AND attempt_id = ? AND lease_epoch = ?
        `)
        .run(
          input.sequence,
          now,
          input.availability,
          updatedAttemptHMAC.digest,
          updatedAttemptHMAC.hmac,
          input.missionId,
          input.attemptId,
          input.leaseEpoch
        );

      // Update mission lease expiry
      const missionData = {
        missionId: mission.missionId,
        kind: mission.kind,
        riskClass: mission.riskClass,
        goal: mission.goal,
        phase: mission.phase,
        attemptId: mission.attemptId,
        workerId: mission.workerId,
        leaseEpoch: mission.leaseEpoch,
        leaseExpiresAtMs: renewedLeaseExpiry,
        requiredCapabilitiesJson: canonicalJson(mission.requiredCapabilities),
        costBudgetRemaining: mission.costBudgetRemaining,
        recoveryPending: mission.recoveryPending ? 1 : 0,
        failureClass: mission.failureClass,
        evidenceRef: mission.evidenceRef,
        checkpointSequence: mission.checkpointSequence,
        checkpointDigest: mission.checkpointDigest,
        createdAtMs: mission.createdAtMs,
        updatedAtMs: now,
      };
      const missionHMAC = this.computeRowHMAC(missionData);

      this.db
        .prepare(`
          UPDATE continuity_missions
          SET lease_expires_at_ms = ?, updated_at_ms = ?, row_digest = ?, row_hmac = ?
          WHERE mission_id = ?
        `)
        .run(renewedLeaseExpiry, now, missionHMAC.digest, missionHMAC.hmac, input.missionId);

      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'HEARTBEAT_ACCEPTED', {
        sequence: input.sequence,
        leaseExpiresAtMs: renewedLeaseExpiry,
      });

      return {
        accepted: true,
        reason: 'HEARTBEAT_ACCEPTED',
        observedAtMs: now,
        leaseExpiresAtMs: renewedLeaseExpiry,
      };
    });
  }

  checkpoint(input: {
    missionId: string;
    attemptId: string;
    leaseEpoch: number;
    checkpoint: MissionCheckpoint;
  }): MissionCheckpointRecord {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.missionId);

      if (!mission) {
        throw new ContinuityError(
          'MISSION_NOT_FOUND',
          `Mission '${input.missionId}' not found for checkpoint`
        );
      }

      if (input.leaseEpoch !== mission.leaseEpoch) {
        throw new ContinuityError(
          'STALE_FENCE',
          `Stale fence: checkpoint epoch ${input.leaseEpoch} does not match active epoch ${mission.leaseEpoch}`
        );
      }
      if (input.attemptId !== mission.attemptId) {
        throw new ContinuityError(
          'STALE_FENCE',
          `Stale fence: checkpoint attempt '${input.attemptId}' does not match active attempt '${mission.attemptId}'`
        );
      }

      validateCheckpoint(input.checkpoint, mission.kind);

      if (input.checkpoint.missionId !== input.missionId) {
        throw new ContinuityError('INVALID_INPUT', 'Checkpoint missionId mismatch');
      }
      if (input.checkpoint.attemptId !== input.attemptId) {
        throw new ContinuityError('INVALID_INPUT', 'Checkpoint attemptId mismatch');
      }
      if (input.checkpoint.leaseEpoch !== input.leaseEpoch) {
        throw new ContinuityError('INVALID_INPUT', 'Checkpoint leaseEpoch mismatch');
      }
      if (input.checkpoint.sequence <= mission.checkpointSequence) {
        throw new ContinuityError(
          'INVALID_INPUT',
          `Checkpoint sequence ${input.checkpoint.sequence} must be greater than current sequence ${mission.checkpointSequence}`
        );
      }

      // If in TAKEN_OVER, checkpointing transitions to EXECUTING
      let targetPhase = mission.phase;
      if (mission.phase === 'TAKEN_OVER') {
        targetPhase = 'EXECUTING';
        this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'PHASE_TRANSITION', {
          from: 'TAKEN_OVER',
          to: 'EXECUTING',
        });
      }

      const chkCanonical = canonicalJson(input.checkpoint);
      const chkDigest = sha256(chkCanonical);
      const chkHmac = hmacSha256(this.receiptKey, chkCanonical);

      const chkRowData = {
        missionId: input.missionId,
        attemptId: input.attemptId,
        leaseEpoch: input.leaseEpoch,
        sequence: input.checkpoint.sequence,
        checkpointJson: chkCanonical,
        digest: chkDigest,
        hmac: chkHmac,
        createdAtMs: now,
      };
      const chkRowHMAC = this.computeRowHMAC(chkRowData);

      this.db
        .prepare(`
          INSERT INTO continuity_checkpoints (
            mission_id, attempt_id, lease_epoch, sequence,
            checkpoint_json, digest, hmac, created_at_ms,
            row_digest, row_hmac
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .run(
          input.missionId,
          input.attemptId,
          input.leaseEpoch,
          input.checkpoint.sequence,
          chkCanonical,
          chkDigest,
          chkHmac,
          now,
          chkRowHMAC.digest,
          chkRowHMAC.hmac
        );

      const updatedMissionData = {
        missionId: mission.missionId,
        kind: mission.kind,
        riskClass: mission.riskClass,
        goal: mission.goal,
        phase: targetPhase,
        attemptId: mission.attemptId,
        workerId: mission.workerId,
        leaseEpoch: mission.leaseEpoch,
        leaseExpiresAtMs: mission.leaseExpiresAtMs,
        requiredCapabilitiesJson: canonicalJson(mission.requiredCapabilities),
        costBudgetRemaining: mission.costBudgetRemaining,
        recoveryPending: mission.recoveryPending ? 1 : 0,
        failureClass: mission.failureClass,
        evidenceRef: mission.evidenceRef,
        checkpointSequence: input.checkpoint.sequence,
        checkpointDigest: chkDigest,
        createdAtMs: mission.createdAtMs,
        updatedAtMs: now,
      };
      const updatedMissionHMAC = this.computeRowHMAC(updatedMissionData);

      this.db
        .prepare(`
          UPDATE continuity_missions
          SET phase = ?, checkpoint_sequence = ?, checkpoint_digest = ?,
              updated_at_ms = ?, row_digest = ?, row_hmac = ?
          WHERE mission_id = ?
        `)
        .run(
          targetPhase,
          input.checkpoint.sequence,
          chkDigest,
          now,
          updatedMissionHMAC.digest,
          updatedMissionHMAC.hmac,
          input.missionId
        );

      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'CHECKPOINT_SAVED', {
        sequence: input.checkpoint.sequence,
        digest: chkDigest,
      });

      return {
        missionId: input.missionId,
        attemptId: input.attemptId,
        leaseEpoch: input.leaseEpoch,
        sequence: input.checkpoint.sequence,
        checkpoint: input.checkpoint,
        digest: chkDigest,
        hmac: chkHmac,
        createdAtMs: now,
      };
    });
  }

  beginHandover(input: {
    missionId: string;
    attemptId: string;
    leaseEpoch: number;
    failureClass: FailureClass;
    evidenceRef: string;
  }): MissionRecord {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.missionId);

      if (!mission) {
        throw new ContinuityError(
          'MISSION_NOT_FOUND',
          `Mission '${input.missionId}' not found for handover`
        );
      }

      if (input.leaseEpoch !== mission.leaseEpoch) {
        throw new ContinuityError('STALE_FENCE', 'Stale lease epoch on handover attempt');
      }
      if (input.attemptId !== mission.attemptId) {
        throw new ContinuityError('STALE_FENCE', 'Stale attemptId on handover attempt');
      }

      if (!isValidTransition(mission.phase, 'HANDOVER_PENDING')) {
        throw new ContinuityError(
          'INVALID_TRANSITION',
          `Cannot transition to HANDOVER_PENDING from '${mission.phase}'`
        );
      }

      const updatedMissionData = {
        missionId: mission.missionId,
        kind: mission.kind,
        riskClass: mission.riskClass,
        goal: mission.goal,
        phase: 'HANDOVER_PENDING',
        attemptId: mission.attemptId,
        workerId: mission.workerId,
        leaseEpoch: mission.leaseEpoch,
        leaseExpiresAtMs: now, // Lease expires immediately on handover
        requiredCapabilitiesJson: canonicalJson(mission.requiredCapabilities),
        costBudgetRemaining: mission.costBudgetRemaining,
        recoveryPending: mission.recoveryPending ? 1 : 0,
        failureClass: input.failureClass,
        evidenceRef: input.evidenceRef,
        checkpointSequence: mission.checkpointSequence,
        checkpointDigest: mission.checkpointDigest,
        createdAtMs: mission.createdAtMs,
        updatedAtMs: now,
      };
      const updatedMissionHMAC = this.computeRowHMAC(updatedMissionData);

      this.db
        .prepare(`
          UPDATE continuity_missions
          SET phase = 'HANDOVER_PENDING', lease_expires_at_ms = ?, failure_class = ?,
              evidence_ref = ?, updated_at_ms = ?, row_digest = ?, row_hmac = ?
          WHERE mission_id = ?
        `)
        .run(
          now,
          input.failureClass,
          input.evidenceRef,
          now,
          updatedMissionHMAC.digest,
          updatedMissionHMAC.hmac,
          input.missionId
        );

      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'PHASE_TRANSITION', {
        from: mission.phase,
        to: 'HANDOVER_PENDING',
      });
      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'HANDOVER_BEGUN', {
        failureClass: input.failureClass,
        evidenceRef: input.evidenceRef,
      });

      return {
        ...mission,
        phase: 'HANDOVER_PENDING',
        leaseExpiresAtMs: now,
        failureClass: input.failureClass,
        evidenceRef: input.evidenceRef,
        updatedAtMs: now,
      };
    });
  }

  claimTakeover(input: {
    missionId: string;
    expectedLeaseEpoch: number;
    newAttemptId: string;
    newWorkerId: string;
    offer: CapacityOffer;
  }): TakeoverResult {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.missionId);

      if (!mission) {
        throw new ContinuityError(
          'MISSION_NOT_FOUND',
          `Mission '${input.missionId}' not found for takeover`
        );
      }

      // Idempotent takeover replay check
      if (
        mission.attemptId === input.newAttemptId &&
        mission.workerId === input.newWorkerId &&
        mission.leaseEpoch === input.expectedLeaseEpoch + 1
      ) {
        const latestChk = this.getLatestCheckpoint(input.missionId);
        return {
          mission,
          resumeFrom: latestChk,
          mustCheckpointBeforeEffect: true,
        };
      }

      if (mission.leaseEpoch !== input.expectedLeaseEpoch) {
        throw new ContinuityError(
          'STALE_FENCE',
          `Takeover epoch mismatch: expected ${input.expectedLeaseEpoch}, but active epoch is ${mission.leaseEpoch}`
        );
      }

      if (mission.phase !== 'HANDOVER_PENDING') {
        throw new ContinuityError(
          'INVALID_TRANSITION',
          `Takeover requires current phase HANDOVER_PENDING, found '${mission.phase}'`
        );
      }

      // Retrieve failed attempt metadata to ensure failure domain exclusion and capability fit
      const failedAttemptRow = this.db
        .prepare(`
          SELECT * FROM continuity_attempts
          WHERE mission_id = ? AND lease_epoch = ?
          ORDER BY created_at_ms DESC LIMIT 1
        `)
        .get(input.missionId, input.expectedLeaseEpoch) as AttemptRow | undefined;

      const failedWorkerId = failedAttemptRow ? failedAttemptRow.worker_id : mission.workerId;
      const failedFailureDomain = failedAttemptRow
        ? failedAttemptRow.failure_domain
        : 'unknown_domain';
      let failedProvider = 'unknown_provider';
      if (failedAttemptRow) {
        try {
          const offerParsed = JSON.parse(failedAttemptRow.offer_json) as CapacityOffer;
          failedProvider = offerParsed.providers[0] ?? 'unknown_provider';
        } catch {
          // Fallback
        }
      }

      // Use selectTakeoverCandidate
      const candidateEvaluation = selectTakeoverCandidate({
        failedAttempt: {
          workerId: failedWorkerId,
          failureDomain: failedFailureDomain,
          provider: failedProvider,
        },
        requiredCapabilities: mission.requiredCapabilities,
        remainingCost: mission.costBudgetRemaining,
        offers: [input.offer],
        nowMs: now,
      });

      if (!candidateEvaluation.selected) {
        const rejectReason = candidateEvaluation.rejected[0]?.reason ?? 'INELIGIBLE_WORKER';
        throw new ContinuityError('INELIGIBLE_WORKER', `Takeover candidate rejected: ${rejectReason}`);
      }

      const nextEpoch = mission.leaseEpoch + 1;
      const newLeaseExpiresAtMs = Math.min(now + 60_000, input.offer.observedAtMs + input.offer.ttlMs);

      // Record new attempt
      const attemptData = {
        missionId: input.missionId,
        attemptId: input.newAttemptId,
        leaseEpoch: nextEpoch,
        workerId: input.newWorkerId,
        adapter: input.offer.adapter,
        executionHost: input.offer.executionHost,
        failureDomain: input.offer.failureDomain,
        offerJson: canonicalJson(input.offer),
        storedLeaseTtlMs: input.offer.ttlMs,
        lastHeartbeatSeq: 0,
        lastHeartbeatAtMs: now,
        lastAvailability: input.offer.availability,
        createdAtMs: now,
      };
      const attemptHMAC = this.computeRowHMAC(attemptData);

      this.db
        .prepare(`
          INSERT INTO continuity_attempts (
            mission_id, attempt_id, lease_epoch, worker_id,
            adapter, execution_host, failure_domain, offer_json,
            stored_lease_ttl_ms, last_heartbeat_seq, last_heartbeat_at_ms,
            last_availability, created_at_ms, row_digest, row_hmac
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .run(
          input.missionId,
          input.newAttemptId,
          nextEpoch,
          input.newWorkerId,
          input.offer.adapter,
          input.offer.executionHost,
          input.offer.failureDomain,
          attemptData.offerJson,
          input.offer.ttlMs,
          0,
          now,
          input.offer.availability,
          now,
          attemptHMAC.digest,
          attemptHMAC.hmac
        );

      // Update mission to TAKEN_OVER and clear recovery pending
      const updatedMissionData = {
        missionId: mission.missionId,
        kind: mission.kind,
        riskClass: mission.riskClass,
        goal: mission.goal,
        phase: 'TAKEN_OVER',
        attemptId: input.newAttemptId,
        workerId: input.newWorkerId,
        leaseEpoch: nextEpoch,
        leaseExpiresAtMs: newLeaseExpiresAtMs,
        requiredCapabilitiesJson: canonicalJson(mission.requiredCapabilities),
        costBudgetRemaining: mission.costBudgetRemaining,
        recoveryPending: 0,
        failureClass: mission.failureClass,
        evidenceRef: mission.evidenceRef,
        checkpointSequence: mission.checkpointSequence,
        checkpointDigest: mission.checkpointDigest,
        createdAtMs: mission.createdAtMs,
        updatedAtMs: now,
      };
      const updatedMissionHMAC = this.computeRowHMAC(updatedMissionData);

      this.db
        .prepare(`
          UPDATE continuity_missions
          SET phase = 'TAKEN_OVER', attempt_id = ?, worker_id = ?, lease_epoch = ?,
              lease_expires_at_ms = ?, recovery_pending = 0, updated_at_ms = ?,
              row_digest = ?, row_hmac = ?
          WHERE mission_id = ?
        `)
        .run(
          input.newAttemptId,
          input.newWorkerId,
          nextEpoch,
          newLeaseExpiresAtMs,
          now,
          updatedMissionHMAC.digest,
          updatedMissionHMAC.hmac,
          input.missionId
        );

      this.appendEvent(input.missionId, input.newAttemptId, nextEpoch, 'PHASE_TRANSITION', {
        from: 'HANDOVER_PENDING',
        to: 'TAKEN_OVER',
      });
      this.appendEvent(input.missionId, input.newAttemptId, nextEpoch, 'MISSION_TAKEOVER', {
        previousWorkerId: mission.workerId,
        previousAttemptId: mission.attemptId,
        newWorkerId: input.newWorkerId,
        newAttemptId: input.newAttemptId,
        newLeaseEpoch: nextEpoch,
      });

      const updatedRecord: MissionRecord = {
        ...mission,
        phase: 'TAKEN_OVER',
        attemptId: input.newAttemptId,
        workerId: input.newWorkerId,
        leaseEpoch: nextEpoch,
        leaseExpiresAtMs: newLeaseExpiresAtMs,
        recoveryPending: false,
        updatedAtMs: now,
      };

      const resumeFrom = this.getLatestCheckpoint(input.missionId);

      return {
        mission: updatedRecord,
        resumeFrom,
        mustCheckpointBeforeEffect: true,
      };
    });
  }

  markRecoveryPending(input: {
    missionId: string;
    expectedLeaseEpoch: number;
    reason: string;
  }): RecoveryPendingResult {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.missionId);

      if (!mission) {
        throw new ContinuityError(
          'MISSION_NOT_FOUND',
          `Mission '${input.missionId}' not found for recovery pending`
        );
      }

      if (mission.phase !== 'HANDOVER_PENDING') {
        throw new ContinuityError(
          'INVALID_TRANSITION',
          `markRecoveryPending requires phase HANDOVER_PENDING, found '${mission.phase}'`
        );
      }

      if (mission.leaseEpoch !== input.expectedLeaseEpoch) {
        throw new ContinuityError(
          'STALE_FENCE',
          `Expected epoch mismatch: expected ${input.expectedLeaseEpoch}, found ${mission.leaseEpoch}`
        );
      }

      // Mark recovery_pending = 1 without modifying epoch
      const updatedMissionData = {
        missionId: mission.missionId,
        kind: mission.kind,
        riskClass: mission.riskClass,
        goal: mission.goal,
        phase: mission.phase,
        attemptId: mission.attemptId,
        workerId: mission.workerId,
        leaseEpoch: mission.leaseEpoch,
        leaseExpiresAtMs: mission.leaseExpiresAtMs,
        requiredCapabilitiesJson: canonicalJson(mission.requiredCapabilities),
        costBudgetRemaining: mission.costBudgetRemaining,
        recoveryPending: 1,
        failureClass: mission.failureClass,
        evidenceRef: mission.evidenceRef,
        checkpointSequence: mission.checkpointSequence,
        checkpointDigest: mission.checkpointDigest,
        createdAtMs: mission.createdAtMs,
        updatedAtMs: now,
      };
      const updatedMissionHMAC = this.computeRowHMAC(updatedMissionData);

      this.db
        .prepare(`
          UPDATE continuity_missions
          SET recovery_pending = 1, updated_at_ms = ?, row_digest = ?, row_hmac = ?
          WHERE mission_id = ?
        `)
        .run(now, updatedMissionHMAC.digest, updatedMissionHMAC.hmac, input.missionId);

      this.appendEvent(input.missionId, mission.attemptId, mission.leaseEpoch, 'RECOVERY_PENDING', {
        reason: input.reason,
      });

      return {
        mission: {
          ...mission,
          recoveryPending: true,
          updatedAtMs: now,
        },
        selected: null,
        rejected: [{ workerId: 'none', reason: input.reason }],
      };
    });
  }

  authorizeEffect(input: {
    missionId: string;
    attemptId: string;
    leaseEpoch: number;
    stepId: string;
    action: string;
    argsDigest: string;
    effectKey: string;
  }): EffectPermit {
    return this.withTransaction(() => {
      const now = this.now();
      const expectedKey = sha256(
        input.missionId + ':' + input.stepId + ':' + input.action + ':' + input.argsDigest
      );
      if (input.effectKey !== expectedKey) {
        throw new ContinuityError(
          'INVALID_EFFECT_KEY',
          `Effect key mismatch: provided '${input.effectKey}', expected '${expectedKey}'`
        );
      }

      const mission = this.getMission(input.missionId);
      if (!mission) {
        throw new ContinuityError(
          'MISSION_NOT_FOUND',
          `Mission '${input.missionId}' not found for effect authorization`
        );
      }

      if (input.leaseEpoch !== mission.leaseEpoch) {
        throw new ContinuityError(
          'STALE_FENCE',
          `Stale lease epoch on authorizeEffect: presented ${input.leaseEpoch}, active ${mission.leaseEpoch}`
        );
      }
      if (input.attemptId !== mission.attemptId) {
        throw new ContinuityError(
          'STALE_FENCE',
          `Stale attempt on authorizeEffect: presented '${input.attemptId}', active '${mission.attemptId}'`
        );
      }
      if (mission.leaseExpiresAtMs < now) {
        throw new ContinuityError('STALE_FENCE', 'Lease has expired for effect authorization');
      }

      // Checkpoint rule: The current attempt must write a checkpoint under the current attempt and epoch
      // before any irreversible effect. Otherwise authorizeEffect fails CHECKPOINT_REQUIRED.
      const currentEpochCheckpoint = this.db
        .prepare(`
          SELECT sequence FROM continuity_checkpoints
          WHERE mission_id = ? AND attempt_id = ? AND lease_epoch = ?
          LIMIT 1
        `)
        .get(input.missionId, input.attemptId, input.leaseEpoch);

      if (!currentEpochCheckpoint) {
        throw new ContinuityError(
          'CHECKPOINT_REQUIRED',
          'A checkpoint must be written under the current attempt and epoch before authorizing an effect'
        );
      }

      // Check if effect is already authorized or completed
      const existingEffect = this.db
        .prepare('SELECT * FROM continuity_effects WHERE effect_key = ?')
        .get(input.effectKey) as EffectRow | undefined;

      if (existingEffect) {
        const rowData = {
          effectKey: existingEffect.effect_key,
          missionId: existingEffect.mission_id,
          attemptId: existingEffect.attempt_id,
          leaseEpoch: existingEffect.lease_epoch,
          stepId: existingEffect.step_id,
          action: existingEffect.action,
          argsDigest: existingEffect.args_digest,
          token: existingEffect.token,
          expiresAtMs: existingEffect.expires_at_ms,
          status: existingEffect.status,
          receiptJson: existingEffect.receipt_json,
          completedAtMs: existingEffect.completed_at_ms,
        };
        this.verifyRowIntegrity(rowData, existingEffect.row_digest, existingEffect.row_hmac);

        return {
          missionId: existingEffect.mission_id,
          attemptId: existingEffect.attempt_id,
          leaseEpoch: existingEffect.lease_epoch,
          effectKey: existingEffect.effect_key,
          token: existingEffect.token,
          expiresAtMs: existingEffect.expires_at_ms,
        };
      }

      const token = 'permit_' + sha256(this.receiptKey + ':' + input.effectKey + ':' + now);
      const expiresAtMs = Math.min(mission.leaseExpiresAtMs, now + 30_000);

      const effectData = {
        effectKey: input.effectKey,
        missionId: input.missionId,
        attemptId: input.attemptId,
        leaseEpoch: input.leaseEpoch,
        stepId: input.stepId,
        action: input.action,
        argsDigest: input.argsDigest,
        token,
        expiresAtMs,
        status: 'AUTHORIZED',
        receiptJson: null,
        completedAtMs: null,
      };
      const effectHMAC = this.computeRowHMAC(effectData);

      this.db
        .prepare(`
          INSERT INTO continuity_effects (
            effect_key, mission_id, attempt_id, lease_epoch,
            step_id, action, args_digest, token, expires_at_ms,
            status, receipt_json, completed_at_ms, row_digest, row_hmac
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)
        .run(
          input.effectKey,
          input.missionId,
          input.attemptId,
          input.leaseEpoch,
          input.stepId,
          input.action,
          input.argsDigest,
          token,
          expiresAtMs,
          'AUTHORIZED',
          null,
          null,
          effectHMAC.digest,
          effectHMAC.hmac
        );

      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'EFFECT_AUTHORIZED', {
        effectKey: input.effectKey,
        stepId: input.stepId,
        action: input.action,
      });

      return {
        missionId: input.missionId,
        attemptId: input.attemptId,
        leaseEpoch: input.leaseEpoch,
        effectKey: input.effectKey,
        token,
        expiresAtMs,
      };
    });
  }

  completeEffect(input: {
    permit: EffectPermit;
    receipt: Record<string, unknown>;
  }): EffectCompletion {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.permit.missionId);

      if (!mission) {
        throw new ContinuityError('MISSION_NOT_FOUND', 'Mission not found on effect completion');
      }

      if (input.permit.leaseEpoch !== mission.leaseEpoch) {
        throw new ContinuityError('STALE_FENCE', 'Stale lease epoch on completeEffect');
      }
      if (input.permit.attemptId !== mission.attemptId) {
        throw new ContinuityError('STALE_FENCE', 'Stale attempt on completeEffect');
      }

      const effectRow = this.db
        .prepare('SELECT * FROM continuity_effects WHERE effect_key = ?')
        .get(input.permit.effectKey) as EffectRow | undefined;

      if (!effectRow) {
        throw new ContinuityError('INVALID_INPUT', 'Effect permit not found in database');
      }

      const rowData = {
        effectKey: effectRow.effect_key,
        missionId: effectRow.mission_id,
        attemptId: effectRow.attempt_id,
        leaseEpoch: effectRow.lease_epoch,
        stepId: effectRow.step_id,
        action: effectRow.action,
        argsDigest: effectRow.args_digest,
        token: effectRow.token,
        expiresAtMs: effectRow.expires_at_ms,
        status: effectRow.status,
        receiptJson: effectRow.receipt_json,
        completedAtMs: effectRow.completed_at_ms,
      };
      this.verifyRowIntegrity(rowData, effectRow.row_digest, effectRow.row_hmac);

      if (effectRow.token !== input.permit.token) {
        throw new ContinuityError('INVALID_INPUT', 'Permit token mismatch');
      }

      // Idempotency: duplicate effect completion returns the existing receipt
      if (effectRow.status === 'COMPLETED') {
        return {
          effectKey: input.permit.effectKey,
          duplicate: true,
          receipt: JSON.parse(effectRow.receipt_json!),
          completedAtMs: effectRow.completed_at_ms!,
        };
      }

      const receiptJson = canonicalJson(input.receipt);
      const updatedEffectData = {
        ...rowData,
        status: 'COMPLETED',
        receiptJson,
        completedAtMs: now,
      };
      const updatedEffectHMAC = this.computeRowHMAC(updatedEffectData);

      this.db
        .prepare(`
          UPDATE continuity_effects
          SET status = 'COMPLETED', receipt_json = ?, completed_at_ms = ?,
              row_digest = ?, row_hmac = ?
          WHERE effect_key = ?
        `)
        .run(
          receiptJson,
          now,
          updatedEffectHMAC.digest,
          updatedEffectHMAC.hmac,
          input.permit.effectKey
        );

      this.appendEvent(
        input.permit.missionId,
        input.permit.attemptId,
        input.permit.leaseEpoch,
        'EFFECT_COMPLETED',
        { effectKey: input.permit.effectKey }
      );

      return {
        effectKey: input.permit.effectKey,
        duplicate: false,
        receipt: input.receipt,
        completedAtMs: now,
      };
    });
  }

  finishMission(input: {
    missionId: string;
    attemptId: string;
    leaseEpoch: number;
    phase: 'VERIFYING' | 'OPERATING' | 'REPAIRING' | 'BLOCKED';
    evidenceRef: string;
  }): MissionRecord {
    return this.withTransaction(() => {
      const now = this.now();
      const mission = this.getMission(input.missionId);

      if (!mission) {
        throw new ContinuityError('MISSION_NOT_FOUND', 'Mission not found on finish');
      }

      if (input.leaseEpoch !== mission.leaseEpoch) {
        throw new ContinuityError('STALE_FENCE', 'Stale lease epoch on finishMission');
      }
      if (input.attemptId !== mission.attemptId) {
        throw new ContinuityError('STALE_FENCE', 'Stale attempt on finishMission');
      }

      if (!isValidTransition(mission.phase, input.phase)) {
        throw new ContinuityError(
          'INVALID_TRANSITION',
          `Cannot transition mission from '${mission.phase}' to '${input.phase}'`
        );
      }

      const updatedMissionData = {
        missionId: mission.missionId,
        kind: mission.kind,
        riskClass: mission.riskClass,
        goal: mission.goal,
        phase: input.phase,
        attemptId: mission.attemptId,
        workerId: mission.workerId,
        leaseEpoch: mission.leaseEpoch,
        leaseExpiresAtMs: mission.leaseExpiresAtMs,
        requiredCapabilitiesJson: canonicalJson(mission.requiredCapabilities),
        costBudgetRemaining: mission.costBudgetRemaining,
        recoveryPending: mission.recoveryPending ? 1 : 0,
        failureClass: mission.failureClass,
        evidenceRef: input.evidenceRef,
        checkpointSequence: mission.checkpointSequence,
        checkpointDigest: mission.checkpointDigest,
        createdAtMs: mission.createdAtMs,
        updatedAtMs: now,
      };
      const updatedMissionHMAC = this.computeRowHMAC(updatedMissionData);

      this.db
        .prepare(`
          UPDATE continuity_missions
          SET phase = ?, evidence_ref = ?, updated_at_ms = ?, row_digest = ?, row_hmac = ?
          WHERE mission_id = ?
        `)
        .run(input.phase, input.evidenceRef, now, updatedMissionHMAC.digest, updatedMissionHMAC.hmac, input.missionId);

      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'PHASE_TRANSITION', {
        from: mission.phase,
        to: input.phase,
      });
      this.appendEvent(input.missionId, input.attemptId, input.leaseEpoch, 'MISSION_FINISHED', {
        phase: input.phase,
        evidenceRef: input.evidenceRef,
      });

      return {
        ...mission,
        phase: input.phase,
        evidenceRef: input.evidenceRef,
        updatedAtMs: now,
      };
    });
  }

  private getLatestCheckpoint(missionId: string): MissionCheckpointRecord {
    const row = this.db
      .prepare(`
        SELECT * FROM continuity_checkpoints
        WHERE mission_id = ?
        ORDER BY sequence DESC LIMIT 1
      `)
      .get(missionId) as CheckpointRow | undefined;

    if (!row) {
      throw new ContinuityError('INTEGRITY_ERROR', `No checkpoint found for mission '${missionId}'`);
    }

    return this.mapCheckpointRow(row);
  }

  snapshot(): ContinuitySnapshot {
    // 1. Load and verify all missions
    const missionRows = this.db
      .prepare('SELECT * FROM continuity_missions ORDER BY mission_id ASC')
      .all() as unknown as MissionRow[];

    const missions: MissionRecord[] = [];
    const latestCheckpointByMission: Record<string, MissionCheckpointRecord> = {};

    for (const mRow of missionRows) {
      const mission = this.mapMissionRow(mRow);
      missions.push(mission);
      latestCheckpointByMission[mission.missionId] = this.getLatestCheckpoint(mission.missionId);
    }

    // 2. Load and verify append-only event hash chain
    const eventRows = this.db
      .prepare('SELECT * FROM continuity_events ORDER BY event_id ASC')
      .all() as unknown as EventRow[];

    let expectedPrevHash = '0'.repeat(64);
    const events: ContinuitySnapshot['events'] = [];

    for (const eRow of eventRows) {
      const eventData = {
        missionId: eRow.mission_id,
        attemptId: eRow.attempt_id,
        leaseEpoch: eRow.lease_epoch,
        eventType: eRow.event_type,
        payloadJson: eRow.payload_json,
        createdAtMs: eRow.created_at_ms,
        prevEventHash: eRow.prev_event_hash,
        eventHash: eRow.event_hash,
      };
      this.verifyRowIntegrity(eventData, eRow.row_digest, eRow.row_hmac);

      // Verify hash chain
      if (eRow.prev_event_hash !== expectedPrevHash) {
        throw new ContinuityError(
          'INTEGRITY_ERROR',
          `Event hash chain broken at event_id ${eRow.event_id}: previous hash mismatch`
        );
      }

      const computedEventHash = sha256(
        expectedPrevHash +
          ':' +
          eRow.mission_id +
          ':' +
          eRow.attempt_id +
          ':' +
          eRow.lease_epoch +
          ':' +
          eRow.event_type +
          ':' +
          eRow.payload_json +
          ':' +
          eRow.created_at_ms
      );

      if (computedEventHash !== eRow.event_hash) {
        throw new ContinuityError(
          'INTEGRITY_ERROR',
          `Event hash tampered at event_id ${eRow.event_id}`
        );
      }

      expectedPrevHash = eRow.event_hash;

      events.push({
        eventId: eRow.event_id,
        missionId: eRow.mission_id,
        eventType: eRow.event_type,
        eventHash: eRow.event_hash,
        createdAtMs: eRow.created_at_ms,
      });
    }

    return {
      missions,
      latestCheckpointByMission,
      events,
    };
  }

  close(): void {
    this.db.close();
  }
}
