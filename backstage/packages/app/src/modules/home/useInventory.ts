// One GET through the backend's proxy plugin (app-config proxy.endpoints./estate-state) for
// docs/inventory.json on the state branch, re-read every minute while the page is open
// (crew#740). No host is typed here: the discovery API names the proxy, the config names the
// target. Mirrors useFounder.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { INVENTORY_JSON, InventoryData, parseInventory } from './inventory';
import { REFRESH_MS } from './useEstate';

export type LoadedInventory =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; data: InventoryData };

export const useInventory = () => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<LoadedInventory>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedInventory> => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${INVENTORY_JSON}`);
        if (!r.ok) throw new Error(`${INVENTORY_JSON} answered ${r.status}`);
        return { state: 'ready', data: parseInventory(await r.json()) };
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
