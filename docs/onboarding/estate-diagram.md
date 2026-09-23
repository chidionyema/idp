# Onboarding: estate-diagram

What it is: the one architecture page that cannot drift, because it is rendered from the
catalogue and the catalogue is rendered from the inventory. It answers "what is running, on
which port, from which repository, and did the last scheduled run succeed" without a person
remembering.

How to use it:

- `make diagrams` renders the C4 views and this page together.
- `bin/estate-diagram --check` is the gate: it exits 1 when `docs/architecture/live.md` is not
  what the catalogue says, 3 (BLIND) when there is no catalogue.
- Never edit `docs/architecture/live.md`. Change the inventory collector or `bin/catalog-gen`
  and re-render.

Spec: `features/gates/estate_gates.feature`, scenario "The architecture diagram is drawn from
the catalogue, never by hand". Test: `tests/test_estate_diagram.py`.

Not automated yet: the render is not on a schedule, so the page is as old as the last
`make diagrams` on main. The header prints the inventory timestamp so the age is visible.
