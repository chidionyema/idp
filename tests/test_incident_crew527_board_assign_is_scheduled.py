"""crew#527 CP3 (founder 2026-08-27: "the board should be assigning tickets"): the board's turn
runs on the one scheduler, hourly, under the dead-man wrapper, and BLIND (exit 3: no feed or an
unreadable board) is a finding, not a crash; exit 2 is argparse's usage error, so a picker with no
`assign` verb must never grade as healthy (code-2f, idp#450). An assignment nobody schedules is a claim a session
makes for itself, which is the state this replaces."""
import os
import pathlib
import subprocess
import sys

import yaml

SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "scheduler" / "schedule.yml"


def test_board_assign_is_an_hourly_dead_man_wrapped_turn():
    job = yaml.safe_load(SCHEDULE.read_text())["jobs"]["com.estate.board-assign"]
    assert job["command"][0].endswith("hc-wrap.sh") and job["command"][1] == "board-assign"
    assert job["command"][-2:] == ["~/.claude/scripts/estate_board.py", "assign"]
    assert "--dry-run" not in job["command"]
    assert job["cron"].split()[1:] == ["*", "*", "*", "*"]          # every hour
    assert job["ok_exit"] == [3] and job["env"]["HC_FINDINGS_EXIT"] == "3"
    assert 2 not in job["ok_exit"]
    assert job["skip_on_battery"] is False and job["runs_on"] == "mac"


def test_the_picker_on_this_machine_has_the_assign_verb():
    """The row calls `estate_board.py assign`; a picker without the verb exits 2 (argparse), which
    the row does not treat as a finding, so it pages. Proved against the installed copy."""
    picker = pathlib.Path(os.path.expanduser("~/.claude/scripts/estate_board.py"))
    if not picker.exists():
        import pytest
        pytest.skip("no picker installed on this machine")
    out = subprocess.run([sys.executable, str(picker), "--help"], capture_output=True, text=True, check=False)
    assert "assign" in out.stdout, out.stdout + out.stderr
