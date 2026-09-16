import { createFrontendModule, PageBlueprint } from '@backstage/frontend-plugin-api';

const sovereignPage = PageBlueprint.make({
  name: 'sovereign',
  params: {
    path: '/sovereign',
    loader: () =>
      import('../../pages/SovereignPage').then(m => <m.default />),
  },
});

export const sovereignModule = createFrontendModule({
  pluginId: 'sovereign',
  extensions: [sovereignPage],
});
