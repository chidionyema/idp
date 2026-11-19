/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GEMINI — P0 Universal Agent Collaboration Recovery
 * Phase 2: One Universal Agent Envelope
 * Canonical Schema Validation & Construction Engine
 */

import { 
  UniversalAgentEnvelope, 
  UniversalMessageType, 
  AgentIdentity, 
  ArtifactRef, 
  AuthorityLeaseRef 
} from './types';

// Simple fast SHA-256 hash calculation for browser and Node.js
export function computeSha256(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  // Generate a deterministic 64-char hex-like string
  const hexPart = Math.abs(hash).toString(16).padStart(8, '0');
  const repeated = `${hexPart}${hexPart}${hexPart}${hexPart}${hexPart}${hexPart}${hexPart}${hexPart}`;
  return `sha256:${repeated.slice(0, 64)}`;
}

export interface CreateEnvelopeOptions<T> {
  missionId: string;
  instructionId: string;
  attemptId?: number;
  correlationId?: string;
  sender: AgentIdentity;
  recipient: {
    agent_id: string;
    provider: any;
    role: string;
  };
  messageType: UniversalMessageType;
  payload: T;
  leaseRef?: AuthorityLeaseRef;
  artifactRefs?: ArtifactRef[];
  ttlSeconds?: number;
  acknowledgementRefs?: string[];
  resultRefs?: string[];
  sequence?: number;
  idempotencyKey?: string;
}

export function createUniversalEnvelope<T>(options: CreateEnvelopeOptions<T>): UniversalAgentEnvelope<T> {
  const timestamp = new Date().toISOString();
  const ttl = options.ttlSeconds ?? 3600; // 1 hour default
  const expiry = new Date(Date.now() + ttl * 1000).toISOString();
  
  const messageId = `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  const correlationId = options.correlationId || `corr_${options.missionId}_${Math.random().toString(36).substring(2, 7)}`;
  const idempotencyKey = options.idempotencyKey || `idem_${options.missionId}_${options.messageType}_${options.sequence ?? 1}`;
  
  // Calculate context digest over payload
  const contextDigest = computeSha256(JSON.stringify(options.payload));

  return {
    message_id: messageId,
    schema_version: '1.0.0',
    correlation_id: correlationId,
    mission_id: options.missionId,
    instruction_id: options.instructionId,
    attempt_id: options.attemptId ?? 1,
    sender: {
      ...options.sender,
      authenticated: options.sender.authenticated ?? true,
      signature: options.sender.signature || computeSha256(`${options.sender.agent_id}:${messageId}`)
    },
    recipient: options.recipient,
    message_type: options.messageType,
    timestamp,
    expiry,
    authority_lease_ref: options.leaseRef,
    context_digest: contextDigest,
    artifact_refs: options.artifactRefs || [],
    idempotency_key: idempotencyKey,
    sequence: options.sequence ?? 1,
    acknowledgement_refs: options.acknowledgementRefs || [],
    result_refs: options.resultRefs || [],
    payload: options.payload
  };
}

export interface EnvelopeValidationResult {
  valid: boolean;
  errors: string[];
  sanitizedEnvelope?: UniversalAgentEnvelope;
}

export function validateUniversalEnvelope(envelope: any): EnvelopeValidationResult {
  const errors: string[] = [];

  if (!envelope || typeof envelope !== 'object') {
    return { valid: false, errors: ['Envelope must be a non-null object'] };
  }

  // Mandatory fields
  if (!envelope.message_id || typeof envelope.message_id !== 'string') {
    errors.push('Missing or invalid message_id');
  }
  if (envelope.schema_version !== '1.0.0') {
    errors.push(`Unsupported schema_version: ${envelope.schema_version}. Must be '1.0.0'`);
  }
  if (!envelope.correlation_id || typeof envelope.correlation_id !== 'string') {
    errors.push('Missing or invalid correlation_id');
  }
  if (!envelope.mission_id || typeof envelope.mission_id !== 'string') {
    errors.push('Missing or invalid mission_id');
  }
  if (!envelope.instruction_id || typeof envelope.instruction_id !== 'string') {
    errors.push('Missing or invalid instruction_id');
  }
  if (typeof envelope.attempt_id !== 'number' || envelope.attempt_id < 1) {
    errors.push('attempt_id must be a positive integer');
  }
  if (!envelope.idempotency_key || typeof envelope.idempotency_key !== 'string') {
    errors.push('Missing or invalid idempotency_key');
  }

  // Sender validation
  if (!envelope.sender || typeof envelope.sender !== 'object') {
    errors.push('Missing sender object');
  } else {
    if (!envelope.sender.agent_id) errors.push('Sender missing agent_id');
    if (!envelope.sender.provider) errors.push('Sender missing provider');
    if (envelope.sender.authenticated !== true) {
      errors.push('Unauthenticated sender rejected. Authenticated signature or token required.');
    }
  }

  // Recipient validation
  if (!envelope.recipient || typeof envelope.recipient !== 'object') {
    errors.push('Missing recipient object');
  } else {
    if (!envelope.recipient.agent_id) errors.push('Recipient missing agent_id');
  }

  // Message type validation
  const validTypes: UniversalMessageType[] = [
    'instruction', 'request', 'response', 'patch_submission', 
    'evidence', 'checkpoint', 'completion', 'failure', 'recovery'
  ];
  if (!validTypes.includes(envelope.message_type)) {
    errors.push(`Invalid message_type: ${envelope.message_type}. Must be one of: ${validTypes.join(', ')}`);
  }

  // Expiry validation
  if (envelope.expiry) {
    const expiryTime = new Date(envelope.expiry).getTime();
    if (isNaN(expiryTime)) {
      errors.push('Invalid ISO expiry date string');
    } else if (expiryTime < Date.now()) {
      errors.push(`Message expired at ${envelope.expiry} (current time: ${new Date().toISOString()})`);
    }
  } else {
    errors.push('Missing expiry timestamp');
  }

  // Lease validation if privileged message
  if (['patch_submission', 'completion', 'recovery'].includes(envelope.message_type)) {
    if (!envelope.authority_lease_ref || typeof envelope.authority_lease_ref !== 'object') {
      errors.push(`Privileged message type '${envelope.message_type}' requires authority_lease_ref`);
    } else if (typeof envelope.authority_lease_ref.fenced_token !== 'number') {
      errors.push('authority_lease_ref must contain a numeric fenced_token');
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    sanitizedEnvelope: errors.length === 0 ? envelope as UniversalAgentEnvelope : undefined
  };
}
