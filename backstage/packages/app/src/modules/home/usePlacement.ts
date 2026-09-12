// One GET through the backend's proxy plugin (app-config proxy.endpoints./estate-state) for
// docs/placement.json on the rendered state branch, re-read every minute while the page is open.
// The same door useFounder.ts uses, and no host is typed here: the discovery API names the proxy,
// the config names the target (LAW 46).
//
// WHY. bin/idp-fits-a-node answers "could these workloads be placed again" and its answer reached
// a CI job and nowhere else. On 2026-09-12 the cluster sat at 96% of CPU REQUESTS while using
// 39%/85% of ACTUAL CPU and the second catalogue replica was Pending -- facts that existed only in
// a log. This reads the measurement the cluster publishes so a person can see it.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { Placement, summarisePlacement, PlacementSummary } from './placement';
import { REFRESH_MS } from './useEstate';

export const PLACEMENT_JSON = '/estate-state/docs/placement.json';

export type LoadedPlacement =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; summary: PlacementSummary; at: string };

export const usePlacement = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedPlacement>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedPlacement> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${PLACEMENT_JSON}`);
        if (!r.ok) throw new Error(`${PLACEMENT_JSON} answered ${r.status}`);
        const body = (await r.json()) as Placement;
        return {
          state: 'ready',
          summary: summarisePlacement(body),
          at: body.at ?? '',
        };
      } catch (e) {
        // A document that cannot be read is an error, never an empty and healthy cluster. The
        // whole point of this tile is to say when placement is unknown.
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
  }, [discoveryApi, fetchApi]);

  return loaded;
};
