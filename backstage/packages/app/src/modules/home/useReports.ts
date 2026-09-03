// Two GETs through the backend's proxy plugin (app-config proxy.endpoints./estate-state): the
// report index, re-read every minute while the page is open, and the body of the report the
// founder is looking at. No host is typed here: the discovery API names the proxy, the config
// names the target. Mirrors useInventory (crew#740).
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import {
  REPORTS_BASE,
  REPORTS_INDEX,
  Report,
  parseReports,
} from './reportIndex';
import { REFRESH_MS } from './useEstate';

export type LoadedReports =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; reports: Report[] };

export const useReports = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedReports>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedReports> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${REPORTS_INDEX}`);
        if (!r.ok) throw new Error(`${REPORTS_INDEX} answered ${r.status}`);
        return { state: 'ready', reports: parseReports(await r.json()) };
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

export type LoadedBody =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; text: string };

/** The markdown of one report, re-read whenever the file name or the index changes. */
export const useReportBody = (file: string | undefined, version: string) => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedBody>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    if (!file) return undefined;
    setLoaded({ state: 'loading' });
    (async () => {
      let next: LoadedBody;
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${REPORTS_BASE}${file}`);
        if (!r.ok) throw new Error(`${file} answered ${r.status}`);
        next = { state: 'ready', text: await r.text() };
      } catch (e) {
        next = { state: 'error', error: String((e as Error)?.message ?? e) };
      }
      if (!cancelled) setLoaded(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [discoveryApi, fetchApi, file, version]);

  return loaded;
};
