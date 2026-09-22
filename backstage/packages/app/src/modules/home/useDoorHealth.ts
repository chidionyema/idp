// CP6: the live half of the founder-door fact -- one GET through the backend's proxy plugin for
// the door's own health endpoint, re-read every minute while the page is open, in the same shape
// useVendor.ts and useHealthchecks.ts already use (no host, no key typed here; the discovery API
// names the proxy and app-config names the target). doorHealthOf() decides which door a founder
// surface is; an entity that is not one of the three reads nothing.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { REFRESH_MS } from './useEstate';
import { DoorHealth, DoorRead } from './doorHealth';

export const useDoorHealth = (door: DoorHealth | undefined): DoorRead => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [read, setRead] = useState<DoorRead>({ state: 'loading' });
  const path = door?.path;

  useEffect(() => {
    if (!path) {
      // Not one of CP6's doors: nothing to read. Kept as 'loading' rather than an error --
      // the caller never renders this hook's result for a non-door entity.
      return undefined;
    }
    let cancelled = false;
    const go = async () => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${path}`);
        if (!cancelled) setRead({ state: 'answered', status: r.status });
      } catch (e) {
        // A door that could not be reached is 'unread', never a status: -1 or a fabricated
        // 200. Rule 13: an unknown answer is not a passing one.
        if (!cancelled) {
          setRead({ state: 'unread', error: String((e as Error)?.message ?? e) });
        }
      }
    };
    void go();
    const timer = setInterval(go, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [discoveryApi, fetchApi, path]);

  return read;
};
