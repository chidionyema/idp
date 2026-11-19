/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GEMINI — P0 Universal Agent Collaboration Recovery
 * Phase 3: Transport & Execution Integration
 * - NATS JetStream with durable consumers & DLQ
 * - Authenticated HTTPS Adapter for sandboxed agents (Z.ai, Kimi)
 * - Git Peer Board discovery & offline fallback
 */

import { UniversalAgentEnvelope, ArtifactRef } from './types';
import { validateUniversalEnvelope, computeSha256 } from './envelope';

export interface TransportAckResult {
  acknowledged: boolean;
  messageId: string;
  deliveryAttempt: number;
  routedToDlq?: boolean;
  error?: string;
}

export interface NatsConsumerStats {
  streamName: string;
  consumerName: string;
  numPending: number;
  numAckPending: number;
  numRedelivered: number;
  lastDeliveredSeq: number;
  lag: number;
}

/**
 * 1. NATS JetStream Durable Stream & Consumer Simulator
 */
export class NatsJetStreamTransport {
  private streamName: string = 'ESTATE_COLLABORATION';
  private dlqStreamName: string = 'dlq.estate.collaboration';
  private messages: Map<string, UniversalAgentEnvelope> = new Map();
  private deliveryAttempts: Map<string, number> = new Map();
  private deadLetterQueue: UniversalAgentEnvelope[] = [];
  private acknowledgedMessages: Set<string> = new Set();
  private isConnected: boolean = true;
  private maxDeliveries: number = 3;

  public setConnectionState(connected: boolean) {
    this.isConnected = connected;
  }

  public getIsConnected(): boolean {
    return this.isConnected;
  }

  public publish(envelope: UniversalAgentEnvelope): { success: boolean; seq: number; error?: string } {
    if (!this.isConnected) {
      return { success: false, seq: -1, error: 'NATS_CONNECTION_DOWN: Transport is unreachable' };
    }

    const validation = validateUniversalEnvelope(envelope);
    if (!validation.valid) {
      return { success: false, seq: -1, error: `VALIDATION_FAILED: ${validation.errors.join('; ')}` };
    }

    this.messages.set(envelope.message_id, envelope);
    this.deliveryAttempts.set(envelope.message_id, 0);
    return { success: true, seq: this.messages.size };
  }

  public deliver(consumerName: string, recipientAgentId: string): UniversalAgentEnvelope[] {
    if (!this.isConnected) return [];

    const pending: UniversalAgentEnvelope[] = [];
    for (const [msgId, env] of this.messages.entries()) {
      if (this.acknowledgedMessages.has(msgId)) continue;
      if (env.recipient.agent_id !== recipientAgentId && env.recipient.agent_id !== 'any') continue;

      const attempts = (this.deliveryAttempts.get(msgId) || 0) + 1;
      this.deliveryAttempts.set(msgId, attempts);

      if (attempts > this.maxDeliveries) {
        // Exceeded bounded redelivery -> route to DLQ
        if (!this.deadLetterQueue.some(m => m.message_id === msgId)) {
          this.deadLetterQueue.push(env);
        }
        this.acknowledgedMessages.add(msgId);
        continue;
      }

      pending.push(env);
    }

    return pending;
  }

  public acknowledge(messageId: string): TransportAckResult {
    const attempts = this.deliveryAttempts.get(messageId) || 1;
    this.acknowledgedMessages.add(messageId);
    return { acknowledged: true, messageId, deliveryAttempt: attempts };
  }

  public negativeAcknowledge(messageId: string, reason: string): TransportAckResult {
    if (this.acknowledgedMessages.has(messageId)) {
      return { acknowledged: false, messageId, deliveryAttempt: this.deliveryAttempts.get(messageId) || this.maxDeliveries, routedToDlq: true, error: reason };
    }

    const attempts = (this.deliveryAttempts.get(messageId) || 0) + 1;
    this.deliveryAttempts.set(messageId, attempts);

    if (attempts >= this.maxDeliveries) {
      const msg = this.messages.get(messageId);
      if (msg && !this.deadLetterQueue.some(m => m.message_id === messageId)) {
        this.deadLetterQueue.push(msg);
      }
      this.acknowledgedMessages.add(messageId);
      return { acknowledged: false, messageId, deliveryAttempt: attempts, routedToDlq: true, error: reason };
    }

    return { acknowledged: false, messageId, deliveryAttempt: attempts, routedToDlq: false, error: reason };
  }

