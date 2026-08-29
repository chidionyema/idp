// What the front page knows, with no React in it (crew#459 redesign, 2026-08-29).
//
// Two kinds of thing live on the page. A *layer* is one Flux Kustomization the cluster runs,
// held in the catalogue as a `platform-layer` Component (bin/catalog-platform); its state is
// read live from the cluster's Flux and Deployment objects, never from a file. A *door* is a
// `founder-surface` Component; its state is the probe bin/catalog-gen stamped on it. Both
// end as one of six words, and the page's first sentence is the worst word's count.
import { Entity } from '@backstage/catalog-model';
import { STATE_ORDER, State } from '../theme/tokens';

export const FOUNDER_SURFACE_TYPE = 'founder-surface';
export const PLATFORM_LAYER_TYPE = 'platform-layer';
export const LAYER_ANNOTATION = 'estate/flux-kustomization';
export const FLUX_LABEL = 'kustomize.toolkit.fluxcd.io/name';

// A door probed more than three hours ago is not shown green (silent green is the defect class).
export const STALE_AFTER_MS = 3 * 60 * 60 * 1000;

export type Health = 'down' | 'stale' | 'unchecked' | 'up';
export const HEALTH_LABEL: Record<Health, string> = {
  down: 'Down',
  stale: 'Not checked lately',
  unchecked: 'Not checked',
  up: 'Up',
};
export const healthOf = (entity: Entity, now: number = Date.now()): Health => {
  const ann = entity.metadata.annotations ?? {};
  const verdict = ann['estate/health'];
  if (!verdict) return 'unchecked';
  if (verdict.startsWith('FAIL')) return 'down';
  const at = Date.parse(ann['estate/health-checked-at'] ?? '');
  if (Number.isNaN(at) || now - at > STALE_AFTER_MS) return 'stale';
  return 'up';
};
export const HEALTH_STATE: Record<Health, State> = {
  down: 'red',
  stale: 'stale',
  unchecked: 'blind',
  up: 'good',
};
export const needsYou = (h: Health) => h === 'down' || h === 'stale';

// The slice of a Flux Kustomization / HelmRelease the page reads. Anything else is ignored.
export type FluxObject = {
  metadata: { name: string; namespace?: string };
  spec?: { suspend?: boolean };
  status?: {
    conditions?: {
      type: string;
      status: string;
      reason?: string;
      message?: string;
      lastTransitionTime?: string;
    }[];
    lastAppliedRevision?: string;
    lastAttemptedRevision?: string;
  };
};
export type DeploymentObject = {
  metadata: {
    name: string;
    namespace?: string;
    labels?: Record<string, string>;
  };
  spec?: { replicas?: number };
  status?: { readyReplicas?: number; replicas?: number };
};

/** Live state per layer, keyed by Kustomization name. `undefined` means the cluster was not read. */
export type Live =
  | {
      kustomizations: Record<string, FluxObject>;
      deployments: DeploymentObject[];
      readAt: number;
    }
  | undefined;

export type LayerState = {
  state: State;
  /** One plain clause: "Ready", "Suspended", the Flux reason, or why it could not be read. */
  why: string;
  pods?: { ready: number; wanted: number };
};

const cond = (o: FluxObject, type: string) =>
  (o.status?.conditions ?? []).find(c => c.type === type);

/**
 * Six words from a Flux object. Suspended is a hand on it (Needs you); Ready=False is red;
 * Ready=Unknown / Reconciling is running; Ready=True is good; no status at all is blind, and
 * a layer the cluster did not list is blind too: a thing nobody could check is never green.
 */
export const fluxState = (o: FluxObject | undefined): LayerState => {
  if (!o) return { state: 'blind', why: 'Not found on the cluster' };
  if (o.spec?.suspend) return { state: 'needs', why: 'Suspended by hand' };
  const ready = cond(o, 'Ready');
  if (!ready) return { state: 'blind', why: 'No status yet' };
  if (ready.status === 'False')
    return {
      state: 'red',
      why: ready.reason ? `${ready.reason}` : 'Not ready',
    };
  if (ready.status !== 'True' || cond(o, 'Reconciling'))
    return { state: 'running', why: ready.reason ?? 'Reconciling' };
  const healthy = cond(o, 'Healthy');
  if (healthy && healthy.status === 'False')
    return { state: 'red', why: healthy.reason ?? 'Not healthy' };
  return { state: 'good', why: 'Ready' };
};

