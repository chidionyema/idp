// cost/meter.ts
// The room weighs every cost. Not just dollars — carbon, latency, trust.
// It makes the cost FELT, not read. And it is always askable.

import type { Cost, TraceId } from '../core/types';
import { addCost, ZERO_COST } from '../core/types';
import type { EventBus, RoomEvents } from '../core/events';

export interface Budget {
  readonly usd: number;
  readonly carbonGrams: number;
  readonly windowMs: number;
}

export const DEFAULT_BUDGET: Budget = {
  usd: 5.0,
  carbonGrams: 500,
  windowMs: 24 * 60 * 60 * 1000,
};

export class CostMeter {
  private total: Cost = ZERO_COST;
  private windowStart = Date.now();
  private budget: Budget;

  constructor(
    private readonly events: EventBus<RoomEvents>,
    budget?: Partial<Budget>,
  ) {
    this.budget = { ...DEFAULT_BUDGET, ...budget };
  }

  charge(cost: Cost, traceId: TraceId): void {
    this.total = addCost(this.total, cost);
    this.events.emit('cost:incurred', { cost, traceId });

    const windowAge = Date.now() - this.windowStart;
    if (windowAge > this.budget.windowMs) {
      this.windowStart = Date.now();
      return;
    }

    if (this.total.usd > this.budget.usd * 0.8) {
      this.events.emit('cost:budget_warning', {
        spent: this.total.usd,
        budget: this.budget.usd,
      });
    }
  }

  totalCost(): Cost { return this.total; }

  /** 0..1, how much of the dollar budget is spent. */
  pressure(): number {
    return Math.min(1, this.total.usd / this.budget.usd);
  }

  /** 0..1, how much of the carbon budget is spent. */
  carbonPressure(): number {
    return Math.min(1, this.total.carbonGrams / this.budget.carbonGrams);
  }

  reset(): void {
    this.total = ZERO_COST;
    this.windowStart = Date.now();
  }
}
