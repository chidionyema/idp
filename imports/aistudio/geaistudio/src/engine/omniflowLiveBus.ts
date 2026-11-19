/**
 * Authoritative OMNIFLOW Real-Time Cross-Surface Collaboration Bus (#7481 / #8133 / #7794 / #8184)
 *
 * Connects Console CLI workers, Web browsers, Mobile/Messaging adapters, and Cloud runners
 * over one durable server-authoritative HTTPS + SSE fabric:
 *  - Idempotent envelope ingestion (`idempotencyKey` deduplication)
 *  - Addressing: `@all`, `@formation:<name>`, or `@agent:<agentId>`
 *  - Monotonic fencing tokens (`f_1 < f_2 < ...`) with stale-fence `409` rejection
 *  - Independent verifier separation (`verifierId !== holderAgentId`, else `403`)
 *  - Automatic lease recovery when a participant's heartbeat TTL expires (0 lost instructions)
 *  - Real outside-in DNS + retired OKE IP (`193.123.184.22`) + `/health` external spine probe
 *    (strictly obeys `defect/live-services-failed-while-declared-2026-11-16`: never fakes green)
 */

import dns from 'node:dns/promises';
import fs from 'node:fs';
import path from 'node:path';
import { pureSha256Hex } from './pureSha256';
import { validateIngestUrl } from './debugPackBuilder';
import {
  BoundaryManifestValidation,
  validateUnsealedChangeManifest,
} from './meridianCapabilityCalculus';

export type BusSurfaceClass =
  | 'FOUNDER_COCKPIT'
  | 'CONSOLE_CLI'
  | 'WEB_BROWSER'
  | 'API_WORKER'
  | 'CLOUD_RUNNER'
  | 'MOBILE_MESSAGING';

export type OmniflowMessageVerb =
  | 'ASK'
  | 'OFFER'
  | 'CLAIM'
  | 'PATCH_REF'
  | 'EVIDENCE_REF'
  | 'BLOCKED'
  | 'STATUS'
  | 'RECOVERY';

export type EnvelopeCustodyStage =
  | 'PUBLISHED'
  | 'DELIVERED'
  | 'LEASED'
  | 'EXECUTING'
  | 'VERIFIED_EFFECT'
  | 'LEASE_EXPIRED_RECOVERING'
  | 'BLOCKED';

export interface BusParticipant {
  agentId: string;
  displayName: string;
  surfaceClass: BusSurfaceClass;
  transport: 'SSE_HTTPS' | 'CLI_BRIDGE' | 'WEBHOOK' | 'CLOUDFLARE_DO';
  capabilities: string[];
  formations: string[];
  connected: boolean;
  joinedAtUtc: string;
  lastHeartbeatUtc: string;
  lastHeartbeatMs: number;
  ttlMs: number;
  activeLeasesCount: number;
}

export interface OmniflowBusMessage {
  seq: number;
  envelopeId: string;
  correlationId: string;
  idempotencyKey: string;
  fromAgent: string;
  fromSurface: BusSurfaceClass;
  target: string; // '@all' | '@formation:<name>' | '@agent:<id>'
  verb: OmniflowMessageVerb;
  body: string;
  artifactRef: string | null;
  requiresClaim: boolean;
  custodyStage: EnvelopeCustodyStage;
  holderAgentId: string | null;
  fencingToken: number | null;
  verifierId: string | null;
  verificationNote: string | null;
  verificationReceiptSha256: string | null;
  recoveryCount: number;
  createdAtUtc: string;
  updatedAtUtc: string;
  envelopeSha256: string;
  proposedFiles?: string[];
  boundaryValidation?: BoundaryManifestValidation;
}

export type ExternalSpineProbeStatus =
  | 'NOT_PROBED'
  | 'LIVE_VERIFIED'
  | 'RETIRED_OKE_IP_BLOCKED'
  | 'NXDOMAIN_OR_UNREACHABLE'
  | 'HTTP_ERROR';

export interface ExternalSpineProbeReceipt {
  targetUrl: string;
  status: ExternalSpineProbeStatus;
  dnsResolvedIps: string[];
  retiredOkeIpDetected: boolean;
  httpStatus: number | null;
  latencyMs: number | null;
  errorDetail: string | null;
  probedAtUtc: string;
  receiptSha256: string;
}

