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
backend.add(import('./credentialIngest'));

// techdocs plugin
backend.add(import('@backstage/plugin-techdocs-backend'));

// auth plugin
backend.add(import('@backstage/plugin-auth-backend'));
// The estate front door signs people in; Backstage trusts its headers (src/auth).
backend.add(import('./auth'));
// Guest provider. Until 2026-10-03 it was `yarn start` only (production did not
// register this module). RC-1b (founder, 2026-10-03: "open the anonymous lane"):
// a visitor whose front-door exchange failed can still speak to /face -- the
// sign-in error screen offers the guest provider as a fallthrough, and the voice
// door itself is anonymous and rate-limited at the edge (overlays/oke/httproute.yaml).
// This session only mounts the SPA; it grants no API authority beyond what the
// route already lets any Bearer-less visitor do.
backend.add(import('@backstage/plugin-auth-backend-module-guest-provider'));

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

// Every .py module in the estate becomes a catalogue entity by running
// `bin/catalog-projection --json` on a schedule; the projection is a pure
// deterministic function over source, so the catalogue cannot drift from the
// code (crew#740 CP6). No hand-written entity for projection work.
backend.add(
  import('catalog-backend-module-estate-projection'),
);

// permission plugin
backend.add(import('@backstage/plugin-permission-backend'));
// Gates scaffolder templates tagged founder-action to group:default/platform; every other
// permission (catalog browsing, search, techdocs, notifications, kubernetes, ...) stays
// allowed. See src/permissionPolicy.ts for why this is a catalog-entity policy.
backend.add(import('./permissionPolicy'));

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
