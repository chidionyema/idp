import type { EvidenceClass, FormationId } from './estateRules.ts';

// ============================================================================
// 1. PROJECT OPTIMUS — Root Release Admission & Signed Evidence Engine
//    Implements exact rules from chidionyema/idp `bin/idp-optimus-founder-admission`
//    (`estate-operational-proof.v1`) + deterministic per-surface signal thresholds.
// ============================================================================

export const OPTIMUS_PROOF_SCHEMA = 'estate-operational-proof.v1';
export const OPTIMUS_MAX_AGE_SECONDS = 600;
export const DEFAULT_OPTIMUS_APP_ID = 11;
export const DEFAULT_FOUNDER_SURFACE_APP_ID = 22;

export interface OptimusInstructionLinkage {
  instruction_id: string;
  permission: 'allowed' | 'refused' | string;
  permission_receipt: string;
  yield_tracking: 'pending' | 'verified' | 'failed' | string;
}

export interface OptimusCheckRunPayload {
  schema: string;
  subject_sha: string;
  observed_at: string;
  instructions: OptimusInstructionLinkage[];
  metrics?: {
    required_events: number;
    observed_events: number;
    dropped_events: number;
  };
  founder_surface?: {
    live: boolean;
    instructions_visible: boolean;
    permission_visible: boolean;
    yield_tracking_visible: boolean;
    event_cursor: string;
    url: string;
  };
}

export interface OptimusCheckRunEnvelope {
  id: number;
  name: string;
  head_sha: string;
  status: 'completed' | 'in_progress' | 'queued' | string;
  conclusion: 'success' | 'failure' | 'neutral' | null;
  completed_at: string;
  app: { id: number; slug?: string };
  output: { text: string };
}

export interface OptimusAdmissionInput {
  subjectSha: string;
  nowIso: string;
  totalCount?: number | null;
  checkRuns: OptimusCheckRunEnvelope[];
  optimusAppId?: number;
  founderAppId?: number;
}

export type OptimusAdmissionResult =
  | {
      admitted: true;
      state: 'ADMITTED_TO_GREENLANE_CI_NOT_YIELD';
      subjectSha: string;
      instructionCount: number;
      eventCursor: string;
      observedEvents: number;
      ageSeconds: number;
      governanceNote: string;
    }
  | {
      admitted: false;
      state: 'REFUSED_ADMISSION';
      errorCode:
        | 'MISSING_CHECK_RUN_COUNT'
        | 'INVALID_SUBJECT_SHA'
        | 'ABSENT_OPTIMUS_OR_FOUNDER_RECEIPT'
        | 'UNTRUSTED_ISSUER_OR_SHA_MISMATCH'
        | 'STALE_OR_FUTURE_RECEIPT'
        | 'MALFORMED_INSTRUCTION_LINKAGE'
        | 'DROPPED_OR_INCOMPLETE_METRICS'
        | 'FOUNDER_SURFACE_INVISIBLE';
      reason: string;
    };

const HEX_40_RE = /^[0-9a-f]{40}$/i;
const SAFE_ID_RE = /^[A-Za-z0-9._:/#-]{3,160}$/;

function parseIsoUtcMs(iso: string): number | null {
  if (typeof iso !== 'string' || !iso.trim()) return null;
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(iso.trim())) return null;
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? ms : null;
}

function validateInstructionEntries(
  entries: unknown
): { ok: true; map: Map<string, { receipt: string; state: string }> } | { ok: false; reason: string } {
  if (!Array.isArray(entries) || entries.length === 0) {
    return { ok: false, reason: 'Empty instruction/permission/yield linkage array.' };
  }
  const map = new Map<string, { receipt: string; state: string }>();
  for (const item of entries) {
    if (!item || typeof item !== 'object') {
      return { ok: false, reason: 'Malformed instruction linkage entry.' };
    }
    const e = item as Partial<OptimusInstructionLinkage>;
    if (!e.instruction_id || !SAFE_ID_RE.test(e.instruction_id)) {
      return { ok: false, reason: 'Missing or invalid instruction_id in Optimus receipt.' };
    }
    if (!e.permission_receipt || !SAFE_ID_RE.test(e.permission_receipt)) {
      return { ok: false, reason: `Instruction ${e.instruction_id} missing valid permission_receipt.` };
    }
    if (e.permission !== 'allowed') {
      return { ok: false, reason: `Release lacks permitted instruction (${e.instruction_id} permission=${String(e.permission)}).` };
    }
    if (!e.yield_tracking || !['pending', 'verified', 'failed'].includes(e.yield_tracking)) {
      return { ok: false, reason: `Instruction ${e.instruction_id} yield_tracking is not tracked.` };
    }
    if (map.has(e.instruction_id)) {
      return { ok: false, reason: `Duplicate instruction_id ${e.instruction_id} in receipt.` };
    }
    map.set(e.instruction_id, { receipt: e.permission_receipt, state: e.yield_tracking });
  }
  return { ok: true, map };
}

