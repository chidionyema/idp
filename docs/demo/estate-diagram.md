# Demo: estate-diagram

R29 (founder, 2026-08-25): diagrams are generated from what is running; a hand-drawn one
is deleted. `bin/estate-diagram` reads `catalog/catalog-info.yaml` (itself generated from
`~/.estate/state/inventory.json` by `bin/catalog-gen`) and writes `docs/architecture/live.md`.

```
$ bin/catalog-gen && bin/estate-diagram
estate-diagram: 129 lines -> docs/architecture/live.md
$ bin/estate-diagram --check
ok    estate-diagram: .../docs/architecture/live.md matches the catalogue
$ echo "hand drawn" >> docs/architecture/live.md && bin/estate-diagram --check; echo rc=$?
FAIL  estate-diagram: .../live.md is not what .../catalog-info.yaml says; run bin/estate-diagram
rc=1
```

The page opens in the portal under Architecture → Live estate. The Mermaid graph shows each
repository with its job, guard and ledger counts, every listening port attached to the checkout
that runs it, and vendor coupling as dotted edges. The table below it lists every scheduled job
with interval, last status and owner.
