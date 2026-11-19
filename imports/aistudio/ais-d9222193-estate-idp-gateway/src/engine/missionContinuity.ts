import { createHash, createHmac } from 'node:crypto';

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

export class ContinuityError extends Error {
  code: ContinuityErrorCode;

  constructor(code: ContinuityErrorCode, message: string) {
    super(message);
    this.name = 'ContinuityError';
    this.code = code;
    Object.setPrototypeOf(this, ContinuityError.prototype);
  }
}

export interface CapacityOffer {
  workerId: string;
  adapter: string;
  executionHost: string;
  failureDomain: string;
  providers: string[];
  capabilities: string[];
  availability: AvailabilityState;
  quotaState: 'AVAILABLE' | 'EXHAUSTED' | 'UNKNOWN';
  contextState: 'SUFFICIENT' | 'LOW' | 'UNKNOWN';
  concurrencyAvailable: number;
  costBudgetRemaining: number;
  verifiedSuccessRate: number | null;
  p95LatencyMs: number | null;
  authenticated: boolean;
  observedAtMs: number;
  ttlMs: number;
}

export interface MissionCheckpoint {
  schema: 'genesis.mission-checkpoint/v1';
  missionId: string;
  attemptId: string;
  leaseEpoch: number;
  sequence: number;
  phase: MissionPhase;
  goal: string;
  subgoals: Array<{ id: string; text: string; status: 'OPEN' | 'DONE' | 'BLOCKED' }>;
  verifiedFacts: Array<{ claim: string; source: string; digest: string }>;
  decisions: Array<{ id: string; decision: string; rationale: string }>;
  constraints: string[];
  attemptedActions: string[];
  failedEvidenceRefs: string[];
  nextAction: string;
  branch: string | null;
  commit: string | null;
  commitVerified: boolean;
  capabilityScope: string[];
  contextDigest: string;
  createdAtMs: number;
}

export interface MissionRecord {
  missionId: string;
  kind: MissionKind;
  riskClass: 'P0' | 'P1' | 'P2';
  goal: string;
  phase: MissionPhase;
  attemptId: string;
  workerId: string;
  leaseEpoch: number;
  leaseExpiresAtMs: number;
  requiredCapabilities: string[];
  costBudgetRemaining: number;
  recoveryPending: boolean;
  failureClass: FailureClass | null;
  evidenceRef: string | null;
  checkpointSequence: number;
  checkpointDigest: string;
  createdAtMs: number;
  updatedAtMs: number;
}

export interface HeartbeatResult {
  accepted: boolean;
  reason: string;
  observedAtMs: number;
  leaseExpiresAtMs: number;
}

export interface MissionCheckpointRecord {
  missionId: string;
  attemptId: string;
  leaseEpoch: number;
  sequence: number;
  checkpoint: MissionCheckpoint;
  digest: string;
  hmac: string;
  createdAtMs: number;
}

export interface TakeoverResult {
  mission: MissionRecord;
  resumeFrom: MissionCheckpointRecord;
  mustCheckpointBeforeEffect: true;
}

export interface EffectPermit {
  missionId: string;
  attemptId: string;
  leaseEpoch: number;
  effectKey: string;
  token: string;
  expiresAtMs: number;
}

export interface EffectCompletion {
  effectKey: string;
  duplicate: boolean;
  receipt: Record<string, unknown>;
  completedAtMs: number;
}

export interface RecoveryPendingResult {
  mission: MissionRecord;
  selected: null;
  rejected: Array<{ workerId: string; reason: string }>;
}

export interface ContinuitySnapshot {
  missions: MissionRecord[];
  latestCheckpointByMission: Record<string, MissionCheckpointRecord>;
  events: Array<{
    eventId: number;
    missionId: string;
    eventType: string;
    eventHash: string;
    createdAtMs: number;
  }>;
}

/**
 * Deterministic Canonical JSON Serialization
 * Recursively sorts keys alphabetically with no added whitespace.
 */