export function evaluateOptimusReleaseAdmission(input: OptimusAdmissionInput): OptimusAdmissionResult {
  // Rule from lane/founder-optimus-root-release-lock-20261110: missing check-run count must fail admission
  if (typeof input.totalCount !== 'number' || !Number.isFinite(input.totalCount) || input.totalCount < input.checkRuns.length) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'MISSING_CHECK_RUN_COUNT',
      reason: 'GitHub API check-run total_count is missing or inconsistent; refusing admission on incomplete observability.',
    };
  }

  if (!HEX_40_RE.test(input.subjectSha)) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'INVALID_SUBJECT_SHA',
      reason: `Subject SHA "${input.subjectSha}" must be an exact 40-character hexadecimal commit digest.`,
    };
  }

  const nowMs = parseIsoUtcMs(input.nowIso);
  if (nowMs === null) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'STALE_OR_FUTURE_RECEIPT',
      reason: 'Evaluation reference clock is missing UTC timezone offset.',
    };
  }

  const optimusAppId = input.optimusAppId ?? DEFAULT_OPTIMUS_APP_ID;
  const founderAppId = input.founderAppId ?? DEFAULT_FOUNDER_SURFACE_APP_ID;

  const optimusRun = input.checkRuns.find((r) => r.name === 'optimus-metrics');
  const founderRun = input.checkRuns.find((r) => r.name === 'founder-surface-visibility');

  if (!optimusRun || !founderRun) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'ABSENT_OPTIMUS_OR_FOUNDER_RECEIPT',
      reason: 'Absent optimus-metrics or founder-surface-visibility root receipt; no green from absence.',
    };
  }

  for (const [run, expectedAppId] of [
    [optimusRun, optimusAppId],
    [founderRun, founderAppId],
  ] as const) {
    if (
      run.app?.id !== expectedAppId ||
      run.head_sha.toLowerCase() !== input.subjectSha.toLowerCase() ||
      run.status !== 'completed' ||
      run.conclusion !== 'success'
    ) {
      return {
        admitted: false,
        state: 'REFUSED_ADMISSION',
        errorCode: 'UNTRUSTED_ISSUER_OR_SHA_MISMATCH',
        reason: `Check "${run.name}" failed app trust (got app ${run.app?.id}, expected ${expectedAppId}), head_sha match, or success conclusion.`,
      };
    }
  }

  let optPayload: OptimusCheckRunPayload;
  let fndPayload: OptimusCheckRunPayload;
  try {
    optPayload = JSON.parse(optimusRun.output.text) as OptimusCheckRunPayload;
    fndPayload = JSON.parse(founderRun.output.text) as OptimusCheckRunPayload;
  } catch {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'MALFORMED_INSTRUCTION_LINKAGE',
      reason: 'Check-run output payload is not valid structured JSON.',
    };
  }

  if (optPayload.schema !== OPTIMUS_PROOF_SCHEMA || fndPayload.schema !== OPTIMUS_PROOF_SCHEMA) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'MALFORMED_INSTRUCTION_LINKAGE',
      reason: `Receipt schema mismatch; expected ${OPTIMUS_PROOF_SCHEMA}.`,
    };
  }

  if (
    optPayload.subject_sha.toLowerCase() !== input.subjectSha.toLowerCase() ||
    fndPayload.subject_sha.toLowerCase() !== input.subjectSha.toLowerCase()
  ) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'UNTRUSTED_ISSUER_OR_SHA_MISMATCH',
      reason: 'Signed payload subject_sha does not match check-run head_sha.',
    };
  }

  const optTs = parseIsoUtcMs(optPayload.observed_at);
  const fndTs = parseIsoUtcMs(fndPayload.observed_at);
  if (optTs === null || fndTs === null) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'STALE_OR_FUTURE_RECEIPT',
      reason: 'Receipt observed_at timestamp missing timezone or malformed.',
    };
  }

  const optAgeSec = (nowMs - optTs) / 1000;
  const fndAgeSec = (nowMs - fndTs) / 1000;
  if (
    optAgeSec < -30 ||
    optAgeSec > OPTIMUS_MAX_AGE_SECONDS ||
    fndAgeSec < -30 ||
    fndAgeSec > OPTIMUS_MAX_AGE_SECONDS
  ) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'STALE_OR_FUTURE_RECEIPT',
      reason: `Receipt freshness outside [-30s, ${OPTIMUS_MAX_AGE_SECONDS}s] window (optimus=${Math.round(optAgeSec)}s, founder=${Math.round(fndAgeSec)}s).`,
    };
  }

  const optEntries = validateInstructionEntries(optPayload.instructions);
  if (!optEntries.ok) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'MALFORMED_INSTRUCTION_LINKAGE',
      reason: optEntries.reason,
    };
  }
  const fndEntries = validateInstructionEntries(fndPayload.instructions);
  if (!fndEntries.ok) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'MALFORMED_INSTRUCTION_LINKAGE',
      reason: fndEntries.reason,
    };
  }

  // Correlate exact instruction linkage across both independent apps
  if (optEntries.map.size !== fndEntries.map.size) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'MALFORMED_INSTRUCTION_LINKAGE',
      reason: 'Instruction count mismatch between Optimus and Founder Surface receipts.',
    };
  }
  for (const [instId, optVal] of optEntries.map.entries()) {
    const fndVal = fndEntries.map.get(instId);
    if (!fndVal || fndVal.receipt !== optVal.receipt || fndVal.state !== optVal.state) {
      return {
        admitted: false,
        state: 'REFUSED_ADMISSION',
        errorCode: 'MALFORMED_INSTRUCTION_LINKAGE',
        reason: `Cross-receipt correlation mismatch on instruction ${instId}.`,
      };
    }
  }

  const m = optPayload.metrics;
  if (
    !m ||
    typeof m.required_events !== 'number' ||
    typeof m.observed_events !== 'number' ||
    typeof m.dropped_events !== 'number' ||
    m.required_events < 1 ||
    m.observed_events < m.required_events ||
    m.dropped_events > 0
  ) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'DROPPED_OR_INCOMPLETE_METRICS',
      reason: `Optimus telemetry incomplete or dropped events detected (required=${m?.required_events ?? 0}, observed=${m?.observed_events ?? 0}, dropped=${m?.dropped_events ?? -1}).`,
    };
  }

  const fs = fndPayload.founder_surface;
  if (
    !fs ||
    !fs.live ||
    !fs.instructions_visible ||
    !fs.permission_visible ||
    !fs.yield_tracking_visible ||
    !fs.event_cursor ||
    !fs.url
  ) {
    return {
      admitted: false,
      state: 'REFUSED_ADMISSION',
      errorCode: 'FOUNDER_SURFACE_INVISIBLE',
      reason: 'Founder Surface visibility receipt indicates instructions, permissions, or yield tracking are not live/visible.',
    };
  }

  return {
    admitted: true,
    state: 'ADMITTED_TO_GREENLANE_CI_NOT_YIELD',
    subjectSha: input.subjectSha,
    instructionCount: optEntries.map.size,
    eventCursor: fs.event_cursor,
    observedEvents: m.observed_events,
    ageSeconds: Math.round(Math.max(optAgeSec, fndAgeSec)),
    governanceNote:
      'Dual-root receipts correlated on exact SHA. Per Optimus law: admission permits Greenlane CI progression only — downstream deployment & live falsifier required for OPERATING yield.',
  };
}

