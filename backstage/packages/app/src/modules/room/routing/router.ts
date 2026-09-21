// routing/router.ts
// The router negotiates. It does not play. For every task, it asks:
//   what capability, what sovereignty, what latency, what cost, what trust?
// Then it chooses. And it tells you.

import type { EventBus, RoomEvents } from '../core/events';
import { err, ok, type Result } from '../core/result';
import type {
  Cost,
  Failure,
  Modality,
  ModelId,
  Provenance,
  RegionId,
  Retention,
  SovereigntyTier,
  TraceId,
  UtteranceId,
} from '../core/types';
import type { ModelManifest } from '../models/manifest';
import { estimateCost } from '../models/manifest';
import type { ModelRegistry } from '../models/registry';

export interface RoutingRequest {
  readonly traceId: TraceId;
  readonly utteranceId: UtteranceId;
  readonly modality: Modality;
  readonly inputTokens: number;
  readonly expectedOutputTokens: number;
  readonly sovereignty: SovereigntyTier;
  readonly region: RegionId;
  readonly maxUsd?: number;
  readonly maxLatencyMs?: number;
  readonly preferModelIds?: readonly ModelId[];
  readonly avoidModelIds?: readonly ModelId[];
  readonly requiredTags?: readonly string[];
  readonly userRetention?: Retention;
  readonly reason: string;
}

export interface RoutingDecision {
  readonly manifest: ModelManifest;
  readonly cost: Cost;
  readonly alternatives: readonly ModelManifest[];
  readonly why: string;
}

export interface HealthMap {
  isHealthy(id: ModelId): boolean;
  noteFailure(id: ModelId, failure: Failure): void;
  noteSuccess(id: ModelId, latencyMs: number): void;
  latencyP50(id: ModelId): number;
}

export interface RouterDeps {
  readonly registry: ModelRegistry;
  readonly events: EventBus<RoomEvents>;
  /** Live health map, updated by the health poller. */
  readonly health: HealthMap;
}

export class Router {
  constructor(private readonly deps: RouterDeps) {}

  route(req: RoutingRequest): Result<RoutingDecision, Failure> {
    this.deps.events.emit('route:started', {
      traceId: req.traceId,
      modality: req.modality,
      at: Date.now(),
    });

    // 1. Gather candidates by capability and sovereignty.
    const candidates = this.deps.registry.query({
      modality: req.modality,
      regionId: req.region,
      requireHealthy: false,
      excludeRetired: true,
      tags: req.requiredTags,
    });

    if (candidates.length === 0) {
      const f: Failure = {
        kind: 'unavailable',
        message: `no model for ${req.modality} in ${req.region}`,
        retryable: false,
        at: Date.now(),
      };
      this.deps.events.emit('route:failed', { failure: f, traceId: req.traceId });
      return err(f);
    }

    // 2. Filter by sovereignty. A model may refuse data it cannot hold.
    const sovereign = candidates.filter(m =>
      sovereigntyAllows(m.sovereignty, req.sovereignty),
    );
    if (sovereign.length === 0) {
      const f: Failure = {
        kind: 'sovereignty',
        message: `no model in ${req.region} satisfies ${req.sovereignty}`,
        retryable: false,
        at: Date.now(),
      };
      this.deps.events.emit('route:failed', { failure: f, traceId: req.traceId });
      return err(f);
    }

    // 3. Filter by budget, if a budget was given.
    let affordable = sovereign;
    if (req.maxUsd !== undefined) {
      affordable = sovereign.filter(m => {
        const c = estimateCost(m, req.inputTokens, req.expectedOutputTokens);
        return c.usd <= req.maxUsd!;
      });
      if (affordable.length === 0) {
        // Budget too tight — return the cheapest, but flag it.
        affordable = [cheapest(sovereign, req)];
      }
    }

    // 4. Filter by avoid list.
    const allowed = req.avoidModelIds
      ? affordable.filter(m => !req.avoidModelIds!.includes(m.id))
      : affordable;
    if (allowed.length === 0) {
      const f: Failure = {
        kind: 'budget',
        message: 'all candidate models are on the avoid list',
        retryable: false,
        at: Date.now(),
      };
      this.deps.events.emit('route:failed', { failure: f, traceId: req.traceId });
      return err(f);
    }

    // 5. Score.
    const scored = allowed.map(m => ({
      manifest: m,
      score: this.score(m, req),
    }));
    scored.sort((a, b) => b.score - a.score);

    // 6. Prefer explicit preference, if it is among the candidates.
    let chosen = scored[0].manifest;
    if (req.preferModelIds && req.preferModelIds.length > 0) {
      for (const id of req.preferModelIds) {
        const found = allowed.find(m => m.id === id);
        if (found) {
          chosen = found;
          break;
        }
      }
    }

    const cost = estimateCost(chosen, req.inputTokens, req.expectedOutputTokens);
    const why = this.explain(
      chosen,
      scored.slice(1, 4).map(s => s.manifest),
      req,
    );

    const decision: RoutingDecision = {
      manifest: chosen,
      cost,
      alternatives: scored.slice(1, 4).map(s => s.manifest),
      why,
    };

    const provenance: Provenance = {
      traceId: req.traceId,
      utteranceId: req.utteranceId,
      modelId: chosen.id,
      providerId: chosen.providerId,
      regionId: chosen.regionId,
      modality: req.modality,
      startedAt: Date.now(),
      finishedAt: 0,
      cost,
      retention: req.userRetention ?? chosen.retention,
      sovereignty: chosen.sovereignty,
      fallbacks: [],
      reason: why,
    };

    this.deps.events.emit('route:chosen', { provenance });
    return ok(decision);
  }

