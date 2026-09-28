// The buyer sandbox's countdown (docs/specs/backstage-as-a-product.md CP2). One read per
// refresh through the same kubernetes proxy `useEstate.ts` already uses, against the
// Kustomization the demo-sandbox workflow stamps when it runs. The countdown is local: the
// hook reads the cluster every REFRESH_MS and ticks the displayed remaining time every
// second without re-reading (LAW 51: one round trip per source, no clock-driven GETs).
import { useEffect, useState } from 'react';
import { useApi } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { REFRESH_MS } from './useEstate';

/** The Kustomization stamped by .github/workflows/demo-sandbox.yml; same name in every cluster. */
export const DEMO_SANDBOX = 'demo-sandbox';
/** Kyverno label name the cleanup controller honours; the spec names it verbatim. */
export const TTL_LABEL = 'cleanup.kyverno.io/ttl';
/** Kustomization path through the kubernetes proxy; matches the FLUX constant in useEstate.ts. */
const DEMO_SANDBOX_PATH = `/apis/kustomize.toolkit.fluxcd.io/v1/namespaces/demo-sandbox/kustomizations/${DEMO_SANDBOX}`;
/** Where the value of the TTL label lives, in milliseconds. */
const HOLD_RE = /^(\d+)(h|m|s)$/;

export type SandboxState =
  | { state: 'absent' }
  | { state: 'loading' }
  | {
      state: 'countdown';
      remainingMs: number;
      ttlMs: number;
      createdAt: string;
    }
  | { state: 'expired'; ttlMs: number; createdAt: string }
  | { state: 'error'; error: string };

/** Read a "1h" / "30m" / "60s" TTL string as milliseconds; undefined when the shape is unknown. */
export const parseTtlMs = (s: string | undefined): number | undefined => {
  if (!s) return undefined;
  const m = HOLD_RE.exec(s.trim());
  if (!m) return undefined;
  const n = Number(m[1]);
  if (!Number.isFinite(n) || n <= 0) return undefined;
  switch (m[2]) {
    case 'h':
      return n * 60 * 60 * 1000;
    case 'm':
      return n * 60 * 1000;
    case 's':
      return n * 1000;
    default:
      return undefined;
  }
};

/** How much hold is left at `now` for a Kustomization born at `createdAt` with `ttlMs` of hold. */
export const remainingMs = (
  createdAt: string,
  ttlMs: number,
  now: number,
): number => {
  const born = Date.parse(createdAt);
  if (Number.isNaN(born)) return 0;
  return Math.max(0, born + ttlMs - now);
};

type FluxObject = {
  metadata?: {
    name?: string;
    namespace?: string;
    creationTimestamp?: string;
    labels?: Record<string, string>;
  };
};

export const useSandbox = (): SandboxState => {
  const kubernetesApi = useApi(kubernetesApiRef);
  const [data, setData] = useState<SandboxState>({ state: 'loading' });
  const [, setTick] = useState(0);

  // Two intervals: REFRESH_MS for the cluster read (the source of truth), and 1s for the
  // displayed countdown (pure local recompute against the cached createdAt + ttlMs). The local
  // tick never hits the network.
  useEffect(() => {
    let cancelled = false;
    const read = async () => {
      try {
        const clusters = await kubernetesApi.getClusters();
        const clusterName = clusters[0]?.name;
        if (!clusterName) {
          if (!cancelled)
            setData({ state: 'error', error: 'No cluster is configured' });
          return;
        }
        const r = await kubernetesApi.proxy({
          clusterName,
          path: DEMO_SANDBOX_PATH,
        });
        if (r.status === 404) {
          if (!cancelled) setData({ state: 'absent' });
          return;
        }
        if (!r.ok) {
          if (!cancelled)
            setData({
              state: 'error',
              error: `${DEMO_SANDBOX_PATH} answered ${r.status}`,
            });
          return;
        }
        const body = (await r.json()) as FluxObject;
        const createdAt = body.metadata?.creationTimestamp;
        const ttl = parseTtlMs(body.metadata?.labels?.[TTL_LABEL]);
        if (!createdAt || ttl === undefined) {
          if (!cancelled) setData({ state: 'absent' });
          return;
        }
        const remaining = remainingMs(createdAt, ttl, Date.now());
        if (!cancelled) {
          setData(
            remaining <= 0
              ? { state: 'expired', ttlMs: ttl, createdAt }
              : {
                  state: 'countdown',
                  remainingMs: remaining,
                  ttlMs: ttl,
                  createdAt,
                },
          );
        }
      } catch (e) {
        if (!cancelled)
          setData({
            state: 'error',
            error: String((e as Error)?.message ?? e),
          });
      }
    };
    read();
    const refresh = setInterval(read, REFRESH_MS);
    const tick = setInterval(() => setTick(t => t + 1), 1000);
    return () => {
      cancelled = true;
      clearInterval(refresh);
      clearInterval(tick);
    };
  }, [kubernetesApi]);

  // Recompute the displayed remaining time on every local tick. The cluster read above already
  // gave us ttlMs and createdAt; we just compute against `now` again.
  if (data.state === 'countdown') {
    const now = Date.now();
    const remaining = remainingMs(data.createdAt, data.ttlMs, now);
    if (remaining <= 0) return { state: 'expired', ttlMs: data.ttlMs, createdAt: data.createdAt };
    if (remaining !== data.remainingMs) {
      // Return the fresh value without setting state (would trigger an extra render). The
      // tick above already schedules a re-render.
      return { ...data, remainingMs: remaining };
    }
  }
  return data;
};
