# Demo: the Demo Standard itself (crew#805)

The first machine-rendered demo is the estate compiler's. Its script is `demos/intent-compiler.tape`;
CI (`demo-render` workflow) replays it against the real `bin/intent-compile` and commits the
recording to `docs/demos/intent-compiler.gif` — the file below appears after the first green run
of that workflow on this branch, and refreshes itself on every change to the compiler.

![The estate compiler, recorded by the machines](../demos/intent-compiler.gif)

Run it yourself: `python3 bin/intent-compile --intents tests/fixtures/intent/good --out /tmp/x`

## The backfill: two more features got their recordings the same way

`demos/catalog-links.tape` — the catalogue generates from real inventory, every Component carries
a URL, and two runs are byte-identical:

![The catalogue links demo, recorded by the machines](../demos/catalog-links.gif)

`demos/drill-evidence.tape` — the login drill's shape, its config coming from the estate DNA, and
its test framework passing:

![The login drill demo, recorded by the machines](../demos/drill-evidence.gif)

Each file appears after the workflow's first green run touching it and refreshes on every change.
