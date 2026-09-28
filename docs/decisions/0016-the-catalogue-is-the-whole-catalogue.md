# The catalogue is the whole catalogue

Date: 2026-09-02

## Status

Accepted.

## Research (on the record)

Bleeding-edge Backstage UI in 2026 is the New Frontend System (default since
v1.49) plus Backstage UI (BUI) CSS tokens, not Material 3 and not a second
portal. Catalogue completeness is official: `page:catalog` cursor pagination
and `catalog-filter` `initialFilter` in `app-config.yaml`
(https://backstage.io/docs/features/software-catalog/catalog-customization).
English overlays use `TranslationBlueprint`
(https://backstage.io/docs/frontend-system/building-plugins/internationalization).

Adopted: that stack, already in this app (`createApp` from
`@backstage/frontend-defaults`, `@backstage/ui`).

Rejected: a from-scratch Instagram card feed, a second CSS framework, forking
Backstage to rename software-catalog.

## Context

plugin-catalog 2.0.8 defaults the index to kind `component` and list `owned`.
Git holds hundreds of other kinds. They exist in the API and flash behind a
short table.

## Decision

The index opens on every kind and on Everything. Cursor pagination pages the
catalog API, fifty at a time, in the content pane. The menu puts Catalogue,
Health, Docs and You first; Create, Map, Kubernetes, Tools and Find sit under
More. Cryptic plugin English is overlaid, not forked.

## Consequences

A visitor scrolls the catalogue instead of discovering a hidden filter. An
investor is not greeted by Scaffolder. The login drill's graded words (Owner,
Templates, Owned, Search, Catalog Graph) stay.
