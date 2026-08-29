// The home plugin's own page is replaced: a module for `home` that makes a page
// extension with the default name yields the id `page:home`, which overrides the
// plugin's page at "/". The widget grid (and the toolkit whose links pointed at
// 127.0.0.1) goes with it; the front page is the founder god view (crew#459).
import {
  createFrontendModule,
  PageBlueprint,
} from '@backstage/frontend-plugin-api';

const estateHomePage = PageBlueprint.make({
  params: {
    path: '/',
    loader: () => import('./EstateHome').then(m => <m.EstateHome />),
  },
});

// /pair: the founder types Moonlight's PIN into the portal and it reaches Sunshine on the
// Mac over the proxy (crew#562, founder-screen-access path 1). Listed as a founder surface
// in backstage/founder/catalog-info.yaml so the crew#401 gate and the god view carry it.
const pairPhonePage = PageBlueprint.make({
  name: 'pair',
  params: {
    path: '/pair',
    loader: () => import('./PairPhone').then(m => <m.PairPhone />),
  },
});

export const homeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [estateHomePage, pairPhonePage],
});
