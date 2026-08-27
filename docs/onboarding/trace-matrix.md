# Onboarding: making a feature count

A feature is BOUND when a tracked test loads it with `scenarios("<path>.feature")` (the same rule
`bin/spec-gate` applies). To move a row from UNBOUND to BOUND, add `sovereign/tests/bdd/test_gate_<x>.py`
with `scenarios("features/<dir>/<x>.feature")` and real steps. `pytest.mark.pending` in that test
grades the row PENDING, not BOUND. `bin/trace-matrix --check` exits 1 while any row is UNBOUND; it
is report mode today (65 rows) and becomes a gate when the count is 0.
