# Onboarding: making a feature count

A feature is BOUND when a tracked test loads it with `scenarios("<path>.feature")` (the same rule
`bin/spec-gate` applies). To move a row from UNBOUND to BOUND, add `sovereign/tests/bdd/test_gate_<x>.py`
with `scenarios("features/<dir>/<x>.feature")` and real steps. `pytest.mark.pending` in that test
grades the row PENDING, not BOUND. `bin/trace-matrix --check` exits 1 while any row is UNBOUND; it
is report mode today (65 rows) and becomes a gate when the count is 0.

## PROSE rows

A feature under `docs/prose/` is intent that nothing runs, by the `bin/spec-gate` rule (crew#297): it moves back under `features/` the day a test names it. The matrix counts these as **PROSE**, lists them after UNBOUND, and never fails `--check` on them. UNBOUND is reserved for a feature under `features/` with no test, which is the defect.
