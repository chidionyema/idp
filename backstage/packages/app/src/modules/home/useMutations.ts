// Reads `GET /api/proxy/fleetview/mutations`, the same discovery-API/`plugin://proxy` route
// Fleet.tsx already uses for `/fleetview/sessions` -- one client pattern for this whole plugin,
// not a second one for this tile. Re-read every minute while the page is open (REFRESH_MS,
// same cadence useFounder.ts already uses for "what waits on you").
import { useCallback, useEffect, useState } from 'react';
import { fetchApiRef, useApi } from '@backstage/frontend-plugin-api';
import { MutationsData, parseMutations } from './mutations';
import { REFRESH_MS } from './useEstate';

export type LoadedMutations =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; data: MutationsData };

// The founder's own merge path: one button press here calls this, never an agent's own task
// loop (see fleetview-backend/src/mutations.py's docstring). `admit_mutation`, underneath, still
// only ever produces a branch and a commit -- `pr_required: true`, never a live merge.
export type ActionResult =
  | { ok: true; branch?: string | null; commit_sha?: string; rejected?: boolean }
  | { ok: false; error: string };

export const useMutations = () => {
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedMutations>({ state: 'loading' });
  const [busy, setBusy] = useState<string | null>(null);

  const read = useCallback(async (): Promise<LoadedMutations> => {
    try {
      const res = await fetchApi.fetch('plugin://proxy/fleetview/mutations');
      if (!res.ok) throw new Error(`/fleetview/mutations answered ${res.status}`);
      return { state: 'ready', data: parseMutations(await res.json()) };
    } catch (e) {
      return { state: 'error', error: String((e as Error)?.message ?? e) };
    }
  }, [fetchApi]);

  useEffect(() => {
    let cancelled = false;
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
  }, [read]);

  const act = useCallback(
    async (path: 'approve' | 'reject', ledgerId: string): Promise<ActionResult> => {
      setBusy(ledgerId);
      try {
        const res = await fetchApi.fetch(`plugin://proxy/fleetview/mutations/${path}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ledger_id: ledgerId }),
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok || body?.ok !== true) {
          return { ok: false, error: String(body?.error ?? `HTTP ${res.status}`) };
        }
        return body as ActionResult;
      } catch (e) {
        return { ok: false, error: String((e as Error)?.message ?? e) };
      } finally {
        setBusy(null);
        setLoaded(await read());
      }
    },
    [fetchApi, read],
  );

  return {
    loaded,
    busy,
    approve: (ledgerId: string) => act('approve', ledgerId),
    reject: (ledgerId: string) => act('reject', ledgerId),
  };
};
