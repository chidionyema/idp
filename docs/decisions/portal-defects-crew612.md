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


## 2026-09-01: The phone had no menu, and the front page was ours

Founder, on his phone, looking at the live portal: "where the fuck is the menu"; "why would
someone scroll to bottom of page to see menu"; "I need things organised so I can find
information quickly, not scrolling and wondering"; "use Backstage templates"; "our UI and
design skills are shit"; "so don't bother." Five review rounds had graded desktop screenshots
only. Two defects, one fix each, no design of our own:

6. **The phone menu.** Backstage's Sidebar folds into a bottom bar under 600px. The nav
   (`modules/nav/EstateNav.tsx`) now switches on that same breakpoint to Material UI's own
   `Drawer` anchored left, behind a button a screen reader calls "Open menu," listing the ten
   doors in order; the desktop Sidebar is untouched. `bin/idp-login-drill` reads the page at
   390px every hour, opens the menu by its spoken name, fails unless all ten doors are on
   screen, and photographs `home-phone.png`, `home-phone-menu.png`, `create-phone.png` and
   `create.png` into the run's artifact. It also counts Template entities and fails on zero.
7. **The front page.** "/" was 1,200 lines of this repository's own design (the god view from the earlier redesign)
   in one long scroll. It is now Backstage's own home page: `@backstage/plugin-home` 0.9.9 is
   loaded in `App.tsx`, the module no longer overrides `page:home`, and `app-config.yaml`
   seeds the grid (search bar, the ten doors as the toolkit, starred entities, recently and
   most visited) with the plugin's documented `defaultConfig`. The layout is the documented
   custom-layout template (Page, Header, Content, CustomHomepageGrid) with the estate's name
   in the header. The god view is kept at `/estate`, unlinked, graded by the drill, until its
   numbers become widgets or it is deleted. Research on record: the plugin's changelog entry
   for 0.9.9 ("new frontend system widget blueprints ... `defaultConfig`") and the docs page
   https://backstage.io/docs/getting-started/homepage/ ; the extension ids and config keys
   were read from the published 0.9.9 tarball's `dist/alpha.esm.js`, not from memory.

Test: `tests/test_crew612_portal_doors_are_real_and_distinct.py` (phone menu, front page,
toolkit equals menu). Founder receipt: none yet; he sees it on his phone after his deploy.
