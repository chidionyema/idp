# Onboarding: portal catalogue overlay

This page is for anyone picking up the buyer-facing catalogue, or reviewing it
for the first time.

## What it is for

The portal is the estate's front door. This overlay makes the catalogue page list
every kind (not owned components only), names the menu in plain English, and uses
Backstage's own NFS cursor pagination plus official UI tokens.

## What it costs

Nothing extra in production: the same Backstage image, the same Oracle login.
Locally it is `yarn start` in `backstage/` (frontend on 3100, backend on 7107).

## Where it lives

```
backstage/app-config.yaml                          catalogue filters and pagination
backstage/packages/app/src/modules/nav/EstateNav.tsx   first-five menu, More submenu
backstage/packages/app/src/estate-bui.css          Backstage UI token overlay
backstage/packages/app/src/modules/i18n/           words the visitor reads
docs/decisions/0016-the-catalogue-is-the-whole-catalogue.md
```

## How to stop it

Revert this branch. Do not leave a second catalogue feed or a hand-drawn nav
in its place.

## How to turn it back on

Merge the pull request and let Flux roll the Backstage image.
