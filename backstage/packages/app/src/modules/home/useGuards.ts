// The guard inventory, read from the estate MCP server through the backend proxy.
//
// Same shape as useHealthchecks: one GET, re-read on the page's own interval, and every failure
// reported as a failure rather than as an empty list. An empty list and an unreadable endpoint are
// different answers and the Ops page must never show one as the other.
import { useEffect, useState } from 'react';
import { discoveryApiRef, fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { GUARD_NAMES, GuardSummary } from './guards';
import { REFRESH_MS } from './useEstate';

const GUARDS = '/guards';

export type LoadedGuards =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; rows: GuardSummary[]; total: number; unreadable: string[] };

type Answer = {
  total_guards?: number;
  fired?: Record<string, { fired?: number; blocked?: number; last_at?: string; last_command?: string }>;
  unreadable?: string[];
};

export const useGuards = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedGuards>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${GUARDS}`);
        if (!r.ok) throw new Error(`The guard inventory answered ${r.status}`);
        const body = (await r.json()) as Answer;
        // The tool returns guards ALREADY AGGREGATED (`fired` is a map of counts), so this
        // builds the rows directly. The first version fed that map through `summarise`, which
        // parses LEDGER LINES and filters by timestamp -- so every guard was filtered out and the
        // page said "no guard has fired" while holding two that had. Measured by the page's own
        // test: it expected 2 guards and got 0.
        const rows = Object.entries(body.fired ?? {}).map(([guard, c]) => ({
          guard,
          name: GUARD_NAMES[guard]?.name ?? guard,
          what: GUARD_NAMES[guard]?.what ?? '',
          events: c.fired ?? 0,
          blocked: c.blocked ?? 0,
          lastAt: c.last_at ?? '',
          lastCommand: c.last_command ?? '',
        })).sort((a, b) => (a.lastAt < b.lastAt ? 1 : -1));
        if (!cancelled) {
          setLoaded({
            state: 'ready',
            rows,
            total: body.total_guards ?? 0,
            unreadable: body.unreadable ?? [],
          });
        }
      } catch (e) {
        if (!cancelled) setLoaded({ state: 'error', error: String((e as Error)?.message ?? e) });
      }
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