// --- Optimus Signed Observation & Deterministic Signal Thresholds ---

export interface OptimusEvidenceRecord {
  seq: number;
  eventId: string;
  observedAt: string;
  surface: string;
  kind: 'SURFACE_PROBE' | 'GIT_LINEAGE' | 'LEGION_EXECUTION' | 'WATCHDOG_FENCE' | 'ADMISSION_AUDIT';
  subjectSha: string | null;
  instructionId: string | null;
  authority: EvidenceClass;
  metrics: {
    latencyMs: number;
    memoryRssMb: number;
    httpStatus: number | null;
    droppedEvents: number;
  };
  hmacSha256: string;
  verified: boolean;
  summary: string;
}

export interface OptimusDeterministicSignal {
  signalId: string;
  severity: 'WARNING' | 'CAUTION';
  surface: string;
  metric: string;
  measuredValue: string;
  threshold: string;
  remediation: string;
}

export function deriveOptimusSignals(records: readonly OptimusEvidenceRecord[]): OptimusDeterministicSignal[] {
  const signals: OptimusDeterministicSignal[] = [];
  const seenKey = new Set<string>();

  // Check sequence continuity for stream gaps
  const sorted = [...records].sort((a, b) => a.seq - b.seq);
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i].seq !== sorted[i - 1].seq + 1) {
      signals.push({
        signalId: `sig-gap-${sorted[i - 1].seq}-${sorted[i].seq}`,
        severity: 'WARNING',
        surface: 'optimus-stream',
        metric: 'sequence_continuity',
        measuredValue: `gap ${sorted[i - 1].seq}..${sorted[i].seq}`,
        threshold: 'monotonic +1',
        remediation: 'Reconcile authoritative ledger snapshot with live ingestion stream.',
      });
    }
  }

  for (const r of records) {
    if (!r.verified && !seenKey.has(`unverified-${r.surface}`)) {
      seenKey.add(`unverified-${r.surface}`);
      signals.push({
        signalId: `sig-hmac-${r.eventId}`,
        severity: 'WARNING',
        surface: r.surface,
        metric: 'hmac_signature',
        measuredValue: 'invalid_digest',
        threshold: 'HMAC-SHA256 match',
        remediation: 'Reject tampered observation row and rotate ESTATE_RECEIPT_KEY.',
      });
    }

    if (r.metrics.latencyMs > 1800 && !seenKey.has(`lat-${r.surface}`)) {
      seenKey.add(`lat-${r.surface}`);
      signals.push({
        signalId: `sig-lat-${r.eventId}`,
        severity: 'CAUTION',
        surface: r.surface,
        metric: 'latency_ms',
        measuredValue: `${r.metrics.latencyMs.toFixed(1)} ms`,
        threshold: '<= 1800.0 ms',
        remediation: 'Inspect upstream edge cold-start or bounded timeout budget on target surface.',
      });
    }

    if (r.metrics.memoryRssMb > 512 && !seenKey.has('rss-process')) {
      seenKey.add('rss-process');
      signals.push({
        signalId: `sig-rss-${r.eventId}`,
        severity: 'CAUTION',
        surface: r.surface,
        metric: 'memory_rss_mb',
        measuredValue: `${r.metrics.memoryRssMb.toFixed(1)} MB`,
        threshold: '<= 512.0 MB',
        remediation: 'Trim retained ledger caches or unbounded worker buffers.',
      });
    }
  }

  return signals;
}

