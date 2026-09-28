// One round trip (LAW 51): the catalogue query for every founder surface. The Tools page reads
// no cluster; a door's state is the probe bin/catalog-gen stamped on the entity.
import { useEffect, useState } from 'react';
import { Entity } from '@backstage/catalog-model';
import { useApi } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { FOUNDER_SURFACE_TYPE } from './estate';

export type Doors =
  | { state: 'loading' }
  | { state: 'error'; error: Error }
  | { state: 'ready'; doors: Entity[] };

export const useDoors = (): Doors => {
  const catalogApi = useApi(catalogApiRef);
  const [doors, setDoors] = useState<Doors>({ state: 'loading' });
  useEffect(() => {
    let cancelled = false;
    catalogApi
      .getEntities({
        filter: { kind: 'Component', 'spec.type': FOUNDER_SURFACE_TYPE },
      })
      .then(r => {
        if (!cancelled) setDoors({ state: 'ready', doors: r.items });
      })
      .catch(e => {
        if (!cancelled)
          setDoors({ state: 'error', error: e instanceof Error ? e : new Error(String(e)) });
      });
    return () => {
      cancelled = true;
    };
  }, [catalogApi]);
  return doors;
};
