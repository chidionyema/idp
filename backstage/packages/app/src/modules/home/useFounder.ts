// One GET through the backend's proxy plugin (app-config proxy.endpoints./estate-state) for
// docs/founder.json on the rendered state branch, re-read every minute while the page is open
// (crew#684 CP4). No host is typed here: the discovery API names the proxy, the config names
// the target.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { FOUNDER_JSON, FounderData, parseFounder } from './founder';
import { REFRESH_MS } from './useEstate';

export type LoadedFounder =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; data: FounderData };

export const useFounder = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedFounder>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedFounder> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${FOUNDER_JSON}`);
        if (!r.ok) throw new Error(`${FOUNDER_JSON} answered ${r.status}`);
        return { state: 'ready', data: parseFounder(await r.json()) };
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
  }, [discoveryApi, fetchApi]);

  return loaded;
};