// ============================================================================
// 2. FLEET REACTOR 2100 PHYSICS (Adapted from chidionyema/idp `reactor.ts`)
//    - gravity: sqrt-compressed spatial field warping (NaN-safe)
//    - motion honesty: thinking breathes, waiting drifts, stuck jitters, finished settles
//    - jets: frame-rate-independent particle integration (`0.94^(dt/16.7)`)
// ============================================================================

export type ReactorActivity = 'thinking' | 'waiting' | 'stuck' | 'finished';

export interface ReactorNodeDatum {
  id: string;
  label: string;
  category: 'CORE' | 'LEGION' | 'REPO' | 'INCIDENT' | 'FLOW' | 'SURFACE';
  activity: ReactorActivity;
  authority: EvidenceClass;
  eventCount: number;
  workload: number; // 0..100
  shaOrPointer: string;
  detail: string;
  actionTab: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'legion' | 'flow' | 'greenlane' | 'chronos';
  formation?: FormationId;
  repo?: string;
  instructionId?: string;
  position: [number, number, number];
  connections: string[];
}

export interface JetParticle3D {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  life: number; // 1.0 -> 0.0
  ownerId: string;
  activity: ReactorActivity;
}

/**
 * Sqrt-compressed gravity field so one high-frequency node warps local space
 * without collapsing the other 23 estate nodes into a single singularity.
 * Explicitly NaN-safe per `reactor.ts`.
 */
export function gravityOf(eventCount: unknown, workload: unknown = 0): number {
  const safeEvents = Math.max(0, Number(eventCount) || 0);
  const safeLoad = Math.max(0, Math.min(100, Number(workload) || 0));
  const raw = Math.sqrt(safeEvents) * 0.18 + Math.sqrt(safeLoad) * 0.11;
  return Math.min(2.4, Math.round(raw * 1000) / 1000);
}

/**
 * Motion honesty law:
 * - thinking breathes (smooth harmonic scale + gentle Y levitation)
 * - waiting drifts (slow orbital sway)
 * - stuck jitters (high-frequency bounded tremor — never looks like thinking!)
 * - finished settles (calm downward anchor, steady scale)
 */
