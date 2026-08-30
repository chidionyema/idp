// Cluster health, summarised from four list reads (crew#684 CP1): nodes, pods, Flux
// Kustomizations and HelmReleases. Pure: the hook feeds it raw objects, the page draws what
// it returns, tests prove it on fixtures. Nothing here names a namespace or a node (LAW 46).
import { FluxObject, fluxState } from './estate';
import { State } from '../theme/tokens';

export type NodeObject = {
  metadata: { name: string };
  spec?: { unschedulable?: boolean };
  status?: { conditions?: { type: string; status: string }[] };
};
export type PodObject = {
  metadata: { name: string; namespace?: string };
  status?: {
    phase?: string;
    conditions?: { type: string; status: string }[];
  };
};

export type FluxRow = {
  kind: 'Kustomization' | 'HelmRelease';
  name: string;
  namespace: string;
  state: State;
  why: string;
};

export type ClusterHealth = {
  nodes: { ready: number; total: number; notReady: string[] };
  /** Pods that are not Ready and not finished, counted by namespace, largest first. */
  podsNotReady: { namespace: string; count: number }[];
  flux: { ready: number; total: number; notReady: FluxRow[] };
  /** One word for the tile's pill, and one clause for its tooltip. */
  state: State;
  why: string;
  readAt: number;
};

const cond = (
  o: { status?: { conditions?: { type: string; status: string }[] } },
  type: string,
) => (o.status?.conditions ?? []).find(c => c.type === type);

export const nodeReady = (n: NodeObject) =>
  cond(n, 'Ready')?.status === 'True' && !n.spec?.unschedulable;

/** A pod counts as not ready when it is still meant to run and its Ready condition is not True. */
export const podNotReady = (p: PodObject) => {
  const phase = p.status?.phase ?? 'Unknown';
  if (phase === 'Succeeded') return false;
  return cond(p, 'Ready')?.status !== 'True';
};

export const summarise = (
  nodes: NodeObject[],
  pods: PodObject[],
  kustomizations: FluxObject[],
  helmReleases: FluxObject[],
  readAt: number = Date.now(),
): ClusterHealth => {
  const notReadyNodes = nodes
    .filter(n => !nodeReady(n))
    .map(n => n.metadata.name);
  const byNs: Record<string, number> = {};
  for (const p of pods.filter(podNotReady)) {
    const ns = p.metadata.namespace ?? '(none)';
    byNs[ns] = (byNs[ns] ?? 0) + 1;
  }
  const podsNotReady = Object.entries(byNs)
    .map(([namespace, count]) => ({ namespace, count }))
    .sort(
      (a, b) => b.count - a.count || a.namespace.localeCompare(b.namespace),
    );
  const rows: FluxRow[] = [
    ...kustomizations.map(o => ({ kind: 'Kustomization' as const, o })),
    ...helmReleases.map(o => ({ kind: 'HelmRelease' as const, o })),
  ].map(({ kind, o }) => {
    const s = fluxState(o);
    return {
      kind,
      name: o.metadata.name,
      namespace: o.metadata.namespace ?? '',
      state: s.state,
      why: s.why,
    };
  });
  const fluxNotReady = rows.filter(r => r.state !== 'good');
  const podCount = podsNotReady.reduce((n, r) => n + r.count, 0);

  let state: State = 'good';
  let why = 'Every node, pod and Flux row is ready';
  if (nodes.length === 0 && rows.length === 0) {
    state = 'blind';
    why = 'The cluster listed nothing';
  } else if (notReadyNodes.length > 0) {
    state = 'red';
    why = `${notReadyNodes.length} of ${nodes.length} nodes not ready`;
  } else if (fluxNotReady.some(r => r.state === 'red')) {
    state = 'red';
    why = `${fluxNotReady.filter(r => r.state === 'red').length} Flux rows red`;
  } else if (podCount > 0) {
    state = 'red';
    why = `${podCount} pods not ready`;
  } else if (fluxNotReady.some(r => r.state === 'needs')) {
    state = 'needs';
    why = `${
      fluxNotReady.filter(r => r.state === 'needs').length
    } Flux rows suspended by hand`;
  } else if (fluxNotReady.length > 0) {
    state = 'running';
    why = `${fluxNotReady.length} Flux rows still reconciling`;
  }
  return {
    nodes: {
      ready: nodes.length - notReadyNodes.length,
      total: nodes.length,
      notReady: notReadyNodes,
    },
    podsNotReady,
    flux: {
      ready: rows.length - fluxNotReady.length,
      total: rows.length,
      notReady: fluxNotReady,
    },
    state,
    why,
    readAt,
  };
};

/** The one sentence the drill grades: numbers, never adjectives. */
export const healthSentence = (h: ClusterHealth): string => {
  const pods = h.podsNotReady.reduce((n, r) => n + r.count, 0);
  return `${h.nodes.ready} of ${h.nodes.total} nodes ready, ${pods} pods not ready, ${h.flux.ready} of ${h.flux.total} Flux rows ready.`;
};
