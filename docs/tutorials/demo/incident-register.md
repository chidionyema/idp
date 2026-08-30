# Demo: the incident register

    bin/incident-register --check

Prints one line: `ok      incident-register   docs/reference/incident-register.yaml matches 350 incident tests`,
or `FAIL  incident-register  stale: run bin/incident-register and commit` when a guard was added and
the register was not regenerated. The register is read from the docstring of every
`tests/test_incident_*.py` file: the date, the ticket, what broke, the rule that now refuses it,
and the class of mistake it belongs to. Nothing on the page is typed; run `bin/incident-register`
and the page and the YAML are rebuilt from the corpus. The fast gate runs `--check` on every push,
so a session cannot add a guard without the register learning it (crew#679 CP1).