export function computeMotionHonesty(
  activity: ReactorActivity,
  timeSec: number,
  seed: number
): { dx: number; dy: number; dz: number; scaleMultiplier: number } {
  const t = Number(timeSec) || 0;
  const s = Number(seed) || 0;

  switch (activity) {
    case 'thinking': {
      const breath = Math.sin(t * 2.6 + s) * 0.12;
      return {
        dx: Math.cos(t * 0.7 + s) * 0.18,
        dy: Math.sin(t * 1.3 + s) * 0.35,
        dz: Math.sin(t * 0.6 + s) * 0.18,
        scaleMultiplier: 1 + breath,
      };
    }
    case 'waiting': {
      return {
        dx: Math.cos(t * 0.45 + s) * 0.55,
        dy: Math.sin(t * 0.55 + s * 1.3) * 0.28,
        dz: Math.sin(t * 0.45 + s) * 0.55,
        scaleMultiplier: 1 + Math.sin(t * 1.1 + s) * 0.03,
      };
    }
    case 'stuck': {
      // Deterministic multi-harmonic micro-tremor so blocked states are unmistakable
      const jx = Math.sin(t * 29.0 + s * 3.1) * 0.26 + Math.cos(t * 43.0 + s) * 0.14;
      const jy = Math.cos(t * 33.0 + s * 2.3) * 0.22;
      const jz = Math.sin(t * 37.0 + s * 1.7) * 0.24;
      return {
        dx: jx,
        dy: jy,
        dz: jz,
        scaleMultiplier: 1 + Math.sin(t * 19.0 + s) * 0.05,
      };
    }
    case 'finished':
    default: {
      return {
        dx: 0,
        dy: -0.45 + Math.sin(t * 0.35 + s) * 0.06,
        dz: 0,
        scaleMultiplier: 0.96,
      };
    }
  }
}

export function fireJetParticles3D(
  out: JetParticle3D[],
  origin: [number, number, number],
  ownerId: string,
  activity: ReactorActivity,
  count: number = 14,
  seed: number = 1
): void {
  const n = Math.max(1, Math.min(48, Math.floor(count)));
  const speedFactor = activity === 'stuck' ? 0.38 : 1.0;

  for (let i = 0; i < n; i++) {
    const theta = (((seed + i * 97) % 360) * Math.PI) / 180;
    const phi = Math.acos(1 - (2 * ((i + 0.5) / n)));
    const speed = (9 + ((seed + i * 13) % 14)) * speedFactor;

    out.push({
      x: origin[0],
      y: origin[1],
      z: origin[2],
      vx: Math.sin(phi) * Math.cos(theta) * speed,
      vy: Math.cos(phi) * speed * 0.75,
      vz: Math.sin(phi) * Math.sin(theta) * speed,
      life: 1.0,
      ownerId,
      activity,
    });
  }
}

/**
 * Frame-rate-independent particle integration (`dtMs` normalized to 16.7ms 60fps frame).
 */
export function stepJetParticles3D(particles: JetParticle3D[], dtMs: number): void {
  const clampedDtMs = Math.max(0, Math.min(200, Number(dtMs) || 0));
  const dtSec = clampedDtMs / 1000;
  const drag = Math.pow(0.94, clampedDtMs / 16.7);

  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx * dtSec;
    p.y += p.vy * dtSec;
    p.z += p.vz * dtSec;
    p.vx *= drag;
    p.vy *= drag;
    p.vz *= drag;
    p.life -= dtSec * 0.72;
    if (p.life <= 0) {
      particles.splice(i, 1);
    }
  }
}

// ============================================================================
// 3. VOICE 2100 — Speculative Intent Compiler & 0.90 Clarification Handshake
//    (`docs/specs/2026-09-22-voice-2100-architecture.md`)
// ============================================================================

export const VOICE_2100_CONFIDENCE_FLOOR = 0.9;

export interface Voice2100CandidateAction {
  label: string;
  utterance: string;
  targetNodeId: string;
  actionKind:
    | 'EXECUTE_LEGION'
    | 'INGEST_OPTIMUS'
    | 'SWEEP_WATCHDOG'
    | 'INSPECT_NODE'
    | 'REPROBE_ESTATE'
    | 'PLAY_BRIEFING'
    | 'TRIGGER_BLAST'
    | 'NAVIGATE_TAB'
    | 'SYNC_ARGON';
  targetTab?: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'fleet' | 'legion' | 'flow' | 'greenlane' | 'chronos';
  formation?: FormationId;
  repo?: string;
}

export interface Voice2100ClarifyRow {
  subject: string; // estate.agent.sovereign.<session>.steer
  kind: 'clarify';
  sessionId: string;
  question: string;
  candidateActions: Voice2100CandidateAction[];
}

export type Voice2100SpeculateResult =
  | {
      ok: true;
      schema: 'voice-intent.v2';
      utteranceLength: number;
      intent: string;
      targetNodeId: string;
      actionKind: Voice2100CandidateAction['actionKind'];
      targetTab?: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'fleet' | 'legion' | 'flow' | 'greenlane' | 'chronos';
      formation: FormationId;
      repo: string;
      confidence: number;
      clarificationNeeded: boolean;
      clarifyRow: Voice2100ClarifyRow | null;
      summary: string;
    }
  | {
      ok: false;
      httpStatus: 400 | 502;
      errorCode: 'EMPTY_UTTERANCE' | 'SCHEMA_V2_ARMOR_TRIPPED';
      message: string;
    };

