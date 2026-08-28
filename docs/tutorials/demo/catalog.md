# Demo: catalog-gen and catalog-refcheck

`bin/catalog-gen` reads the estate inventory (`~/.estate/state/inventory.json`,
produced by LAW 39's inventory job) and writes it out as `catalog-info.yaml`,
the Backstage entity format the portal renders. `bin/catalog-refcheck` then
checks that every reference inside that file — `owner`, `system`, `dependsOn`
and the rest — points at an entity that actually exists in the file.

Run against a fixture inventory:

```
$ tmp=$(mktemp -d)
$ INV=tests/fixtures/inventory.json OUT="$tmp/out" python3 bin/catalog-gen
catalog-gen: 13 entities, 3 dependsOn edges -> .../out/catalog-info.yaml
  container      1
  ledger         1
  listener       2
  repo           3
  scheduled_job  1
  stacks         1  (example)
  vendors        1  (anthropic)
  orphans        4  (asset in no tracked repo -- LAW 24)
  techdocs       0  (repo with an mkdocs.yml)
  well-known     0  (repo carrying github.com/project-slug + backstage.io/source-location)

$ python3 bin/catalog-refcheck "$tmp/out/catalog-info.yaml"
13 entities, 26 references, all resolve
```

A dangling reference — an entity whose `owner:` or `dependsOn:` names
something not defined anywhere in the file — exits 1 and names each offender,
because Backstage resolves references lazily: a broken reference renders as an
ordinary link and 404s only when someone clicks it, so a catalogue can look
complete and be broken. `bin/idp-ci` proves this by building a catalogue with
a reference intentionally left dangling and confirming `catalog-refcheck`
catches it.

`ESTATE_ENV` controls the `lifecycle` label every entity gets
(`dev`/`stage` → `experimental`, `prod` → `production`); with nothing set it
defaults to `dev`, the safer of the two possible mistakes.
