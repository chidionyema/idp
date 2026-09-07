// The live "On the cluster" card for the estate entity overview (spec CP5's live-state door,
// scoped to one catalogue entity). For a layer the estate catalogue stamps with a flux
// kustomization (every platform layer carries `estate/flux-kustomization`; read 2026-09-05:
// all 64 do), this reads Fresh from the cluster whether the kustomization is Ready and how
// many of its pods are up, drawn in the same six-words-and-no-invention language the home page
// uses. No new probe and no bare link: it reuses the exact Kubernetes proxy read /ops and
// /showcase already perform, and the layerState/podsOf helpers estate.ts already tests. A layer
// the cluster did not answer is a "could not be read" card, never a green one (rule 13).
import { useEffect, useState } from 'react';
import { Entity } from '@backstage/catalog-model';
import { useApi } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { Card, CardContent, Typography } from '@material-ui/core';
import {
  DeploymentObject,
  FluxObject,
  LAYER_ANNOTATION,
  LayerState,
  Live,
  layerName,
  layerState,
} from '../home/estate';

const FLUX_KINDS = '/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations';
const DEPLOYMENTS = '/apis/apps/v1/deployments';
/** Re-read while the card is open, the same cadence the home page's cluster tile uses. */
const REFRESH_MS = 60_000;

/** true when the catalogue entity names the flux kustomization behind it (`estate/flux-kustomization`). */
export const isOnCluster = (entity: Entity): boolean =>
  Boolean(entity.metadata?.annotations?.[LAYER_ANNOTATION]);

/** One catalogue entity's live cluster read: either a read in progress, a read that failed on the
 * wire, or the estate's own verdict for the layer -- the same State words the home page uses. A
 * layer is never stamped with a fabricated 'ready': if the cluster answered, the real State
 * (good / red / needs / stale / blind) from estate.layerState is what a person sees, and its
 * why and pods ride along. */
export type LayerRead =
  | { state: 'loading' }
  | { state: 'unread'; error: string }
  | LayerState;

/** A minimal stand-in for the Kubernetes API the caller already holds. */
export type KubernetesApi = {
  getClusters(): Promise<Array<{ name?: string }>>;
  proxy(opts: { clusterName?: string; path: string }): Promise<Response>;
};

/** Fetch the kustomization list + its labelled deployments in one Promise.all (LAW 51),
 * shaped exactly as useEstate shapes them into a Live. One flux name from entity -> the
 * kustomizations map is keyed by flux name, so layerState resolves the card's ready verdict. */
export async function fetchLive(
  api: KubernetesApi,
): Promise<Live | undefined> {
  try {
    const clusters = await api.getClusters();
    const clusterName = clusters[0]?.name;
    if (!clusterName) return undefined;
    const get = async (path: string) => {
      const r = await api.proxy({ clusterName, path });
      if (!r.ok) throw new Error(`${path} answered ${r.status}`);
      return (await r.json()) as { items: unknown[] };
    };
    const [k, d] = await Promise.all([get(FLUX_KINDS), get(DEPLOYMENTS)]);
    const kustomizations: Record<string, FluxObject> = {};
    for (const o of k.items as FluxObject[]) kustomizations[o.metadata.name] = o;
    return {
      kustomizations,
      deployments: d.items as DeploymentObject[],
      readAt: Date.now(),
    };
  } catch {
    return undefined;
  }
}

/** The hook: one entity's live state, re-read on a clock while the card is mounted. Uses the
 * caller's Kubernetes API (or an injected fake in tests) through the same ref proxy pattern. */
export function useLayerLive(entity: Entity, api?: KubernetesApi): LayerRead {
  const contextApi = useApi(kubernetesApiRef);
  const effective: KubernetesApi | undefined =
    api ?? (contextApi as unknown as KubernetesApi);
  const [read, setRead] = useState<LayerRead>({ state: 'loading' });
  const flux = layerName(entity);
  useEffect(() => {
    let cancelled = false;
    let clock: ReturnType<typeof setInterval> | undefined;
    // entity metadata identity drives the effect; flux is derived from it.
    if (effective) {
      const go = async () => {
        setRead({ state: 'loading' });
        const got = await fetchLive(effective);
        if (cancelled) return;
        if (!got) {
          setRead({ state: 'unread', error: 'The cluster did not answer' });
          return;
        }
        setRead(layerState(entity, got));
      };
      void go();
      clock = setInterval(go, REFRESH_MS);
    } else {
      setRead({ state: 'unread', error: 'No cluster is configured' });
    }
    // one cleanup for both branches, so the effect always returns the same shape
    return () => {
      cancelled = true;
      if (clock !== undefined) clearInterval(clock);
    };
  }, [effective, entity, flux]);
  return read;
}

/** Pure: one LayerRead -> the stable line a person reads (testable without a cluster). */
export function layerStateLine(read: LayerRead): LayerState {
  // The person sees words, never the raw HTTP/error code: an unread cluster is always told
  // as 'the cluster did not answer', and `error` is only machine detail (LAW: a number is not
  // a sentence). A loading read is a Reading line, never a verdict.
  if (read.state === 'unread') return { state: 'blind', why: 'The cluster did not answer' };
  if (read.state === 'loading') return { state: 'blind', why: 'Reading the cluster' };
  return read;
}

/** One plain sentence for one LayerState, the way DESIGN-RULES 21/22 want the words front-loaded. */
export function layerSentence(s: LayerState): string {
  if (s.state === 'good') {
    return s.pods && s.pods.wanted > 0
      ? `Ready — ${s.pods.ready} of ${s.pods.wanted} pods ready.`
      : 'Ready.';
  }
  const pod = s.pods && s.pods.wanted > 0 ? ` ${s.pods.ready} of ${s.pods.wanted} pods ready.` : '';
  return s.state === 'needs' || s.state === 'blind' || s.state === 'stale'
    ? `${s.why}.${pod}`
    : `${s.why}.${pod}`;
}

/** The rendered card. Names itself in plain English and is never silent-green. */
export function LayerOnCluster({ entity }: { entity: Entity }) {
  const read = useLayerLive(entity);
  const sentence = layerSentence(layerStateLine(read));
  return (
    <Card variant="outlined" data-testid="layer-on-cluster">
      <CardContent>
        <Typography variant="overline">On the cluster</Typography>
        <Typography variant="body2">{sentence}</Typography>
      </CardContent>
    </Card>
  );
}
