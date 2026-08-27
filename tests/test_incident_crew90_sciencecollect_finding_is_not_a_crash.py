"""Incident test, crew#90 (2026-08-24, fixed 2026-08-27): com.founder.sciencecollect collects every
source and then exits 1 to report a stale one. Under Dagster that read as a crash: three in a row
opened the circuit breaker (crew#85), so the job went silent exactly when it had a finding.
Rule: the row declares exit 1 as a finding, for the scheduler (ok_exit) and for the dead-man
check (HC_FINDINGS_EXIT), and any other nonzero code is still a crash. Rung 4, both ways.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))

JOBS = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())["jobs"]


def test_incident_crew90_sciencecollect_finding_is_not_a_crash():
    spec = JOBS["com.founder.sciencecollect"]
    assert spec["ok_exit"] == [1]
    assert spec["env"]["HC_FINDINGS_EXIT"] == "1"


def test_incident_crew90_declared_finding_passes_and_a_crash_still_fails():
    pytest.importorskip("dagster")
    from estate_scheduler.definitions import exit_is_ok

    spec = JOBS["com.founder.sciencecollect"]
    assert exit_is_ok(spec, 1) and not exit_is_ok(spec, 2), "a finding passes, a crash still fails"
