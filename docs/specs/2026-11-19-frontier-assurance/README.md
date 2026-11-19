# Frontier assurance implementation candidate — #7523

This branch stages actual source modifications against 99420ce372fa53dc859553e1f414c85ab2f62854. It is an isolated research candidate, NOT an authenticated lane, claim, release, production enforcement, or full CI verdict.

Existing modules contain the receipt validator, binary calibration, fixed-horizon experiment, mutation evidence classifier, no-test rejection, and preliminary exact lane-head check before Greenlane creates a PR. Actual source tests are in tests/test_frontier_assurance_core.py (adapted from the 44 locally passing fragment tests). The single-class judge fixture is corrected. Full acceptance feature is here until runtime BDD bindings are complete.

The fleet must review/format, execute source tests and full CI, bind the remaining Gherkin scenarios, add the existing QUAD-backed signer and trusted test-inventory adapters, atomic nonce/lease/ref handling, independent test execution, polyglot structured mutation results and BASE_RED recovery, then submit via authenticated Greenlane. The preliminary _ensure_pr barrier still relies on existing checks (including their current skip semantics), not the v2 receipt, and cannot make external GitHub ref updates atomic. Do not enforce it on main until the positive/negative canary proves operations continue. Coordinate #8103 before touching the landing path; #8076 for real mutation workflows, #7734 for signed trust, #6061 for credential exclusivity and #7927 for workers. No duplicate claims.

Run: python -m pytest -q tests/test_frontier_assurance_core.py tests/test_nsvee_verify_door.py tests/judge/test_calibration.py tests/judge/test_drift.py tests/test_greenlane_github.py
Run canonical ruff and bin/idp-ci as applicable before a lane submission. No test result for the assembled source is asserted yet.
