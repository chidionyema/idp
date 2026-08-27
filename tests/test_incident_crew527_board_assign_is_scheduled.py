"""crew#527 CP3 (founder 2026-08-27: "the board should be assigning tickets"): the board's turn
runs on the one scheduler, hourly, under the dead-man wrapper, and BLIND (exit 2: no feed or an
unreadable board) is a finding, not a crash. An assignment nobody schedules is a claim a session
makes for itself, which is the state this replaces."""
import pathlib

import yaml

SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "scheduler" / "schedule.yml"


def test_board_assign_is_an_hourly_dead_man_wrapped_turn():
    job = yaml.safe_load(SCHEDULE.read_text())["jobs"]["com.estate.board-assign"]
    assert job["command"][0].endswith("hc-wrap.sh") and job["command"][1] == "board-assign"
    assert job["command"][-2:] == ["~/.claude/scripts/estate_board.py", "assign"]
    assert "--dry-run" not in job["command"]
    assert job["cron"].split()[1:] == ["*", "*", "*", "*"]          # every hour
    assert job["ok_exit"] == [2] and job["env"]["HC_FINDINGS_EXIT"] == "2"
    assert job["skip_on_battery"] is False and job["runs_on"] == "mac"
