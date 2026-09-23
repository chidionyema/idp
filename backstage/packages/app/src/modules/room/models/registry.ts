// models/registry.ts
// The registry holds every manifest the room knows. It is updated live:
// health checks poll, new manifests are ingested, retired models are marked.

import type { ModelId, Modality, ProviderId, RegionId, SovereigntyTier } from '../core/types';
import type { ModelManifest } from './manifest';
import { validateManifest } from './manifest';

export interface RegistryQuery {
  readonly modality?: Modality;
  readonly regionId?: RegionId;
  readonly providerId?: ProviderId;
  readonly sovereignty?: SovereigntyTier;
  readonly maxUsd?: number;
  readonly excludeRetired?: boolean;
  readonly requireHealthy?: boolean;
  readonly tags?: readonly string[];
}

export class ModelRegistry {
  private readonly manifests = new Map<ModelId, ModelManifest>();
  private readonly listeners = new Set<() => void>();

  upsert(manifest: ModelManifest): void {
    const v = validateManifest(manifest);
    if (!v.ok) {
      throw new Error(`invalid manifest ${manifest.id}: ${v.errors.join(', ')}`);
    }
    this.manifests.set(manifest.id, manifest);
    this.notify();
  }

  remove(id: ModelId): void {
    if (this.manifests.delete(id)) this.notify();
  }

  get(id: ModelId): ModelManifest | undefined {
    return this.manifests.get(id);
  }

  all(): readonly ModelManifest[] {
    return Array.from(this.manifests.values());
  }

  query(q: RegistryQuery): readonly ModelManifest[] {
    const now = Date.now();
    return this.all().filter(m => {
      if (q.excludeRetired !== false && m.retiredAt !== null && m.retiredAt <= now) {
        return false;
      }
      if (q.modality && !m.modalities.includes(q.modality)) return false;
      if (q.regionId && m.regionId !== q.regionId) return false;
      if (q.providerId && m.providerId !== q.providerId) return false;
      if (q.sovereignty && m.sovereignty !== q.sovereignty) return false;
      if (q.requireHealthy && m.health !== 'healthy') return false;
      if (q.tags && q.tags.length > 0) {
        for (const t of q.tags) if (!m.tags.includes(t)) return false;
      }
      if (q.maxUsd !== undefined && m.pricePerMOutput > q.maxUsd) return false;
      return true;
    });
  }

  /** Called by the health poller. */
  setHealth(id: ModelId, health: ModelManifest['health']): void {
    const m = this.manifests.get(id);
    if (!m) return;
    if (m.health === health) return;
    this.manifests.set(id, { ...m, health });
    this.notify();
  }

  onChange(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private notify(): void {
    for (const fn of this.listeners) {
      try {
        fn();
      } catch (e) {
        console.error('[room] registry listener', e);
      }
    }
  }
}
