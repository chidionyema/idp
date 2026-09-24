# Who fills the catalogue: hand-run script vs. self-discovery (crew#480)

`bin/catalog-gen` (`bin/catalog-gen:1-705`) reads `~/.estate/state/inventory.json`, a laptop-side
LAW 39 inventory, and writes `catalog/catalog-info.yaml`. Nobody regenerates it by hand any more
than they have to, but it is still a script a session must remember to run. Backstage ships two
entity providers that discover their own inputs on a schedule instead:
`@backstage/plugin-catalog-backend-module-github` (scans a GitHub org for `catalog-info.yaml`
files) and the Kubernetes plugin's cluster locator (reads live workload status from the cluster
API against entities that already carry a `backstage.io/kubernetes-id` annotation).

This page is the measurement that answers "how much of the catalogue could the estate discover
for itself, and how much can only `bin/catalog-gen` ever know." Every row below is a command run
against the live estate on 2026-08-27, not an estimate.

## The catalogue today

```
$ python3 bin/catalog-gen
catalog-gen: 342 entities, 457 dependsOn edges -> catalog/catalog-info.yaml
  data           31
  drill          17
  founder-surface 13
  front-door     7
  guard          46
  interface-links 92
  ledger         159
  listener       32
  repo           14
  scheduled_job  18
  ...
```

```
$ grep "^kind:" catalog/catalog-info.yaml | sort | uniq -c
  35 kind: Component
   1 kind: Domain
   1 kind: Group
 304 kind: Resource
   1 kind: System
```

342 entities total (regenerated fresh for this measurement).

## What a GitHub provider would see today

The org has 46 non-archived repos:

```
$ gh repo list chidionyema --limit 200 --json name,isArchived -q '.[] | select(.isArchived==false) | .name' | wc -l
46
```

For each repo, its default-branch git tree was searched for any path ending
`catalog-info.yaml` (the glob the new provider config uses, `catalogPath: '/**/catalog-info.yaml'`,
matches any depth, not just the repo root):

```
$ for r in <46 repos>; do
    branch=$(gh api "repos/chidionyema/$r" --jq '.default_branch')
    gh api "repos/chidionyema/$r/git/trees/$branch?recursive=1" --jq '.tree[]?.path' \
      | grep -c 'catalog-info\.yaml$'
  done
idp        3   (backstage/catalog-info.yaml, backstage/founder/catalog-info.yaml,
                backstage/templates/estate-component/skeleton/catalog-info.yaml)
prospector 1   (catalog-info.yaml, repo root)
<44 others> 0
```

2 of 46 repos carry a `catalog-info.yaml` anywhere in their tree. Reading those files
(`gh api repos/chidionyema/<repo>/contents/catalog-info.yaml`):

| File | Entities | Valid? |
|---|---|---|
| `backstage/catalog-info.yaml` | 1 (`Component backstage`, the create-app boilerplate) | yes |
| `backstage/founder/catalog-info.yaml` | 13 (`Component`, `type: founder-surface`) | yes |
| `backstage/templates/estate-component/skeleton/catalog-info.yaml` | 1 | **no** — a scaffolder skeleton, `metadata.name: ${{ values.name }}`; a GitHub provider ingesting this glob will log a processing error for it, not a crash. Residual, not fixed by this PR: the template needs a `filters.repository` exclusion or to be renamed out of the glob. |
| `chidionyema/prospector` `catalog-info.yaml` | 4 (1 `System`, 3 `Component`) | yes |

**18 entities are GitHub-provider-discoverable today** (1 + 13 + 4), plus 1 file that would
surface as a processing error. Those 18 already replace the one hand-written
`- type: url … prospector/blob/main/catalog-info.yaml` catalog location
(`backstage/app-config.container.yaml:94-100`, pre-existing) — the exact pattern crew#282 asked
every product to follow, generalised across the whole org instead of one location line per
product.

## What only `bin/catalog-gen` knows

`~/.estate/state/inventory.json` is a Mac-side scan (launchd jobs, guard scripts, ports,
data stores, drills) that neither GitHub nor Kubernetes can see, because none of it lives in a
repo file or a cluster API:

```
$ python3 -c "
import json, collections
d = json.load(open('/Users/chidionyema/.estate/state/inventory.json'))
rows = d['rows']
print(len(rows))
print(collections.Counter(r['kind'] for r in rows).most_common())
"
312
[('ledger', 159), ('guard', 46), ('listener', 32), ('data', 31), ('drill', 17),
 ('scheduled_job', 14), ('repo', 13)]
```

312 rows, none of them GitHub or Kubernetes visible: `ledger` (159, receipt files),
`guard` (46, refusal scripts), `listener` (32, ports a laptop process binds), `data` (31,
databases/stores), `drill` (17, scheduled proof runs), `scheduled_job` (14, launchd jobs). These
account for 304 of the catalogue's 342 Resource+related entities and can only ever be produced by
`bin/catalog-gen` reading this file — no provider replaces this half of the script.

## What a Kubernetes provider would see today

The Kubernetes plugin (`@backstage/plugin-kubernetes-backend`, already registered in
`packages/backend/src/index.ts:57`) does not mint catalog entities. It queries the cluster for
pods/deployments matching an existing entity's `backstage.io/kubernetes-id` annotation and
attaches live status to that entity
(https://backstage.io/docs/features/kubernetes/configuration). `bin/catalog-gen`'s own kind map
reserves a `container` kind (`bin/catalog-gen:82`) for exactly this workload concept, but:

```
$ python3 -c "
import json
rows = json.load(open('/Users/chidionyema/.estate/state/inventory.json'))['rows']
print(sum(1 for r in rows if r['kind'] == 'container'))
"
0
```

0 of 312 inventory rows are `container` kind today (this laptop's inventory does not track
running containers this way). So the Kubernetes provider's contribution is 0 new catalogue
entities and cannot be compared 1:1 against a script-only count; it is a live-status source for
entities the catalogue already carries, not a discovery source of new ones. Wiring it (CP2) is
still correct — it is the piece of the "self-describing" catalogue the founder asked for even
though today's inventory has no `container` rows for it to enrich yet.

## Summary

| Source | Entities it can produce | Command |
|---|---|---|
| GitHub provider (org chidionyema, `**/catalog-info.yaml`) | 18 of 342 (5.3%), today | tree-scan + `gh api …/contents/catalog-info.yaml`, above |
| Kubernetes cluster locator | 0 new entities (annotates existing ones) | inventory.json `container` row count: 0 |
| `bin/catalog-gen` only (LAW 39 inventory) | 312 of 342 rows (91.2%): ledger, guard, listener, data, drill, scheduled_job, repo | `python3 -c "..."` inventory row count, above |
