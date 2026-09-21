// core/events.ts
// The room speaks to itself in events. Every layer is decoupled. If the
// router dies, the UI still knows. If the UI dies, the router still routes.

import type {
  AgentId,
  Cost,
  Failure,
  FailureKind,
  Modality,
  ModelId,
  Provenance,
  TraceId,
  UserId,
  Utterance,
} from './types';

type Listener<T> = (event: T) => void;

export class EventBus<Events extends Record<string, unknown>> {
  private readonly listeners = new Map<keyof Events, Set<Listener<unknown>>>();
  private readonly buffer = new Map<keyof Events, unknown[]>();
  private readonly bufferSize: number;

  constructor(bufferSize = 100) {
    this.bufferSize = bufferSize;
  }

  on<K extends keyof Events>(key: K, fn: Listener<Events[K]>): () => void {
    let set = this.listeners.get(key);
    if (!set) {
      set = new Set();
      this.listeners.set(key, set);
    }
    set.add(fn as Listener<unknown>);
    return () => set!.delete(fn as Listener<unknown>);
  }

  emit<K extends keyof Events>(key: K, event: Events[K]): void {
    const set = this.listeners.get(key);
    if (set) {
      for (const fn of set) {
        try {
          (fn as Listener<Events[K]>)(event);
        } catch (e) {
          // A listener error must not take down the bus.
          console.error(`[room] listener error on ${String(key)}`, e);
        }
      }
    }
    // Buffer for late subscribers (e.g., UI mounting after a route).
    let buf = this.buffer.get(key);
    if (!buf) {
      buf = [];
      this.buffer.set(key, buf);
    }
    buf.push(event);
    if (buf.length > this.bufferSize) buf.shift();
  }

  recent<K extends keyof Events>(key: K): readonly Events[K][] {
    return (this.buffer.get(key) ?? []) as Events[K][];
  }

  clear(): void {
    this.listeners.clear();
    this.buffer.clear();
  }
}

// The room's event vocabulary.
export type RoomEvents = {
  'user:arrived': { userId: UserId; at: number };
  'user:left': { userId: UserId; at: number };
  'voice:partial': { utterance: Utterance };
  'voice:final': { utterance: Utterance };
  'voice:silence': { at: number };
  'wake:detected': { word: string; confidence: number; at: number };
  'route:started': { traceId: TraceId; modality: Modality; at: number };
  'route:chosen': { provenance: Provenance };
  'route:failed': { failure: Failure; traceId: TraceId };
  'route:fallback': { from: ModelId; to: ModelId; reason: string };
  'agent:spotlighted': { agentId: AgentId; at: number };
  'agent:released': { agentId: AgentId; at: number };
  'agent:stuck': { agentId: AgentId; since: number };
  'agent:unstuck': { agentId: AgentId; at: number };
  'memory:kept': { key: string; at: number };
  'memory:forgotten': { key: string; at: number };
  'cost:incurred': { cost: Cost; traceId: TraceId };
  'cost:budget_warning': { spent: number; budget: number };
  'room:dim': { at: number };
  'room:wake': { at: number };
  'failure:degraded': { kind: FailureKind; message: string };
};
