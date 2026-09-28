// Four list reads through the Backstage Kubernetes plugin's proxy, in one Promise.all, every
// minute while the page is open (crew#684 CP1). The same door useEstate.ts already uses:
// no script, no second server, the mature plugin the image ships (ADR 0009 row
// ops-dashboard-cluster-health).
import { useEffect, useState } from 'react';
import { useApi } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { FluxObject } from './estate';
import {
  ClusterHealth,
  NodeObject,
  PodObject,
  summarise,
} from './clusterHealth';
import { REFRESH_MS } from './useEstate';

export const NODES = '/api/v1/nodes';
export const PODS = '/api/v1/pods';
export const KUSTOMIZATIONS =
  '/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations';
export const HELMRELEASES = '/apis/helm.toolkit.fluxcd.io/v2/helmreleases';

export type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; health: ClusterHealth };

export const useClusterHealth = () => {
  const kubernetesApi = useApi(kubernetesApiRef);
  const [loaded, setLoaded] = useState<Loaded>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<Loaded> => {
      try {
        const clusters = await kubernetesApi.getClusters();
        const clusterName = clusters[0]?.name;
        if (!clusterName)
          return { state: 'error', error: 'No cluster is configured' };
        const get = async <T>(path: string): Promise<T[]> => {
          const r = await kubernetesApi.proxy({ clusterName, path });
          if (!r.ok) throw new Error(`${path} answered ${r.status}`);
          return ((await r.json()) as { items: T[] }).items ?? [];
        };
        const [nodes, pods, ks, hr] = await Promise.all([
          get<NodeObject>(NODES),
          get<PodObject>(PODS),
          get<FluxObject>(KUSTOMIZATIONS),
          get<FluxObject>(HELMRELEASES),
        ]);
        return { state: 'ready', health: summarise(nodes, pods, ks, hr) };
      } catch (e) {
        return { state: 'error', error: String((e as Error)?.message ?? e) };
      }
    };
    const tick = async () => {
      const next = await read();
      if (!cancelled) setLoaded(next);
    };
    tick();
    const timer = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [kubernetesApi]);

  return loaded;
};
