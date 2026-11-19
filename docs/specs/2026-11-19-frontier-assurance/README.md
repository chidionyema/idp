# Frontier assurance implementation candidate — #7523

This branch stages actual source modifications against 99420ce372fa53dc859553e1f414c85ab2f62854. It is an isolated research candidate, NOT an authenticated lane, claim, release, production enforcement, or full CI verdict.

Existing modules contain the receipt validator, binary calibration, fixed-horizon experiment, mutation evidence classifier, no-test rejection, and preliminary exact lane-head check before Greenlane creates a PR. Actual source tests are in tests/test_frontier_assurance_core.py (adapted from the 44 locally passing fragment tests). The single-class judge fixture is corrected. Full acceptance feature is here until runtime BDD bindings are complete.

The fleet must review/format, execute source tests and full CI, bind the remaining Gherkin scenarios, add the existing QUAD-backed signer and trusted test-inventory adapters, atomic nonce/lease/ref handling, independent test execution, polyglot structured mutation results and BASE_RED recovery, then submit via authenticated Greenlane. The preliminary _ensure_pr barrier still relies on existing checks (including their current skip semantics), not the v2 receipt, and cannot make external GitHub ref updates atomic. Do not enforce it on main until the positive/negative canary proves operations continue. Coordinate #8103 before touching the landing path; #8076 for real mutation workflows, #7734 for signed trust, #6061 for credential exclusivity and #7927 for workers. No duplicate claims.

Run: python -m pytest -q tests/test_frontier_assurance_core.py tests/test_nsvee_verify_door.py tests/judge/test_calibration.py tests/judge/test_drift.py tests/test_greenlane_github.py
Run canonical ruff and bin/idp-ci as applicable before a lane submission. No test result for the assembled source is asserted yet.

## Greenlane prefix scheduling

Candidate queue refs now schedule missing exact-prefix checks before the batch is admitted; repeated ticks reuse the immutable SHA ref, and a remote base change refuses admission. The new PR path rereads the remote ref before POST. The adapter still uses existing check semantics and needs canonical CI, trusted signed receipt binding and a fenced promotion boundary. A remote read is not an atomic GitHub PR-create lease.

## Adversarial falsifiers

The source suite now checks malformed verifier rosters and path scope, mutable callback evidence, order-independent survivor handling, weak runner refusal and independent JSON observations (expected values never sent to the candidate). `verify_json_cases` is a bounded pure-function oracle adapter, not an attestation authority. It defaults to the isolated Docker runner and refuses direct rlimits fallback. Local subprocess fixtures are not evidence of prod sandbox isolation. The existing synthetic Greenlane test backend now represents remote refs where the admission path reads them.

## Executable acceptance coverage

`features/assurance/frontier-core.feature` is bound via `sovereign/tests/bdd/test_frontier_assurance_bdd.py` to the component predicates and actual subprocess observations. The broader spec still includes unimplemented live authority/custody/concurrent promotion scenarios; this feature does not waive them. Local extraction harness: 67 passed in 3.69s, exercising revised core predicates and real subprocess fixtures, not the complete repository. The environment cannot resolve GitHub for checkout and lacks pytest-bdd and ruff; canonical BDD and complete source CI are unexecuted here.
