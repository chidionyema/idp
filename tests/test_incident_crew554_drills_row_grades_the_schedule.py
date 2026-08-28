"""crew#554 CP2: the drills row grades the schedule itself. On 2026-08-28 every hourly cron on
the account fired 1-3 times in 24h while the catalogue showed green ages from push-triggered
runs. bin/idp-drills-row now counts scheduled firings per workflow in the last 24h against what
the cron promises and goes red under 80%."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-drills-row"


def _load():
    """Import the script's pure cron helpers without running its main body."""
    text = SCRIPT.read_text()
    helpers = text[text.index("def _field("):text.index("now = datetime.now(timezone.utc)")]
    ns: dict = {}
    exec("from datetime import datetime, timedelta, timezone\n" + helpers, ns)  # noqa: S102 - the script's own helpers
    return ns


def test_expected_firings_match_the_cron_promise() -> None:
    ns = _load()
    end = datetime(2026, 8, 28, 2, 34, tzinfo=timezone.utc)
    assert ns["expected_firings"]("23 * * * *", end) == 24
    assert ns["expected_firings"]("*/10 * * * *", end) == 144
    assert ns["expected_firings"]("3-59/15 * * * *", end) == 96
    assert ns["expected_firings"]("17 5 * * *", end) == 1
    assert ns["expected_firings"]("0 6 * * 1", end) == 0  # a Friday window holds no Monday
    assert ns["expected_firings"]("not a cron", end) == 0


def _fake_gh(b: Path, sched_runs: int, now: datetime) -> None:
    runs = [{"createdAt": now.strftime("%Y-%m-%dT%H:%M:%SZ")} for _ in range(sched_runs)]
    (b / "gh").write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json\n"
        "a = sys.argv[1:]\n"
        "if a[:2] == ['auth', 'status']: sys.exit(0)\n"
        "if '--event' in a: print(json.dumps(%s)); sys.exit(0)\n"
        "print(json.dumps([{'updatedAt': '%s'}]))\n" % (json.dumps(runs), now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    )
    (b / "gh").chmod((b / "gh").stat().st_mode | stat.S_IEXEC)


def _estate(tmp: Path, sched_runs: int) -> tuple[Path, Path]:
    now = datetime.now(timezone.utc)
    b = tmp / "bin"
    b.mkdir()
    _fake_gh(b, sched_runs, now)
    wfd = tmp / ".github" / "workflows"
    wfd.mkdir(parents=True)
    (wfd / "login-drill.yml").write_text("name: login-drill\n")
    cat = tmp / "catalogue.yaml"
    cat.write_text("drills:\n  - name: login-drill\n    workflow: login-drill.yml\n    schedule: '23 * * * *'\n    max_age_hours: 3\n")
    return b, cat


def _run(tmp: Path, b: Path, cat: Path) -> subprocess.CompletedProcess:
    env = {"PATH": f"{b}:{os.path.dirname(os.sys.executable)}:/usr/bin:/bin", "HOME": str(tmp)}
    return subprocess.run([str(SCRIPT), str(cat), str(tmp)], env=env, capture_output=True, text=True, timeout=60)


def test_a_cron_that_fired_twice_in_24h_is_a_red_schedule_row(tmp_path: Path) -> None:
    b, cat = _estate(tmp_path, 2)
    r = _run(tmp_path, b, cat)
    assert "ok        drills    login-drill" in r.stdout, r.stdout + r.stderr
    assert "FAIL      drills    schedule               login-drill.yml fired 2 of 24 promised" in r.stdout, r.stdout
    assert r.returncode == 1 and "1 of 1 schedules dropped: login-drill.yml" in r.stdout


def test_a_cron_that_fired_every_hour_is_green(tmp_path: Path) -> None:
    b, cat = _estate(tmp_path, 24)
    r = _run(tmp_path, b, cat)
    assert "ok        drills    schedule               login-drill.yml fired 24 of 24 promised" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0 and "1/1 schedules alive" in r.stdout
