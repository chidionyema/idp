"""crew#508 CP8: the outward research intake runs on the one scheduler, daily, under the
dead-man wrapper, from the crew checkout. A pull nobody schedules is research that stops."""
import pathlib

import yaml

SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "scheduler" / "schedule.yml"


def test_research_intake_is_a_daily_dead_man_wrapped_job():
    job = yaml.safe_load(SCHEDULE.read_text())["jobs"]["com.estate.research-intake"]
    assert job["command"][0].endswith("hc-wrap.sh") and job["command"][1] == "research-intake"
    assert job["command"][-2:] == ["$CODE/crew/science/research_intake.py", "pull"]
    assert job["cwd"] == "$CODE/crew" and job["cron"].split()[2:] == ["*", "*", "*"]
    assert job["skip_on_battery"] is False