export function canonicalJson(val: unknown): string {
  if (val === null || typeof val !== 'object') {
    return JSON.stringify(val);
  }
  if (Array.isArray(val)) {
    return '[' + val.map((item) => canonicalJson(item)).join(',') + ']';
  }
  const obj = val as Record<string, unknown>;
  const sortedKeys = Object.keys(obj).sort();
  const entries = sortedKeys.map(
    (key) => JSON.stringify(key) + ':' + canonicalJson(obj[key])
  );
  return '{' + entries.join(',') + '}';
}

/**
 * Computes SHA-256 digest in lowercase hexadecimal format.
 */
export function sha256(data: string): string {
  return createHash('sha256').update(data, 'utf8').digest('hex');
}

/**
 * Computes HMAC-SHA256 signature in lowercase hexadecimal format.
 */
export function hmacSha256(key: string, data: string): string {
  return createHmac('sha256', key).update(data, 'utf8').digest('hex');
}

/**
 * Computes the unique deterministic effect key.
 */
export function computeEffectKey(
  missionId: string,
  stepId: string,
  action: string,
  argsDigest: string
): string {
  return sha256(missionId + ':' + stepId + ':' + action + ':' + argsDigest);
}

/**
 * Allowed phase transition graph per specification:
 * QUEUED -> CLAIMED
 * CLAIMED -> EXECUTING | HANDOVER_PENDING | BLOCKED
 * EXECUTING -> CHECKPOINTING | HANDOVER_PENDING | VERIFYING | BLOCKED
 * CHECKPOINTING -> EXECUTING | HANDOVER_PENDING
 * HANDOVER_PENDING -> TAKEN_OVER | BLOCKED
 * TAKEN_OVER -> EXECUTING | VERIFYING | BLOCKED
 * VERIFYING -> OPERATING | REPAIRING | BLOCKED
 * REPAIRING -> EXECUTING | BLOCKED
 */
export const ALLOWED_TRANSITIONS: Readonly<Record<MissionPhase, readonly MissionPhase[]>> = {
  QUEUED: ['CLAIMED'],
  CLAIMED: ['EXECUTING', 'HANDOVER_PENDING', 'BLOCKED'],
  EXECUTING: ['CHECKPOINTING', 'HANDOVER_PENDING', 'VERIFYING', 'BLOCKED'],
  CHECKPOINTING: ['EXECUTING', 'HANDOVER_PENDING'],
  HANDOVER_PENDING: ['TAKEN_OVER', 'BLOCKED'],
  TAKEN_OVER: ['EXECUTING', 'VERIFYING', 'BLOCKED'],
  VERIFYING: ['OPERATING', 'REPAIRING', 'BLOCKED'],
  REPAIRING: ['EXECUTING', 'BLOCKED'],
  OPERATING: [],
  BLOCKED: [],
};

export function isValidTransition(from: MissionPhase, to: MissionPhase): boolean {
  const allowed = ALLOWED_TRANSITIONS[from];
  return Array.isArray(allowed) && allowed.includes(to);
}

const COMMON_SECRET_PATTERNS = [
  /ghp_[A-Za-z0-9_]+/i,
  /github_pat_[A-Za-z0-9_]+/i,
  /AIza[0-9A-Za-z-_]+/i,
  /sk-[0-9A-Za-z-_]+/i,
  /-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----/i,
  /password=/i,
];

function scanForSecrets(val: unknown): void {
  if (typeof val === 'string') {
    for (const pattern of COMMON_SECRET_PATTERNS) {
      if (pattern.test(val)) {
        // Never echo the secret in the error message
        throw new ContinuityError(
          'CHECKPOINT_CONTAINS_SECRET',
          'Checkpoint contains disallowed secret pattern'
        );
      }
    }
    return;
  }
  if (val && typeof val === 'object') {
    if (Array.isArray(val)) {
      for (const item of val) {
        scanForSecrets(item);
      }
    } else {
      for (const key of Object.keys(val)) {
        scanForSecrets((val as Record<string, unknown>)[key]);
      }
    }
  }
}

/**
 * Validates a mission checkpoint against structural, secret, and code-specific rules.
 */
