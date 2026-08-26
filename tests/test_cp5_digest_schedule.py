"""crew#284 CP5: the daily digest is a row on the one estate scheduler.

Rung 2/4: one invariant between two files that drift independently --
schedule.yml's cron hour and presence.digest_hour. The launchd plist that
`sb digest --launchd` prints is not the scheduler (LAW 43: Dagster is).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
JOB = "ai.estate.sovereign-digest"


def _job() -> dict:
    jobs = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())["jobs"]
    assert JOB in jobs, f"{JOB} missing from scheduler/schedule.yml"
    return jobs[JOB]


def _digest_hour_default() -> int:
    src = (ROOT / "sovereign" / "presence" / "config_keys.py").read_text()
    m = re.search(r'"presence\.digest_hour":\s*\(\s*(\d+),', src)
    assert m, "presence.digest_hour default not found"
    return int(m.group(1))


def test_digest_job_runs_sb_digest_send() -> None:
    cmd = _job()["command"]
    assert cmd[-3:] == ["sovereign.cli", "digest", "--send"]
    assert "-m" in cmd and "sovereign.cli" in cmd


def test_digest_cron_hour_matches_presence_digest_hour() -> None:
    minute, hour, *rest = str(_job()["cron"]).split()
    assert rest == ["*", "*", "*"], "the digest is daily"
    assert int(hour) == _digest_hour_default(), f"schedule.yml fires at {hour}, presence.digest_hour is {_digest_hour_default()}"


def test_digest_job_is_described() -> None:
    # describe audits the whole file and prints one `ok`/`FAIL` line per job.
    # Only this job's line is this test's business: other jobs point at
    # scripts outside the repo that may be absent on the machine running it.
    r = subprocess.run(
        [sys.executable, "-m", "estate_scheduler.describe"],
        cwd=ROOT / "scheduler", capture_output=True, text=True,
    )
    line = next((l for l in r.stdout.splitlines() if JOB in l), "")
    assert line.startswith("ok"), line or r.stdout


def test_self_check_job_enforces_every_five_minutes() -> None:
    jobs = yaml.safe_load((ROOT / "scheduler" / "schedule.yml").read_text())["jobs"]
    job = jobs["ai.estate.sovereign-self-check"]
    assert job["command"][-4:] == ["sovereign.cli", "self-check", "--enforce", "--json"]
    assert str(job["cron"]).split()[0] == "*/5"
