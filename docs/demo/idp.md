# Demo — the estate portal

Two portals over one catalogue. This is a real run, captured 2026-08-24, not an
illustration. Every line below came out of the commands above it.

## Building both renderings from one source

Both generators read the same file, `~/.estate/state/inventory.json`, which the
hourly inventory job writes. Neither generator stores anything of its own, so if
the inventory is wrong both portals are wrong in the same way at the same time —
which is the point. Two portals that could disagree would be two sources of truth.

```
$ bin/db-gen
db-gen: 194 rows -> /Users/chidionyema/dev/code/idp/catalog/estate.db
[{"table": "assets", "count": 194},
 {"table": "meta", "count": 1}]

$ bin/catalog-gen
catalog-gen: 194 entities -> /Users/chidionyema/dev/code/idp/catalog/catalog-info.yaml
  data           10
  drill          13
  guard          32
  ledger         70
  repo           23
  scheduled_job  43
```

194 assets in, 194 rows and 194 entities out.

## The fallback answering

Datasette is the fallback renderer. It runs on Python and has no build step, so
it is up in under a second and a broken Node install cannot touch it.

```
$ curl -s http://127.0.0.1:8001/-/versions.json | jq -c "{datasette:.datasette.version, sqlite:.sqlite.version}"
{"datasette":"0.65.3","sqlite":"3.53.2"}
```

## The five numbers diligence starts with

This is a saved SQL query, served over HTTP. A stranger can open the page, read
the SQL that produced each number, edit it, and re-run it. Nothing here is
asserted by anyone.

```
$ curl -s "http://127.0.0.1:8001/estate/risk_summary.json?_shape=array" | jq -c ".[]"
{"risk":"repos with no licence file","n":17}
{"risk":"drills never run","n":5}
{"risk":"repos with uncommitted work","n":17}
{"risk":"repos not backed up offsite","n":1}
{"risk":"assets coupled to one provider","n":113}
```

Those are not comfortable numbers, and they are on the front page on purpose.
A platform that shows only what works reads as one nobody has examined.

## Drilling into one of them

Each count is a link to the rows behind it.

```
$ curl -s "http://127.0.0.1:8001/estate/repos_without_licence.json?_shape=array" | jq -r ".[].id" | head -6
.estate
.claude
AwesomeProject
crew
ebookStore
ecommerce-clean
```

Seventeen repositories carry no licence file, which means nobody currently has
the right to use them — including a buyer. Named here rather than found by
somebody else later.

## What the switch looks like

Both renderers are already running at their own URLs, so the 0-second switch is
opening the other link. The 10-second switch is for when the link itself has been
handed out and the thing behind it has to change:

```
$ bin/idp-switch fallback
was:  |-- / proxy http://127.0.0.1:8001
now:  http://chidis-macbook-pro.tail3f2ff4.ts.net:8443/  ->  Datasette (127.0.0.1:8001, HTTP 200)
live: the tailnet listener answered 200 in 0.031880s
```

The command refuses if the renderer it is switching to is not answering, and it
proves the switch by asking the published listener rather than by saying it
worked.

## What the tailnet listener is actually serving

Two angles on the same fact. First what Tailscale says it is proxying:

```
$ tailscale serve status
http://chidis-macbook-pro:8443 (tailnet only)
http://chidis-macbook-pro.tail3f2ff4.ts.net:8443 (tailnet only)
|-- / proxy http://127.0.0.1:8001
```

Then what comes back when you ask it:

```
$ curl -sS -H 'Host: chidis-macbook-pro.tail3f2ff4.ts.net:8443' http://100.112.51.80:8443/ \
    | grep -o '<title>[^<]*</title>'
<title>Estate catalogue — fallback renderer: estate</title>
```

The Host header is there because this Mac does not resolve its own MagicDNS
name. Other devices on the tailnet do, so a name lookup from here would report
a failure that is not one.

## Proving the portal is not quietly wrong

The first time Backstage ingested this catalogue it took 53 of the 194 entities
and rejected the rest. The page rendered perfectly. Nothing went red. The reason
was one line in the backend log:

```
catalog warn Policy check failed for resource:default/no-anthropic; caused by
Error: Malformed envelope, /metadata/annotations/estate~1age-h must be string
```

The generator was writing `estate/age-h: 3`, which YAML reads as a number, and
Backstage requires annotation values to be strings. Three quarters of the estate
was missing from a portal that looked finished.

So `bin/idp-verify` compares what the generator wrote against what each renderer
actually serves, and names what is missing:

```
$ bin/idp-verify --wait
source    194 entities in catalog-info.yaml
fallback  194 rows served over HTTP -- matches
          waiting: 2 of 194 not ingested yet
primary   all 194 entities ingested by Backstage -- matches

PASS      both renderers agree with the inventory: 194 entities
```

A check that has only ever been seen passing is not a check. One deliberately
malformed entity was added to the catalogue to see it fail:

```
$ bin/idp-verify
source    195 entities in catalog-info.yaml
FAIL      fallback serves '194', expected 195 (db has 194, HTTP 200)
FAIL      primary is missing 1 of 195 entities:
            Resource/zz-guard-paired-control
          look for 'Policy check failed' in logs/backstage.log

FAIL      the portal does not match the inventory
$ echo $?
1
```

It names the entity rather than reporting a count, catches it in both renderers
independently, and exits 1. The malformed entity was then removed and the check
returned to PASS, which is the run above.
