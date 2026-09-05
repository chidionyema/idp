# Demo: estate-showcase

Founder, 2026-08-27 (crew#474): "if any part of estate does not meet elite grade status shout
out loud, we need to expose ourselves before the market exposes us and correct it."

## The command

    cd ~/dev/code/idp && ESTATE_CODE=~/dev/code bin/estate-showcase

## What it printed (2026-08-27)

```
estate-showcase: 403 lines, 31 GAP rows -> docs/SHOWCASE.md
- Entities: **287 ELITE**, **31 GAP**, **49 BLIND** of 367
- Standards rows: **10 live**, **12 not yet** of 22
- Science: 15 rows on the science page, 2 BLIND
```

## What that run established

Every entity in the catalogue got a grade from its own annotations, the GAP rows were written
before any ELITE row, and the standards rows that are not yet live were listed with their
status. The 49 BLIND rows are entities whose deciding annotation the inventory has not
produced; they are never counted as ELITE.

## What it looks like when it cannot measure

No catalogue: `BLIND estate-showcase: no catalogue at ... (run bin/catalog-gen)`, exit 3.
No standards table or science page: a BLIND row on the page naming the path it expected.

## Where it runs

`bin/catalog-render` renders it after `bin/estate-diagram` on every `com.estate.catalog-render`
run, commits `docs/SHOWCASE.md` on the same branch as the live diagram, and the portal
shows it under "Estate showcase". `bin/estate-showcase --check` exits 1 when the page on
disk drifts from the inputs.
