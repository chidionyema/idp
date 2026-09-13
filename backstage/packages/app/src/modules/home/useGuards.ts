// The guard inventory, read through the backend's proxy plugin (app-config
// proxy.endpoints./estate-state). The same door useFounder.ts, usePlacement.ts and useCompiled.ts
// use; no host is typed here (LAW 46).
//
// The path is `/guards`, not `/guards.json`: mcp/plugins/estate_guards.py serves it under that
// name and the ops page reads it through the estate-state proxy beside the other readings.
//
// WHY THIS IS A PAGE AND NOT A FILE. Fifty-six guards sit in rules.yaml and every one of them is
// green in CI, which proves they pass, not that they are asked anything. The inventory the estate
// MCP server keeps records how many times each guard was consulted and how many commands it
// refused -- a guard that has refused nothing has never been tested by a real mistake. This hook
// is what puts that on the ops page beside the cluster readings.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { GuardsDoc } from './guards';
import { REFRESH_MS } from './useEstate';

export const GUARDS_JSON = '/guards';

export type LoadedGuards =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; guards: GuardsDoc };

export const useGuards = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedGuards>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedGuards> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${GUARDS_JSON}`);
        if (!r.ok) throw new Error(`${GUARDS_JSON} answered ${r.status}`);
        const body = (await r.json()) as GuardsDoc;
        return { state: 'ready', guards: body };
      } catch (e) {
        // A guard list that cannot be read is an error, never an estate with no guards: saying
        // "none fired" when the answer is unknown is the exact lie this page exists to end.
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
