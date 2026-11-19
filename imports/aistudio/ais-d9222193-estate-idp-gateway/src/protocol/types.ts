/**
 * Canonical Estate IDP Protocol & Client Harness Types
 * Architecture: CONSULT Client & Cross-Language Reference Harness
 * Canonical Authority: platform/estate/context/server.py:739 & node_protocol.json:19
 */

export type ActionType = 'read' | 'safe_mutation' | 'unsafe_mutation' | 'mutation';

// Canonical offline safe action allowlist per node_protocol.json:19 & node_protocol.py:104
export type CanonicalOfflineAction = 'launch' | 'back' | 'home' | 'wait';
export const CANONICAL_OFFLINE_ALLOWLIST: readonly CanonicalOfflineAction[] = [
  'launch',
  'back',
  'home',
  'wait',
] as const;

export type SurfaceId =
  | 'mac_session_460567726510256'
  | 'argon_genesis_cluster'
  | 'mobile_node_ios_client'
  | 'ci_worker_runner_01';

export type AgreementState = 'agreed' | 'deferred' | 'blind';

export interface Lease {
  token: string;
  surfaceId: string;
  grantedAt: number;
  expiresAt: number;
  scope: string[];
}

/**
 * Receipt Presence Record:
 * Guarantees receipt presence, digest binding, and rulesHash alignment per canonical gateway.
 * Note: A cryptographic digital signature requires asymmetric Greenlane/KMS key identity integration.
 */
export interface Receipt {
  receiptId: string;
  callId: string;
  idempotencyKey: string;
  actionType: ActionType;
  surfaceId: string;
  tenantId: string;
  issuedAt: number;
  compiledContextHash: string;
  rulesHash: string;
  digest: string;
  issuer: string;
  // Cryptographic signature metadata (if key identity is configured)
  signature?: string;
  keyId?: string;
  signatureAlgorithm?: 'HMAC-SHA256' | 'Ed25519' | 'none';
}

export interface Envelope<T = unknown> {
  callId: string;
  tenantId?: string;
  surfaceId: SurfaceId | string;
  capability: string;
  actionType: ActionType;
  isOnline: boolean;
  lease?: Lease | null;
  compiledContextHash?: string;
  idempotencyKey?: string;
  rulesHash?: string;
  payload: T;
  evidenceDigest?: string;
  workingDirectory?: string;
}

export interface AdmissionRefusal {
  admitted: false;
  code:
    | 'RULES_HASH_MISMATCH'
    | 'UNKNOWN_RULE_READ_ONLY'
    | 'UNSAFE_OFFLINE_MUTATION_REFUSED'
    | 'OFFLINE_ACTION_NOT_IN_ALLOWLIST'
    | 'LEASE_REQUIRED'
    | 'LEASE_EXPIRED'
    | 'COMPILED_CONTEXT_HASH_REQUIRED'
    | 'IDEMPOTENCY_KEY_REQUIRED'
    | 'SHORT_LOOP_DETECTED'
    | 'CAPABILITY_HANDLER_FAILED'
    | 'RECEIPT_GENERATION_FAILED';
  reason: string;
}

export interface AdmissionSuccess<R = unknown> {
  admitted: true;
  queued?: boolean;
  receipt?: Receipt;
  cached?: boolean;
  data: R;
}

export type AdmissionResult<R = unknown> = AdmissionSuccess<R> | AdmissionRefusal;

export interface CapabilityHandler<T = unknown, R = unknown> {
  (envelope: Envelope<T>): Promise<R> | R;
}

export interface GovernanceClause {
  clauseNumber: number;
  name: string;
  decidableByMachine: 'Yes' | 'Partly' | 'Mostly' | 'No' | 'Measure only';
  enforcementMode: 'enforced' | 'linted' | 'advice';
  details: string;
  requiredDeclaration: string;
}

export interface SurfaceAck {
  surfaceId: SurfaceId | string;
  label: string;
  token?: string;
  state: AgreementState;
  deadlineMs?: number;
  lastSeenMs: number;
  authSource: 'Argon Genesis (Cluster)' | 'Local Self-Report (Deprecated)' | 'Cryptographic One-Time Token';
}

export interface TelemetryMetric {
  id: string;
  timestamp: number;
  surfaceId: string;
  callId: string;
  action: string;
  status: 'admitted' | 'refused' | 'queued' | 'cached';
  durationMs: number;
  reason?: string;
  receiptId?: string;
}

export interface StoredIdempotencyRecord {
  tenantId: string;
  surfaceId: string;
  capability: string;
  idempotencyKey: string;
  compiledContextHash: string;
  result: unknown;
  receipt?: Receipt;
  storedAt: number;
}
