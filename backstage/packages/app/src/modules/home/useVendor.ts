// CP3: the live half of the vendor fact -- one GET through the backend's proxy plugin for the
// vendor's own health endpoint, re-read every minute while the page is open, in the same shape
// useHealthchecks.ts and useGuards.ts already use (no host, no key typed here; the discovery API
// names the proxy and app-config names the target). vendorOf() decides which vendor a founder
// surface is; an entity that is not one of the three reads nothing.
import { useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { REFRESH_MS } from './useEstate';
import { Vendor, VendorRead } from './vendor';

export const useVendor = (vendor: Vendor | undefined): VendorRead => {
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  const [read, setRead] = useState<VendorRead>({ state: 'loading' });
  const path = vendor?.path;

  useEffect(() => {
    if (!path) {
      // Not a vendor surface: nothing to read. Kept as 'loading' rather than an error --
      // the caller never renders this hook's result for a non-vendor entity.
      return undefined;
    }
    let cancelled = false;
    const go = async () => {
      try {
        const base = await discoveryApi.getBaseUrl('proxy');
        const r = await fetchApi.fetch(`${base}${path}`);
        if (!cancelled) setRead({ state: 'answered', status: r.status });
      } catch (e) {
        // A vendor that could not be reached is 'unread', never a status: -1 or a fabricated
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