export interface OmniflowLiveBusSnapshot {
  schemaVersion: 'meridian-omniflow-live-bus-v1';
  generatedAtUtc: string;
  totalPublished: number;
  fenceEpoch: number;
  connectedParticipantsCount: number;
  openClaimableCount: number;
  activeLeasedCount: number;
  verifiedCount: number;
  staleFenceRejectionsCount: number;
  selfVerifyBlockedCount: number;
  recoveredExpiredLeasesCount: number;
  admissionBoundaryRejectedCount: number;
  autoDecomposedLanesCount: number;
  participants: BusParticipant[];
  messages: OmniflowBusMessage[];
  externalSpineProbe: ExternalSpineProbeReceipt;
}

export const RETIRED_OKE_IP_DENYLIST: ReadonlySet<string> = new Set(['193.123.184.22']);
export const DEFAULT_EXTERNAL_SPINE_URL = 'https://estate-bus.mumchimp.com/health';
export const BUS_JOURNAL_RELATIVE_PATH = 'dist-exports/omniflow-live-bus.json';

interface PersistedBusJournal {
  fenceEpoch: number;
  nextSeq: number;
  staleFenceRejectionsCount: number;
  selfVerifyBlockedCount: number;
  recoveredExpiredLeasesCount: number;
  messages: OmniflowBusMessage[];
  externalSpineProbe: ExternalSpineProbeReceipt;
}

export class OmniflowLiveBusEngine {
  private participants: Map<string, BusParticipant> = new Map();
  private messages: OmniflowBusMessage[] = [];
  private byIdempotencyKey: Map<string, OmniflowBusMessage> = new Map();
  private subscribers: Set<(snapshot: OmniflowLiveBusSnapshot) => void> = new Set();
  private fenceEpoch = 500;
  private nextSeq = 1;
  private staleFenceRejectionsCount = 0;
  private selfVerifyBlockedCount = 0;
  private recoveredExpiredLeasesCount = 0;
  private admissionBoundaryRejectedCount = 0;
  private autoDecomposedLanesCount = 0;
  private journalPath: string | null;
  private externalSpineProbe: ExternalSpineProbeReceipt;

  constructor(options?: { repoRoot?: string; journalPath?: string | null }) {
    if (options?.journalPath === null) {
      this.journalPath = null;
    } else if (options?.journalPath) {
      this.journalPath = options.journalPath;
    } else if (options?.repoRoot) {
      this.journalPath = path.join(options.repoRoot, BUS_JOURNAL_RELATIVE_PATH);
    } else {
      this.journalPath = null;
    }

    this.externalSpineProbe = {
      targetUrl: DEFAULT_EXTERNAL_SPINE_URL,
      status: 'NOT_PROBED',
      dnsResolvedIps: [],
      retiredOkeIpDetected: false,
      httpStatus: null,
      latencyMs: null,
      errorDetail: 'Not probed in this process yet. Click Probe Live Endpoint to run real DNS + HTTP verification.',
      probedAtUtc: new Date().toISOString(),
      receiptSha256: pureSha256Hex(`not-probed:${DEFAULT_EXTERNAL_SPINE_URL}`),
    };

    const hydrated = this.loadJournal();
    if (!hydrated) {
      this.seedInitialRoomMessage();
    }
    this.ensureBaselineCockpitParticipant();
  }

  private ensureBaselineCockpitParticipant(): void {
    const nowMs = Date.now();
    const nowUtc = new Date(nowMs).toISOString();
    if (!this.participants.has('founder-genesis-cockpit')) {
      this.participants.set('founder-genesis-cockpit', {
        agentId: 'founder-genesis-cockpit',
        displayName: 'Genesis Founder Cockpit (Server Anchor)',
        surfaceClass: 'FOUNDER_COCKPIT',
        transport: 'SSE_HTTPS',
        capabilities: ['founder:approve', 'karma:inspect', 'dispatch:all'],
        formations: ['concierge', 'greenlane', 'council'],
        connected: true,
        joinedAtUtc: nowUtc,
        lastHeartbeatUtc: nowUtc,
        lastHeartbeatMs: nowMs,
        ttlMs: 3_600_000,
        activeLeasesCount: 0,
      });
    }
  }

