"""crew#584 CP4, 2026-08-28. Founder: "is our build exponentially faster", "get faster at getting
faster". The answer was dug out of three job logs by hand; nothing on the estate said, on its
own, whether a pull request goes green faster this week than last. bin/idp-loop-meter reads the
ledger GitHub already keeps (ci runs on pull_request events) and prints one line: the median
wall-clock this week against last week, red when the loop got slower. No network: gh is a stub."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-loop-meter"
NOW = datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc)


def _runs(this_week: list[int], last_week: list[int]) -> list[dict]:
    out = []
    for days_ago, secs in [(1, s) for s in this_week] + [(9, s) for s in last_week]:
        c = NOW - timedelta(days=days_ago)
        out.append({"createdAt": c.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "updatedAt": (c + timedelta(seconds=secs)).strftime("%Y-%m-%dT%H:%M:%SZ")})
    return out


def _run(tmp: Path, runs: list[dict] | None) -> subprocess.CompletedProcess:
    fake = tmp / "bin"; fake.mkdir(parents=True, exist_ok=True)
    gh = fake / "gh"
    gh.write_text("#!/bin/sh\nexit 1\n" if runs is None else "#!/bin/sh\ncat <<'EOF'\n" + json.dumps(runs) + "\nEOF\n")
    gh.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake}:{os.environ['PATH']}", "IDP_LOOP_METER_NOW": str(int(NOW.timestamp()))}
    return subprocess.run([str(SCRIPT), "o/r"], env=env, capture_output=True, text=True)


def test_the_meter_says_this_week_against_last(tmp_path):
    out = _run(tmp_path, _runs([274, 280, 260], [400, 422, 390]))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "ok    loop-meter: median PR wall-clock this week 274s (n=3), last week 400s (n=3)" in out.stdout, out.stdout


def test_a_slower_week_is_red(tmp_path):
    out = _run(tmp_path, _runs([600, 620], [400, 410]))
    assert out.returncode == 1 and "FAIL  loop-meter: the loop got slower" in out.stdout, out.stdout


def test_no_gh_or_no_runs_is_blind_never_a_pass(tmp_path):
    assert _run(tmp_path, None).returncode == 2
    out = _run(tmp_path / "b", _runs([], [400]))
    assert out.returncode == 2 and "BLIND" in out.stdout, out.stdout


def test_the_drill_renders_the_row():
    drill = (ROOT / "bin" / "idp-verify-drill").read_text()
    assert 'idp-loop-meter' in drill and 'loop-meter' in drill
