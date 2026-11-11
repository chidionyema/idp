# Muster failure modes

Every row names an executable test. A production integration failure that has
no row and test is not considered handled.

| ID | Failure | Expected response | Test |
|---|---|---|---|
| F-MU-1 | Receipt edited after execution | chain verification refuses the run | `tamper_detected` |
| F-MU-2 | Event payload edited | event-chain verification refuses the run | `event_tamper_detected` |
| F-MU-3 | Process dies after completed steps | resume from completed-step map without repeating verified work | `crash_resume_via_done_map` |
| F-MU-4 | Formation requests runaway fan-out | request refused before any unit executes | `k2_fanout_cap_enforced` |
| F-MU-5 | Debate does not converge | hard round cap and judge receipt | `k3_debate_bounded_and_judged` |
| F-MU-6 | Tournament rewards raw pass@k | utility ordering prefers useful work per unit cost | `k4_bracket_utility_ordering` |
| F-MU-7 | Gate veto is advisory | veto is returned as a terminal refusal value | `k5_gate_veto_halts` |
| F-MU-8 | Doctrine lacks a required duty | doctrine conformance fails loudly | `doctrine_conformance` |
| F-MU-9 | Either rank system can bypass the other | effective permission requires both systems to clear | `rank_min_policy` |
| F-MU-10 | Nested formation returns the wrong type | fractal K1 run completes and verifies | `complete_run_verifies` |
| F-MU-11 | SHA implementation drifts from FIPS vectors | known vectors fail immediately | `sha256_vectors` |

Integration-only risks are named in `INTEGRATION.md`. They are not claimed as
handled by this core and must each arrive with a failure-mode row and executable
test before the production binding is enabled.
