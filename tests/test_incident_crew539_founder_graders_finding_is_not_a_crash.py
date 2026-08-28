"""Incident test, crew#539 (2026-08-28): com.founder.board, com.founder.ingit and
com.founder.lawenforcement are graders: each writes its page or map and then exits 1 to say
"I found something" (a red board row, a load-bearing hole, a dead guard). None declared it, so
under the scheduler every finding read as a crash, three in a row opened the breaker and
`scheduler-status` showed `open circuits: 5` — the estate stopped grading itself exactly while
it had findings. Same class as crew#90 (sciencecollect) and crew#300 (bundlepush).
Rule: a grader row declares exit 1 as a finding for the scheduler (ok_exit) and, when it runs
under hc-wrap, for the dead-man check (HC_FINDINGS_EXIT); any other nonzero code is still a crash.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))

JOBS = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())["jobs"]
GRADERS = ["com.founder.board", "com.founder.ingit", "com.founder.lawenforcement"]


@pytest.mark.parametrize("row", GRADERS)
def test_founder_grader_declares_exit_1_as_a_finding(row):
    spec = JOBS[row]
    assert spec["ok_exit"] == [1], f"{row}: a finding must not open the breaker"
    if any("hc-wrap" in a for a in spec["command"]):
        assert spec["env"]["HC_FINDINGS_EXIT"] == "1", f"{row}: hc-wrap must not page on a finding"


@pytest.mark.parametrize("row", GRADERS)
def test_a_finding_passes_and_a_crash_still_fails(row):
    pytest.importorskip("dagster")
    from estate_scheduler.definitions import exit_is_ok

    spec = JOBS[row]
    assert exit_is_ok(spec, 1) and not exit_is_ok(spec, 2), "a finding passes, a crash still fails"
