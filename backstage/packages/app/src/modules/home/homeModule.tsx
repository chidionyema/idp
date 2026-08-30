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

// /tools: every door on one page, grouped from the catalogue (crew#684 CP0, founder
// 2026-08-30: "another page in backstage just pure tools"). Listed as a founder surface in
// backstage/founder/catalog-info.yaml so the crew#401 gate and the login drill carry it.
const toolsPage = PageBlueprint.make({
  name: 'tools',
  params: {
    path: '/tools',
    loader: () => import('./Tools').then(m => <m.Tools />),
  },
});

// crew#684 CP1: the Ops dashboard, "I need to see everything". The cluster tile first; the
// open-reds table, founder tiles and the drills row land on the same page in later checkpoints.
const opsPage = PageBlueprint.make({
  name: 'ops',
  params: {
    path: '/ops',
    loader: () => import('./Ops').then(m => <m.Ops />),
  },
});

export const homeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [estateHomePage, pairPhonePage, toolsPage, opsPage],
});