  private seedInitialRoomMessage(): void {
    this.publishMessage({
      fromAgent: 'founder-genesis-cockpit',
      fromSurface: 'FOUNDER_COCKPIT',
      target: '@all',
      verb: 'STATUS',
      body:
        'OMNIFLOW live cross-surface room active. Console CLIs (`scripts/estate-bus-cli.mjs`), Web tabs, Mobile/WhatsApp adapters, and Cloud runners share one durable SSE + HTTPS custody stream.',
      correlationId: 'corr-omniflow-room-boot',
      idempotencyKey: 'idem-omniflow-room-boot-v1',
      requiresClaim: false,
    });
  }

  private loadJournal(): boolean {
    if (!this.journalPath || !fs.existsSync(this.journalPath)) {
      return false;
    }
    try {
      const raw = fs.readFileSync(this.journalPath, 'utf8');
      const parsed = JSON.parse(raw) as Partial<PersistedBusJournal>;
      if (!Array.isArray(parsed.messages)) return false;
      this.fenceEpoch = Number(parsed.fenceEpoch) || 500;
      this.nextSeq = Number(parsed.nextSeq) || parsed.messages.length + 1;
      this.staleFenceRejectionsCount = Number(parsed.staleFenceRejectionsCount) || 0;
      this.selfVerifyBlockedCount = Number(parsed.selfVerifyBlockedCount) || 0;
      this.recoveredExpiredLeasesCount = Number(parsed.recoveredExpiredLeasesCount) || 0;
      this.messages = parsed.messages.slice(0, 200);
      this.byIdempotencyKey.clear();
      for (const msg of this.messages) {
        this.byIdempotencyKey.set(msg.idempotencyKey, msg);
      }
      if (parsed.externalSpineProbe?.targetUrl) {
        this.externalSpineProbe = parsed.externalSpineProbe;
      }
      return this.messages.length > 0;
    } catch {
      return false;
    }
  }

  private saveJournal(): void {
    if (!this.journalPath) return;
    try {
      fs.mkdirSync(path.dirname(this.journalPath), { recursive: true });
      const payload: PersistedBusJournal = {
        fenceEpoch: this.fenceEpoch,
        nextSeq: this.nextSeq,
        staleFenceRejectionsCount: this.staleFenceRejectionsCount,
        selfVerifyBlockedCount: this.selfVerifyBlockedCount,
        recoveredExpiredLeasesCount: this.recoveredExpiredLeasesCount,
        messages: this.messages.slice(0, 200),
        externalSpineProbe: this.externalSpineProbe,
      };
      fs.writeFileSync(this.journalPath, JSON.stringify(payload, null, 2));
    } catch {
      // Non-fatal journal persistence error
    }
  }

  private emitSnapshot(): void {
    if (this.subscribers.size === 0) return;
    const snap = this.getSnapshot();
    for (const cb of this.subscribers) {
      try {
        cb(snap);
      } catch {
        // Isolate subscriber failure
      }
    }
  }

  public subscribe(listener: (snapshot: OmniflowLiveBusSnapshot) => void): () => void {
    this.subscribers.add(listener);
    return () => {
      this.subscribers.delete(listener);
    };
  }

  public registerParticipant(input: {
    agentId: string;
    displayName?: string;
    surfaceClass?: BusSurfaceClass;
    transport?: BusParticipant['transport'];
    capabilities?: string[];
    formations?: string[];
    ttlMs?: number;
    nowMs?: number;
  }): BusParticipant {
    const cleanId = input.agentId.trim().slice(0, 64);
    if (!cleanId) {
      throw new Error('agentId is required');
    }
    const nowMs = input.nowMs ?? Date.now();
    const nowUtc = new Date(nowMs).toISOString();
    const existing = this.participants.get(cleanId);
    const activeLeasesCount = this.messages.filter(
      (m) =>
        m.holderAgentId === cleanId &&
        (m.custodyStage === 'LEASED' || m.custodyStage === 'EXECUTING')
    ).length;

    const record: BusParticipant = {
      agentId: cleanId,
      displayName: (input.displayName ?? existing?.displayName ?? cleanId).trim().slice(0, 96),
      surfaceClass: input.surfaceClass ?? existing?.surfaceClass ?? 'CONSOLE_CLI',
      transport: input.transport ?? existing?.transport ?? 'CLI_BRIDGE',
      capabilities:
        input.capabilities && input.capabilities.length > 0
          ? input.capabilities.map((c) => c.trim()).filter(Boolean).slice(0, 12)
          : existing?.capabilities ?? ['general:assist'],
      formations:
        input.formations && input.formations.length > 0
          ? input.formations.map((f) => f.trim()).filter(Boolean).slice(0, 8)
          : existing?.formations ?? ['general'],
      connected: true,
      joinedAtUtc: existing?.joinedAtUtc ?? nowUtc,
      lastHeartbeatUtc: nowUtc,
      lastHeartbeatMs: nowMs,
      ttlMs: Math.max(5_000, Math.min(3_600_000, Number(input.ttlMs) || existing?.ttlMs || 60_000)),
      activeLeasesCount,
    };
    this.participants.set(cleanId, record);
    this.emitSnapshot();
    return record;
  }

