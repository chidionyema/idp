/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GEMINI — P0 Universal Agent Collaboration Recovery
 * Phase 4: Temporal Continuity & Fenced Ownership Engine
 * 600-second stall recovery, idempotent deduplication, checkpoint provenance
 */

import { 
  MissionCustodyRecord, 
  AuthorityLeaseRef, 
  CheckpointPayload,
  UniversalAgentEnvelope 
} from './types';
import { computeSha256 } from './envelope';

export interface TemporalCustodyState {
  missions: Map<string, MissionCustodyRecord>;
  idempotencyHistory: Map<string, { resultDigest: string; timestamp: string }>;
  checkpoints: Map<string, CheckpointPayload[]>;
  fencedLeases: Map<string, AuthorityLeaseRef>;
}

export class TemporalContinuityEngine {
  private missions: Map<string, MissionCustodyRecord> = new Map();
  private idempotencyHistory: Map<string, { resultDigest: string; timestamp: string }> = new Map();
  private checkpoints: Map<string, CheckpointPayload[]> = new Map();
  private fencedLeases: Map<string, AuthorityLeaseRef> = new Map();
  private readonly STALL_TIMEOUT_SECONDS: number = 600; // 600-second policy

  constructor() {
    this.seedInitialMissions();
  }

  private seedInitialMissions() {
    const now = Date.now();
    // Active healthy mission
    this.createMission({
      missionId: 'MSN-COLLAB-2026-001',
      instructionId: 'INST-GEMINI-REUSE-01',
      title: 'Execute Cross-Provider Zero-Downtime Migration',
      ownerAgent: 'gemini-executive-lead',
      executorAgent: 'gemini-executive-lead',
      leaseDurationSeconds: 1200
    });

    // Stalled mission to demonstrate autonomous 600s recovery
    const stalledMissionId = 'MSN-COLLAB-2026-002';
    const stalledStarted = new Date(now - 640 * 1000).toISOString();
    const stalledLease: AuthorityLeaseRef = {
      lease_id: 'LEASE-7771-002',
      fenced_token: 1,
      owner: 'deepseek-reasoner-agent-02',
      acquired_at: stalledStarted,
      expires_at: new Date(now - 40 * 1000).toISOString(),
      heartbeat_interval_seconds: 60
    };

    this.fencedLeases.set(stalledMissionId, stalledLease);
    this.missions.set(stalledMissionId, {
      mission_id: stalledMissionId,
      instruction_id: 'INST-DEEPSEEK-REASON-02',
      title: 'Analyze Vector Sharding Distributed Latency',
      owner_agent: 'deepseek-reasoner-agent-02',
      current_executor: 'deepseek-reasoner-agent-02',
      status: 'IN_EXECUTION',
      fenced_token: 1,
      started_at: stalledStarted,
      updated_at: stalledStarted,
      elapsed_seconds: 640,
      recovery_trigger_seconds: 600
    });
  }

  public createMission(options: {
    missionId: string;
    instructionId: string;
    title: string;
    ownerAgent: string;
    executorAgent: string;
    leaseDurationSeconds?: number;
  }): { mission: MissionCustodyRecord; lease: AuthorityLeaseRef } {
    const duration = options.leaseDurationSeconds || 900;
    const now = new Date();
    const expiresAt = new Date(now.getTime() + duration * 1000).toISOString();

    const lease: AuthorityLeaseRef = {
      lease_id: `LEASE-7771-${options.missionId}`,
      fenced_token: 1,
      owner: options.executorAgent,
      acquired_at: now.toISOString(),
      expires_at: expiresAt,
      heartbeat_interval_seconds: 60
    };

    const mission: MissionCustodyRecord = {
      mission_id: options.missionId,
      instruction_id: options.instructionId,
      title: options.title,
      owner_agent: options.ownerAgent,
      current_executor: options.executorAgent,
      status: 'IN_EXECUTION',
      fenced_token: 1,
      started_at: now.toISOString(),
      updated_at: now.toISOString(),
      elapsed_seconds: 0,
      recovery_trigger_seconds: this.STALL_TIMEOUT_SECONDS
    };

    this.fencedLeases.set(options.missionId, lease);
    this.missions.set(options.missionId, mission);
    return { mission, lease };
  }

