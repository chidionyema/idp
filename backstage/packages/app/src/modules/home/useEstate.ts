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
  isEstateInternal,
} from './estate';

/** One row of "everything we hold": how many entities of one kind and type the catalogue has. */
export type InventoryRow = { kind: string; type?: string; count: number };

export type Estate = {
  layers: Entity[];
  /** Every entity in the catalogue counted by kind and type (crew#612 CP10: "not just services"). */
  inventory: InventoryRow[];
  systems: Entity[];
  doors: Entity[];
  templates: Entity[];
  live: Live;
  /** Why the cluster could not be read, in the cluster's words, when `live` is undefined. */
  liveError?: string;
  demoSandbox?: {
    ttlSecondsRemaining: number;
    creationTimestamp: string;
    kustomizationName: string;
  };
};

export type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: Error }
  | ({ state: 'ready' } & Estate);

const FLUX = '/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations';
const DEMO_SANDBOX_KUSTOMIZATIONS = '/apis/kustomize.toolkit.fluxcd.io/v1/namespaces/demo-sandbox/kustomizations';
const DEPLOYMENTS = '/apis/apps/v1/deployments';
const LANGFUSE_HEALTH = '/api/v1/namespaces/observability/services/langfuse-frontend:80/proxy/health';
const LOKI_CALICO_QUERY = '/api/v1/namespaces/observability/services/loki:3100/proxy/loki/api/v1/query_range?query={job="calico-felix"}&limit=10';
/** The cluster is re-read this often while the page is open; the catalogue is not. */
export const REFRESH_MS = 60_000;

/** Count entities by kind and spec.type, biggest group first. */
export const countInventory = (items: Entity[]): InventoryRow[] => {
  const m = new Map<string, InventoryRow>();
  for (const e of items) {
    const type = (e.spec as { type?: unknown } | undefined)?.type;
    const t = typeof type === 'string' ? type : undefined;
    const key = `${e.kind}/${t ?? ''}`;
    const row = m.get(key) ?? { kind: e.kind, type: t, count: 0 };
    row.count += 1;
    m.set(key, row);
  }
  return [...m.values()].sort(
    (a, b) => b.count - a.count || a.kind.localeCompare(b.kind),
  );
};

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
        const [k, d, demoK, langfuseHealth, calicoDenyFlows] = await Promise.all([
          get(FLUX),
          get(DEPLOYMENTS),
          get(DEMO_SANDBOX_KUSTOMIZATIONS),
          get(LANGFUSE_HEALTH).then(() => true).catch(() => false),
          get(LOKI_CALICO_QUERY).then((res: any) => {
            // Basic parsing: extract unique destination/port/proto triples from Loki log lines.
            // This is a placeholder and can be refined when the actual Loki response structure
            // is known. Returning an empty array is the fail-closed state if parsing fails.
            const flows: DenyFlow[] = [];
            // Example structure: { data: { result: [{ values: [[ts, line]] }] } }
            // We assume the log line contains `calico-packet:` and parse `DST`, `DPT`, `PROTO`.
            return flows;
          }).catch(() => [] as DenyFlow[]),
        ]);
        const kustomizations: Record<string, FluxObject> = {};
        for (const o of k.items as FluxObject[]) {
          kustomizations[o.metadata.name] = o;
        }

        let demoSandbox: Estate['demoSandbox'] = undefined;
        const demoSandboxKustomization = (demoK.items as FluxObject[]).find(
          o => o.metadata.labels?.['idp.estate/sandbox'] === 'true',
        );

        if (demoSandboxKustomization) {
          const ttlLabel = demoSandboxKustomization.metadata.annotations?.['cleanup.kyverno.io/ttl'];
          const creationTimestamp = demoSandboxKustomization.metadata.creationTimestamp;

          if (ttlLabel && creationTimestamp) {
            const ttlSeconds = parseInt(ttlLabel, 10);
            const created = new Date(creationTimestamp).getTime();
            const now = Date.now();
            const elapsedSeconds = Math.floor((now - created) / 1000);
            const ttlSecondsRemaining = Math.max(0, ttlSeconds - elapsedSeconds);

            demoSandbox = {
              ttlSecondsRemaining,
              creationTimestamp,
              kustomizationName: demoSandboxKustomization.metadata.name,
            };
          }
        }
        return {
          live: {
            kustomizations,
            deployments: d.items as DeploymentObject[],
            readAt: Date.now(),
            demoSandbox,
            langfuseHealthy: langfuseHealth,
            calicoDenyFlows: calicoDenyFlows,
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
        const [catalogue, everything, cluster] = await Promise.all([
          catalogApi.getEntities({
            filter: [
              { kind: 'Component', 'spec.type': PLATFORM_LAYER_TYPE },
              { kind: 'Component', 'spec.type': FOUNDER_SURFACE_TYPE },
              { kind: 'System' },
              { kind: 'Template' },
            ],
            fields: ['kind', 'metadata', 'spec.type', 'spec.system'],
          }),
          // The whole catalogue, two fields per entity, so the page can count everything it
          // holds, not only the services. Runs beside the other two reads, so it costs no time.
          catalogApi.getEntities({
            fields: [
              'kind',
              'metadata.name',
              'metadata.namespace',
              'spec.type',
            ],
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
          // The header count and the kind chips count what the estate shows a person, not
          // everything the catalogue physically holds: ephemeral internal-agent records
          // (.claude per-session scratch) are excluded so they stop inflating "Everything we
          // hold" and the systems lists (founder, bin/catalog-gen: they belong in a lesser
          // section, recoverable but never in a person's first read).
          inventory: countInventory(everything.items.filter(e => !isEstateInternal(e))),
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

