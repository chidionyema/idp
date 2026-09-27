// The intent_result contract (fleetview-backend voice_intents.py) and how /fleet shows it.

export type IntentStatus = 'ok' | 'error' | 'pending_confirmation' | 'cancelled';
export type IntentCue = 'pulse' | 'burn' | 'comet_spawn' | 'shield_flash';
export type IntentSeverity = 'info' | 'warn' | 'danger';

export interface IntentResult {
  kind: 'intent_result';
  intent: string;
  status: IntentStatus;
  text: string;
  visual: { cue: IntentCue; target: 'fleet'; severity: IntentSeverity };
  ticket: string | null;
}

export interface ReactorCue {
  kind: 'pulse' | 'burn' | 'fire' | 'shield';
  severity: IntentSeverity;
  color: string;
}

export const SEVERITY_COLOR: Record<IntentSeverity, string> = {
  info: '#00f0ff',
  warn: '#ffb000',
  danger: '#ff0055',
};

const STATUSES: IntentStatus[] = ['ok', 'error', 'pending_confirmation', 'cancelled'];
const CUES: IntentCue[] = ['pulse', 'burn', 'comet_spawn', 'shield_flash'];
const SEVERITIES: IntentSeverity[] = ['info', 'warn', 'danger'];

export function parseIntentResult(msg: unknown): IntentResult | null {
  if (typeof msg !== 'object' || msg === null) {
    return null;
  }
  const m = msg as Record<string, unknown>;
  if (m.kind !== 'intent_result') {
    return null;
  }
  if (typeof m.intent !== 'string' || m.intent.length === 0) {
    return null;
  }
  if (typeof m.status !== 'string' || !STATUSES.includes(m.status as IntentStatus)) {
    return null;
  }
  if (typeof m.text !== 'string') {
    return null;
  }
  if (typeof m.visual !== 'object' || m.visual === null) {
    return null;
  }
  const v = m.visual as Record<string, unknown>;
  if (typeof v.cue !== 'string' || !CUES.includes(v.cue as IntentCue)) {
    return null;
  }
  if (v.target !== 'fleet') {
    return null;
  }
  if (typeof v.severity !== 'string' || !SEVERITIES.includes(v.severity as IntentSeverity)) {
    return null;
  }
  const ticket = typeof m.ticket === 'string' ? m.ticket : null;

  return {
    kind: 'intent_result',
    intent: m.intent,
    status: m.status as IntentStatus,
    text: m.text,
    visual: {
      cue: v.cue as IntentCue,
      target: 'fleet',
      severity: v.severity as IntentSeverity,
    },
    ticket,
  };
}

const CUE_TO_REACTOR_KIND: Record<IntentCue, ReactorCue['kind']> = {
  pulse: 'pulse',
  burn: 'burn',
  comet_spawn: 'fire',
  shield_flash: 'shield',
};

export function cueToReactor(r: IntentResult): ReactorCue {
  const severity = r.visual.severity;
  return {
    kind: CUE_TO_REACTOR_KIND[r.visual.cue],
    severity,
    color: SEVERITY_COLOR[severity],
  };
}
