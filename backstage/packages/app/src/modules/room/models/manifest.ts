// models/manifest.ts
// Every model the room can reach is described by a manifest. The room reads
// manifests, not APIs. Swap a manifest, swap a model. No code changes.

import type {
  Cost,
  Modality,
  ModelId,
  ProviderId,
  RegionId,
  Retention,
  SovereigntyTier,
} from '../core/types';

export interface ModelManifest {
  readonly id: ModelId;
  readonly providerId: ProviderId;
  readonly regionId: RegionId;
  readonly displayName: string;
  readonly version: string;
  readonly releasedAt: number;
  readonly retiredAt: number | null;

  readonly modalities: readonly Modality[];
  readonly contextWindow: number;
  readonly maxOutput: number;

  /** What this model costs per 1M input/output tokens, in USD. */
  readonly pricePerMInput: number;
  readonly pricePerMOutput: number;

  /** Estimated carbon per 1M tokens, in grams CO2e. */
  readonly carbonPerMTokens: number;

  /** Data residency this model enforces. */
  readonly sovereignty: SovereigntyTier;

  /** What the provider does with data. */
  readonly retention: Retention;

  /** Documented refusal categories. */
  readonly refusals: readonly string[];

  /** Languages supported, BCP-47. Empty = unknown. */
  readonly languages: readonly string[];

  /** Observed p50/p95 latency, in ms, from the room's own measurements. */
  readonly latency: { readonly p50: number; readonly p95: number };

  /** Health: the room updates this live. */
  readonly health: 'healthy' | 'degraded' | 'down' | 'unknown';

  /** Free-form tags for policy matching. */
  readonly tags: readonly string[];
}

export interface ManifestValidation {
  readonly ok: boolean;
  readonly errors: readonly string[];
}

const REQUIRED_FIELDS: ReadonlyArray<keyof ModelManifest> = [
  'id',
  'providerId',
  'regionId',
  'displayName',
  'version',
  'modalities',
  'contextWindow',
  'maxOutput',
  'pricePerMInput',
  'pricePerMOutput',
  'carbonPerMTokens',
  'sovereignty',
  'retention',
  'refusals',
  'languages',
  'latency',
  'health',
  'tags',
];

export function validateManifest(m: Partial<ModelManifest>): ManifestValidation {
  const errors: string[] = [];
  for (const f of REQUIRED_FIELDS) {
    if (m[f] === undefined) errors.push(`missing field: ${String(f)}`);
  }
  if (m.modalities && m.modalities.length === 0) {
    errors.push('modalities must not be empty');
  }
  if (m.contextWindow !== undefined && m.contextWindow <= 0) {
    errors.push('contextWindow must be > 0');
  }
  if (m.maxOutput !== undefined && m.maxOutput <= 0) {
    errors.push('maxOutput must be > 0');
  }
  if (m.pricePerMInput !== undefined && m.pricePerMInput < 0) {
    errors.push('pricePerMInput must be >= 0');
  }
  if (m.pricePerMOutput !== undefined && m.pricePerMOutput < 0) {
    errors.push('pricePerMOutput must be >= 0');
  }
  return { ok: errors.length === 0, errors };
}

/** Estimate cost for a call, given input and expected output tokens. */
export function estimateCost(
  m: ModelManifest,
  inputTokens: number,
  outputTokens: number,
): Cost {
  const usd =
    (inputTokens / 1_000_000) * m.pricePerMInput +
    (outputTokens / 1_000_000) * m.pricePerMOutput;
  const carbonGrams =
    ((inputTokens + outputTokens) / 1_000_000) * m.carbonPerMTokens;
  return {
    usd,
    carbonGrams,
    latencyMs: m.latency.p50,
    trustPenalty: m.retention.kind === 'persistent' ? 0.1 : 0,
  };
}
