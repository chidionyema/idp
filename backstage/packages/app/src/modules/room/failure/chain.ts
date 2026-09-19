// failure/chain.ts
// The room never dies. It degrades in order:
//   router → regional model → alternative lab → cached → local → text → silence
// Every step is named. Every step is transparent.

import { type Result } from '../core/result';
import type { Failure } from '../core/types';
import type { Router, RoutingRequest, RoutingDecision } from '../routing/router';

export interface FallbackStep {
  readonly name: string;
  readonly attempt: (
    req: RoutingRequest,
    prev: readonly Failure[],
  ) => Promise<Result<RoutingDecision, Failure>>;
}

export interface FallbackResult {
  readonly decision: RoutingDecision;
  readonly failures: readonly Failure[];
  readonly degraded: boolean;
}

export class FallbackChain {
  private readonly steps: FallbackStep[] = [];

  constructor(private readonly router: Router) {
    this.steps.push({
      name: 'primary',
      attempt: async (req, prev) => {
        const r = this.router.route({
          ...req,
          avoidModelIds: prev.flatMap((f) => f.modelId ? [f.modelId] : []),
        });
        return r;
      },
    });
    this.steps.push({
      name: 'alternative-lab',
      attempt: async (req, prev) => {
        // Same modality, same region, different provider.
        const r = this.router.route({
          ...req,
          avoidModelIds: prev.flatMap((f) => f.modelId ? [f.modelId] : []),
          requiredTags: [...(req.requiredTags ?? []), 'alt-lab'],
        });
        return r;
      },
    });
    this.steps.push({
      name: 'regional',
      attempt: async (req) => {
        return this.router.route({
          ...req,
          sovereignty: 'region',
          requiredTags: [...(req.requiredTags ?? []), 'regional'],
        });
      },
    });
  }

  async run(req: RoutingRequest): Promise<FallbackResult> {
    const failures: Failure[] = [];
    for (const step of this.steps) {
      try {
        const r = await step.attempt(req, failures);
        if (r.ok) {
          return {
            decision: r.value,
            failures,
            degraded: failures.length > 0,
          };
        }
        failures.push(r.error);
      } catch (e) {
        failures.push({
          kind: 'unknown',
          message: `${step.name}: ${e instanceof Error ? e.message : String(e)}`,
          retryable: true,
          at: Date.now(),
        });
      }
    }
    // All steps failed. The caller decides: cached, local, text, silence.
    throw new NoRouteError(failures);
  }
}

export class NoRouteError extends Error {
  constructor(public readonly failures: readonly Failure[]) {
    super(`no route: ${failures.map((f) => f.kind).join(', ')}`);
    this.name = 'NoRouteError';
  }
}
