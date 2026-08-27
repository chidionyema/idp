"""crew#85, 2026-08-27: eight scheduler rows still ran ~/.hermes/scripts/launchd_receipt.py after
~/.claude/scripts 41cc47e moved it (2026-08-26 12:17Z); the plists were updated, schedule.yml was
not, and every one of those jobs failed on exit 2 until the breaker opened. Two sentinels tripped
the breaker by exiting 1 to report a finding. Rules: every literal path in a job command resolves
to a file on this machine, and a declared ok_exit code is not a failure. Rung 4, both ways."""
import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scheduler"))
pytest.importorskip("dagster")
from estate_scheduler.definitions import exit_is_ok  # noqa: E402

JOBS = yaml.safe_load((ROOT / "scheduler/schedule.yml").read_text())["jobs"]


def _paths(cmd):
    for a in cmd:
        a = os.path.expanduser(a)
        if a.startswith("/") and "$" not in a:
            yield a


@pytest.mark.skipif(not (Path.home() / ".claude/scripts").is_dir(), reason="estate scripts checkout absent (CI)")
def test_every_literal_command_path_exists_on_this_machine():
    missing = [(j, p) for j, s in JOBS.items() for p in _paths(s["command"]) if not Path(p).exists()]
    assert missing == [], missing


def test_no_row_runs_from_the_dead_hermes_tree_or_watches_fly():
    text = (ROOT / "scheduler/schedule.yml").read_text()
    assert "~/.hermes/scripts/" not in text
    assert "com.prospector-control.failover-watch" not in JOBS  # R1: Fly is not coming back


def test_a_declared_finding_code_passes_and_an_undeclared_one_still_fails():
    assert exit_is_ok({}, 0) and not exit_is_ok({}, 1)
    assert exit_is_ok({"ok_exit": [1]}, 1) and not exit_is_ok({"ok_exit": [1]}, 2)
    assert JOBS["com.estate.costsentinel"]["ok_exit"] == [1]
