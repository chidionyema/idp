"""crew#527 CP1 (founder 2026-08-27: "apply science to our board ... help us with velocity"): the
per-lane velocity row runs on the one scheduler, daily, under the dead-man wrapper, from the crew
checkout, and a red lane is a finding (exit 1 accepted, HC_FINDINGS_EXIT) rather than a crash.
A measurement nobody schedules is a feeling by next week."""
import pathlib

import yaml

SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "scheduler" / "schedule.yml"


def test_velocity_is_a_daily_dead_man_wrapped_check():
    job = yaml.safe_load(SCHEDULE.read_text())["jobs"]["com.estate.velocity"]
    assert job["command"][0].endswith("hc-wrap.sh") and job["command"][1] == "velocity"
    assert job["command"][-2:] == ["$CODE/crew/science/velocity.py", "--check"]
    assert job["cwd"] == "$CODE/crew" and job["cron"].split()[2:] == ["*", "*", "*"]
    assert job["ok_exit"] == [1] and job["env"]["HC_FINDINGS_EXIT"] == "1"
    assert job["skip_on_battery"] is False and job["runs_on"] == "mac"
