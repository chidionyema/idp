// Two round trips for the open-reds table (crew#684 CP2), in one Promise.all: the catalogue
// (drills and doors in one query) and Alertmanager's active alerts, read through the same
// Kubernetes plugin proxy the cluster tile uses, via the service proxy the cluster API offers
// (platform/backstage/base/rbac.yaml grants services/proxy for it). Re-read every minute.
import { useEffect, useState } from 'react';
import { useApi } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import { FOUNDER_SURFACE_TYPE } from './estate';
import {
  AlertmanagerAlert,
  DRILL_TYPE,
  Red,
  redsFromAlerts,
  redsFromEntities,
  sortReds,
} from './openReds';
import { REFRESH_MS } from './useEstate';

/** The chart's Alertmanager Service: `<HelmRelease name>-alertmanager` in the monitoring namespace. */
export const ALERTMANAGER_NAMESPACE = 'monitoring';
export const ALERTMANAGER_SERVICE = 'kube-prometheus-stack-alertmanager';
export const ALERTS =
  `/api/v1/namespaces/${ALERTMANAGER_NAMESPACE}/services/${ALERTMANAGER_SERVICE}:9093` +
  '/proxy/api/v2/alerts?active=true&silenced=false&inhibited=false';

export type OpenReds =
  | { state: 'loading' }
  | {
      state: 'ready';
      reds: Red[];
      /** A source that could not be read; its reds are unknown, never zero. */
      unread: string[];
    };

export const useOpenReds = (): OpenReds => {
  const catalogApi = useApi(catalogApiRef);
  const kubernetesApi = useApi(kubernetesApiRef);
  const [loaded, setLoaded] = useState<OpenReds>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const readAlerts = async (): Promise<AlertmanagerAlert[]> => {
      const clusters = await kubernetesApi.getClusters();
      const clusterName = clusters[0]?.name;
      if (!clusterName) throw new Error('No cluster is configured');
      const r = await kubernetesApi.proxy({ clusterName, path: ALERTS });
      if (!r.ok) throw new Error(`Alertmanager answered ${r.status}`);
      const body = await r.json();
      return Array.isArray(body) ? body : [];
    };
    const readEntities = () =>
      catalogApi
        .getEntities({
          filter: [
            { kind: 'Resource', 'spec.type': DRILL_TYPE },
            { kind: 'Component', 'spec.type': FOUNDER_SURFACE_TYPE },
          ],
        })
        .then(r => r.items);
    const tick = async () => {
      const [alerts, entities] = await Promise.allSettled([
        readAlerts(),
        readEntities(),
      ]);
      if (cancelled) return;
      const unread: string[] = [];
      const reds: Red[] = [];
      if (alerts.status === 'fulfilled')
        reds.push(...redsFromAlerts(alerts.value));
      else
        unread.push(
          `Alertmanager: ${String(alerts.reason?.message ?? alerts.reason)}`,
        );
      if (entities.status === 'fulfilled')
        reds.push(...redsFromEntities(entities.value));
      else
        unread.push(
          `Catalogue: ${String(entities.reason?.message ?? entities.reason)}`,
        );
      setLoaded({ state: 'ready', reds: sortReds(reds), unread });
    };
    tick();
    const timer = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [catalogApi, kubernetesApi]);

  return loaded;
};