  public getConsumerStats(consumerName: string): NatsConsumerStats {
    let unacked = 0;
    for (const msgId of this.messages.keys()) {
      if (!this.acknowledgedMessages.has(msgId)) unacked++;
    }

    return {
      streamName: this.streamName,
      consumerName,
      numPending: unacked,
      numAckPending: unacked > 0 ? 1 : 0,
      numRedelivered: Array.from(this.deliveryAttempts.values()).filter(a => a > 1).length,
      lastDeliveredSeq: this.messages.size,
      lag: unacked
    };
  }

  public getDeadLetterQueue(): UniversalAgentEnvelope[] {
    return [...this.deadLetterQueue];
  }
}

/**
 * 2. Authenticated HTTPS Adapter for Sandboxed Agents
 * Allows Z.ai / Kimi / external agents to submit & pull without Git write credentials
 */
export interface HttpsAdapterSession {
  token: string;
  agentId: string;
  provider: string;
  permissions: ('SUBMIT_MESSAGE' | 'SUBMIT_PATCH' | 'READ_EVIDENCE' | 'READ_RECEIPTS')[];
  expiresAt: string;
}

export class AuthenticatedHttpsAdapter {
  private sessions: Map<string, HttpsAdapterSession> = new Map();
  private outbox: UniversalAgentEnvelope[] = [];
  private storedArtifacts: Map<string, { meta: ArtifactRef; data: string }> = new Map();
  private receipts: Map<string, any> = new Map();

  constructor() {
    // Seed initial session for Z.ai sandboxed agent
    this.registerSession({
      token: 'bearer_zai_sandboxed_token_99182',
      agentId: 'zai-sandboxed-agent-01',
      provider: 'zai',
      permissions: ['SUBMIT_MESSAGE', 'SUBMIT_PATCH', 'READ_EVIDENCE', 'READ_RECEIPTS'],
      expiresAt: new Date(Date.now() + 86400000).toISOString()
    });

    // Seed session for DeepSeek agent
    this.registerSession({
      token: 'bearer_deepseek_reasoner_token_48123',
      agentId: 'deepseek-reasoner-agent-02',
      provider: 'deepseek',
      permissions: ['SUBMIT_MESSAGE', 'READ_EVIDENCE', 'READ_RECEIPTS'],
      expiresAt: new Date(Date.now() + 86400000).toISOString()
    });
  }

  public registerSession(session: HttpsAdapterSession) {
    this.sessions.set(session.token, session);
  }

  public authenticate(token: string): HttpsAdapterSession | null {
    const session = this.sessions.get(token);
    if (!session) return null;
    if (new Date(session.expiresAt).getTime() < Date.now()) return null;
    return session;
  }

  public submitEnvelope(token: string, envelope: UniversalAgentEnvelope): { success: boolean; messageId?: string; receiptHash?: string; error?: string } {
    const session = this.authenticate(token);
    if (!session) {
      return { success: false, error: 'UNAUTHORIZED: Invalid or expired Bearer token' };
    }

    if (envelope.message_type === 'patch_submission' && !session.permissions.includes('SUBMIT_PATCH')) {
      return { success: false, error: 'FORBIDDEN: Session lacks SUBMIT_PATCH permission' };
    }

    const validation = validateUniversalEnvelope(envelope);
    if (!validation.valid) {
      return { success: false, error: `BAD_REQUEST: ${validation.errors.join('; ')}` };
    }

    this.outbox.push(envelope);
    const receiptHash = computeSha256(`https_submission:${envelope.message_id}:${Date.now()}`);
    this.receipts.set(envelope.idempotency_key, {
      status: 'ACCEPTED_DURABLE',
      message_id: envelope.message_id,
      receiptHash,
      accepted_at: new Date().toISOString()
    });

    return { success: true, messageId: envelope.message_id, receiptHash };
  }

  public storeArtifact(token: string, meta: ArtifactRef, content: string): { success: boolean; uri?: string; error?: string } {
    const session = this.authenticate(token);
    if (!session) return { success: false, error: 'UNAUTHORIZED' };

    const uri = `estate://artifacts/${meta.id}/${meta.filename}`;
    this.storedArtifacts.set(meta.id, { meta: { ...meta, uri }, data: content });
    return { success: true, uri };
  }

