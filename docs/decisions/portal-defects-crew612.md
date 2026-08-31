# Portal defects fixed in one pass

Five portal defects the founder named on [the portal-defects
ticket](https://github.com/chidionyema/crew/issues/612), fixed in the files that own them
and nowhere else. Authored with Cursor on 2026-08-31; delivered as one pull request.

## What changed and why

1. **Brand.** `app.title` and `organization.name` in `backstage/app-config.yaml` read
   Mumchimp; the portal is the estate portal, not the store. Both now read Bytesync.
   `LogoFull`/`LogoIcon` already render from `app.title`, so the sidebar wordmark, the
   icon letter and the browser tab follow the config with no component edit.
2. **Create menu.** The scaffolder plugin was registered on the server side and in
   `app-config.yaml` catalog locations, but never added to the portal app, so `/create`
   answered 404 while the nav pointed at it. `scaffolderPlugin` is now a feature in
   `App.tsx` and the nav carries a Create item.
3. **Duplicate gear icon.** Kubernetes and Ops both used a gear; Kubernetes now uses
   `DnsIcon` so each nav item reads as itself.
4. **Hash-jump routes.** `/#screens` and `/#kubernetes` were anchors into a page that no
   longer lays out that way; the nav now points at the real catalog route with kind
   filters, and the screens section is reached by scrolling the home page it sits on.
5. **Map.** The catalog-graph plugin is wired at `/catalog-graph` with a Map nav item:
   every system and its relations in one navigable view. Home inventory chips moved above
   the service cards so the estate count is visible without scrolling.

## What was left alone, deliberately

- SQLite `:memory:` in `app-config.yaml` is local-dev only; production loads
  `app-config.production.yaml` (Postgres via `${POSTGRES_HOST}`). Unchanged.
- The pre-existing `tsc` error in `modules/metrics/index.tsx` (missing upstream types)
  predates this change and is not touched by it.

## Naming note

Bytesync is the name the catalogue hierarchy uses today; the parent-company name is an
open decision on [the company-name ticket](https://github.com/chidionyema/crew/issues/691).
If that decision lands a different name, the fix is the same two config lines this change
touched.
