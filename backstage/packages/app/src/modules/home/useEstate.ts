// Two round trips for the whole page (LAW 51): one catalogue query for every kind the page
// shows, and one cluster read through the Kubernetes plugin's proxy for Flux state and
// Deployments, batched into a single Promise.all. Forty-three per-entity pod calls were the
// naive plan; the Flux list is one GET.
import { useCallback, useEffect, useState } from 'react';
import { Entity } from '@backstage/catalog-model';
import { useApi } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import {
  DeploymentObject,
  FOUNDER_SURFACE_TYPE,
  FluxObject,
  Live,
  PLATFORM_LAYER_TYPE,
  byTitle,
} from './estate';

export type Estate = {
  layers: Entity[];
  systems: Entity[];
  doors: Entity[];
  templates: Entity[];
  live: Live;
  /** Why the cluster could not be read, in the cluster's words, when `live` is undefined. */
  liveError?: string;
};

export type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: Error }
  | ({ state: 'ready' } & Estate);

const FLUX = '/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations';
const DEPLOYMENTS = '/apis/apps/v1/deployments';
/** The cluster is re-read this often while the page is open; the catalogue is not. */
export const REFRESH_MS = 60_000;

export const useEstate = () => {
  const catalogApi = useApi(catalogApiRef);
  const kubernetesApi = useApi(kubernetesApiRef);
  const [loaded, setLoaded] = useState<Loaded>({ state: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => {
    setLoaded({ state: 'loading' });
    setAttempt(a => a + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const readCluster = async (): Promise<
      Pick<Estate, 'live' | 'liveError'>
    > => {
      try {
        const clusters = await kubernetesApi.getClusters();
        const clusterName = clusters[0]?.name;
        if (!clusterName)
          return { live: undefined, liveError: 'No cluster is configured' };
        const get = async (path: string) => {
          const r = await kubernetesApi.proxy({ clusterName, path });
          if (!r.ok) throw new Error(`${path} answered ${r.status}`);
          return (await r.json()) as { items: unknown[] };
        };
        const [k, d] = await Promise.all([get(FLUX), get(DEPLOYMENTS)]);
        const kustomizations: Record<string, FluxObject> = {};
        for (const o of k.items as FluxObject[])
          kustomizations[o.metadata.name] = o;
        return {
          live: {
            kustomizations,
            deployments: d.items as DeploymentObject[],
            readAt: Date.now(),
          },
        };
      } catch (e) {
        return {
          live: undefined,
          liveError: String((e as Error)?.message ?? e),
        };
      }
    };
    let timer: ReturnType<typeof setInterval> | undefined;
    (async () => {
      try {
        const [catalogue, cluster] = await Promise.all([
          catalogApi.getEntities({
            filter: [
              { kind: 'Component', 'spec.type': PLATFORM_LAYER_TYPE },
              { kind: 'Component', 'spec.type': FOUNDER_SURFACE_TYPE },
              { kind: 'System' },
              { kind: 'Template' },
            ],
            fields: ['kind', 'metadata', 'spec.type', 'spec.system'],
          }),
          readCluster(),
        ]);
        if (cancelled) return;
        const items = catalogue.items;
        const ofType = (t: string) =>
          items
            .filter(e => e.kind === 'Component' && (e.spec as any)?.type === t)
            .sort(byTitle);
        setLoaded({
          state: 'ready',
          layers: ofType(PLATFORM_LAYER_TYPE),
          doors: ofType(FOUNDER_SURFACE_TYPE),
          systems: items.filter(e => e.kind === 'System').sort(byTitle),
          templates: items.filter(e => e.kind === 'Template').sort(byTitle),
          ...cluster,
        });
        timer = setInterval(async () => {
          const again = await readCluster();
          if (cancelled) return;
          setLoaded(prev =>
            prev.state === 'ready' ? { ...prev, ...again } : prev,
          );
        }, REFRESH_MS);
      } catch (error) {
        if (!cancelled) setLoaded({ state: 'error', error: error as Error });
      }
    })();
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [catalogApi, kubernetesApi, attempt]);

  return { loaded, retry };
};
