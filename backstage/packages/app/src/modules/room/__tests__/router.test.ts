// __tests__/router.test.ts
// The router is the heart. It must route correctly under every edge:
// sovereignty, budget, avoid-lists, retirements, health.

// THE SPEC'S TESTS ASSUMED VITEST; this estate runs jest.
//
// Your spec is written model-agnostic and runner-agnostic, and every module in it is
// framework-neutral except this one line -- the test file imports from 'vitest'. The repo's
// runner is jest (backstage-cli repo test), so the spec's own suite could not execute here at
// all: "Cannot find module 'vitest'". One import, and 215 lines of your tests run.
//
// @jest/globals is the direct equivalent of vitest's import: same four names, same semantics.
// Nothing else in the file changes.
import { describe, it, expect } from '@jest/globals';
import { Router } from '../routing/router';
import { ModelRegistry } from '../models/registry';
import { LiveHealthMap } from '../routing/health';
import { EventBus, type RoomEvents } from '../core/events';
import { asModelId, asProviderId, asRegionId, asTraceId, asUtteranceId } from '../core/types';
import type { ModelManifest } from '../models/manifest';

function manifest(overrides: Partial<ModelManifest> = {}): ModelManifest {
  return {
    id: asModelId('m1'),
    providerId: asProviderId('p1'),
    regionId: asRegionId('eu-west'),
    displayName: 'M1',
    version: '1.0',
    releasedAt: Date.now() - 1e9,
    retiredAt: null,
    modalities: ['reason'],
    contextWindow: 8192,
    maxOutput: 1024,
    pricePerMInput: 1,
    pricePerMOutput: 2,
    carbonPerMTokens: 10,
    sovereignty: 'anywhere',
    retention: { kind: 'none' },
    refusals: [],
    languages: ['en'],
    latency: { p50: 200, p95: 800 },
    health: 'healthy',
    tags: [],
    ...overrides,
  };
}

function makeRouter() {
  const registry = new ModelRegistry();
  const events = new EventBus<RoomEvents>();
  const health = new LiveHealthMap();
  const router = new Router({ registry, events, health });
  return { registry, events, health, router };
}

describe('Router', () => {
  it('routes to a healthy model in-region', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest());
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 200,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      reason: 'test',
    });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.manifest.id).toBe(asModelId('m1'));
  });

  it('rejects when no model exists for the modality', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest({ modalities: ['speak'] }));
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 200,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      reason: 'test',
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.kind).toBe('unavailable');
  });

  it('rejects when sovereignty is stricter than the model allows', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest({ sovereignty: 'anywhere' }));
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 200,
      sovereignty: 'device',
      region: asRegionId('eu-west'),
      reason: 'test',
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.kind).toBe('sovereignty');
  });

  it('honors an avoid list', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest({ id: asModelId('a') }));
    registry.upsert(manifest({ id: asModelId('b') }));
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 200,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      avoidModelIds: [asModelId('a')],
      reason: 'test',
    });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.manifest.id).toBe(asModelId('b'));
  });

  it('picks the cheapest model under a budget', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest({ id: asModelId('cheap'), pricePerMOutput: 0.1 }));
    registry.upsert(manifest({ id: asModelId('pricey'), pricePerMOutput: 100 }));
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 1000,
      expectedOutputTokens: 1000,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      maxUsd: 0.001,
      reason: 'test',
    });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.manifest.id).toBe(asModelId('cheap'));
  });

  it('excludes retired models', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest({ retiredAt: Date.now() - 1000 }));
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 200,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      reason: 'test',
    });
    expect(r.ok).toBe(false);
  });

  it('prefers an explicitly preferred model when available', () => {
    const { registry, router } = makeRouter();
    registry.upsert(manifest({ id: asModelId('a'), pricePerMOutput: 0.1 }));
    registry.upsert(manifest({ id: asModelId('b'), pricePerMOutput: 100 }));
    const r = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 100,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      preferModelIds: [asModelId('b')],
      reason: 'user preference',
    });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value.manifest.id).toBe(asModelId('b'));
  });

  it('records a failure and reroutes away from the failed model', () => {
    const { registry, health, router } = makeRouter();
    registry.upsert(manifest({ id: asModelId('a') }));
    registry.upsert(manifest({ id: asModelId('b') }));
    const first = router.route({
      traceId: asTraceId('t1'),
      utteranceId: asUtteranceId('u1'),
      modality: 'reason',
      inputTokens: 100,
      expectedOutputTokens: 100,
      sovereignty: 'anywhere',
      region: asRegionId('eu-west'),
      preferModelIds: [asModelId('a')],
      reason: 'test',
    });
    expect(first.ok).toBe(true);
    if (!first.ok) return;
    router.recordFailure(
      {
        traceId: asTraceId('t1'),
        utteranceId: asUtteranceId('u1'),
        modelId: asModelId('a'),
        providerId: asProviderId('p1'),
        regionId: asRegionId('eu-west'),
        modality: 'reason',
        startedAt: Date.now(),
        finishedAt: Date.now(),
        cost: { usd: 0, carbonGrams: 0, latencyMs: 0, trustPenalty: 0 },
        retention: { kind: 'none' },
        sovereignty: 'anywhere',
        fallbacks: [],
        reason: 'test',
      },
      {
        kind: 'unavailable',
        message: 'provider down',
        retryable: true,
        at: Date.now(),
      },
    );
    // Health should now mark 'a' as down for a while.
    expect(health.isHealthy(asModelId('a'))).toBe(false);
  });
});
