// Cursor pagination will not fetch if every filter is empty (plugin-catalog-react
// useEntityListProvider). Kind starts as "" so every kind shows, and that left
// no backend filter, so the table stayed on "No records". Namespace default is
// a real filter that still includes every kind this estate ships.
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { CatalogFilterBlueprint } from '@backstage/plugin-catalog-react/alpha';
import { EntityNamespacePicker } from '@backstage/plugin-catalog-react';

const namespaceFilter = CatalogFilterBlueprint.make({
  name: 'namespace',
  params: {
    loader: async () => (
      <EntityNamespacePicker initiallySelectedNamespaces={['default']} />
    ),
  },
});

export const catalogFiltersModule = createFrontendModule({
  pluginId: 'catalog',
  extensions: [namespaceFilter],
});
