# Demo: the incident register

    bin/incident-register

Prints `wrote docs/reference/incident-register.yaml: 354 incidents` and one line per fault class
with its count; the same generator runs inside every docs build, so the portal's copy is always
the corpus as of that build. The register is read from the docstring of every
`tests/test_incident_*.py` file: the date, the ticket, what broke, the rule that now refuses it,
and the class of mistake it belongs to. Nothing on the page is typed; run `bin/incident-register`
and the page and the YAML are rebuilt from the corpus. The docs build writes the YAML through `bin/mkdocs_hooks/incident_register.py`, so nothing is committed and nothing can be stale (crew#679 CP2).
