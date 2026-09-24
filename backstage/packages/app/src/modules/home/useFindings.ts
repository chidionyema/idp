// Two list reads through the Backstage Kubernetes plugin's proxy, every minute while the Ops
// page is open (crew#718): the doctor's Result objects and its own Deployment, so a quiet tile
// can say whether the doctor is running or merely silent (LAW 28). The same door
// useClusterHealth.ts uses; platform/backstage/base/rbac.yaml grants the read.
import { useEffect, useState } from 'react';
import { useApi } from '@backstage/frontend-plugin-api';
import { kubernetesApiRef } from '@backstage/plugin-kubernetes';
import {
  DOCTOR_NAMESPACE,
  DeploymentObject,
  Doctor,
  ResultObject,
  summariseFindings,
} from './findings';
import { REFRESH_MS } from './useEstate';

export const RESULTS = '/apis/core.k8sgpt.ai/v1alpha1/results';
export const DOCTOR_DEPLOYMENTS = `/apis/apps/v1/namespaces/${DOCTOR_NAMESPACE}/deployments`;

export type LoadedFindings =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; doctor: Doctor };

export const useFindings = () => {
  const kubernetesApi = useApi(kubernetesApiRef);
  const [loaded, setLoaded] = useState<LoadedFindings>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    const read = async (): Promise<LoadedFindings> => {
      try {
        const clusters = await kubernetesApi.getClusters();
        const clusterName = clusters[0]?.name;
        if (!clusterName)
          return { state: 'error', error: 'No cluster is configured' };
        const get = async <T>(path: string): Promise<T[]> => {
          const r = await kubernetesApi.proxy({ clusterName, path });
          if (!r.ok) throw new Error(`${path} answered ${r.status}`);
          return ((await r.json()) as { items: T[] }).items ?? [];
        };
        const [results, deployments] = await Promise.all([
          get<ResultObject>(RESULTS),
          get<DeploymentObject>(DOCTOR_DEPLOYMENTS),
        ]);
        return { state: 'ready', doctor: summariseFindings(results, deployments) };
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
  }, [kubernetesApi]);

  return loaded;
};
