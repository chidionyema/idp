// core/types.ts
// The room's vocabulary. Every type here is load-bearing. Nothing is
// decorative. If a type is here, some edge case depends on it.

// ─── Identity ──────────────────────────────────────────────────────────────

export type UserId = string & { readonly __brand: 'UserId' };
export type AgentId = string & { readonly __brand: 'AgentId' };
export type ModelId = string & { readonly __brand: 'ModelId' };
export type ProviderId = string & { readonly __brand: 'ProviderId' };
export type RegionId = string & { readonly __brand: 'RegionId' };
export type UtteranceId = string & { readonly __brand: 'UtteranceId' };
export type TraceId = string & { readonly __brand: 'TraceId' };

export const asUserId = (s: string): UserId => s as UserId;
export const asAgentId = (s: string): AgentId => s as AgentId;
export const asModelId = (s: string): ModelId => s as ModelId;
export const asProviderId = (s: string): ProviderId => s as ProviderId;
export const asRegionId = (s: string): RegionId => s as RegionId;
export const asUtteranceId = (s: string): UtteranceId => s as UtteranceId;
export const asTraceId = (s: string): TraceId => s as TraceId;

// ─── Modality ──────────────────────────────────────────────────────────────

export type Modality =
  | 'transcribe'
  | 'reason'
  | 'speak'
  | 'see'
  | 'embed'
  | 'rerank';

// ─── Sovereignty ───────────────────────────────────────────────────────────

export type SovereigntyTier =
  | 'anywhere' // data may leave the region
  | 'region' // data must stay in the user's region
  | 'country' // data must stay in the user's country
  | 'device'; // data must never leave the device

// ─── Retention ─────────────────────────────────────────────────────────────

export type Retention =
  | { kind: 'none' } // forget immediately
  | { kind: 'session' } // forget when the room dims
  | { kind: 'duration'; ms: number } // forget after ms
  | { kind: 'persistent' }; // keep until told otherwise

// ─── Cost ──────────────────────────────────────────────────────────────────

export interface Cost {
  readonly usd: number; // dollars, fractional
  readonly carbonGrams: number; // grams CO2e
  readonly latencyMs: number; // wall-clock estimate
  readonly trustPenalty: number; // 0..1, how much this erodes trust
}

export const ZERO_COST: Cost = {
  usd: 0,
  carbonGrams: 0,
  latencyMs: 0,
  trustPenalty: 0,
};

export function addCost(a: Cost, b: Cost): Cost {
  return {
    usd: a.usd + b.usd,
    carbonGrams: a.carbonGrams + b.carbonGrams,
    latencyMs: a.latencyMs + b.latencyMs,
    trustPenalty: a.trustPenalty + b.trustPenalty,
  };
}

// ─── Failure ───────────────────────────────────────────────────────────────

export type FailureKind =
  | 'network'
  | 'auth'
  | 'rate_limit'
  | 'timeout'
  | 'refusal'
  | 'hallucination'
  | 'unavailable'
  | 'sovereignty'
  | 'budget'
  | 'unknown';

export interface Failure {
  readonly kind: FailureKind;
  readonly message: string;
  readonly providerId?: ProviderId;
  readonly modelId?: ModelId;
  readonly retryable: boolean;
  readonly at: number;
}

// ─── Provenance ────────────────────────────────────────────────────────────

export interface Provenance {
  readonly traceId: TraceId;
  readonly utteranceId: UtteranceId;
  readonly modelId: ModelId;
  readonly providerId: ProviderId;
  readonly regionId: RegionId;
  readonly modality: Modality;
  readonly startedAt: number;
  readonly finishedAt: number;
  readonly cost: Cost;
  readonly retention: Retention;
  readonly sovereignty: SovereigntyTier;
  readonly fallbacks: readonly Failure[];
  readonly reason: string; // why THIS model, THIS region, THIS moment
}

// ─── Utterance ─────────────────────────────────────────────────────────────

export type Speaker =
  | { kind: 'user'; userId: UserId }
  | { kind: 'agent'; agentId: AgentId }
  | { kind: 'room' };

export interface Utterance {
  readonly id: UtteranceId;
  readonly speaker: Speaker;
  readonly text: string;
  readonly isPartial: boolean;
  readonly at: number;
  readonly confidence: number; // 0..1 for STT
}