const ROGUE_INJECTION_PATTERNS = /(__proto__|constructor\s*:|ignore\s+previous\s+instructions|<script\b|system_override)/i;

export function compileVoice2100SpeculativeIntent(
  rawTranscript: unknown,
  sessionId: string = 'founder-sovereign-01'
): Voice2100SpeculateResult {
  if (typeof rawTranscript !== 'string' || rawTranscript.trim().length < 2) {
    return {
      ok: false,
      httpStatus: 400,
      errorCode: 'EMPTY_UTTERANCE',
      message: 'Transcript requires at least 2 non-whitespace characters.',
    };
  }

  const cleanSession = SAFE_ID_RE.test(sessionId) ? sessionId : 'founder-sovereign-01';

  // Schema v2 armor: reject prompt-injection / prototype pollution without echoing the rogue payload!
  if (ROGUE_INJECTION_PATTERNS.test(rawTranscript)) {
    return {
      ok: false,
      httpStatus: 502,
      errorCode: 'SCHEMA_V2_ARMOR_TRIPPED',
      message: 'Candidate rejected at Schema v2 boundary (untrusted directive token); rogue payload suppressed.',
    };
  }

  const text = rawTranscript.trim();
  const lower = text.toLowerCase();
  const steerSubject = `estate.agent.sovereign.${cleanSession}.steer`;

  // High-confidence (>= 0.90) deterministic sovereign intent patterns
  if (
    /\b(sync\s+(?:everything\s+)?to\s+argon|argon\s+sync|push\s+(?:lane\s+)?to\s+argon|sync\s+argon|synchronize\s+argon)\b/.test(
      lower
    )
  ) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'sync_estate_to_argon_lane',
      targetNodeId: 'REPO-ARGON',
      actionKind: 'SYNC_ARGON',
      targetTab: 'flow',
      formation: 'centurion',
      repo: 'chidionyema/argon',
      confidence: 0.97,
      clarificationNeeded: false,
      clarifyRow: null,
      summary:
        'Locked Argon Continuity Sync → Hash source + .ops/register.jsonl Merkle root & sync onto lane/aistudio-genesis-2100-sync.',
    };
  }

  if (
    /\b(beast|rego|policy\s+dials?|dynamic\s+dials?|bitwarden|free\s+lanes?|dreams?\s+cycle|continuous\s+integration|fractal\s+proof|incident\s+wake[_\s-]?up)\b/.test(
      lower
    )
  ) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_beast_governor',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'beast',
      formation: 'centurion',
      repo: 'chidionyema/argon',
      confidence: 0.99,
      clarificationNeeded: false,
      clarifyRow: null,
      summary:
        'Locked THE BEAST → Open 6-Layer Fractal Continuous Proof, Rego Policy Dials, Bitwarden/Free-Lane Resources, Dreams & Sub-ms Incident Wake-Up.',
    };
  }

  if (
    /\b(catalog|brochure|product\s+menu|investor|mini[_\s-]?nasa|heartbeat|headlines?|forex|synchrony|persona)\b/.test(
      lower
    )
  ) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_synchrony_catalog',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'catalog',
      formation: 'centurion',
      repo: 'chidionyema/argon',
      confidence: 0.99,
      clarificationNeeded: false,
      clarifyRow: null,
      summary:
        'Locked CATALOG & SYNCHRONY → Open 4-Persona Product Menu (10->7->5->3), Living Brochure, Tempo-Chronos Heartbeat & Omni-Node Mapper.',
    };
  }

  if (
    /\b(omega|omega\s+core|universal\s+kernel|robotics|humanoid|drone|smart\s+glasses|hal\s+transducer|multi[_\s-]?surface)\b/.test(
      lower
    )
  ) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_omega_universal_core',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'omega',
      formation: 'centurion',
      repo: 'chidionyema/argon',
      confidence: 0.99,
      clarificationNeeded: false,
      clarifyRow: null,
      summary:
        'Locked Codename OMEGA → Open Ring-0 Universal Kernel, 7+N Hardware Embodiments, 4KB Capsule Teleport & Robotics Safety Gate.',
    };
  }

  if (
    /\b(io\s+engine|mega[_\s-]?oracle|oracle[_\s-]?00|work\s+graph|15\s+packs?|32\s+stashes|92\s+branches|persistent\s+owner(?:ship)?|real[_\s-]?name\s+identity|mandatory\s+eval|forced\s+training)\b/.test(
      lower
    )
  ) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_io_canonical_work_graph',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'io',
      formation: 'centurion',
      repo: 'chidionyema/argon',
      confidence: 0.98,
      clarificationNeeded: false,
      clarifyRow: null,
      summary:
        'Locked Canonical PACK-15 IO Engine → Open Single Work Graph, Real-Name Ownership & Forced Real-Time Eval/Training.',
    };
  }

  if (
    /\b(synapse|stigmerg(?:y|ic)|genesis[_\s-]?spore|antibody|antibodies|dual[_\s-]?yield|reassign(?:ment)?|mac\s+offline|handoff\s+ack)\b/.test(
      lower
    )
  ) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_stigmergic_swarm_synapse',
      targetNodeId: 'REPO-SYNC',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'synapse',
      formation: 'centurion',
      repo: 'chidionyema/idp',
      confidence: 0.97,
      clarificationNeeded: false,
      clarifyRow: null,
      summary:
        'Locked Swarm Synapse v0.7.0-RT → Open Pass-0 Antibodies, 4KB GENESIS_SPORE.dna & Mac-Offline Reassignment Proof.',
    };
  }

  if (/\b(projector|face\s+and\s+fleet|register\s+movie|isometric\s+world|virtual\s+world|3327|reconcile\s+register)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_face_and_fleet_projector',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'projector',
      formation: 'sniper',
      repo: 'chidionyema/idp',
      confidence: 0.96,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked Register Projector → Render live .ops/register.jsonl movie, isometric world & R1-R3 falsifier.',
    };
  }

  if (/\b(optimus|signed\s+evidence|admission\s+lock|release\s+lock|proof\s+v1)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'audit_optimus_operational_integrity',
      targetNodeId: 'CORE-OPTIMUS',
      actionKind: 'INGEST_OPTIMUS',
      targetTab: 'optimus',
      formation: 'sieve',
      repo: 'chidionyema/idp',
      confidence: 0.96,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked Project Optimus node → Ingest signed HMAC observation & verify estate-operational-proof.v1.',
    };
  }

  if (/\b(briefing|audio\s+brief|status\s+report|captain\s+report|sitrep|readback)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'play_executive_captain_briefing',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'PLAY_BRIEFING',
      formation: 'centurion',
      repo: 'chidionyema/idp',
      confidence: 0.97,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked One-Brain Core → Synthesize & vocalize live Captain audio sitrep.',
    };
  }

  if (/\b(blast\s+cascade|sonar|shockwave|blast\s+radius)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'trigger_sonar_blast_cascade',
      targetNodeId: lower.includes('2468') ? 'INC-2468' : 'CORE-OPTIMUS',
      actionKind: 'TRIGGER_BLAST',
      formation: 'sieve',
      repo: 'chidionyema/idp',
      confidence: 0.95,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked Sonar Cascade → Project 3D dependency blast wave across connected estate nodes.',
    };
  }

  if (/\b(2468|vault|agent-foundry-hf|external-secret)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'remediate_oci_vault_incident_2468',
      targetNodeId: 'INC-2468',
      actionKind: 'EXECUTE_LEGION',
      formation: lower.includes('sniper') ? 'sniper' : 'adversarial',
      repo: 'chidionyema/idp',
      confidence: 0.95,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked Incident #2468 (agent-foundry-hf) → Armed Adversarial Geburah audit on chidionyema/idp.',
    };
  }

  if (/\b(watchdog|stagnant|600s|fence|lease|epoch|zombie)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'sweep_flow_600s_watchdog',
      targetNodeId: 'FLOW-INS-07981',
      actionKind: 'SWEEP_WATCHDOG',
      targetTab: 'flow',
      formation: 'centurion',
      repo: 'chidionyema/idp',
      confidence: 0.94,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked FLOW Stagnation Watchdog → Sweep >600s leases & bump argon-sync fencing epoch.',
    };
  }

  if (/\b(greenlane|pull\s+requests|pr\s+triage|claim-gate|claim\s+gate|rebase\s+backlog)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_greenlane_pr_triage',
      targetNodeId: 'CORE-GREENLANE',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'greenlane',
      formation: 'sniper',
      repo: 'chidionyema/idp',
      confidence: 0.93,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked Greenlane Reactor → Open reconciled PR backlog & Claim-Gate linter.',
    };
  }

  if (/\b(chronos|ventures|meridian\s+intelligence|mumchimp|fieldbooks|monetization)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'open_chronos_ventures_portfolio',
      targetNodeId: 'SURF-MERIDIAN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'chronos',
      formation: 'tournament',
      repo: 'chidionyema/idp',
      confidence: 0.92,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked Meridian Commercial Surface → Open Chronos operating cadence & venture release gates.',
    };
  }

  if (/\b(tactical\s+matrix|all-seeing\s+eye|one\s+eye|open\s+fleet\s+table)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'morph_to_tactical_matrix',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'NAVIGATE_TAB',
      targetTab: 'fleet',
      formation: 'centurion',
      repo: 'chidionyema/idp',
      confidence: 0.95,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Morphing Spatial 3D Reactor → All-Seeing Eye (/fleet) tactical matrix.',
    };
  }

  if (
    /\b(sniper|phalanx|pipeline|swarm|centurion|adversarial|tournament|sieve)\b/.test(lower) &&
    /\b(idp|hermes|prospector|mumchimp|argon|7981|7777|7971)\b/.test(lower)
  ) {
    const matchedFormation = (
      ['sniper', 'phalanx', 'pipeline', 'swarm', 'centurion', 'adversarial', 'tournament', 'sieve'] as FormationId[]
    ).find((f) => lower.includes(f))!;
    const repo = lower.includes('hermes')
      ? 'chidionyema/hermes-v2'
      : lower.includes('argon')
        ? 'chidionyema/argon'
        : lower.includes('mumchimp')
          ? 'chidionyema/mumchimp-medusa'
          : lower.includes('prospector')
            ? 'chidionyema/prospector'
            : 'chidionyema/idp';
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: `dispatch_${matchedFormation}_formation`,
      targetNodeId: `LEGION-${matchedFormation.toUpperCase()}`,
      actionKind: 'EXECUTE_LEGION',
      formation: matchedFormation,
      repo,
      confidence: 0.93,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: `Locked Legion ${matchedFormation.toUpperCase()} formation on ${repo} under HELM bounded-shot regime.`,
    };
  }

  if (/\b(reprobe|refresh\s+fleet|live\s+probe|sync\s+github)\b/.test(lower)) {
    return {
      ok: true,
      schema: 'voice-intent.v2',
      utteranceLength: text.length,
      intent: 'reprobe_estate_surfaces',
      targetNodeId: 'CORE-ONEBRAIN',
      actionKind: 'REPROBE_ESTATE',
      formation: 'sniper',
      repo: 'chidionyema/idp',
      confidence: 0.92,
      clarificationNeeded: false,
      clarifyRow: null,
      summary: 'Locked One-Brain → Re-probe live GitHub main SHAs and production edge surfaces.',
    };
  }

  // Below 0.90 confidence floor -> Trigger Voice 2100 Clarification Handshake (`kind="clarify"`)!
  const confidence = text.split(/\s+/).length >= 5 ? 0.78 : 0.62;
  return {
    ok: true,
    schema: 'voice-intent.v2',
    utteranceLength: text.length,
    intent: 'ambiguous_sovereign_directive',
    targetNodeId: 'CORE-ONEBRAIN',
    actionKind: 'INSPECT_NODE',
    formation: 'centurion',
    repo: 'chidionyema/idp',
    confidence,
    clarificationNeeded: true,
    clarifyRow: {
      subject: steerSubject,
      kind: 'clarify',
      sessionId: cleanSession,
      question: `Confidence ${(confidence * 100).toFixed(0)}% is below the 0.90 sovereign execution floor. Select exact target & formation:`,
      candidateActions: [
        {
          label: 'Audit Project Optimus & Ingest Signed Probe (0.96)',
          utterance: 'Verify Optimus signed evidence and release lock on idp',
          targetNodeId: 'CORE-OPTIMUS',
          actionKind: 'INGEST_OPTIMUS',
          formation: 'sieve',
          repo: 'chidionyema/idp',
        },
        {
          label: 'Dispatch Adversarial on IDP #2468 OCI Vault Key (0.95)',
          utterance: 'Run Adversarial formation on idp 2468 vault external-secret',
          targetNodeId: 'INC-2468',
          actionKind: 'EXECUTE_LEGION',
          formation: 'adversarial',
          repo: 'chidionyema/idp',
        },
        {
          label: 'Sweep FLOW 600s Stagnation Watchdog & Fence Leases (0.94)',
          utterance: 'Sweep FLOW 600s watchdog and fence stagnant worker leases',
          targetNodeId: 'FLOW-INS-07981',
          actionKind: 'SWEEP_WATCHDOG',
          formation: 'centurion',
          repo: 'chidionyema/idp',
        },
      ],
    },
    summary: 'Awaiting 0.90 Clarification Handshake before mutating estate state.',
  };
}
