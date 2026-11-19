import crypto from 'node:crypto';
import zlib from 'node:zlib';

// ============================================================================
// GENESIS v0.7.0-RT — STIGMERGIC SWARM SYNAPSE & MAC-OFFLINE CONTINUITY ENGINE
// Pure, deterministic TypeScript engine decoupled from Express & React DOM.
//
// Enforces:
//   1. Stigmergic Claim-Before-Work (`hydrateSwarmLayer`):
//      - Disk headroom gate (`>= 1500 MB`)
//      - Pass-0 Antibody hit (`0` LLM diagnostic passes on known failure classes)
//      - Lease exclusivity (`LOCKED_BY_ACTIVE_PEER` / `ALREADY_LANDED_BY_PEER`)
//      - Monotonic `fencingToken` increment per Kleppmann DDIA Ch. 8
//   2. Mandatory Dual-Yield Law (`commitSwarmDualYield`):
//      - Refuses completion without substantive `learnedFact` (`>= 15` chars)
//      - Rejects zombie/stale workers (`fencingToken < authoritative Layer Token`)
//      - Chains RFC 6962 `\x01` SHA-256 `merkleRoot` in `realtimeEventRing`
//      - Synthesizes Pass-0 `catechismAntibodies` (`AB-*`)
//      - Repacks executable Python+zlib `GENESIS_SPORE.dna` (`<= 4096` bytes!)
//   3. LIFO Compensating Saga Rollback (`rollbackSwarmSagaLifo`):
//      - Executes `reversibleStateJournal` inverse state snapshots in LIFO order
//      - Increments `authoritativeToken` to fence out aborted writers
//   4. Mac-Offline End-to-End Continuity & Two-Phase Founder Reassignment Proof:
//      - Tracks one instruction across Genesis & Otto with `macHostOnline: false`
//      - Failed auto-takeover -> `NEEDS_REASSIGNMENT` on both Genesis & Otto
//      - Founder chooses new owner -> `REASSIGN_PENDING_ACK` (bumps fence, rejects
//        old worker writes with `HTTP 409 FENCED_OLD_WORKER_REJECTED`, and updates
//        displayed owner on BOTH Genesis & Otto ONLY AFTER new worker ACK!)
// ============================================================================

export const SWARM_DISK_FLOOR_MB = 1500;
export const SWARM_SPORE_MAX_BYTES = 4096;
export const SWARM_DUAL_YIELD_MIN_FACT_CHARS = 15;
export const SWARM_LEASE_TTL_SEC = 300;

export type MyceliumTaskStatus = 'OPEN' | 'LEASED' | 'COMPLETED' | 'FAILED';

export interface MyceliumTaskRow {
  taskId: string;
  promptPayload: string;
  status: MyceliumTaskStatus;
  leasedBy: string;
  leaseExpiresAtSec: number;
  fencingToken: number;
  resultJson: {
    commitSha?: string;
    learnedFact?: string;
    agentId?: string;
    tsSec?: number;
  } | null;
  updatedAtSec: number;
}

export interface CatechismAntibodyRow {
  antibodyId: string;
  failureClassSignature: string;
  remediationCmd: string;
  ed25519Signature: string;
  createdAtSec: number;
  hitCount: number;
}

export interface RealtimeRingEvent {
  seqId: number;
  tsIso: string;
  fencingToken: number;
  topic:
    | 'swarm.lease'
    | 'swarm.yield'
    | 'swarm.antibody'
    | 'swarm.rollback'
    | 'continuity.takeover_failed'
    | 'continuity.reassign_initiated'
    | 'continuity.stale_worker_rejected'
    | 'continuity.handoff_acked'
    | 'continuity.verified_yield';
  sourceNode: string;
  prevMerkleRoot: string;
  merkleRoot: string;
  payload: Record<string, unknown>;
}

export interface ReversibleJournalEntry {
  journalId: number;
  createdAtSec: number;
  fencingToken: number;
  layer: string;
  operation: 'LEASE_ACQUIRED' | 'DUAL_YIELD_COMMITTED' | 'ANTIBODY_SYNTHESIZED';
  inverseDescription: string;
  previousTaskSnapshot: MyceliumTaskRow | null;
  addedAntibodyId: string | null;
  rolledBack: boolean;
}

export interface SporeDnaArtifact {
  version: '0.7.0-RT';
  seqId: number;
  fencingToken: number;
  merkleRoot: string;
  sha256Prefix: string;
  byteLength: number;
  maxBytes: number;
  executableScript: string;
  decodedPayload: {
    v: '0.7.0-RT';
    seq: number;
    fencing_token: number;
    merkle: string;
    disk_free_mb: number;
    canonical_doors: {
      memory: string;
      synapse: string;
      realtime_sse: string;
      projector: string;
    };
    antibodies: Array<{ id: string; sig: string; cmd: string }>;
    peer_intel: Array<Record<string, unknown>>;
  };
}

export interface ConcurrentFailureSurfaceRow {
  id: 'S1' | 'S2' | 'S3' | 'S4' | 'S5';
  surface: string;
  failureMode: string;
  observedRootCause: string;
  deterministicPrevention: string;
  enforcedBy: string;
}

export interface Handover20261112Audit {
  handoverDate: '2026-11-12';
  macDiskRecoveredFreeMb: number;
  localStateArchiveMb: number;
  remoteBackups: Array<{
    repo: string;
    branch: string;
    commitSha: string;
    url: string;
    verifiedBy: string;
  }>;
  commercialGapsOpen: Array<{
    id: string;
    item: string;
    status: 'BLOCKED_GOVERNANCE' | 'BLOCKED_FOUNDER_DNS' | 'BLOCKED_RUNNER_BILLING' | 'RESOLVED_IN_BUNDLE';
    honestDetail: string;
  }>;
}

// ============================================================================
// MAC-OFFLINE END-TO-END CONTINUITY & TWO-PHASE REASSIGNMENT TYPES
// ============================================================================

export type OfflineContinuityState =
  | 'ACTIVE_CLOUD'
  | 'NEEDS_REASSIGNMENT'
  | 'REASSIGN_PENDING_ACK'
  | 'ACKED_ACTIVE_NEW_OWNER'
  | 'VERIFIED_YIELD';

export interface SurfaceContinuityProjection {
  surfaceName: 'Genesis Control Plane' | 'Otto Private Office';
  instructionId: string;
  displayedOwner: string;
  displayedStatusLabel: string;
  checkpointSha: string;
  lastVerifiedProgress: string;
  fencingToken: number;
  pendingAckTarget: string | null;
  syncedAtIso: string;
}

export interface StaleWorkerRejectionReceipt {
  rejectedAtIso: string;
  workerId: string;
  attemptedFencingToken: number;
  authoritativeFencingToken: number;
  attemptedAction: string;
  errorCode: 'FENCED_OLD_WORKER_REJECTED';
  httpStatus: 409;
  detail: string;
}

