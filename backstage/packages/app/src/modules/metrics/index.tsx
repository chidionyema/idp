// Metrics on every cluster entity's page (founder, 2026-08-29: "i need all metrics exposed ...
// on backstage ... always ... numbers for everything we collect"; crew#645 CP5).
//
// The mature plugin for this is Roadie's Prometheus plugin. It is written for the legacy
// frontend system, so it comes in through Backstage's own compatibility layer: the legacy plugin
// (and its API factory, which talks to the `/prometheus/api` proxy) is converted, and its entity
// content is wrapped so `useEntity` and the API holder resolve inside the new catalog page.
// The Kubernetes tab needs no code here: `@backstage/plugin-kubernetes/alpha` in App.tsx ships
// it, and it lights up once an entity carries `backstage.io/kubernetes-namespace` and
// `backstage.io/kubernetes-label-selector`, which bin/catalog-gen now writes for every Flux row
// and Helm chart on the cluster.
import { compatWrapper, convertLegacyPlugin } from '@backstage/core-compat-api';
import { EntityContentBlueprint } from '@backstage/plugin-catalog-react/alpha';
import {
  backstagePluginPrometheusPlugin,
  EntityPrometheusContent,
  isPrometheusAvailable,
} from '@roadiehq/backstage-plugin-prometheus';

const metricsContent = EntityContentBlueprint.make({
  name: 'metrics',
  params: {
    path: '/metrics',
    title: 'Metrics',
    filter: isPrometheusAvailable,
    loader: async () =>
      compatWrapper(
        <EntityPrometheusContent
          // Recording rules are evaluated every minute (platform/monitoring/rules/capacity.yaml);
          // one hour at one-minute steps is the window a boot or a crash loop shows up in.
          step={60}
          range={{ hours: 1 }}
          showAlertsAnnotations
        />,
      ),
  },
});

export const metricsPlugin = convertLegacyPlugin(backstagePluginPrometheusPlugin, {
  extensions: [metricsContent],
});