  public heartbeatParticipant(agentId: string, nowMs = Date.now()): BusParticipant | null {
    const existing = this.participants.get(agentId.trim());
    if (!existing) return null;
    existing.connected = true;
    existing.lastHeartbeatMs = nowMs;
    existing.lastHeartbeatUtc = new Date(nowMs).toISOString();
    existing.activeLeasesCount = this.messages.filter(
      (m) =>
        m.holderAgentId === existing.agentId &&
        (m.custodyStage === 'LEASED' || m.custodyStage === 'EXECUTING')
    ).length;
    this.emitSnapshot();
    return existing;
  }

  public disconnectParticipant(agentId: string, nowMs = Date.now()): {
    disconnected: boolean;
    releasedEnvelopes: string[];
  } {
    const cleanId = agentId.trim();
    const existing = this.participants.get(cleanId);
    if (!existing) {
      return { disconnected: false, releasedEnvelopes: [] };
    }
    existing.connected = false;
    existing.activeLeasesCount = 0;

    const releasedEnvelopes: string[] = [];
    const nowUtc = new Date(nowMs).toISOString();
    for (const msg of this.messages) {
      if (
        msg.holderAgentId === cleanId &&
        (msg.custodyStage === 'LEASED' || msg.custodyStage === 'EXECUTING')
      ) {
        msg.custodyStage = 'LEASE_EXPIRED_RECOVERING';
        msg.holderAgentId = null;
        msg.recoveryCount += 1;
        msg.updatedAtUtc = nowUtc;
        releasedEnvelopes.push(msg.envelopeId);
        this.recoveredExpiredLeasesCount += 1;
      }
    }
    this.saveJournal();
    this.emitSnapshot();
    return { disconnected: true, releasedEnvelopes };
  }

  /**
   * Sweeps stale participants whose heartbeat exceeded TTL and requeues any held leases
   * so work is never stranded inside a terminated CLI/browser session.
   */
  public sweepExpiredParticipants(nowMs = Date.now()): {
    expiredAgentIds: string[];
    recoveredEnvelopeIds: string[];
  } {
    const expiredAgentIds: string[] = [];
    const recoveredEnvelopeIds: string[] = [];
    const nowUtc = new Date(nowMs).toISOString();

    for (const p of this.participants.values()) {
      if (p.agentId === 'founder-genesis-cockpit') continue;
      if (p.connected && nowMs - p.lastHeartbeatMs > p.ttlMs) {
        p.connected = false;
        p.activeLeasesCount = 0;
        expiredAgentIds.push(p.agentId);

        for (const msg of this.messages) {
          if (
            msg.holderAgentId === p.agentId &&
            (msg.custodyStage === 'LEASED' || msg.custodyStage === 'EXECUTING')
          ) {
            msg.custodyStage = 'LEASE_EXPIRED_RECOVERING';
            msg.holderAgentId = null;
            msg.recoveryCount += 1;
            msg.updatedAtUtc = nowUtc;
            recoveredEnvelopeIds.push(msg.envelopeId);
            this.recoveredExpiredLeasesCount += 1;
          }
        }
      }
    }

    if (expiredAgentIds.length > 0 || recoveredEnvelopeIds.length > 0) {
      this.saveJournal();
      this.emitSnapshot();
    }
    return { expiredAgentIds, recoveredEnvelopeIds };
  }