  /**
   * Idempotency Guard: Verifies that duplicate deliveries cannot cause duplicate privileged effects
   */
  public checkAndRecordIdempotency(key: string, payload: any): { isDuplicate: boolean; previousDigest?: string } {
    const existing = this.idempotencyHistory.get(key);
    if (existing) {
      return { isDuplicate: true, previousDigest: existing.resultDigest };
    }

    const digest = computeSha256(JSON.stringify(payload));
    this.idempotencyHistory.set(key, { resultDigest: digest, timestamp: new Date().toISOString() });
    return { isDuplicate: false, previousDigest: undefined };
  }

  /**
   * Checkpoint Provenance: Stores state checkpoints with parent hash links
   */
  public recordCheckpoint(missionId: string, checkpoint: CheckpointPayload): { success: boolean; hash: string } {
    const list = this.checkpoints.get(missionId) || [];
    const parentHash = list.length > 0 ? list[list.length - 1].checkpoint_id : 'genesis';
    const hash = computeSha256(`${missionId}:${checkpoint.stage}:${parentHash}`);

    const enrichedCheckpoint: CheckpointPayload = {
      ...checkpoint,
      checkpoint_id: hash,
      provenance_chain: [...checkpoint.provenance_chain, parentHash]
    };

    list.push(enrichedCheckpoint);
    this.checkpoints.set(missionId, list);

    const mission = this.missions.get(missionId);
    if (mission) {
      mission.last_checkpoint = hash;
      mission.updated_at = new Date().toISOString();
    }

    return { success: true, hash };
  }

  /**
   * Autonomous 600-Second Recovery Mechanism
   * Checks for stalled missions where elapsed time >= 600s and lease is expired or heartbeat lost
   */
  public evaluateAndRecoverStalledMissions(recoveryExecutor: string = 'gemini-executive-lead'): MissionCustodyRecord[] {
    const recovered: MissionCustodyRecord[] = [];
    const now = Date.now();

    for (const [missionId, mission] of this.missions.entries()) {
      if (mission.status === 'COMPLETED' || mission.status === 'FAILED') continue;

      const lease = this.fencedLeases.get(missionId);
      const isExpired = lease ? new Date(lease.expires_at).getTime() < now : true;
      const isStalled = mission.elapsed_seconds >= this.STALL_TIMEOUT_SECONDS;

      if (isStalled || isExpired) {
        // Increment fenced token monotonically to invalidate any late messages from dead agent
        const nextFencedToken = (lease ? lease.fenced_token : mission.fenced_token) + 1;
        
        const newLease: AuthorityLeaseRef = {
          lease_id: `LEASE-TAKEOVER-${missionId}-F${nextFencedToken}`,
          fenced_token: nextFencedToken,
          owner: recoveryExecutor,
          acquired_at: new Date().toISOString(),
          expires_at: new Date(now + 900 * 1000).toISOString(),
          heartbeat_interval_seconds: 60
        };

        this.fencedLeases.set(missionId, newLease);

        mission.current_executor = recoveryExecutor;
        mission.status = 'STALLED_RECOVERED';
        mission.fenced_token = nextFencedToken;
        mission.updated_at = new Date().toISOString();

        recovered.push(mission);
      }
    }

    return recovered;
  }

  /**
   * Fenced Lease Guard: Rejects any action if the message's fenced token is stale
   */
  public validateFencedLease(missionId: string, messageFencedToken: number): { valid: boolean; currentFencedToken: number; error?: string } {
    const lease = this.fencedLeases.get(missionId);
    if (!lease) {
      return { valid: false, currentFencedToken: 0, error: `No active lease found for mission ${missionId}` };
    }

    if (messageFencedToken < lease.fenced_token) {
      return { 
        valid: false, 
        currentFencedToken: lease.fenced_token, 
        error: `STALE_FENCED_TOKEN: Message token (${messageFencedToken}) is superseded by current fence token (${lease.fenced_token}). Lease takeover has occurred.` 
      };
    }

    return { valid: true, currentFencedToken: lease.fenced_token };
  }

  public getMission(missionId: string): MissionCustodyRecord | undefined {
    return this.missions.get(missionId);
  }

  public getAllMissions(): MissionCustodyRecord[] {
    return Array.from(this.missions.values());
  }

  public getCheckpoints(missionId: string): CheckpointPayload[] {
    return this.checkpoints.get(missionId) || [];
  }
}
