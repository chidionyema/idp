// A minimal catalogApi stand-in for suites that only read entities.
//
// WHY THIS EXISTS. '@backstage/plugin-catalog-react/testUtils'.catalogApiMock reaches a
// '@backstage/frontend-test-utils' member (MockWithApiFactory) that the installed shared
// store does not export, so any suite importing it fails AT IMPORT TIME on main. The home
// suites only ever exercise getEntities, so the mock here only provides getEntities.
import { Entity } from '@backstage/catalog-model';

export const catalogApiWith = (entities: Entity[]) => ({
  getEntities: async () => ({ items: entities }),
});