export const podsOf = (
  deployments: DeploymentObject[],
  layer: string,
): { ready: number; wanted: number } | undefined => {
  const mine = deployments.filter(
    d => d.metadata.labels?.[FLUX_LABEL] === layer,
  );
  if (mine.length === 0) return undefined;
  return mine.reduce(
    (acc, d) => ({
      ready: acc.ready + (d.status?.readyReplicas ?? 0),
      wanted: acc.wanted + (d.spec?.replicas ?? 0),
    }),
    { ready: 0, wanted: 0 },
  );
};

export const layerName = (e: Entity): string =>
  (e.metadata.annotations ?? {})[LAYER_ANNOTATION] ?? e.metadata.name;

export const layerState = (e: Entity, live: Live): LayerState => {
  if (!live) return { state: 'blind', why: 'The cluster did not answer' };
  const name = layerName(e);
  const s = fluxState(live.kustomizations[name]);
  const pods = podsOf(live.deployments, name);
  if (pods && s.state === 'good' && pods.ready < pods.wanted)
    return {
      ...s,
      pods,
      state: 'red',
      why: `${pods.ready} of ${pods.wanted} pods ready`,
    };
  return { ...s, pods };
};

export const doorState = (e: Entity, now: number = Date.now()): LayerState => {
  const h = healthOf(e, now);
  return { state: HEALTH_STATE[h], why: HEALTH_LABEL[h] };
};

export const rank = (s: State) => STATE_ORDER.indexOf(s);

export const byTitle = (a: Entity, b: Entity) =>
  (a.metadata.title ?? a.metadata.name).localeCompare(
    b.metadata.title ?? b.metadata.name,
  );

export type Counts = Record<State, number>;
export const count = (states: State[]): Counts => {
  const c: Counts = {
    red: 0,
    needs: 0,
    running: 0,
    good: 0,
    stale: 0,
    blind: 0,
  };
  for (const s of states) c[s] += 1;
  return c;
};

/** The first sentence on the page. Worst word first; "thing" because a layer and a door both count. */
export const verdict = (c: Counts, total: number): string => {
  const say = (n: number, what: string) =>
    `${n} ${n === 1 ? 'thing' : 'things'} ${what}.`;
  if (total === 0) return 'Nothing is registered yet.';
  if (c.red > 0) return say(c.red, c.red === 1 ? 'is red' : 'are red');
  if (c.needs > 0)
    return say(c.needs, c.needs === 1 ? 'needs you' : 'need you');
  if (c.stale > 0)
    return say(c.stale, c.stale === 1 ? 'is stale' : 'are stale');
  if (c.blind > 0) return say(c.blind, "can't be checked");
  if (c.running > 0)
    return say(
      c.running,
      c.running === 1 ? 'is still starting' : 'are still starting',
    );
  return `Everything we run is good. ${total} things checked.`;
};

export const templatePath = (t: Entity): string =>
  `/create/templates/${t.metadata.namespace ?? 'default'}/${t.metadata.name}`;

export const entityPath = (e: Entity) =>
  `/catalog/${e.metadata.namespace ?? 'default'}/${e.kind.toLowerCase()}/${
    e.metadata.name
  }`;

export const systemOf = (e: Entity): string => {
  const s = (e.spec as { system?: string } | undefined)?.system;
  return typeof s === 'string' ? s : 'other';
};

const text = (e: Entity): string =>
  [
    e.metadata.title,
    e.metadata.name,
    e.metadata.description,
    systemOf(e),
    ...(e.metadata.tags ?? []),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

export const matches = (query: string, items: Entity[]): Entity[] => {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return items;
  return items.filter(e => words.every(w => text(e).includes(w)));
};