  public publishMessage(input: {
    fromAgent: string;
    fromSurface?: BusSurfaceClass;
    target?: string;
    verb?: OmniflowMessageVerb;
    body: string;
    artifactRef?: string | null;
    correlationId?: string;
    idempotencyKey?: string;
    requiresClaim?: boolean;
    proposedFiles?: string[];
    autoDecompose?: boolean;
  }): {
    ok: boolean;
    httpStatus: number;
    error?: string;
    deduplicated: boolean;
    message?: OmniflowBusMessage;
    decomposedMessages?: OmniflowBusMessage[];
    boundaryValidation?: BoundaryManifestValidation;
  } {
    const body = String(input.body ?? '').trim().slice(0, 2000);
    if (!body) {
      throw new Error('Message body is required');
    }
    const fromAgent = String(input.fromAgent ?? '').trim().slice(0, 64) || 'anonymous-surface';

    // RFCE #8188: Admit(P) => BoundaryValid(P) before dispatching or spending inference tokens
    let boundaryValidation: BoundaryManifestValidation | undefined;
    if (Array.isArray(input.proposedFiles) && input.proposedFiles.length > 0) {
      boundaryValidation = validateUnsealedChangeManifest(input.proposedFiles);
      if (!boundaryValidation.boundaryValid) {
        if (!input.autoDecompose) {
          this.admissionBoundaryRejectedCount += 1;
          this.saveJournal();
          this.emitSnapshot();
          return {
            ok: false,
            httpStatus: 422,
            error: `ADMISSION_BLOCKED_BOUNDARY_INVALID (${boundaryValidation.violationCodes.join(', ')}): ${boundaryValidation.summary}`,
            deduplicated: false,
            boundaryValidation,
          };
        }

        // Validate -> Decompose into compliant single-subsystem, <=5-file lanes!
        const childMessages: OmniflowBusMessage[] = [];
        for (const lane of boundaryValidation.decomposedLanes) {
          const laneIdem = input.idempotencyKey
            ? `${input.idempotencyKey}:lane-${lane.laneIndex}`
            : undefined;
          const child = this.publishMessage({
            ...input,
            body: `[${lane.laneId} · subsystem=${lane.subsystem} · files=${lane.fileCount}/5] ${body} (${lane.files.join(', ')})`,
            idempotencyKey: laneIdem,
            proposedFiles: lane.files,
            autoDecompose: false,
          });
          if (child.message) {
            childMessages.push(child.message);
          }
        }
        this.autoDecomposedLanesCount += childMessages.length;
        this.saveJournal();
        this.emitSnapshot();
        return {
          ok: true,
          httpStatus: 201,
          deduplicated: false,
          message: childMessages[0],
          decomposedMessages: childMessages,
          boundaryValidation,
        };
      }
    }

    const idemKey =
      (input.idempotencyKey ?? '').trim() ||
      `idem-${pureSha256Hex(`${fromAgent}|${input.target ?? '@all'}|${body}|${this.nextSeq}`).slice(0, 16)}`;

    const existing = this.byIdempotencyKey.get(idemKey);
    if (existing) {
      return {
        ok: true,
        httpStatus: 200,
        deduplicated: true,
        message: existing,
        boundaryValidation,
      };
    }

    const nowUtc = new Date().toISOString();
    const seq = this.nextSeq++;
    const envelopeId = `MSG-${String(seq).padStart(4, '0')}`;
    const target = (input.target ?? '@all').trim() || '@all';
    const verb: OmniflowMessageVerb = input.verb ?? 'ASK';
    const requiresClaim = Boolean(input.requiresClaim ?? (verb === 'ASK' || verb === 'OFFER'));
    const correlationId = (input.correlationId ?? '').trim() || `corr-${envelopeId.toLowerCase()}`;
    const fromSurface: BusSurfaceClass =
      input.fromSurface ??
      this.participants.get(fromAgent)?.surfaceClass ??
      'CONSOLE_CLI';

    // Auto-touch sender presence if connected
    const sender = this.participants.get(fromAgent);
    if (sender) {
      sender.connected = true;
      sender.lastHeartbeatMs = Date.now();
      sender.lastHeartbeatUtc = nowUtc;
    }

    const envelopeSha256 = pureSha256Hex(
      [seq, envelopeId, correlationId, idemKey, fromAgent, target, verb, body].join('|')
    );

    const record: OmniflowBusMessage = {
      seq,
      envelopeId,
      correlationId,
      idempotencyKey: idemKey,
      fromAgent,
      fromSurface,
      target,
      verb,
      body,
      artifactRef: input.artifactRef ? String(input.artifactRef).trim().slice(0, 240) : null,
      requiresClaim,
      custodyStage: requiresClaim ? 'DELIVERED' : 'PUBLISHED',
      holderAgentId: null,
      fencingToken: null,
      verifierId: null,
      verificationNote: null,
      verificationReceiptSha256: null,
      recoveryCount: 0,
      createdAtUtc: nowUtc,
      updatedAtUtc: nowUtc,
      envelopeSha256,
      ...(input.proposedFiles ? { proposedFiles: input.proposedFiles } : {}),
      ...(boundaryValidation ? { boundaryValidation } : {}),
    };

    this.messages.unshift(record);
    if (this.messages.length > 200) {
      const removed = this.messages.pop();
      if (removed) this.byIdempotencyKey.delete(removed.idempotencyKey);
    }
    this.byIdempotencyKey.set(idemKey, record);
    this.saveJournal();
    this.emitSnapshot();
    return {
      ok: true,
      httpStatus: 201,
      deduplicated: false,
      message: record,
      boundaryValidation,
    };
  }