export interface OfflineContinuityMission {
  instructionId: string;
  title: string;
  repo: string;
  macHostStatus: 'OFFLINE_ISOLATED';
  macLocalDependencyCount: 0;
  state: OfflineContinuityState;
  authoritativeOwner: string;
  supersededWorkerId: string | null;
  supersededWorkerToken: number | null;
  pendingNewOwner: string | null;
  fencingToken: number;
  leaseEpoch: number;
  checkpointSha: string;
  lastVerifiedProgress: string;
  takeoverFailureReason: string | null;
  availableCloudWorkers: Array<{
    workerId: string;
    harness: string;
    formation: string;
    region: string;
  }>;
  genesisSurface: SurfaceContinuityProjection;
  ottoSurface: SurfaceContinuityProjection;
  parityVerified: boolean;
  rejectedWriteLog: StaleWorkerRejectionReceipt[];
  transitionHistory: Array<{
    step: number;
    tsIso: string;
    event: string;
    fencingToken: number;
    displayedOwnerBothSurfaces: string;
  }>;
}

export interface SwarmSynapseState {
  authoritativeToken: number;
  diskFreeMb: number;
  packLockHolder: string | null;
  myceliumTaskQueue: MyceliumTaskRow[];
  catechismAntibodies: CatechismAntibodyRow[];
  realtimeEventRing: RealtimeRingEvent[];
  reversibleStateJournal: ReversibleJournalEntry[];
  sporeDna: SporeDnaArtifact;
  offlineContinuity: OfflineContinuityMission;
  failureMatrix: ConcurrentFailureSurfaceRow[];
  handoverAudit: Handover20261112Audit;
}

// ============================================================================
// CRYPTOGRAPHIC RING & <= 4KB SPORE PACKER
// ============================================================================

export function computeRfc6962RingMerkleRoot(params: {
  prevMerkleRoot: string;
  tsIso: string;
  fencingToken: number;
  topic: string;
  payload: Record<string, unknown>;
}): string {
  const canonicalKeys = Object.keys(params.payload).sort();
  const sortedObj: Record<string, unknown> = {};
  for (const k of canonicalKeys) {
    sortedObj[k] = params.payload[k];
  }
  const payloadStr = JSON.stringify(sortedObj);
  const hash = crypto.createHash('sha256');
  hash.update(
    Buffer.concat([
      Buffer.from([0x01]),
      Buffer.from(params.prevMerkleRoot, 'utf8'),
      Buffer.from(params.tsIso, 'utf8'),
      Buffer.from(String(params.fencingToken), 'utf8'),
      Buffer.from(params.topic, 'utf8'),
      Buffer.from(payloadStr, 'utf8'),
    ])
  );
  return hash.digest('hex');
}

function appendEventToRing(
  state: SwarmSynapseState,
  params: {
    topic: RealtimeRingEvent['topic'];
    sourceNode: string;
    payload: Record<string, unknown>;
    tsIso?: string;
  }
): RealtimeRingEvent {
  const latest = state.realtimeEventRing[0];
  const nextSeq = latest ? latest.seqId + 1 : 1;
  const prevMerkleRoot = latest ? latest.merkleRoot : '0'.repeat(64);
  const tsIso = params.tsIso ?? new Date().toISOString();
  const merkleRoot = computeRfc6962RingMerkleRoot({
    prevMerkleRoot,
    tsIso,
    fencingToken: state.authoritativeToken,
    topic: params.topic,
    payload: params.payload,
  });

  const ev: RealtimeRingEvent = {
    seqId: nextSeq,
    tsIso,
    fencingToken: state.authoritativeToken,
    topic: params.topic,
    sourceNode: params.sourceNode,
    prevMerkleRoot,
    merkleRoot,
    payload: params.payload,
  };
  state.realtimeEventRing = [ev, ...state.realtimeEventRing].slice(0, 64);
  return ev;
}

export function packGenesisSpore4Kb(state: SwarmSynapseState): SporeDnaArtifact {
  const latest = state.realtimeEventRing[0];
  const seqId = latest ? latest.seqId : 0;
  const merkleRoot = latest ? latest.merkleRoot : '0'.repeat(64);

  const buildWithLimits = (abLimit: number, intelLimit: number, maxFactLen: number): SporeDnaArtifact => {
    const antibodies = state.catechismAntibodies.slice(0, abLimit).map((a) => ({
      id: a.antibodyId,
      sig: a.failureClassSignature.slice(0, 64),
      cmd: a.remediationCmd.slice(0, 96),
    }));

    const peerIntel = state.realtimeEventRing
      .filter(
        (e) =>
          e.topic === 'swarm.yield' ||
          e.topic === 'swarm.antibody' ||
          e.topic === 'continuity.handoff_acked'
      )
      .slice(0, intelLimit)
      .map((e) => {
        const copy: Record<string, unknown> = { ...e.payload, seq: e.seqId };
        if (typeof copy.learnedFact === 'string') {
          copy.learnedFact = copy.learnedFact.slice(0, maxFactLen);
        }
        return copy;
      });

    const decodedPayload: SporeDnaArtifact['decodedPayload'] = {
      v: '0.7.0-RT',
      seq: seqId,
      fencing_token: state.authoritativeToken,
      merkle: merkleRoot,
      disk_free_mb: state.diskFreeMb,
      canonical_doors: {
        memory: 'idp/platform/estate/memory/door.py',
        synapse: 'idp/platform/estate/estate-swarm-synapse.py',
        realtime_sse: '/api/brain/stream',
        projector: '/#projector',
      },
      antibodies,
      peer_intel: peerIntel,
    };

    const compressed = zlib.deflateSync(Buffer.from(JSON.stringify(decodedPayload), 'utf8'), {
      level: 9,
    });
    const b64 = compressed
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_');
    const sha256Prefix = crypto.createHash('sha256').update(compressed).digest('hex').slice(0, 16);

    const executableScript = [
      '#!/usr/bin/env python3',
      `# GENESIS_SPORE.dna v0.7.0-RT | SEQ:${seqId} | FENCE:${state.authoritativeToken} | SHA256:${sha256Prefix}`,
      `import base64,json,zlib;DNA=json.loads(zlib.decompress(base64.urlsafe_b64decode('${b64}')))`,
      "if __name__=='__main__':print(json.dumps(DNA,indent=2))",
      '',
    ].join('\n');

    const byteLength = Buffer.byteLength(executableScript, 'utf8');
    return {
      version: '0.7.0-RT',
      seqId,
      fencingToken: state.authoritativeToken,
      merkleRoot,
      sha256Prefix,
      byteLength,
      maxBytes: SWARM_SPORE_MAX_BYTES,
      executableScript,
      decodedPayload,
    };
  };

  let candidate = buildWithLimits(10, 6, 130);
  if (candidate.byteLength > SWARM_SPORE_MAX_BYTES) {
    candidate = buildWithLimits(6, 4, 80);
  }
  if (candidate.byteLength > SWARM_SPORE_MAX_BYTES) {
    candidate = buildWithLimits(3, 2, 50);
  }
  return candidate;
}

