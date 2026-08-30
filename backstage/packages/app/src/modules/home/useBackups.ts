// One GET through the backend's proxy plugin (app-config proxy.endpoints./estate-state) for
// docs/backups.json on the rendered state branch, re-read every minute while the page is open.
// The same door useFounder.ts uses: no host typed here.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { BACKUPS_JSON, BackupsData, parseBackups } from './backups';
import { REFRESH_MS } from './useEstate';

export type LoadedBackups =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; data: BackupsData };

export const useBackups = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedBackups>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedBackups> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${BACKUPS_JSON}`);
        if (!r.ok) throw new Error(`${BACKUPS_JSON} answered ${r.status}`);
        return { state: 'ready', data: parseBackups(await r.json()) };
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