export function validateCheckpoint(checkpoint: MissionCheckpoint, kind: MissionKind): void {
  if (!checkpoint || typeof checkpoint !== 'object') {
    throw new ContinuityError('INVALID_INPUT', 'Checkpoint must be an object');
  }
  if (checkpoint.schema !== 'genesis.mission-checkpoint/v1') {
    throw new ContinuityError('INVALID_INPUT', 'Invalid checkpoint schema');
  }
  if (!checkpoint.missionId || typeof checkpoint.missionId !== 'string') {
    throw new ContinuityError('INVALID_INPUT', 'Missing or invalid checkpoint missionId');
  }
  if (!checkpoint.attemptId || typeof checkpoint.attemptId !== 'string') {
    throw new ContinuityError('INVALID_INPUT', 'Missing or invalid checkpoint attemptId');
  }
  if (typeof checkpoint.leaseEpoch !== 'number' || checkpoint.leaseEpoch < 1) {
    throw new ContinuityError('INVALID_INPUT', 'Invalid checkpoint leaseEpoch');
  }
  if (typeof checkpoint.sequence !== 'number' || checkpoint.sequence < 1) {
    throw new ContinuityError('INVALID_INPUT', 'Invalid checkpoint sequence');
  }

  // Scan recursively for common secret shapes
  scanForSecrets(checkpoint);

  // For kind === 'code', a checkpoint requires a non-empty branch, a full 40-character lowercase commit SHA and commitVerified === true
  if (kind === 'code') {
    if (!checkpoint.branch || typeof checkpoint.branch !== 'string' || checkpoint.branch.trim() === '') {
      throw new ContinuityError('INVALID_INPUT', 'Code mission requires a non-empty branch');
    }
    if (!checkpoint.commit || typeof checkpoint.commit !== 'string' || !/^[0-9a-f]{40}$/.test(checkpoint.commit)) {
      throw new ContinuityError(
        'INVALID_INPUT',
        'Code mission requires a full 40-character lowercase hex commit SHA'
      );
    }
    if (checkpoint.commitVerified !== true) {
      throw new ContinuityError('INVALID_INPUT', 'Code mission requires commitVerified === true');
    }
  }
}

/**
 * Determines if checkpointing is required based on resource usage, turn count, and pending effects.
 */
export function checkpointRequired(input: {
  knownContextRemainingRatio: number | null;
  knownTokenRemainingRatio: number | null;
  turnIndex: number;
  maxTurns: number;
  elapsedMs: number;
  maxElapsedMs: number;
  providerFaultCount: number;
  irreversibleEffectPending: boolean;
}): { required: boolean; reasons: string[] } {
  const reasons: string[] = [];

  if (input.irreversibleEffectPending) {
    reasons.push('IRREVERSIBLE_EFFECT_PENDING');
  }

  if (input.knownContextRemainingRatio !== null && input.knownContextRemainingRatio <= 0.3) {
    reasons.push('LOW_CONTEXT_REMAINING');
  }

  if (input.knownTokenRemainingRatio !== null && input.knownTokenRemainingRatio <= 0.3) {
    reasons.push('LOW_TOKEN_REMAINING');
  }

  if (input.maxTurns > 0 && input.turnIndex / input.maxTurns >= 0.9) {
    reasons.push('HIGH_TURN_USAGE');
  }

  if (input.maxElapsedMs > 0 && input.elapsedMs / input.maxElapsedMs >= 0.8) {
    reasons.push('HIGH_ELAPSED_USAGE');
  }

  if (input.providerFaultCount >= 1) {
    reasons.push('PROVIDER_FAULT_OCCURRED');
  }

  // If both ratios are unknown, require checkpointing after 12 turns
  if (input.knownContextRemainingRatio === null && input.knownTokenRemainingRatio === null) {
    if (input.turnIndex >= 12) {
      reasons.push('UNKNOWN_RATIOS_TURN_THRESHOLD_EXCEEDED');
    }
  }

  return {
    required: reasons.length > 0,
    reasons,
  };
}

/**
 * Evaluates candidate offers and selects the best eligible takeover candidate.
 */