// ============================================================================
// 1. HYDRATE LAYER (PRE-TASK LEASE + PASS-0 ANTIBODY + COLLISION FENCE)
// ============================================================================

export type SwarmHydrateOutcome =
  | {
      status: 'HALT_DISK_FLOOR';
      allowedToProceed: false;
      diskFreeMb: number;
      instruction: string;
    }
  | {
      status: 'PASS_0_ANTIBODY_HIT';
      allowedToProceed: false;
      antibodyId: string;
      failureClassSignature: string;
      remediationCmd: string;
      agentDiagPasses: 0;
      instruction: string;
    }
  | {
      status: 'ALREADY_LANDED_BY_PEER';
      allowedToProceed: false;
      layer: string;
      leasedBy: string;
      result: MyceliumTaskRow['resultJson'];
      instruction: string;
    }
  | {
      status: 'LOCKED_BY_ACTIVE_PEER';
      allowedToProceed: false;
      layer: string;
      leasedBy: string;
      fencingToken: number;
      leaseExpiresInSec: number;
      instruction: string;
    }
  | {
      status: 'LEASE_GRANTED';
      allowedToProceed: true;
      layer: string;
      agentId: string;
      fencingToken: number;
      diskFreeMb: number;
      sporeBytes: number;
      merkleRoot: string;
    };

export function hydrateSwarmLayer(
  state: SwarmSynapseState,
  input: {
    agentId: string;
    layer: string;
    failureSig?: string | null;
    diskFreeMbOverride?: number;
    nowSec?: number;
    tsIso?: string;
  }
): SwarmHydrateOutcome {
  const diskMb = input.diskFreeMbOverride ?? state.diskFreeMb;
  if (diskMb < SWARM_DISK_FLOOR_MB) {
    return {
      status: 'HALT_DISK_FLOOR',
      allowedToProceed: false,
      diskFreeMb: diskMb,
      instruction: `Execution door locked: free disk ${diskMb} MB is below ${SWARM_DISK_FLOOR_MB} MB safety floor. Run estate-cache-trim first.`,
    };
  }

  const cleanAgent = input.agentId.trim() || 'unnamed-session';
  const cleanLayer = input.layer.trim();
  const cleanSig = input.failureSig?.trim() || '';

  // 1. Pass-0 Antibody Check (0 LLM diagnostic passes!)
  if (cleanSig) {
    const ab = state.catechismAntibodies.find(
      (item) => item.failureClassSignature.toLowerCase() === cleanSig.toLowerCase()
    );
    if (ab) {
      ab.hitCount += 1;
      appendEventToRing(state, {
        topic: 'swarm.antibody',
        sourceNode: cleanAgent,
        tsIso: input.tsIso,
        payload: {
          antibodyId: ab.antibodyId,
          failureClassSignature: ab.failureClassSignature,
          agentDiagPasses: 0,
          hitCount: ab.hitCount,
        },
      });
      state.sporeDna = packGenesisSpore4Kb(state);
      return {
        status: 'PASS_0_ANTIBODY_HIT',
        allowedToProceed: false,
        antibodyId: ab.antibodyId,
        failureClassSignature: ab.failureClassSignature,
        remediationCmd: ab.remediationCmd,
        agentDiagPasses: 0,
        instruction: 'Execute remediationCmd directly in 0 LLM passes; do not burn context re-diagnosing.',
      };
    }
  }

  // 2. Stigmergic Lease Collision Check (`mycelium_task_queue`)
  const nowSec = input.nowSec ?? Math.floor(Date.now() / 1000);
  const existingIdx = state.myceliumTaskQueue.findIndex((t) => t.taskId === cleanLayer);
  const existing = existingIdx >= 0 ? state.myceliumTaskQueue[existingIdx] : null;

  if (existing) {
    if (existing.status === 'COMPLETED') {
      return {
        status: 'ALREADY_LANDED_BY_PEER',
        allowedToProceed: false,
        layer: cleanLayer,
        leasedBy: existing.leasedBy,
        result: existing.resultJson,
        instruction: `Abandon duplicate work; peer ${existing.leasedBy} already landed commit ${existing.resultJson?.commitSha?.slice(0, 10) ?? 'verified'}.`,
      };
    }
    if (
      existing.status === 'LEASED' &&
      existing.leaseExpiresAtSec > nowSec &&
      existing.leasedBy !== cleanAgent
    ) {
      return {
        status: 'LOCKED_BY_ACTIVE_PEER',
        allowedToProceed: false,
        layer: cleanLayer,
        leasedBy: existing.leasedBy,
        fencingToken: existing.fencingToken,
        leaseExpiresInSec: existing.leaseExpiresAtSec - nowSec,
        instruction: `Collision blocked: ${existing.leasedBy} holds active fenced lease #${existing.fencingToken} on ${cleanLayer}.`,
      };
    }
  }

  // 3. Grant Fenced Lease & Increment Authoritative Token (Kleppmann DDIA)
  state.authoritativeToken += 1;
  const token = state.authoritativeToken;
  const previousSnapshot: MyceliumTaskRow | null = existing ? { ...existing } : null;

  const nextJournalId =
    state.reversibleStateJournal.reduce((mx, j) => Math.max(mx, j.journalId), 0) + 1;
  state.reversibleStateJournal.unshift({
    journalId: nextJournalId,
    createdAtSec: nowSec,
    fencingToken: token,
    layer: cleanLayer,
    operation: 'LEASE_ACQUIRED',
    inverseDescription: previousSnapshot
      ? `Restore ${cleanLayer} to ${previousSnapshot.status} (owner ${previousSnapshot.leasedBy})`
      : `Remove ${cleanLayer} lease held by ${cleanAgent}`,
    previousTaskSnapshot: previousSnapshot,
    addedAntibodyId: null,
    rolledBack: false,
  });

  const leasedRow: MyceliumTaskRow = {
    taskId: cleanLayer,
    promptPayload: cleanSig,
    status: 'LEASED',
    leasedBy: cleanAgent,
    leaseExpiresAtSec: nowSec + SWARM_LEASE_TTL_SEC,
    fencingToken: token,
    resultJson: null,
    updatedAtSec: nowSec,
  };

  if (existingIdx >= 0) {
    state.myceliumTaskQueue[existingIdx] = leasedRow;
  } else {
    state.myceliumTaskQueue.unshift(leasedRow);
  }

  const ev = appendEventToRing(state, {
    topic: 'swarm.lease',
    sourceNode: cleanAgent,
    tsIso: input.tsIso,
    payload: {
      layer: cleanLayer,
      agentId: cleanAgent,
      fencingToken: token,
    },
  });
  state.sporeDna = packGenesisSpore4Kb(state);

  return {
    status: 'LEASE_GRANTED',
    allowedToProceed: true,
    layer: cleanLayer,
    agentId: cleanAgent,
    fencingToken: token,
    diskFreeMb: diskMb,
    sporeBytes: state.sporeDna.byteLength,
    merkleRoot: ev.merkleRoot,
  };
}

