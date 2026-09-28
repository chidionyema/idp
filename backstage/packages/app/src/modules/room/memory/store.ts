// memory/store.ts
// The room remembers what you asked it to remember. It forgets everything
// else. It can tell you what it keeps. It can forget on command, immediately,
// everywhere.

import type { EventBus, RoomEvents } from '../core/events';
import type { UserId } from '../core/types';

export interface MemoryEntry {
  readonly key: string;
  readonly userId: UserId;
  readonly value: string;
  readonly keptAt: number;
  readonly expiresAt: number | null;
  readonly reason: string;   // why the room kept it
}

export interface MemoryConfig {
  /** Where the memory lives. Cloud-first: a remote store by default. */
  readonly store: MemoryBackend;
}

export interface MemoryBackend {
  put(entry: MemoryEntry): Promise<void>;
  get(userId: UserId, key: string): Promise<MemoryEntry | null>;
  list(userId: UserId): Promise<readonly MemoryEntry[]>;
  delete(userId: UserId, key: string): Promise<void>;
  deleteAll(userId: UserId): Promise<void>;
}

export class Memory {
  constructor(
    private readonly backend: MemoryBackend,
    private readonly events: EventBus<RoomEvents>,
  ) {}

  async keep(entry: MemoryEntry): Promise<void> {
    await this.backend.put(entry);
    this.events.emit('memory:kept', { key: entry.key, at: Date.now() });
  }

  async recall(userId: UserId, key: string): Promise<MemoryEntry | null> {
    const e = await this.backend.get(userId, key);
    if (!e) return null;
    if (e.expiresAt !== null && e.expiresAt <= Date.now()) {
      await this.backend.delete(userId, key);
      return null;
    }
    return e;
  }

  async tell(userId: UserId): Promise<readonly MemoryEntry[]> {
    const all = await this.backend.list(userId);
    return all.filter((e) => e.expiresAt === null || e.expiresAt > Date.now());
  }

  async forget(userId: UserId, key: string): Promise<void> {
    await this.backend.delete(userId, key);
    this.events.emit('memory:forgotten', { key, at: Date.now() });
  }

  async forgetAll(userId: UserId): Promise<void> {
    await this.backend.deleteAll(userId);
    this.events.emit('memory:forgotten', { key: '*', at: Date.now() });
  }

  /** Sweep expired entries. Call periodically. */
  async sweep(userId: UserId): Promise<number> {
    const all = await this.backend.list(userId);
    const now = Date.now();
    let n = 0;
    for (const e of all) {
      if (e.expiresAt !== null && e.expiresAt <= now) {
        await this.backend.delete(userId, e.key);
        n++;
      }
    }
    return n;
  }
}