export function selectTakeoverCandidate(input: {
  failedAttempt: { workerId: string; failureDomain: string; provider: string };
  requiredCapabilities: string[];
  remainingCost: number;
  offers: CapacityOffer[];
  nowMs: number;
}): {
  selected: CapacityOffer | null;
  rejected: Array<{ workerId: string; reason: string }>;
} {
  const rejected: Array<{ workerId: string; reason: string }> = [];
  const eligible: CapacityOffer[] = [];

  for (const offer of input.offers) {
    if (!offer.authenticated) {
      rejected.push({ workerId: offer.workerId, reason: 'UNAUTHENTICATED' });
      continue;
    }
    if (offer.observedAtMs + offer.ttlMs < input.nowMs) {
      rejected.push({ workerId: offer.workerId, reason: 'STALE_OFFER' });
      continue;
    }
    if (offer.observedAtMs > input.nowMs + 5000) {
      rejected.push({ workerId: offer.workerId, reason: 'FUTURE_OFFER' });
      continue;
    }
    if (offer.availability !== 'AVAILABLE') {
      rejected.push({ workerId: offer.workerId, reason: `UNAVAILABLE_${offer.availability}` });
      continue;
    }
    if (offer.quotaState !== 'AVAILABLE') {
      rejected.push({ workerId: offer.workerId, reason: `QUOTA_${offer.quotaState}` });
      continue;
    }
    if (offer.contextState !== 'SUFFICIENT') {
      rejected.push({ workerId: offer.workerId, reason: `CONTEXT_${offer.contextState}` });
      continue;
    }
    if (offer.concurrencyAvailable <= 0) {
      rejected.push({ workerId: offer.workerId, reason: 'CONCURRENCY_EXHAUSTED' });
      continue;
    }
    if (offer.costBudgetRemaining < input.remainingCost) {
      rejected.push({ workerId: offer.workerId, reason: 'COST_INSUFFICIENT' });
      continue;
    }
    const hasAllCapabilities = input.requiredCapabilities.every((cap) =>
      offer.capabilities.includes(cap)
    );
    if (!hasAllCapabilities) {
      rejected.push({ workerId: offer.workerId, reason: 'MISSING_REQUIRED_CAPABILITIES' });
      continue;
    }
    if (offer.workerId === input.failedAttempt.workerId) {
      rejected.push({ workerId: offer.workerId, reason: 'SAME_WORKER' });
      continue;
    }
    if (offer.failureDomain === input.failedAttempt.failureDomain) {
      rejected.push({ workerId: offer.workerId, reason: 'SAME_FAILURE_DOMAIN' });
      continue;
    }
    if (offer.verifiedSuccessRate === null || offer.p95LatencyMs === null) {
      rejected.push({ workerId: offer.workerId, reason: 'MISSING_VERIFIED_METRICS' });
      continue;
    }

    eligible.push(offer);
  }

  if (eligible.length === 0) {
    return { selected: null, rejected };
  }

  // Eligible ranking order:
  // 1. different provider from the failed attempt;
  // 2. higher verified success rate;
  // 3. lower p95 latency;
  // 4. lower cost;
  // 5. lexicographic worker id.
  eligible.sort((a, b) => {
    const aDifferentProvider = !a.providers.includes(input.failedAttempt.provider);
    const bDifferentProvider = !b.providers.includes(input.failedAttempt.provider);
    if (aDifferentProvider !== bDifferentProvider) {
      return aDifferentProvider ? -1 : 1;
    }

    if (b.verifiedSuccessRate! !== a.verifiedSuccessRate!) {
      return b.verifiedSuccessRate! - a.verifiedSuccessRate!;
    }

    if (a.p95LatencyMs! !== b.p95LatencyMs!) {
      return a.p95LatencyMs! - b.p95LatencyMs!;
    }

    if (a.costBudgetRemaining !== b.costBudgetRemaining) {
      return a.costBudgetRemaining - b.costBudgetRemaining;
    }

    return a.workerId.localeCompare(b.workerId);
  });

  return {
    selected: eligible[0],
    rejected,
  };
}

export { MissionContinuityKernel } from './missionContinuity.sqlite.js';