  public getReceipt(token: string, idempotencyKey: string): any {
    const session = this.authenticate(token);
    if (!session) return { error: 'UNAUTHORIZED' };
    return this.receipts.get(idempotencyKey) || null;
  }

  public pollMessages(token: string, agentId: string): UniversalAgentEnvelope[] {
    const session = this.authenticate(token);
    if (!session) return [];
    return this.outbox.filter(m => m.recipient.agent_id === agentId || m.recipient.agent_id === 'any');
  }
}

/**
 * 3. Git Peer Board Engine (refs/heads/peer-board/collaboration-v1)
 * Offline discovery & fallback storage without secrets or unrestricted executables
 */
export interface GitPeerBoardManifest {
  version: string;
  commitSha: string;
  syncedAt: string;
  activeAgents: Array<{
    agentId: string;
    role: string;
    lastHeartbeat: string;
    transportPreference: string;
  }>;
  pendingMissionsDigest: string;
  offlineEnvelopesCount: number;
}

export class GitPeerBoardEngine {
  private branch: string = 'refs/heads/peer-board/collaboration-v1';
  private bufferedOfflineEnvelopes: UniversalAgentEnvelope[] = [];
  private lastCommitSha: string = 'c90f23a';

  public publishOfflineFallback(envelope: UniversalAgentEnvelope): { success: boolean; commitSha: string; digest: string } {
    // Guardrail: Sanitize to prevent storing raw secrets or executable payloads in Git
    const sanitizedEnvelope = {
      ...envelope,
      payload: this.sanitizeForGit(envelope.payload)
    };

    this.bufferedOfflineEnvelopes.push(sanitizedEnvelope);
    this.lastCommitSha = `git_${Date.now().toString(16)}`;
    const digest = computeSha256(JSON.stringify(sanitizedEnvelope));

    return {
      success: true,
      commitSha: this.lastCommitSha,
      digest
    };
  }

  private sanitizeForGit(payload: any): any {
    if (!payload || typeof payload !== 'object') return payload;
    const sanitized = { ...payload };
    // Redact tokens or secrets if accidentally present
    for (const key of Object.keys(sanitized)) {
      if (/token|secret|password|private_key/i.test(key)) {
        sanitized[key] = '[REDACTED_GIT_PEER_BOARD_POLICY]';
      }
    }
    return sanitized;
  }

  public reconcileOnNatsReconnected(nats: NatsJetStreamTransport): { reconciledCount: number; deduplicatedCount: number } {
    let reconciledCount = 0;
    let deduplicatedCount = 0;

    for (const env of this.bufferedOfflineEnvelopes) {
      const pub = nats.publish(env);
      if (pub.success) {
        reconciledCount++;
      } else {
        deduplicatedCount++;
      }
    }

    this.bufferedOfflineEnvelopes = [];
    return { reconciledCount, deduplicatedCount };
  }

  public getManifest(): GitPeerBoardManifest {
    return {
      version: '1.0.0',
      commitSha: this.lastCommitSha,
      syncedAt: new Date().toISOString(),
      activeAgents: [
        { agentId: 'gemini-executive-lead', role: 'Executive Lead & Executor', lastHeartbeat: new Date().toISOString(), transportPreference: 'NATS' },
        { agentId: 'kimi-analyst-reader', role: 'Read-Only Correlated Analyst', lastHeartbeat: new Date().toISOString(), transportPreference: 'HTTPS_READ_ONLY' },
        { agentId: 'zai-sandboxed-agent-01', role: 'Sandboxed Contributor', lastHeartbeat: new Date().toISOString(), transportPreference: 'HTTPS_ADAPTER' },
        { agentId: 'deepseek-reasoner-agent-02', role: 'Autonomous Math & Reasoning', lastHeartbeat: new Date().toISOString(), transportPreference: 'NATS_OR_HTTPS' }
      ],
      pendingMissionsDigest: computeSha256(JSON.stringify(this.bufferedOfflineEnvelopes)),
      offlineEnvelopesCount: this.bufferedOfflineEnvelopes.length
    };
  }
}
