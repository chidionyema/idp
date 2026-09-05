/*
 * Hi!
 *
 * Note that this is an EXAMPLE Backstage backend. Please check the README.
 *
 * Happy hacking!
 */

import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

backend.add(import('@backstage/plugin-app-backend'));
backend.add(import('@backstage/plugin-proxy-backend'));

// scaffolder plugin
backend.add(import('@backstage/plugin-scaffolder-backend'));
backend.add(import('@backstage/plugin-scaffolder-backend-module-github'));
backend.add(
  import('@backstage/plugin-scaffolder-backend-module-notifications'),
);

// crew#857: serves the feature register (features.yaml) and pre-computed
// plan (plan.json) from the ConfigMap mounted at /app/feature-register/.
// The scaffolder custom field extension reads these to render the store
// form with live prices and fit.
backend.add(import('./featureRegister'));

// techdocs plugin
backend.add(import('@backstage/plugin-techdocs-backend'));

// auth plugin
backend.add(import('@backstage/plugin-auth-backend'));
// The estate front door signs people in; Backstage trusts its headers (src/auth).
backend.add(import('./auth'));
// Official guest provider for `yarn start` only. The production image sets
// NODE_ENV=production and does not register this module, so the live catalogue
// stays on the front door. Do not set dangerouslyAllowOutsideDevelopment here.
if (process.env.NODE_ENV !== 'production') {
  backend.add(import('@backstage/plugin-auth-backend-module-guest-provider'));
}

// catalog plugin
backend.add(import('@backstage/plugin-catalog-backend'));
backend.add(
  import('@backstage/plugin-catalog-backend-module-scaffolder-entity-model'),
);

// See https://backstage.io/docs/features/software-catalog/configuration#subscribing-to-catalog-errors
backend.add(import('@backstage/plugin-catalog-backend-module-logs'));

// Every Dagster asset, job and schedule becomes a catalogue entity by polling Dagster's GraphQL
// API on catalog.providers.dagster.schedule; no hand-written entity for scheduler work (crew#468).
backend.add(
  import('catalog-backend-module-dagster-entity-provider'),
);

// permission plugin
backend.add(import('@backstage/plugin-permission-backend'));
// See https://backstage.io/docs/permissions/getting-started for how to create your own permission policy
backend.add(
  import('@backstage/plugin-permission-backend-module-allow-all-policy'),
);

// search plugin
backend.add(import('@backstage/plugin-search-backend'));

// search engine
// See https://backstage.io/docs/features/search/search-engines
backend.add(import('@backstage/plugin-search-backend-module-pg'));

// search collators
backend.add(import('@backstage/plugin-search-backend-module-catalog'));
backend.add(import('@backstage/plugin-search-backend-module-techdocs'));

// kubernetes plugin
backend.add(import('@backstage/plugin-kubernetes-backend'));

// user settings plugin
backend.add(import('@backstage/plugin-user-settings-backend'));

// notifications and signals plugins
backend.add(import('@backstage/plugin-notifications-backend'));
backend.add(import('@backstage/plugin-signals-backend'));

// mcp actions plugin
backend.add(import('@backstage/plugin-mcp-actions-backend'));

backend.start();