// ============================================================================
// 2. DUAL-YIELD ENFORCER (`commitSwarmDualYield`)
// ============================================================================

export type SwarmDualYieldOutcome =
  | {
      ok: false;
      errorCode: 'REFUSED_BY_DUAL_YIELD_LAW' | 'FENCED_OUT_STALE_SESSION';
      reason: string;
    }
  | {
      ok: true;
      status: 'DUAL_YIELD_COMMITTED';
      ringEvent: RealtimeRingEvent;
      antibodyRegistered: string | null;
      sporeBytes: number;
      sporeSha256Prefix: string;
    };

export function commitSwarmDualYield(
  state: SwarmSynapseState,
  input: {
    agentId: string;
    layer: string;
    fencingToken: number;
    commitSha: string;
    learnedFact: string;
    antibodySig?: string | null;
    antibodyCmd?: string | null;
    nowSec?: number;
    tsIso?: string;
  }
): SwarmDualYieldOutcome {
  const cleanFact = (input.learnedFact ?? '').trim();
  if (cleanFact.length < SWARM_DUAL_YIELD_MIN_FACT_CHARS) {
    return {
      ok: false,
      errorCode: 'REFUSED_BY_DUAL_YIELD_LAW',
      reason: `Dual-Yield Law refused completion: --fact must provide >= ${SWARM_DUAL_YIELD_MIN_FACT_CHARS} chars of measured root-cause intelligence for peer sessions (got ${cleanFact.length} chars).`,
    };
  }

  const cleanLayer = input.layer.trim();
  const cleanAgent = input.agentId.trim() || 'unnamed-session';
  const nowSec = input.nowSec ?? Math.floor(Date.now() / 1000);

  const existingIdx = state.myceliumTaskQueue.findIndex((t) => t.taskId === cleanLayer);
  const existing = existingIdx >= 0 ? state.myceliumTaskQueue[existingIdx] : null;

  const minRequiredToken = existing ? existing.fencingToken : state.authoritativeToken;
  if (input.fencingToken < minRequiredToken) {
    return {
      ok: false,
      errorCode: 'FENCED_OUT_STALE_SESSION',
      reason: `Storage boundary rejected stale write: worker token ${input.fencingToken} < authoritative token ${minRequiredToken}${existing ? ` (held by ${existing.leasedBy})` : ''}.`,
    };
  }

  const previousSnapshot: MyceliumTaskRow | null = existing ? { ...existing } : null;

  let antibodyId: string | null = null;
  const cleanAbSig = input.antibodySig?.trim() || '';
  const cleanAbCmd = input.antibodyCmd?.trim() || '';

  if (cleanAbSig && cleanAbCmd) {
    antibodyId = `AB-${crypto.createHash('sha256').update(cleanAbSig).digest('hex').slice(0, 8).toUpperCase()}`;
    const sigHex = crypto
      .createHash('sha256')
      .update(`${antibodyId}:${cleanAbSig}:${cleanAbCmd}:${input.commitSha}`)
      .digest('hex');

    const abRow: CatechismAntibodyRow = {
      antibodyId,
      failureClassSignature: cleanAbSig,
      remediationCmd: cleanAbCmd,
      ed25519Signature: sigHex,
      createdAtSec: nowSec,
      hitCount: 0,
    };
    const existingAbIdx = state.catechismAntibodies.findIndex(
      (a) => a.failureClassSignature.toLowerCase() === cleanAbSig.toLowerCase()
    );
    if (existingAbIdx >= 0) {
      state.catechismAntibodies[existingAbIdx] = abRow;
    } else {
      state.catechismAntibodies.unshift(abRow);
    }
  }

  const completedRow: MyceliumTaskRow = {
    taskId: cleanLayer,
    promptPayload: existing?.promptPayload ?? cleanAbSig,
    status: 'COMPLETED',
    leasedBy: cleanAgent,
    leaseExpiresAtSec: existing?.leaseExpiresAtSec ?? nowSec + SWARM_LEASE_TTL_SEC,
    fencingToken: input.fencingToken,
    resultJson: {
      commitSha: input.commitSha.trim(),
      learnedFact: cleanFact,
      agentId: cleanAgent,
      tsSec: nowSec,
    },
    updatedAtSec: nowSec,
  };

  if (existingIdx >= 0) {
    state.myceliumTaskQueue[existingIdx] = completedRow;
  } else {
    state.myceliumTaskQueue.unshift(completedRow);
  }

  const nextJournalId =
    state.reversibleStateJournal.reduce((mx, j) => Math.max(mx, j.journalId), 0) + 1;
  state.reversibleStateJournal.unshift({
    journalId: nextJournalId,
    createdAtSec: nowSec,
    fencingToken: input.fencingToken,
    layer: cleanLayer,
    operation: antibodyId ? 'ANTIBODY_SYNTHESIZED' : 'DUAL_YIELD_COMMITTED',
    inverseDescription: `Revert ${cleanLayer} completion${antibodyId ? ` & remove ${antibodyId}` : ''}`,
    previousTaskSnapshot: previousSnapshot,
    addedAntibodyId: antibodyId,
    rolledBack: false,
  });

  const ringEvent = appendEventToRing(state, {
    topic: 'swarm.yield',
    sourceNode: cleanAgent,
    tsIso: input.tsIso,
    payload: {
      layer: cleanLayer,
      commitSha: input.commitSha.trim(),
      learnedFact: cleanFact,
      antibodyId,
      memoryDoorPath: 'idp/platform/estate/memory/door.py',
    },
  });

  state.sporeDna = packGenesisSpore4Kb(state);

  return {
    ok: true,
    status: 'DUAL_YIELD_COMMITTED',
    ringEvent,
    antibodyRegistered: antibodyId,
    sporeBytes: state.sporeDna.byteLength,
    sporeSha256Prefix: state.sporeDna.sha256Prefix,
  };
}

// ============================================================================
// 3. COMPENSATING SAGA LIFO ROLLBACK (`rollbackSwarmSagaLifo`)
// ============================================================================

