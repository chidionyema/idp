// The home plugin's own page is replaced: a module for `home` that makes a page
// extension with the default name yields the id `page:home`, which overrides the
// plugin's page at "/". The widget grid (and the toolkit whose links pointed at
// 127.0.0.1) goes with it; the front page is the founder god view (crew#459).
import { createFrontendModule, PageBlueprint } from '@backstage/frontend-plugin-api';

const estateHomePage = PageBlueprint.make({
  params: {
    path: '/',
    loader: () => import('./EstateHome').then(m => <m.EstateHome />),
  },
});

export const homeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [estateHomePage],
});
