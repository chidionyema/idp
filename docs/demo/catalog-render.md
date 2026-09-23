# Demo: catalog-render

The second half of crew#236 row 2. `bin/estate-diagram` draws the page; `bin/catalog-render`
puts it on main without a person, after every inventory run.

```
$ bin/catalog-render --dry-run
catalog-render --dry-run: would commit
 docs/architecture/live.md | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
$ bin/catalog-render
catalog-render: docs/architecture/live.md pushed to state/live-diagram, PR #117 set to auto-merge
$ bin/catalog-render
catalog-render: page unchanged since the last render; nothing to commit
```

The pull request lands by itself when `security-scan` and `spec-gate` pass. Main is protected
by required checks with no bypass, so this is the only road to main, and it is the same road
a person takes.