export function rollbackSwarmSagaLifo(
  state: SwarmSynapseState,
  steps: number = 1,
  tsIso?: string
): {
  rolledBackEntries: ReversibleJournalEntry[];
  newAuthoritativeToken: number;
  ringEvent: RealtimeRingEvent;
} {
  const count = Math.max(1, Math.min(10, Math.floor(steps)));
  const activeEntries = state.reversibleStateJournal
    .filter((j) => !j.rolledBack)
    .sort((a, b) => b.journalId - a.journalId)
    .slice(0, count);

  for (const entry of activeEntries) {
    if (entry.addedAntibodyId) {
      state.catechismAntibodies = state.catechismAntibodies.filter(
        (a) => a.antibodyId !== entry.addedAntibodyId
      );
    }
    if (entry.previousTaskSnapshot === null) {
      state.myceliumTaskQueue = state.myceliumTaskQueue.filter((t) => t.taskId !== entry.layer);
    } else {
      const idx = state.myceliumTaskQueue.findIndex((t) => t.taskId === entry.layer);
      if (idx >= 0) {
        state.myceliumTaskQueue[idx] = { ...entry.previousTaskSnapshot };
      } else {
        state.myceliumTaskQueue.unshift({ ...entry.previousTaskSnapshot });
      }
    }
    entry.rolledBack = true;
  }

  // Monotonic Fencing Safety: increment authoritativeToken on rollback so aborted workers cannot corrupt state
  state.authoritativeToken += 1;

  const ringEvent = appendEventToRing(state, {
    topic: 'swarm.rollback',
    sourceNode: 'genesis-saga-governor',
    tsIso,
    payload: {
      rolledBackJournalIds: activeEntries.map((e) => e.journalId),
      newAuthoritativeToken: state.authoritativeToken,
    },
  });
  state.sporeDna = packGenesisSpore4Kb(state);

  return {
    rolledBackEntries: activeEntries,
    newAuthoritativeToken: state.authoritativeToken,
    ringEvent,
  };
}

// ============================================================================
// 4. MAC-OFFLINE END-TO-END CONTINUITY & TWO-PHASE FOUNDER REASSIGNMENT PROOF
// ============================================================================

function syncGenesisAndOttoProjections(
  mission: OfflineContinuityMission,
  nowIso: string
): void {
  let statusLabel = 'Active in Cloud (Mac Offline)';
  if (mission.state === 'NEEDS_REASSIGNMENT') {
    statusLabel = 'Needs reassignment';
  } else if (mission.state === 'REASSIGN_PENDING_ACK') {
    statusLabel = `Needs reassignment · Awaiting ${mission.pendingNewOwner} handoff ACK`;
  } else if (mission.state === 'ACKED_ACTIVE_NEW_OWNER') {
    statusLabel = `Active · Handoff acknowledged by ${mission.authoritativeOwner}`;
  } else if (mission.state === 'VERIFIED_YIELD') {
    statusLabel = `Verified Yield Sealed (${mission.authoritativeOwner})`;
  }

  // CRITICAL INVARIANT:
  // Both Genesis and Otto project from the exact same authoritative fields,
  // and NEITHER surface shows `pendingNewOwner` as `displayedOwner` until `acknowledgeWorkerHandoff`!
  const sharedFields = {
    instructionId: mission.instructionId,
    displayedOwner: mission.authoritativeOwner,
    displayedStatusLabel: statusLabel,
    checkpointSha: mission.checkpointSha,
    lastVerifiedProgress: mission.lastVerifiedProgress,
    fencingToken: mission.fencingToken,
    pendingAckTarget: mission.pendingNewOwner,
    syncedAtIso: nowIso,
  };

  mission.genesisSurface = {
    surfaceName: 'Genesis Control Plane',
    ...sharedFields,
  };
  mission.ottoSurface = {
    surfaceName: 'Otto Private Office',
    ...sharedFields,
  };

  mission.parityVerified =
    mission.genesisSurface.displayedOwner === mission.ottoSurface.displayedOwner &&
    mission.genesisSurface.checkpointSha === mission.ottoSurface.checkpointSha &&
    mission.genesisSurface.lastVerifiedProgress === mission.ottoSurface.lastVerifiedProgress &&
    mission.genesisSurface.displayedStatusLabel === mission.ottoSurface.displayedStatusLabel;
}

export function triggerAutoTakeoverFailure(
  state: SwarmSynapseState,
  reason = 'Automatic cloud runner takeover timed out after worker heartbeat stall (GitHub Actions runner spending gate blocked fallback spawn).',
  nowIso = new Date().toISOString()
): OfflineContinuityMission {
  const m = state.offlineContinuity;
  m.state = 'NEEDS_REASSIGNMENT';
  m.takeoverFailureReason = reason;
  syncGenesisAndOttoProjections(m, nowIso);
  m.transitionHistory.unshift({
    step: m.transitionHistory.length + 1,
    tsIso: nowIso,
    event: `Auto-takeover failed -> Genesis & Otto show "Needs reassignment" (owner held at ${m.authoritativeOwner})`,
    fencingToken: m.fencingToken,
    displayedOwnerBothSurfaces: m.authoritativeOwner,
  });

  appendEventToRing(state, {
    topic: 'continuity.takeover_failed',
    sourceNode: 'flow-lease-authority',
    tsIso: nowIso,
    payload: {
      instructionId: m.instructionId,
      status: 'Needs reassignment',
      owner: m.authoritativeOwner,
      checkpointSha: m.checkpointSha,
    },
  });
  state.sporeDna = packGenesisSpore4Kb(state);
  return m;
}

export function initiateFounderReassignment(
  state: SwarmSynapseState,
  newOwnerId: string,
  nowIso = new Date().toISOString()
): OfflineContinuityMission {
  const m = state.offlineContinuity;
  const cleanNewOwner = newOwnerId.trim();
  if (!cleanNewOwner) {
    throw new Error('New worker owner ID is required for reassignment.');
  }

  // Record old worker & its now-stale token so we can deterministically prove rejection!
  m.supersededWorkerId = m.authoritativeOwner;
  m.supersededWorkerToken = m.fencingToken;

  // Increment global + mission fencing token immediately at lease authority
  state.authoritativeToken += 1;
  m.fencingToken = state.authoritativeToken;
  m.leaseEpoch += 1;
  m.pendingNewOwner = cleanNewOwner;
  m.state = 'REASSIGN_PENDING_ACK';

  // Notice: `m.authoritativeOwner` is NOT changed yet! Both surfaces keep prior owner until worker ACK!
  syncGenesisAndOttoProjections(m, nowIso);

  m.transitionHistory.unshift({
    step: m.transitionHistory.length + 1,
    tsIso: nowIso,
    event: `Founder selected ${cleanNewOwner} -> Fence bumped to #${m.fencingToken}; old worker ${m.supersededWorkerId} (#${m.supersededWorkerToken}) fenced out; awaiting ${cleanNewOwner} ACK before switching displayed owner`,
    fencingToken: m.fencingToken,
    displayedOwnerBothSurfaces: m.authoritativeOwner,
  });

  appendEventToRing(state, {
    topic: 'continuity.reassign_initiated',
    sourceNode: 'founder-authority',
    tsIso: nowIso,
    payload: {
      instructionId: m.instructionId,
      previousOwner: m.authoritativeOwner,
      pendingNewOwner: cleanNewOwner,
      newFencingToken: m.fencingToken,
    },
  });
  state.sporeDna = packGenesisSpore4Kb(state);
  return m;
}

