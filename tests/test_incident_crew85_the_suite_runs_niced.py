"""crew#85 row 1 (2026-08-27): the suite lowers its own priority; no caller has to remember
`nice`. Rung 4, incident. Both ways: with the root conftest the priority is >= 10; a run with
`--noconftest` (the evidence block on the PR) reports 0 and this test fails."""
import os


def test_incident_crew85_the_suite_process_is_niced_before_any_test_runs():
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 10
