# Demo: db-gen

`bin/db-gen` loads the estate inventory into a SQLite database, so anything
that needs to count the inventory can query a file instead of asking Backstage
or re-reading the JSON. Run against a fixture:

```
$ tmp=$(mktemp -d)
$ INV=tests/fixtures/inventory.json DB="$tmp/estate.db" SU="$(command -v sqlite-utils)" bin/db-gen
db-gen: 8 rows -> .../estate.db
[{"table": "assets", "count": 8},
 {"table": "meta", "count": 1}]
```

An inventory with zero rows is refused rather than written, because an empty
database renders as a healthy, empty portal and nothing distinguishes that
from "the inventory really is empty":

```
$ echo '{"rows": []}' > /tmp/empty-inv.json
$ INV=/tmp/empty-inv.json DB="$tmp/estate.db" SU="$(command -v sqlite-utils)" bin/db-gen
db-gen: inventory has 0 rows -- refusing to write an empty database
```

Each run writes to a per-process temp file before replacing the database, so
two `db-gen` runs sharing one machine cannot both insert into the same
half-built file — the incident that once produced 478 rows for 239 real
assets when `idp-up` and a hand run collided. `bin/idp-ci` runs two `db-gen`s
concurrently against the same fixture and checks the row count comes out
exactly right.