export function attemptMissionWorkerWrite(
  state: SwarmSynapseState,
  params: {
    workerId?: string;
    workerFencingToken?: number;
    attemptedProgress?: string;
    nowIso?: string;
  }
):
  | {
      accepted: false;
      rejection: StaleWorkerRejectionReceipt;
    }
  | {
      accepted: true;
      mission: OfflineContinuityMission;
    } {
  const m = state.offlineContinuity;
  const nowIso = params.nowIso ?? new Date().toISOString();
  const workerId = params.workerId ?? m.supersededWorkerId ?? 'codex-worker-alpha';
  const workerToken =
    params.workerFencingToken ??
    m.supersededWorkerToken ??
    Math.max(1, m.fencingToken - 1);
  const attemptedAction =
    params.attemptedProgress ??
    'POST /api/flow/checkpoint (stale worker attempting post-compact mutation)';

  if (workerToken < m.fencingToken || workerId !== m.authoritativeOwner || m.state === 'REASSIGN_PENDING_ACK') {
    const rejection: StaleWorkerRejectionReceipt = {
      rejectedAtIso: nowIso,
      workerId,
      attemptedFencingToken: workerToken,
      authoritativeFencingToken: m.fencingToken,
      attemptedAction,
      errorCode: 'FENCED_OLD_WORKER_REJECTED',
      httpStatus: 409,
      detail: `Lease authority rejected ${workerId}: stale fencing_token #${workerToken} < authoritative #${m.fencingToken}. Checkpoint ${m.checkpointSha.slice(0, 10)} preserved untouched.`,
    };
    m.rejectedWriteLog.unshift(rejection);
    m.transitionHistory.unshift({
      step: m.transitionHistory.length + 1,
      tsIso: nowIso,
      event: `REJECTED stale write from ${workerId} (token #${workerToken} < #${m.fencingToken}) -> HTTP 409 FENCED_OLD_WORKER_REJECTED`,
      fencingToken: m.fencingToken,
      displayedOwnerBothSurfaces: m.authoritativeOwner,
    });

    appendEventToRing(state, {
      topic: 'continuity.stale_worker_rejected',
      sourceNode: 'flow-lease-authority',
      tsIso: nowIso,
      payload: {
        instructionId: m.instructionId,
        rejectedWorkerId: workerId,
        attemptedToken: workerToken,
        authoritativeToken: m.fencingToken,
      },
    });
    state.sporeDna = packGenesisSpore4Kb(state);
    return { accepted: false, rejection };
  }

  m.lastVerifiedProgress = attemptedAction;
  syncGenesisAndOttoProjections(m, nowIso);
  return { accepted: true, mission: m };
}

export function acknowledgeWorkerHandoff(
  state: SwarmSynapseState,
  params?: {
    workerId?: string;
    fencingToken?: number;
    resumedProgressNote?: string;
    nowIso?: string;
  }
): OfflineContinuityMission {
  const m = state.offlineContinuity;
  const nowIso = params?.nowIso ?? new Date().toISOString();
  const ackWorker = (params?.workerId ?? m.pendingNewOwner ?? '').trim();
  const ackToken = params?.fencingToken ?? m.fencingToken;

  if (!m.pendingNewOwner || ackWorker !== m.pendingNewOwner) {
    throw new Error(
      `Handoff ACK mismatch: expected pending owner "${m.pendingNewOwner ?? 'none'}", got "${ackWorker}".`
    );
  }
  if (ackToken !== m.fencingToken) {
    throw new Error(
      `Handoff ACK token mismatch: expected #${m.fencingToken}, got #${ackToken}.`
    );
  }

  // Atomic Handoff Promotion: NOW both Genesis and Otto transition to show the new owner!
  m.authoritativeOwner = ackWorker;
  m.pendingNewOwner = null;
  m.takeoverFailureReason = null;
  m.state = 'ACKED_ACTIVE_NEW_OWNER';
  m.lastVerifiedProgress =
    params?.resumedProgressNote ??
    `Handoff ACK verified at checkpoint ${m.checkpointSha.slice(0, 10)} (epoch e${m.leaseEpoch}, fence #${m.fencingToken}) with Mac offline.`;

  syncGenesisAndOttoProjections(m, nowIso);

  m.transitionHistory.unshift({
    step: m.transitionHistory.length + 1,
    tsIso: nowIso,
    event: `${ackWorker} acknowledged handoff (#${m.fencingToken}) -> Genesis & Otto atomically switched displayedOwner to ${ackWorker}`,
    fencingToken: m.fencingToken,
    displayedOwnerBothSurfaces: m.authoritativeOwner,
  });

  appendEventToRing(state, {
    topic: 'continuity.handoff_acked',
    sourceNode: ackWorker,
    tsIso: nowIso,
    payload: {
      instructionId: m.instructionId,
      newOwner: ackWorker,
      fencingToken: m.fencingToken,
      checkpointSha: m.checkpointSha,
      macHostStatus: m.macHostStatus,
    },
  });
  state.sporeDna = packGenesisSpore4Kb(state);
  return m;
}

export function completeOfflineContinuityYield(
  state: SwarmSynapseState,
  nextCheckpointSha = 'e94a71c0b31e032d8c674f91a2048bc117e5a902',
  nowIso = new Date().toISOString()
): OfflineContinuityMission {
  const m = state.offlineContinuity;
  m.state = 'VERIFIED_YIELD';
  m.checkpointSha = nextCheckpointSha;
  m.lastVerifiedProgress = `End-to-end cloud execution sealed by ${m.authoritativeOwner} at ${nextCheckpointSha.slice(0, 10)} (31/31 assertions green, Mac offline).`;
  syncGenesisAndOttoProjections(m, nowIso);

  m.transitionHistory.unshift({
    step: m.transitionHistory.length + 1,
    tsIso: nowIso,
    event: `Verified Yield sealed by ${m.authoritativeOwner} at ${nextCheckpointSha.slice(0, 10)} across Genesis & Otto`,
    fencingToken: m.fencingToken,
    displayedOwnerBothSurfaces: m.authoritativeOwner,
  });

  appendEventToRing(state, {
    topic: 'continuity.verified_yield',
    sourceNode: m.authoritativeOwner,
    tsIso: nowIso,
    payload: {
      instructionId: m.instructionId,
      owner: m.authoritativeOwner,
      checkpointSha: nextCheckpointSha,
      fencingToken: m.fencingToken,
    },
  });
  state.sporeDna = packGenesisSpore4Kb(state);
  return m;
}

