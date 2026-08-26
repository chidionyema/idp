"""Incident test (rung 4), crew#307, 2026-08-26 13:15Z: login-drill.yml sat on main 40 minutes with
cron */5 and GitHub fired zero scheduled runs; nothing said so. bin/idp-drill-heartbeat grades the
age of the newest successful run. Both ways in one run: fresh is ok; stale is FAIL and names the
dispatch command; no run on record is FAIL; an unreadable API is BLIND, never a verdict."""
import datetime, os, stat, subprocess
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "bin" / "idp-drill-heartbeat"


def _run(tmp: Path, age_min: int | None, rc: int = 0) -> subprocess.CompletedProcess:
    b = tmp / "bin"; b.mkdir(exist_ok=True)
    fake = b / "gh"
    if age_min is None:
        out = ""
    else:
        ts = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=age_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
        out = f"999 {ts}"
    fake.write_text(f"#!/usr/bin/env bash\nprintf '%s' '{out}'; exit {rc}\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}", "GH_REPO": "o/r"}
    return subprocess.run(["bash", str(GUARD), "login-drill.yml", "20"], env=env, capture_output=True, text=True)


def test_incident_stale_or_absent_drill_is_fail_fresh_is_ok(tmp_path: Path) -> None:
    ok = _run(tmp_path, 4)
    assert ok.returncode == 0 and ok.stdout.startswith("ok      heartbeat  login-drill.yml  last success 4 min ago (run 999)"), ok.stdout + ok.stderr
    stale = _run(tmp_path, 41)
    assert stale.returncode == 1 and "FAIL    heartbeat  login-drill.yml  last success 41 min ago > 20 (run 999)" in stale.stdout, stale.stdout
    assert "gh workflow run login-drill.yml -R o/r" in stale.stdout
    none = _run(tmp_path, None)
    assert none.returncode == 1 and "no successful run on record" in none.stdout, none.stdout


def test_unreadable_api_is_blind_not_a_verdict(tmp_path: Path) -> None:
    r = _run(tmp_path, None, rc=1)
    assert r.returncode == 2 and r.stdout.startswith("BLIND   heartbeat"), r.stdout
