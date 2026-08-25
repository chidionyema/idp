# Onboarding: catalog-gen and catalog-refcheck

## What they are

`bin/catalog-gen` is a thin adapter: it reads the estate inventory JSON and
writes `catalog-info.yaml` in Backstage's entity format. `bin/catalog-refcheck`
is the gate that checks every reference in a catalogue file resolves to a
defined entity, and refuses when two documents claim the same reference.

## Why they exist

The inventory is the asset (LAW 39: inventory every asset or you build it
twice); `catalog-gen` only translates it into a format the portal can render.
That is deliberate — if Backstage is wrong for this estate in a year, this
adapter changes its output shape and the underlying inventory does not move.
`catalog-refcheck` exists because Backstage resolves a reference lazily: a
`dependsOn` or `owner` naming an entity that does not exist renders as an
ordinary link and only fails when a person clicks it, so a broken catalogue
can look complete in the portal. This is the check that catches it before
merge instead of a buyer's engineer catching it in the demo.

`catalog-gen` also refuses to label the estate's `lifecycle` wrongly: earlier
it hardcoded `production` on every component, which told anyone reading the
portal that a laptop was the production estate. The environment is now
resolved from `$ESTATE_ENV`, then `~/.estate/env`, and falls back to `dev` —
the fallback that makes the reader careful rather than the one that makes
them relaxed.

## When they run

`bin/idp-ci` runs `catalog-gen` against a fixture inventory and checks: the
entity/edge counts, that two concurrent runs cannot double-count assets (the
incident that motivated the per-process scratch file), that two runs over the
same inventory produce byte-identical output, and that a port claimed twice in
the inventory is refused. `catalog-refcheck` then runs against the generated
file and against a deliberately dangling one, proving it discriminates both
ways.

## Related files

```
bin/catalog-gen                       inventory -> catalog-info.yaml
bin/catalog-refcheck                  refuses a catalogue with dangling refs
~/.estate/state/inventory.json        the source (LAW 39)
catalog/                              ports.yaml, reconcile.yaml, manifests -- catalog-gen's OUT default
tests/fixtures/inventory.json         the fixture bin/idp-ci proves against
```
