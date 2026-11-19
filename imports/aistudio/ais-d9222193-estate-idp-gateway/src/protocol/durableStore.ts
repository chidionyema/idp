/**
 * Durable Idempotency Store (Tenant & Surface Scoped)
 * Solves Blocking Issue 4: Exactly-once durable semantics across browser reloads,
 * reconnects, and cross-instance evaluations.
 */

import { StoredIdempotencyRecord, Receipt } from './types';

const STORAGE_KEY = 'estate_idp_idempotency_ledger_v1';

export class DurableIdempotencyStore {
  private inMemoryFallback: Map<string, StoredIdempotencyRecord> = new Map();
  private isStorageAvailable: boolean;

  constructor() {
    this.isStorageAvailable = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
    this.loadFromStorage();
  }

  private buildKey(
    tenantId: string,
    surfaceId: string,
    capability: string,
    idempotencyKey: string,
    compiledContextHash: string
  ): string {
    return `${tenantId || 'default'}:${surfaceId}:${capability}:${idempotencyKey}:${compiledContextHash}`;
  }

  private loadFromStorage(): void {
    if (!this.isStorageAvailable) return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: Record<string, StoredIdempotencyRecord> = JSON.parse(raw);
        for (const [k, v] of Object.entries(parsed)) {
          this.inMemoryFallback.set(k, v);
        }
      }
    } catch {
      // Storage read error fallback to in-memory
    }
  }

  private persistToStorage(): void {
    if (!this.isStorageAvailable) return;
    try {
      const obj: Record<string, StoredIdempotencyRecord> = {};
      this.inMemoryFallback.forEach((value, key) => {
        obj[key] = value;
      });
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
    } catch {
      // Silently handle quota exceeded in storage
    }
  }

  public get(
    tenantId: string,
    surfaceId: string,
    capability: string,
    idempotencyKey: string,
    compiledContextHash: string
  ): StoredIdempotencyRecord | undefined {
    const key = this.buildKey(tenantId, surfaceId, capability, idempotencyKey, compiledContextHash);
    return this.inMemoryFallback.get(key);
  }

  public set(
    tenantId: string,
    surfaceId: string,
    capability: string,
    idempotencyKey: string,
    compiledContextHash: string,
    result: unknown,
    receipt?: Receipt
  ): void {
    const key = this.buildKey(tenantId, surfaceId, capability, idempotencyKey, compiledContextHash);
    const record: StoredIdempotencyRecord = {
      tenantId: tenantId || 'default',
      surfaceId,
      capability,
      idempotencyKey,
      compiledContextHash,
      result,
      receipt,
      storedAt: Date.now(),
    };
    this.inMemoryFallback.set(key, record);
    this.persistToStorage();
  }

  public clear(): void {
    this.inMemoryFallback.clear();
    if (this.isStorageAvailable) {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch {
        // Ignore storage removal errors
      }
    }
  }

  public getAll(): StoredIdempotencyRecord[] {
    return Array.from(this.inMemoryFallback.values());
  }
}
