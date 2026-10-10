// The research department's claims, through the catalogue's own backend plugin
// (/api/research-output/claims, packages/backend/src/researchOutput.ts). Reached as
// plugin://research-output so no host is typed here; the discovery middleware names the plugin.
// Mirrors useReports (crew#740): three states, polled, cancellable. An unavailable department
// is an error state, never silently "no findings" -- the two must not look alike.
import { useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { REFRESH_MS } from './useEstate';

export type Claim = { created_at: string; status: string; statement: string };
export type ResearchEnvelope = {
  available: boolean;
  error?: string;
  count?: number;
  claims?: Claim[];
};

export type LoadedResearch =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; claims: Claim[] };

export const parseResearch = (body: ResearchEnvelope): LoadedResearch => {
  if (!body.available) {
    return { state: 'error', error: body.error ?? 'the research department did not answer' };
  }
  return { state: 'ready', claims: body.claims ?? [] };
};

export const useResearch = (limit = 3): LoadedResearch => {
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedResearch>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await fetchApi.fetch(`plugin://research-output/claims?limit=${limit}`);
        const body = (await r.json()) as ResearchEnvelope;
        const next: LoadedResearch = r.ok
          ? parseResearch(body)
          : { state: 'error', error: body.error ?? `/claims answered ${r.status}` };
        if (!cancelled) setLoaded(next);
      } catch (e) {
        if (!cancelled) {
          setLoaded({ state: 'error', error: String((e as Error)?.message ?? e) });
        }
      }
    };
    tick();
    const timer = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [fetchApi, limit]);

  return loaded;
};
