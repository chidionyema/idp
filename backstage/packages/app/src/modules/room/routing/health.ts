// routing/health.ts
// Live latency and failure tracking. The router uses this to route around
// slowness before the user feels it. Updated on every call, both ways.

import type { Failure, ModelId } from '../core/types';
import type { HealthMap } from './router';

interface HealthState {
  successes: number;
  failures: number;
  latencies: number[]; // ring buffer of recent latencies
  lastFailure: Failure | null;
  downUntil: number;
}

export class LiveHealthMap implements HealthMap {
  private readonly state = new Map<ModelId, HealthState>();
  private readonly window = 50;
  private readonly downCooldownMs = 30_000;

  isHealthy(id: ModelId): boolean {
    const s = this.state.get(id);
    if (!s) return true;
    if (s.downUntil > Date.now()) return false;
    const total = s.successes + s.failures;
    if (total < 5) return true;
    return s.failures / total < 0.5;
  }

  noteFailure(id: ModelId, failure: Failure): void {
    const s = this.get(id);
    s.failures++;
    s.lastFailure = failure;
    if (failure.kind === 'unavailable' || failure.kind === 'network') {
      s.downUntil = Date.now() + this.downCooldownMs;
    }
  }

  noteSuccess(id: ModelId, latencyMs: number): void {
    const s = this.get(id);
    s.successes++;
    s.latencies.push(latencyMs);
    if (s.latencies.length > this.window) s.latencies.shift();
    s.downUntil = 0;
  }

  latencyP50(id: ModelId): number {
    const s = this.state.get(id);
    if (!s || s.latencies.length === 0) return 0;
    const sorted = [...s.latencies].sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  }

  private get(id: ModelId): HealthState {
    let s = this.state.get(id);
    if (!s) {
      s = {
        successes: 0,
        failures: 0,
        latencies: [],
        lastFailure: null,
        downUntil: 0,
      };
      this.state.set(id, s);
    }
    return s;
  }
}
