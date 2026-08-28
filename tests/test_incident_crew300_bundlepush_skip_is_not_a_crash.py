"""Incident test, crew#300 (found 2026-08-28T01:03Z): com.estate.bundlepush escrows every repo,
prints BUNDLE PUSH GREEN, and then exits 2 when one repo was skipped (an oversize bundle, named
in the log). Under Dagster that read as a crash: three in a row on 2026-08-25 opened the circuit
breaker (crew#85), and the job stayed silent for 52 hours while the shallow-clone guard merged
in claude-guards#168 never ran, so the unrestorable bundle it removes sat in R2 and turned the
recover-drill red (idp#441 run 33131027676). Run df9d7e69 reproduced it: GREEN, exit 2, FAILURE.
Rule: the row declares exit 2 as a finding; any other nonzero code is still a crash.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))

JOBS = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())["jobs"]


def test_incident_crew300_bundlepush_skip_is_a_finding():
    spec = JOBS["com.estate.bundlepush"]
    assert spec["ok_exit"] == [2]


def test_incident_crew300_declared_finding_passes_and_a_crash_still_fails():
    pytest.importorskip("dagster")
    from estate_scheduler.definitions import exit_is_ok

    spec = JOBS["com.estate.bundlepush"]
    assert exit_is_ok(spec, 0) and exit_is_ok(spec, 2)
    assert not exit_is_ok(spec, 1), "die() exits 1: still a crash"
