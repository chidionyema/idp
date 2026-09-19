// index.ts
// The room's entry point. Everything is assembled here. Nothing is a
// singleton — you can run many rooms, for many users, in the same process.

export * from './core/result';
export * from './core/types';
export * from './core/events';
export * from './models/manifest';
export * from './models/registry';
export * from './routing/router';
export * from './routing/health';
export * from './voice/presence';
export * from './voice/wake';
export * from './memory/store';
export * from './failure/chain';
export * from './cost/meter';

import { ModelRegistry } from './models/registry';
import { LiveHealthMap } from './routing/health';
import { Router } from './routing/router';
import { FallbackChain } from './failure/chain';
import { CostMeter } from './cost/meter';
import { EventBus, type RoomEvents } from './core/events';
import type { UserId } from './core/types';

export interface RoomRuntime {
  readonly events: EventBus<RoomEvents>;
  readonly registry: ModelRegistry;
  readonly health: LiveHealthMap;
  readonly router: Router;
  readonly fallback: FallbackChain;
  readonly cost: CostMeter;
}

export function createRoomRuntime(userId: UserId): RoomRuntime {
  const events = new EventBus<RoomEvents>();
  const registry = new ModelRegistry();
  const health = new LiveHealthMap();
  const router = new Router({ registry, events, health });
  const fallback = new FallbackChain(router);
  const cost = new CostMeter(events);
  return { events, registry, health, router, fallback, cost };
}
