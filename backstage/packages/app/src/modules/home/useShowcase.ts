// Two GETs through the backend's proxy plugin (app-config proxy.endpoints./estate-state), in one
// Promise.all, re-read every minute while the page is open (LAW 51: one round trip per source).
// Each document fails on its own: a missing showcase page leaves the Otto list standing, and the
// other way round. No host is typed here; the discovery API names the proxy. Mirrors useReports.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import {
  Ability,
  Bar,
  OTTO_INVENTORY_FILE,
  SHOWCASE_FILE,
  parseAbilities,
  parseBar,
} from './showcaseDocs';
import { REFRESH_MS } from './useEstate';

export type LoadedShowcase =
  | { state: 'loading' }
  | {
      state: 'ready';
      bar?: Bar;
      barError?: string;
      abilities: Ability[];
      abilitiesError?: string;
    };

export const useShowcase = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedShowcase>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const text = async (base: string, file: string): Promise<string> => {
      const r = await fetchApi.fetch(`${base}${file}`);
      if (!r.ok) throw new Error(`${file} answered ${r.status}`);
      return r.text();
    };
    const read = async (): Promise<LoadedShowcase> => {
      let base = '';
      try {
        base = await discoveryApi.getBaseUrl('proxy');
      } catch (e) {
        const error = String((e as Error)?.message ?? e);
        return { state: 'ready', barError: error, abilities: [], abilitiesError: error };
      }
      const [bar, otto] = await Promise.allSettled([
        text(base, SHOWCASE_FILE),
        text(base, OTTO_INVENTORY_FILE),
      ]);
      const why = (r: PromiseRejectedResult) =>
        String((r.reason as Error)?.message ?? r.reason);
      const parsedBar = bar.status === 'fulfilled' ? parseBar(bar.value) : undefined;
      return {
        state: 'ready',
        bar: parsedBar,
        barError:
          bar.status === 'rejected'
            ? why(bar)
            : parsedBar
            ? undefined
            : `${SHOWCASE_FILE} carries no bar`,
        abilities: otto.status === 'fulfilled' ? parseAbilities(otto.value) : [],
        abilitiesError: otto.status === 'rejected' ? why(otto) : undefined,
      };
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
