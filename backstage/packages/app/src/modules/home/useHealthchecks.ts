// One GET through the backend's proxy plugin (app-config.container.yaml proxy.endpoints.
// /healthchecks) for the vendor's check list, re-read every minute while the page is open
// (crew#684 CP5). No host and no key are typed here: the discovery API names the proxy, the
// config names the target and holds the key.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { Checks, HC_CHECKS, parseChecks } from './healthchecks';
import { REFRESH_MS } from './useEstate';

export type LoadedChecks =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; data: Checks };

export const useHealthchecks = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedChecks>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedChecks> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${HC_CHECKS}`);
        if (!r.ok) throw new Error(`Healthchecks answered ${r.status}`);
        return { state: 'ready', data: parseChecks(await r.json()) };
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