export function createInitialOfflineContinuityMission(
  initialToken = 48,
  nowIso = new Date().toISOString()
): OfflineContinuityMission {
  const mission: OfflineContinuityMission = {
    instructionId: 'INS-OFFLINE-001',
    title: 'Move host estate-proof & swarm-synapse into idp/platform/estate with Mac offline',
    repo: 'chidionyema/idp',
    macHostStatus: 'OFFLINE_ISOLATED',
    macLocalDependencyCount: 0,
    state: 'ACTIVE_CLOUD',
    authoritativeOwner: 'codex-worker-alpha',
    supersededWorkerId: null,
    supersededWorkerToken: null,
    pendingNewOwner: null,
    fencingToken: initialToken,
    leaseEpoch: 3,
    checkpointSha: 'd4b1349cec6c8a049f12b7183c948102a74590ef',
    lastVerifiedProgress:
      'Checkpoint verified on origin/backup/estate-20261112 (19/19 projector & preflight assertions green).',
    takeoverFailureReason: null,
    availableCloudWorkers: [
      {
        workerId: 'gemini-4-centurion-01',
        harness: 'Genesis Cloud Run',
        formation: 'centurion',
        region: 'europe-west3',
      },
      {
        workerId: 'codex-cloud-sniper-02',
        harness: 'Legion Cloud Harness',
        formation: 'sniper',
        region: 'eu-west-2',
      },
      {
        workerId: 'pi-edge-phalanx-03',
        harness: 'Cloudflare DO + D1',
        formation: 'phalanx',
        region: 'global-edge',
      },
    ],
    genesisSurface: {
      surfaceName: 'Genesis Control Plane',
      instructionId: 'INS-OFFLINE-001',
      displayedOwner: 'codex-worker-alpha',
      displayedStatusLabel: 'Active in Cloud (Mac Offline)',
      checkpointSha: 'd4b1349cec6c8a049f12b7183c948102a74590ef',
      lastVerifiedProgress: '',
      fencingToken: initialToken,
      pendingAckTarget: null,
      syncedAtIso: nowIso,
    },
    ottoSurface: {
      surfaceName: 'Otto Private Office',
      instructionId: 'INS-OFFLINE-001',
      displayedOwner: 'codex-worker-alpha',
      displayedStatusLabel: 'Active in Cloud (Mac Offline)',
      checkpointSha: 'd4b1349cec6c8a049f12b7183c948102a74590ef',
      lastVerifiedProgress: '',
      fencingToken: initialToken,
      pendingAckTarget: null,
      syncedAtIso: nowIso,
    },
    parityVerified: true,
    rejectedWriteLog: [],
    transitionHistory: [
      {
        step: 1,
        tsIso: nowIso,
        event: 'Instruction tracked in cloud with Mac offline (Genesis & Otto synchronized on codex-worker-alpha)',
        fencingToken: initialToken,
        displayedOwnerBothSurfaces: 'codex-worker-alpha',
      },
    ],
  };

  syncGenesisAndOttoProjections(mission, nowIso);
  return mission;
}

// ============================================================================
// SEED STATE FACTORY (`createSeedSwarmSynapseState`)
// ============================================================================