  public claimLease(input: {
    envelopeId: string;
    workerId: string;
    expectedMinFence?: number;
  }): { httpStatus: number; ok: boolean; error?: string; message?: OmniflowBusMessage } {
    const msg = this.messages.find((m) => m.envelopeId === input.envelopeId.trim());
    if (!msg) {
      return { httpStatus: 404, ok: false, error: 'envelope_not_found' };
    }
    const workerId = input.workerId.trim();
    if (!workerId) {
      return { httpStatus: 400, ok: false, error: 'workerId_required' };
    }

    if (
      msg.fencingToken !== null &&
      input.expectedMinFence !== undefined &&
      input.expectedMinFence < msg.fencingToken
    ) {
      this.staleFenceRejectionsCount += 1;
      this.saveJournal();
      this.emitSnapshot();
      return {
        httpStatus: 409,
        ok: false,
        error: `stale_fencing_token: supplied f_${input.expectedMinFence} < current f_${msg.fencingToken}`,
      };
    }

    if (
      msg.custodyStage === 'LEASED' &&
      msg.holderAgentId &&
      msg.holderAgentId !== workerId
    ) {
      this.staleFenceRejectionsCount += 1;
      this.saveJournal();
      this.emitSnapshot();
      return {
        httpStatus: 409,
        ok: false,
        error: `already_leased_to_${msg.holderAgentId}_f_${msg.fencingToken}`,
      };
    }

    if (msg.custodyStage === 'VERIFIED_EFFECT') {
      return {
        httpStatus: 409,
        ok: false,
        error: 'envelope_already_verified',
      };
    }

    const prevHolder = msg.holderAgentId;
    this.fenceEpoch += 1;
    msg.fencingToken = this.fenceEpoch;
    msg.holderAgentId = workerId;
    msg.custodyStage = 'LEASED';
    msg.updatedAtUtc = new Date().toISOString();

    if (prevHolder && this.participants.has(prevHolder)) {
      const p = this.participants.get(prevHolder)!;
      p.activeLeasesCount = Math.max(0, p.activeLeasesCount - 1);
    }
    const holder = this.participants.get(workerId);
    if (holder) {
      holder.activeLeasesCount += 1;
      holder.connected = true;
      holder.lastHeartbeatMs = Date.now();
      holder.lastHeartbeatUtc = msg.updatedAtUtc;
    }

    this.saveJournal();
    this.emitSnapshot();
    return { httpStatus: 200, ok: true, message: msg };
  }

  public submitEffectWithFence(input: {
    envelopeId: string;
    workerId: string;
    fencingToken: number;
    artifactRef?: string;
    note?: string;
  }): { httpStatus: number; ok: boolean; error?: string; message?: OmniflowBusMessage } {
    const msg = this.messages.find((m) => m.envelopeId === input.envelopeId.trim());
    if (!msg) {
      return { httpStatus: 404, ok: false, error: 'envelope_not_found' };
    }
    if (
      msg.holderAgentId !== input.workerId.trim() ||
      msg.fencingToken === null ||
      input.fencingToken < msg.fencingToken
    ) {
      this.staleFenceRejectionsCount += 1;
      this.saveJournal();
      this.emitSnapshot();
      return {
        httpStatus: 409,
        ok: false,
        error: `stale_or_non_holder_write_rejected: current holder=${msg.holderAgentId ?? 'none'} fence=f_${msg.fencingToken ?? 0}`,
      };
    }

    msg.custodyStage = 'EXECUTING';
    if (input.artifactRef) msg.artifactRef = input.artifactRef.trim().slice(0, 240);
    if (input.note) msg.verificationNote = input.note.trim().slice(0, 300);
    msg.updatedAtUtc = new Date().toISOString();

    this.saveJournal();
    this.emitSnapshot();
    return { httpStatus: 200, ok: true, message: msg };
  }

