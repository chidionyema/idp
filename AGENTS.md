# AGENTS.md — the rules of this repository, and the gate that reads them

This file is the version-controlled boundary for agent work in `idp` (crew #180, CP6).
The estate's laws live in `~/AGENTS.md`; this file holds only what is specific to this
repo, and every rule here is machine-checked. A rule with no gate is a wish (LAW 44), so
the table below is not prose: `bin/idp-ci` parses it, runs each gate on its two fixtures,
and fails if any gate does not refuse the bad case and pass the good one in the same run.

Row format, one rule per row. `gate` is a shell function or command defined in `bin/idp-ci`;
`must-fail` and `must-pass` are paths relative to this file.

| rule | gate | must-fail | must-pass |
|---|---|---|---|
| No file names where the checkout, home directory or machine lives (LAW 46) | hardcode_scan | tests/fixtures/hardcoded-path.bad.sh | tests/fixtures/hardcoded-path.good.sh |
| No dependency whose licence blocks a sale; a scan with no licences is not clean (LAW 40) | policy_gate | policy/fixtures/sell-blocking.json | policy/fixtures/clean.json |
| No scheduled job on this laptop that runs in the sleep window or is never pinged (LAW 28) | policy_gate | policy/fixtures/placement-misplaced.json | policy/fixtures/placement-ok.json |

Rules that are already types or tools, and so need no row: compose files must parse
(`docker compose config`), the gateway config must match its release schema
(`check-jsonschema`), every catalog entity must match the Backstage schema, and every
script must pass `shellcheck`, every generator must be idempotent (two runs over one
inventory, byte-identical), the generated catalogue must carry a relationship graph, and
every entity reference in it must resolve to an entity something defines
(`bin/catalog-refcheck`, proved both ways in the same run). Those run unconditionally in
`bin/idp-ci`.

Adding a rule: add a row, add both fixtures, run `bin/idp-ci`. A row whose gate cannot
tell the fixtures apart fails CI, so a rule cannot be written without its proof.
