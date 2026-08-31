import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
// The Kubernetes plugin's API is what the front page reads the cluster through (crew#459).
import kubernetesPlugin from '@backstage/plugin-kubernetes/alpha';
// Templates on /create are the self-service menu (crew#612 item 1, founder 2026-08-31).
import scaffolderPlugin from '@backstage/plugin-scaffolder/alpha';
import { navModule } from './modules/nav';
import { homeModule } from './modules/home';
import { signInModule } from './modules/signin';
import { themeModule } from './modules/theme';
// Live numbers on every cluster entity: the Prometheus tab (founder 2026-08-29, crew#645 CP5).
import { metricsPlugin } from './modules/metrics';

export default createApp({
  features: [
    catalogPlugin,
    kubernetesPlugin,
    scaffolderPlugin,
    navModule,
    homeModule,
    signInModule,
    themeModule,
    metricsPlugin,
  ],
});
