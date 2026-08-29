import { createApp } from '@backstage/frontend-defaults';
import catalogPlugin from '@backstage/plugin-catalog/alpha';
// The Kubernetes plugin's API is what the front page reads the cluster through (crew#459).
import kubernetesPlugin from '@backstage/plugin-kubernetes/alpha';
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
    navModule,
    homeModule,
    signInModule,
    themeModule,
    metricsPlugin,
  ],
});