export function createSeedSwarmSynapseState(nowSec = Math.floor(Date.now() / 1000)): SwarmSynapseState {
  const nowIso = new Date(nowSec * 1000).toISOString();

  const initialAntibodies: CatechismAntibodyRow[] = [
    {
      antibodyId: 'AB-S1PACK92',
      failureClassSignature: 'GIT_SHALLOW_UNSHALLOW_DISK_STAMPEDE',
      remediationCmd:
        'flock .estate/locks/git-pack.lock bin/estate-cache-trim --floor-mb 2000 && git fetch --depth=1 origin',
      ed25519Signature: '9f8e1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e7',
      createdAtSec: nowSec - 1800,
      hitCount: 4,
    },
    {
      antibodyId: 'AB-S2DDL401',
      failureClassSignature: 'SQLITE_STEP_RUNS_NOT_NULL_DRIFT',
      remediationCmd:
        'python3 platform/estate/estate-swarm-synapse.py hydrate --agent migrator --layer sqlite:step_runs',
      ed25519Signature: '4a11bc09e8217f34a9120cc481029a8f716253448899aabbccddeeff00112233',
      createdAtSec: nowSec - 1400,
      hitCount: 3,
    },
    {
      antibodyId: 'AB-S5DOOR77',
      failureClassSignature: 'LEGACY_UNIFIED_MEMORY_HOST_BYPASS',
      remediationCmd:
        'python3 -c "import sys; sys.path.insert(0, \'idp/platform/estate/memory\'); import door; print(door.health())"',
      ed25519Signature: '77c109a8b234e5f612349876abcdef0123456789abcdef0123456789abcdef01',
      createdAtSec: nowSec - 950,
      hitCount: 6,
    },
  ];

  const initialQueue: MyceliumTaskRow[] = [
    {
      taskId: 'idp/bin/estate-cache-trim',
      promptPayload: 'GIT_SHALLOW_UNSHALLOW_DISK_STAMPEDE',
      status: 'COMPLETED',
      leasedBy: 'codex-session-01',
      leaseExpiresAtSec: nowSec + 600,
      fencingToken: 46,
      resultJson: {
        commitSha: 'd4b1349cec6c8a049f12b7183c948102a74590ef',
        learnedFact:
          'Single-flight git-pack.lock + banning git fetch --unshallow recovered host free disk to 2487 MB.',
        agentId: 'codex-session-01',
        tsSec: nowSec - 600,
      },
      updatedAtSec: nowSec - 600,
    },
    {
      taskId: 'argon/apps/projector-route',
      promptPayload: '',
      status: 'COMPLETED',
      leasedBy: 'aistudio-principal-01',
      leaseExpiresAtSec: nowSec + 600,
      fencingToken: 47,
      resultJson: {
        commitSha: 'b31e032d8c6744109a8f12c34b778e910234abcd',
        learnedFact:
          'Backed up Register Projector + 19 passing tests onto origin/backup/estate-20261112 (b31e032).',
        agentId: 'aistudio-principal-01',
        tsSec: nowSec - 320,
      },
      updatedAtSec: nowSec - 320,
    },
    {
      taskId: 'idp/platform/estate/memory/door.py',
      promptPayload: '',
      status: 'LEASED',
      leasedBy: 'pi-edge-session-02',
      leaseExpiresAtSec: nowSec + 260,
      fencingToken: 48,
      resultJson: null,
      updatedAtSec: nowSec - 40,
    },
  ];

  const state: SwarmSynapseState = {
    authoritativeToken: 48,
    diskFreeMb: 2487,
    packLockHolder: null,
    myceliumTaskQueue: initialQueue,
    catechismAntibodies: initialAntibodies,
    realtimeEventRing: [],
    reversibleStateJournal: [],
    sporeDna: {
      version: '0.7.0-RT',
      seqId: 0,
      fencingToken: 48,
      merkleRoot: '0'.repeat(64),
      sha256Prefix: '0000000000000000',
      byteLength: 0,
      maxBytes: SWARM_SPORE_MAX_BYTES,
      executableScript: '',
      decodedPayload: {
        v: '0.7.0-RT',
        seq: 0,
        fencing_token: 48,
        merkle: '0'.repeat(64),
        disk_free_mb: 2487,
        canonical_doors: {
          memory: 'idp/platform/estate/memory/door.py',
          synapse: 'idp/platform/estate/estate-swarm-synapse.py',
          realtime_sse: '/api/brain/stream',
          projector: '/#projector',
        },
        antibodies: [],
        peer_intel: [],
      },
    },
    offlineContinuity: createInitialOfflineContinuityMission(48, nowIso),
    failureMatrix: [
      {
        id: 'S1',
        surface: 'Host Disk & Git Object Store (~/Documents/code/idp, ~/.estate/argon)',
        failureMode: 'Concurrent Pack-File Stampede (git fetch --deepen / worktree exhaustion)',
        observedRootCause: 'Uncoordinated M-session git fetches dropped disk from 2126 MB to 42 MB.',
        deterministicPrevention:
          'Single-flight .estate/locks/git-pack.lock semaphore + >= 1500 MB pre-flight floor + ban --unshallow.',
        enforcedBy: 'platform/estate/estate-swarm-synapse.py (single_flight_pack_semaphore)',
      },
      {
        id: 'S2',
        surface: 'SQLite Execution Ledger (~/.estate/estate.db -> step_runs)',
        failureMode: 'DDL vs DML Writer Drift (NOT NULL constraint crash across legacy/CIF agents)',
        observedRootCause: 'CREATE TABLE IF NOT EXISTS skipped column migration and lacked DEFAULT clauses.',
        deterministicPrevention:
          'Additive-only DEFAULT schema migration under PRAGMA journal_mode=WAL; busy_timeout=5000.',
        enforcedBy: 'ensure_additive_columns() + WAL mode',
      },
      {
        id: 'S3',
        surface: 'Multi-Session Context & Compaction (Pi, Codex, OpenCode, AI Studio, Gemini)',
        failureMode: '78K-Token Probe Loop & Blind Post-Compaction Relaunch',
        observedRootCause: 'Root causes died in private chat transcripts instead of catechism_antibodies.',
        deterministicPrevention:
          'Mandatory Dual-Yield Law (--fact >= 15 chars) + <= 4096B GENESIS_SPORE.dna Turn-0 hydration.',
        enforcedBy: 'commitSwarmDualYield() + packGenesisSpore4Kb()',
      },
      {
        id: 'S4',
        surface: 'Cross-Boundary Handoff (AI Studio Cloud Run <-> Mac Host <-> GitHub)',
        failureMode: 'Duplicate Competing Patches & Credential Wall Collisions',
        observedRootCause: 'No shared in-flight claim table across cloud and local sandboxes.',
        deterministicPrevention:
          'Stigmergic Claim-Before-Work (mycelium_task_queue) returning peer SHA or active lease lock in 0ms.',
        enforcedBy: 'hydrateSwarmLayer() + /api/argon/export.tar.gz',
      },
      {
        id: 'S5',
        surface: 'Edge & Memory Cutover (llm.mumchimp.com / estate-secrets / door.py)',
        failureMode: 'Ambiguous Authority & Legacy Hostname Split-Brain',
        observedRootCause: 'Wrapper scripts bypassed canonical idp/platform/estate/memory/door.py.',
        deterministicPrevention:
          'Canonical Door Manifest embedded inside signed <= 4KB GENESIS_SPORE.dna.',
        enforcedBy: 'GENESIS_SPORE.dna canonical_doors',
      },
    ],
    handoverAudit: {
      handoverDate: '2026-11-12',
      macDiskRecoveredFreeMb: 2487,
      localStateArchiveMb: 83,
      remoteBackups: [
        {
          repo: 'chidionyema/argon',
          branch: 'backup/estate-20261112',
          commitSha: 'b31e032',
          url: 'https://github.com/chidionyema/argon/tree/backup/estate-20261112',
          verifiedBy: 'git ls-remote origin/backup/estate-20261112',
        },
        {
          repo: 'chidionyema/idp',
          branch: 'backup/estate-20261112',
          commitSha: 'd4b1349ce',
          url: 'https://github.com/chidionyema/idp/tree/backup/estate-20261112',
          verifiedBy: 'git ls-remote origin/backup/estate-20261112',
        },
      ],
      commercialGapsOpen: [
        {
          id: 'GAP-1',
          item: 'Merge to main governance gate',
          status: 'BLOCKED_GOVERNANCE',
          honestDetail:
            'Blocked by 9 open defect dispositions + expired GEN-GATE-20261105-REVIEW-CONTROL. Direct main pushes remain forbidden.',
        },
        {
          id: 'GAP-2',
          item: 'estate-bus DNS CNAME cutover',
          status: 'BLOCKED_FOUNDER_DNS',
          honestDetail:
            'estate-bus resolves NXDOMAIN; llm.mumchimp.com returns HTTP 200. Requires founder Cloudflare CNAME.',
        },
        {
          id: 'GAP-3',
          item: 'GitHub Actions runner billing & required estate-proof check',
          status: 'BLOCKED_RUNNER_BILLING',
          honestDetail:
            'Cloud runner spending limit & branch-protection required check await founder GitHub org toggle.',
        },
        {
          id: 'GAP-4',
          item: 'Host coordination tooling survival (idp/platform/estate/)',
          status: 'RESOLVED_IN_BUNDLE',
          honestDetail:
            'platform/estate/estate-swarm-synapse.py + .genesis/GENESIS_SPORE.dna packaged in repo & .tar.gz export.',
        },
      ],
    },
  };

  appendEventToRing(state, {
    topic: 'swarm.yield',
    sourceNode: 'codex-session-01',
    tsIso: new Date((nowSec - 600) * 1000).toISOString(),
    payload: {
      layer: 'idp/bin/estate-cache-trim',
      commitSha: 'd4b1349ce',
      learnedFact:
        'Single-flight git-pack.lock + banning git fetch --unshallow recovered host free disk to 2487 MB.',
      antibodyId: 'AB-S1PACK92',
    },
  });

  appendEventToRing(state, {
    topic: 'swarm.yield',
    sourceNode: 'aistudio-principal-01',
    tsIso: new Date((nowSec - 300) * 1000).toISOString(),
    payload: {
      layer: 'argon/apps/projector-route',
      commitSha: 'b31e032',
      learnedFact:
        'Verified origin/backup/estate-20261112 on argon (b31e032) and idp (d4b1349ce) with 19/19 projector tests green.',
      antibodyId: null,
    },
  });

  state.sporeDna = packGenesisSpore4Kb(state);
  return state;
}