  public verifyIndependently(input: {
    envelopeId: string;
    verifierId: string;
    evidenceNote: string;
  }): { httpStatus: number; ok: boolean; error?: string; message?: OmniflowBusMessage } {
    const msg = this.messages.find((m) => m.envelopeId === input.envelopeId.trim());
    if (!msg) {
      return { httpStatus: 404, ok: false, error: 'envelope_not_found' };
    }
    const verifierId = input.verifierId.trim();
    if (!verifierId) {
      return { httpStatus: 400, ok: false, error: 'verifierId_required' };
    }
    if (msg.holderAgentId && verifierId === msg.holderAgentId) {
      this.selfVerifyBlockedCount += 1;
      this.saveJournal();
      this.emitSnapshot();
      return {
        httpStatus: 403,
        ok: false,
        error: `self_certification_forbidden: ${verifierId} holds active lease f_${msg.fencingToken}`,
      };
    }

    const holder = msg.holderAgentId ? this.participants.get(msg.holderAgentId) : undefined;
    if (holder) {
      holder.activeLeasesCount = Math.max(0, holder.activeLeasesCount - 1);
    }

    msg.custodyStage = 'VERIFIED_EFFECT';
    msg.verifierId = verifierId;
    msg.verificationNote = input.evidenceNote.trim().slice(0, 300);
    msg.updatedAtUtc = new Date().toISOString();
    msg.verificationReceiptSha256 = pureSha256Hex(
      `${msg.envelopeId}|${msg.fencingToken ?? 0}|${verifierId}|${msg.verificationNote}|${msg.updatedAtUtc}`
    );

    this.saveJournal();
    this.emitSnapshot();
    return { httpStatus: 200, ok: true, message: msg };
  }

