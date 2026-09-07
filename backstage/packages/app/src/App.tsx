import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
// Visual estate map at /catalog-graph: every system and its relations as a navigable graph.
// A buyer's engineer reads the whole estate in one view (crew#612 10x, 2026-08-31).
import catalogGraphPlugin from '@backstage/plugin-catalog-graph/alpha';
// The Kubernetes plugin's API is what the front page reads the cluster through (crew#459).
import kubernetesPlugin from '@backstage/plugin-kubernetes/alpha';
// Declared in package.json and wired in the backend since crew#459, but never added here, so
// /search, /docs, /create, /api-docs and /settings answered 404. The nav has linked to them
// the whole time.
import searchPlugin from '@backstage/plugin-search/alpha';
import techdocsPlugin from '@backstage/plugin-techdocs/alpha';
import scaffolderPlugin from '@backstage/plugin-scaffolder/alpha';
import userSettingsPlugin from '@backstage/plugin-user-settings/alpha';
import apiDocsPlugin from '@backstage/plugin-api-docs/alpha';
// The front page is Backstage's own home page (founder, 2026-09-01: "use Backstage templates").
// The widgets still come from that plugin. The drag-and-resize board does not
// (founder 2026-09-03). Layout lives in modules/home/homeLayout.tsx.
import homePlugin from '@backstage/plugin-home/alpha';
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';
import { signInModule } from './modules/signin';
import { catalogFiltersModule } from './modules/catalog';
import { estateDetailModule } from './modules/estateDetail';
import { themeModule } from './modules/theme';
import { wordsModule } from './modules/i18n';
// Live numbers on every cluster entity: the Prometheus tab (founder 2026-08-29, crew#645 CP5).
import { metricsPlugin } from './modules/metrics';
// crew#857: the scaffolder form reads the feature register (features.yaml) at
// render time and shows prices from the pre-computed plan (plan.json).
import { featureRegisterModule } from './modules/featureRegister';

export default createApp({
  features: [
    catalogPlugin,
    catalogGraphPlugin,
    kubernetesPlugin,
    searchPlugin,
    techdocsPlugin,
    scaffolderPlugin,
    apiDocsPlugin,
    homePlugin,
    userSettingsPlugin,
    navModule,
    homeModule,
    signInModule,
    catalogFiltersModule,
    estateDetailModule,
    themeModule,
    wordsModule,
    metricsPlugin,
    featureRegisterModule,
  ],
});
