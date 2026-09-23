// Reads this device's access state every minute while the page is open.
//
// The state itself lives on the device (`bin/idp-jit status`) and never in the browser: the
// portal is not allowed to hold the agent key, so it cannot answer this question by itself.
// The read goes through the estate's own backend door, which runs the same command.
//
// One minute, matching useEstate's REFRESH_MS and useClusterHealth. The token lives an hour,
// so a minute is generous for a surface whose whole job is to be correct when someone looks.
import { useEffect, useState } from 'react';
import { useApi, fetchApiRef } from '@backstage/frontend-plugin-api';
import { DeviceAccess, parseStatus } from './deviceAccess';
import { REFRESH_MS } from './useEstate';

export type DeviceAccessLoaded =
  | { state: 'loading' }
  | { state: 'ready'; access: DeviceAccess };

export const DEVICE_STATUS_PATH = 'plugin://proxy/fleetview/device-status';

export const useDeviceAccess = (): DeviceAccessLoaded => {
  const fetchApi = useApi(fetchApiRef);
  const [loaded, setLoaded] = useState<DeviceAccessLoaded>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<DeviceAccessLoaded> => {
      try {
        const res = await fetchApi.fetch(DEVICE_STATUS_PATH);
        const body = await res.json();
        // The backend always answers 200 with a status object; a non-200 is the door being
        // unreachable rather than the device being unprovisioned, and those are different
        // sentences. `parseStatus` maps anything it cannot read to 'unreadable' carrying the
        // reason, so a broken read never renders as a permissive 'active'.
        if (!res.ok) {
          return {
            state: 'ready',
            access: {
              state: 'unreadable',
              scope: null,
              expiresIn: null,
              subject: null,
              reason: body?.error ?? `the door answered ${res.status}`,
            },
          };
        }
        return { state: 'ready', access: parseStatus(body) };
      } catch (err) {
        return {
          state: 'ready',
          access: {
            state: 'unreadable',
            scope: null,
            expiresIn: null,
            subject: null,
            reason: err instanceof Error ? err.message : String(err),
          },
        };
      }
    };
    const tick = async () => {
      const next = await read();
      if (!cancelled) setLoaded(next);
    };
    void tick();
    const id = setInterval(() => void tick(), REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [fetchApi]);

  return loaded;
};