  /**
   * Real outside-in probe of an external OMNIFLOW bus endpoint (e.g., https://estate-bus.mumchimp.com/health).
   * Enforces defect/live-services-failed-while-declared-2026-11-16:
   *  - Rejects non-HTTPS / SSRF private URLs
   *  - Performs DNS lookup and blocks retired OKE IP `193.123.184.22`
   *  - Performs real HTTP GET probe and never fakes 200 on NXDOMAIN or 404
   */
  public async probeExternalSpine(
    rawUrl = DEFAULT_EXTERNAL_SPINE_URL,
    deps?: {
      lookupFn?: (hostname: string) => Promise<Array<{ address: string }>>;
      fetchFn?: typeof fetch;
    }
  ): Promise<ExternalSpineProbeReceipt> {
    const validated = validateIngestUrl(rawUrl);
    const nowUtc = new Date().toISOString();
    if (!validated.ok) {
      this.externalSpineProbe = {
        targetUrl: rawUrl,
        status: 'HTTP_ERROR',
        dnsResolvedIps: [],
        retiredOkeIpDetected: false,
        httpStatus: null,
        latencyMs: null,
        errorDetail: validated.error,
        probedAtUtc: nowUtc,
        receiptSha256: pureSha256Hex(`invalid:${rawUrl}:${validated.error}:${nowUtc}`),
      };
      this.saveJournal();
      this.emitSnapshot();
      return this.externalSpineProbe;
    }

    const parsedUrl = validated.url;
    const targetUrl = parsedUrl.toString();
    const lookupFn =
      deps?.lookupFn ?? ((host: string) => dns.lookup(host, { all: true }));
    const fetchFn = deps?.fetchFn ?? fetch;

    let ips: string[] = [];
    try {
      const records = await lookupFn(parsedUrl.hostname);
      ips = records.map((r) => r.address);
    } catch (err) {
      this.externalSpineProbe = {
        targetUrl,
        status: 'NXDOMAIN_OR_UNREACHABLE',
        dnsResolvedIps: [],
        retiredOkeIpDetected: false,
        httpStatus: null,
        latencyMs: null,
        errorDetail: `DNS resolution failed (${parsedUrl.hostname}): ${err instanceof Error ? err.message : 'ENOTFOUND'}`,
        probedAtUtc: nowUtc,
        receiptSha256: pureSha256Hex(`nxdomain:${targetUrl}:${nowUtc}`),
      };
      this.saveJournal();
      this.emitSnapshot();
      return this.externalSpineProbe;
    }

    const retiredFound = ips.some((ip) => RETIRED_OKE_IP_DENYLIST.has(ip));
    if (retiredFound) {
      this.externalSpineProbe = {
        targetUrl,
        status: 'RETIRED_OKE_IP_BLOCKED',
        dnsResolvedIps: ips,
        retiredOkeIpDetected: true,
        httpStatus: null,
        latencyMs: null,
        errorDetail: `DNS resolves to retired OKE IP (${ips.join(', ')}) blocked by defect/live-services-failed-while-declared-2026-11-16`,
        probedAtUtc: nowUtc,
        receiptSha256: pureSha256Hex(`retired-oke:${targetUrl}:${ips.join(',')}:${nowUtc}`),
      };
      this.saveJournal();
      this.emitSnapshot();
      return this.externalSpineProbe;
    }

    const t0 = Date.now();
    try {
      const res = await fetchFn(targetUrl, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      const latencyMs = Date.now() - t0;
      const status: ExternalSpineProbeStatus = res.ok ? 'LIVE_VERIFIED' : 'HTTP_ERROR';
      this.externalSpineProbe = {
        targetUrl,
        status,
        dnsResolvedIps: ips,
        retiredOkeIpDetected: false,
        httpStatus: res.status,
        latencyMs,
        errorDetail: res.ok
          ? null
          : `HTTP ${res.status} returned from live probe (${targetUrl})`,
        probedAtUtc: new Date().toISOString(),
        receiptSha256: pureSha256Hex(
          `probe:${targetUrl}:${res.status}:${ips.join(',')}:${latencyMs}`
        ),
      };
    } catch (err) {
      this.externalSpineProbe = {
        targetUrl,
        status: 'NXDOMAIN_OR_UNREACHABLE',
        dnsResolvedIps: ips,
        retiredOkeIpDetected: false,
        httpStatus: null,
        latencyMs: Date.now() - t0,
        errorDetail: err instanceof Error ? err.message : 'External HTTP probe failed',
        probedAtUtc: new Date().toISOString(),
        receiptSha256: pureSha256Hex(`fetch-fail:${targetUrl}:${nowUtc}`),
      };
    }

    this.saveJournal();
    this.emitSnapshot();
    return this.externalSpineProbe;
  }

  public getSnapshot(): OmniflowLiveBusSnapshot {
    const participants = Array.from(this.participants.values()).sort((a, b) => {
      if (a.connected !== b.connected) return a.connected ? -1 : 1;
      return b.lastHeartbeatMs - a.lastHeartbeatMs;
    });
    return {
      schemaVersion: 'meridian-omniflow-live-bus-v1',
      generatedAtUtc: new Date().toISOString(),
      totalPublished: this.nextSeq - 1,
      fenceEpoch: this.fenceEpoch,
      connectedParticipantsCount: participants.filter((p) => p.connected).length,
      openClaimableCount: this.messages.filter(
        (m) =>
          m.requiresClaim &&
          (m.custodyStage === 'DELIVERED' || m.custodyStage === 'LEASE_EXPIRED_RECOVERING')
      ).length,
      activeLeasedCount: this.messages.filter(
        (m) => m.custodyStage === 'LEASED' || m.custodyStage === 'EXECUTING'
      ).length,
      verifiedCount: this.messages.filter((m) => m.custodyStage === 'VERIFIED_EFFECT').length,
      staleFenceRejectionsCount: this.staleFenceRejectionsCount,
      selfVerifyBlockedCount: this.selfVerifyBlockedCount,
      recoveredExpiredLeasesCount: this.recoveredExpiredLeasesCount,
      admissionBoundaryRejectedCount: this.admissionBoundaryRejectedCount,
      autoDecomposedLanesCount: this.autoDecomposedLanesCount,
      participants,
      messages: [...this.messages],
      externalSpineProbe: { ...this.externalSpineProbe },
    };
  }
}