  /** Called by the caller after the model returns. */
  recordSuccess(provenance: Provenance, latencyMs: number): Provenance {
    this.deps.health.noteSuccess(provenance.modelId, latencyMs);
    return { ...provenance, finishedAt: Date.now() };
  }

  /** Called by the caller when the model fails. */
  recordFailure(provenance: Provenance, failure: Failure): Provenance {
    this.deps.health.noteFailure(provenance.modelId, failure);
    this.deps.events.emit('route:failed', { failure, traceId: provenance.traceId });
    return {
      ...provenance,
      fallbacks: [...provenance.fallbacks, failure],
      finishedAt: Date.now(),
    };
  }

  private score(m: ModelManifest, req: RoutingRequest): number {
    const cost = estimateCost(m, req.inputTokens, req.expectedOutputTokens);
    const p50 = this.deps.health.latencyP50(m.id) || m.latency.p50;

    // Lower is better for cost and latency; higher is better for trust.
    const costScore = 1 / (1 + cost.usd * 100);
    const latencyScore = 1 / (1 + p50 / 1000);
    const healthScore = this.deps.health.isHealthy(m.id) ? 1 : 0.1;
    const trustScore = 1 - cost.trustPenalty;

    // Weighted. These weights are policy; they can be tuned per-user.
    return (
      costScore * 0.35 + latencyScore * 0.3 + healthScore * 0.2 + trustScore * 0.15
    );
  }

  private explain(
    chosen: ModelManifest,
    alternatives: readonly ModelManifest[],
    req: RoutingRequest,
  ): string {
    const parts: string[] = [];
    parts.push(`${chosen.displayName} for ${req.modality}`);
    if (req.maxUsd !== undefined) parts.push(`under $${req.maxUsd.toFixed(4)}`);
    parts.push(`in ${chosen.regionId}`);
    if (alternatives.length > 0) {
      parts.push(
        `beat ${alternatives.length} alternative${alternatives.length === 1 ? '' : 's'}`,
      );
    }
    return parts.join(', ');
  }
}

function sovereigntyAllows(
  model: SovereigntyTier,
  user: SovereigntyTier,
): boolean {
  const rank: Record<SovereigntyTier, number> = {
    device: 4,
    country: 3,
    region: 2,
    anywhere: 1,
  };
  return rank[model] >= rank[user];
}

function cheapest(
  candidates: readonly ModelManifest[],
  req: RoutingRequest,
): ModelManifest {
  let best = candidates[0];
  let bestCost = estimateCost(best, req.inputTokens, req.expectedOutputTokens).usd;
  for (const m of candidates.slice(1)) {
    const c = estimateCost(m, req.inputTokens, req.expectedOutputTokens).usd;
    if (c < bestCost) {
      best = m;
      bestCost = c;
    }
  }
  return best;
}
