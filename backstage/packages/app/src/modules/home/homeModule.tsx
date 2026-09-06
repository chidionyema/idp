// The front page at "/" is still Backstage's home plugin (page:home, widgets from
// app-config.yaml). The drag-and-resize board is gone: HomePageLayoutBlueprint lets
// us arrange those same widgets in a fixed layout (founder 2026-09-03: outdated look
// and outdated interactions). The god view from crew#459 stays at /estate.
import { createFrontendModule, PageBlueprint } from '@backstage/frontend-plugin-api';
import { HomePageLayoutBlueprint } from '@backstage/plugin-home-react/alpha';
import { EstateHomeLayout } from './homeLayout';

const homeLayout = HomePageLayoutBlueprint.make({
  params: {
    loader: async () => EstateHomeLayout,
  },
});

// /estate: the crew#459 god view, one card per founder-surface entity, kept off the front
// page and off the menu. Graded by bin/idp-login-drill like every other published path.
const estatePage = PageBlueprint.make({
  name: 'estate',
  params: {
    path: '/estate',
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

// /reports (crew#684, founder 2026-09-01: "can we automate all reports, need report tab in
// Backstage"): every report the estate writes on a clock, read from docs/reports/index.json on
// the state branch through the /estate-state proxy, red when older than twice its schedule.
// Listed as a founder surface in backstage/founder/catalog-info.yaml so the crew#401 gate and
// the login drill carry it.
const reportsPage = PageBlueprint.make({
  name: 'reports',
  params: {
    path: '/reports',
    loader: () => import('./Reports').then(m => <m.Reports />),
  },
});

// /investigate (founder 2026-09-05: "no i would need to be able to aks it fron telegrn and
// backstage also"): ask HolmesGPT a question in plain English and read what it found. The other
// front door onto the same investigator is the ask_holmes tool on the estate MCP server, which
// is how Otto answers it on Telegram. Listed as a founder surface in
// backstage/founder/catalog-info.yaml so the crew#401 gate and the login drill carry it.
const investigatePage = PageBlueprint.make({
  name: 'investigate',
  params: {
    path: '/investigate',
    loader: () => import('./Investigate').then(m => <m.Investigate />),
  },
});

// /showcase (docs/specs/backstage-as-a-product.md CP1, founder 2026-09-05: "showcase needs to
// wow and impress"): the page a buyer's engineer opens first. The graded estate bar off the state
// branch, every system's health drawn live from the cluster, and what Otto does on the door today
// with a receipt per line. Listed as a founder surface in backstage/founder/catalog-info.yaml so
// the crew#401 gate and the login drill carry it.
const showcasePage = PageBlueprint.make({
  name: 'showcase',
  params: {
    path: '/showcase',
    loader: () => import('./Showcase').then(m => <m.Showcase />),
  },
});

export const homeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [
    homeLayout,
    estatePage,
    pairPhonePage,
    toolsPage,
    opsPage,
    reportsPage,
    investigatePage,
    showcasePage,
  ],
});
