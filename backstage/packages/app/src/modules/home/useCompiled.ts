// The compiled estate, read through the backend's proxy plugin (app-config
// proxy.endpoints./estate-state) from docs/compiled-helm.json on the rendered state branch.
// The same door useFounder.ts and usePlacement.ts use; no host is typed here (LAW 46).
//
// WHY. On 2026-09-12 a right-sizing merged five days earlier was not in the cluster. The pull
// request changed a COMMENT claiming "cpu 500m" and left the VALUE at 1000m; every check was green
// because the YAML was valid. The only way to see it was to render the chart by hand. This reads the
// document bin/idp-compile-helm produces so the rendered number is on a page.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { CompiledDoc, CompiledSummary, summariseCompiled } from './compiled';
import { REFRESH_MS } from './useEstate';

export const COMPILED_JSON = '/estate-state/docs/compiled-helm.json';

export type LoadedCompiled =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; summary: CompiledSummary };

export const useCompiled = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedCompiled>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedCompiled> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${COMPILED_JSON}`);
        if (!r.ok) throw new Error(`${COMPILED_JSON} answered ${r.status}`);
        const body = (await r.json()) as CompiledDoc;
        return { state: 'ready', summary: summariseCompiled(body) };
      } catch (e) {
        // A document that cannot be read is an error, never an empty and healthy estate: the whole
        // point is to say when what the charts will run is unknown.
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
