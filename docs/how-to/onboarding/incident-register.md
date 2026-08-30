# Onboarding: an incident becomes a drill

Every mistake in this estate ends as a `tests/test_incident_<ticket>_<what>.py` guard (LAW 45). The
register (`docs/reference/incident-register.md`, generated from `docs/reference/incident-register.yaml`)
is the list of all of them, grouped by the class of mistake, and it is the input the chaos work reads
(crew#679, founder 2026-08-29: "take incidents as input, use it to generate chaos experiments/drills").

To add an incident: write the guard test with a docstring whose first lines say the date, the ticket,
what broke (the founder's words where there are any) and the rule; then run `bin/incident-register`
and commit the regenerated YAML and page with the test. `bin/incident-register --check` in the fast
gate refuses a push where the register is behind the corpus. A class with many rows is the next drill
to write; a class with one row is a guard that has not yet been generalised.
