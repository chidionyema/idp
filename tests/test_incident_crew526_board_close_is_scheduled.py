"""crew#526 CP2 (founder 2026-08-27: "close completed issues"): the close turn runs nightly on the one
scheduler, under the dead-man wrapper, in the crew checkout so its log row lands where velocity reads
it; BLIND is exit 3 (a finding), exit 2 is argparse's usage error and pages (code-2f, idp#450). A
close turn nobody schedules is a session closing issues by hand, which is the state this replaces."""
import os
import pathlib
import subprocess
import sys

import yaml

SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "scheduler" / "schedule.yml"


def test_board_close_is_a_nightly_dead_man_wrapped_turn_in_the_crew_checkout():
    job = yaml.safe_load(SCHEDULE.read_text())["jobs"]["com.estate.board-close"]
    assert job["command"][0].endswith("hc-wrap.sh") and job["command"][1] == "board-close"
    assert job["command"][-2:] == ["~/.claude/scripts/estate_board.py", "close"]
    assert "--dry-run" not in job["command"]
    assert job["cron"].split()[2:] == ["*", "*", "*"] and job["cron"].split()[1] != "*"   # once a day
    assert job["ok_exit"] == [3] and job["env"]["HC_FINDINGS_EXIT"] == "3" and 2 not in job["ok_exit"]
    assert job["cwd"] == "$CODE/crew" and job["env"]["ESTATE_CLOSER_LOG"] == "science/closer.jsonl"
    assert job["skip_on_battery"] is False and job["runs_on"] == "mac"


def test_the_picker_on_this_machine_has_the_close_verb():
    picker = pathlib.Path(os.path.expanduser("~/.claude/scripts/estate_board.py"))
    if not picker.exists():
        import pytest
        pytest.skip("no picker installed on this machine")
    out = subprocess.run([sys.executable, str(picker), "--help"], capture_output=True, text=True, check=False)
    assert "close" in out.stdout, out.stdout + out.stderr
