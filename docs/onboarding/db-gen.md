# Onboarding: db-gen

## What it is

`bin/db-gen` loads the estate inventory JSON into a SQLite database using
`sqlite-utils insert`, so `bin/idp-status` and anything else that wants an
asset count can query a file rather than run a service. It refuses to write a
database when the inventory has zero rows, because an empty database looks
identical to a healthy one with nothing in it.

## Why it exists

It used to be one of two renderings of the same inventory, feeding a Datasette
fallback portal on port 8001. The founder killed that second portal on
2026-08-24 ("ive seen 5 ui faces today"); this remained because it answers a
real question — how many assets does the inventory hold — without a running
service. Neither this database nor the catalogue YAML is the source of truth;
the source is `~/.estate/state/inventory.json`, produced by LAW 39's inventory
job.

It is `sqlite-utils` rather than a hand-written loader on purpose: the
transform is "put this JSON array into a table", which is the one thing
`sqlite-utils` exists to do, and a bespoke script here would be a worse copy
of it.

## When it runs

Whenever the estate inventory needs to be queryable as a database — after
`bin/idp-up`, and inside `bin/idp-ci`, which runs two `db-gen`s concurrently
against a shared fixture to prove the per-process scratch file (`$DB.tmp.$$`)
stops two runs from corrupting one shared temp file, the exact incident that
once doubled the row count on 2026-08-24.

## Related files

```
bin/db-gen                     inventory JSON -> SQLite
bin/catalog-gen                the sibling renderer, into Backstage YAML instead
~/.estate/state/inventory.json the source (LAW 39)
catalog/estate.db              the default output path (DB env var overrides it)
bin/idp-status                 reads this database for the asset count
```
