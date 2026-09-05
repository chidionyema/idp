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
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';
import { signInModule } from './modules/signin';
import { themeModule } from './modules/theme';
// Live numbers on every cluster entity: the Prometheus tab (founder 2026-08-29, crew#645 CP5).
import { metricsPlugin } from './modules/metrics';

export default createApp({
  features: [
    catalogPlugin,
    catalogGraphPlugin,
    kubernetesPlugin,
    searchPlugin,
    techdocsPlugin,
    scaffolderPlugin,
    apiDocsPlugin,
    userSettingsPlugin,
    navModule,
    homeModule,
    signInModule,
    themeModule,
    metricsPlugin,
  ],
});
