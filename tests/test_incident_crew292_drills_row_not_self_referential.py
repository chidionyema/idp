"""crew#292 / crew#300 / idp#441: the drills row may not grade the run it is computed inside.

bin/idp-drills-row is run by bin/idp-verify-drill, which is
.github/workflows/verify-drill.yml, and drills/catalogue.yaml catalogues verify-drill.yml with
max_age_hours 3. Grading a workflow from its own run history, from inside one of its runs, is a
fixpoint: the run in flight has no conclusion yet, so the newest verdict available belongs to an
earlier run, and the first red one makes every later run red for that reason alone. Measured on
2026-08-28, `gh run list --workflow verify-drill.yml --status success --limit 1 --json updatedAt`
answered `[]` while the last twelve completed runs were all `failure` -- the row printed "no
successful run of verify-drill.yml has ever been recorded", failed the run, and so guaranteed the
same answer an hour later. Nothing about the platform could open that loop; only this file could.

Every test here drives the real script with a fake `gh` on PATH. No network socket is opened.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-drills-row"

RUN_IN_FLIGHT = "33170000001"


def _fake_gh(b: Path, last_green: dict, firings: dict) -> None:
    """A gh that answers only the two call shapes the row makes.

    `last_green` maps a workflow file to the ISO timestamp of its latest completed *successful*
    run, or None for "this workflow has never concluded green" -- which is what the real
    `gh run list --status success` returns while a run of it is in flight and every earlier one
    failed. `firings` maps a workflow file to a list of runs for the runs API. Any other call
    shape fails the way the real gh does, so a wrong flag is red in this test, not in CI.
    """
    cfg = json.dumps({"green": last_green, "firings": firings})
    (b / "gh").write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json\n"
        "CFG = json.loads(%s)\n"
        "a = sys.argv[1:]\n"
        "if a[:2] == ['auth', 'status']: sys.exit(0)\n"
        "if a[:2] == ['api', '--paginate'] and a[2].startswith('repos/{owner}/{repo}/actions/workflows/'):\n"
        "    wf = a[2].split('/actions/workflows/')[1].split('/runs?')[0]\n"
        "    print(json.dumps(CFG['firings'].get(wf, []))); sys.exit(0)\n"
        "if a[:2] == ['run', 'list'] and a[-2:] == ['--json', 'updatedAt']:\n"
        "    wf = a[a.index('--workflow') + 1]\n"
        "    assert a[a.index('--status') + 1] == 'success', a\n"
        "    ts = CFG['green'].get(wf)\n"
        "    print(json.dumps([{'updatedAt': ts}] if ts else [])); sys.exit(0)\n"
        "print('fake gh: unexpected call', a, file=sys.stderr); sys.exit(1)\n" % json.dumps(cfg)
    )
    (b / "gh").chmod((b / "gh").stat().st_mode | stat.S_IEXEC)


def _estate(tmp: Path, entries: list, last_green: dict, firings: dict, names: dict | None = None):
    """Write a catalogue, the workflow files it names, and a fake gh. Returns (bin dir, catalogue)."""
    b = tmp / "bin"
    b.mkdir(parents=True)
    _fake_gh(b, last_green, firings)
    wfd = tmp / ".github" / "workflows"
    wfd.mkdir(parents=True)
    lines = ["drills:"]
    for wf, cap in entries:
        stem = wf[:-4] if wf.endswith(".yml") else wf
        (wfd / wf).write_text("name: %s\n" % ((names or {}).get(wf, stem)))
        lines += ["  - name: %s" % stem, "    workflow: %s" % wf,
                  "    schedule: '23 * * * *'", "    max_age_hours: %d" % cap]
    cat = tmp / "catalogue.yaml"
    cat.write_text("\n".join(lines) + "\n")
    return b, cat


def _hourly(n: int, now: datetime) -> list:
    """n scheduled firings, one an hour, as the runs API returns them."""
    return [{"createdAt": (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "event": "schedule", "actor": "github-actions[bot]"} for i in range(n)]


def _run(tmp: Path, b: Path, cat: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    e = {"PATH": "%s:%s:/usr/bin:/bin" % (b, os.path.dirname(sys.executable)), "HOME": str(tmp)}
    e.update(env or {})
    return subprocess.run([str(SCRIPT), str(cat), str(tmp)], env=e, capture_output=True,
                          text=True, timeout=60)


def _in_ci(ref: str = "chidionyema/idp/.github/workflows/verify-drill.yml@refs/heads/main") -> dict:
    return {"GITHUB_RUN_ID": RUN_IN_FLIGHT, "GITHUB_WORKFLOW_REF": ref}


def test_the_workflow_the_row_runs_inside_is_not_graded_by_its_own_history(tmp_path: Path) -> None:
    """The defect, exactly: verify-drill.yml has no green run because this row keeps failing it."""
    now = datetime.now(timezone.utc)
    b, cat = _estate(tmp_path, [("verify-drill.yml", 3)], {"verify-drill.yml": None},
                     {"verify-drill.yml": _hourly(24, now)})
    r = _run(tmp_path, b, cat, _in_ci())
    assert "no successful run of verify-drill.yml has ever been recorded" not in r.stdout, r.stdout
    assert "verify-drill.yml is the run computing this row (run %s)" % RUN_IN_FLIGHT in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0, r.stdout + r.stderr


def test_off_a_runner_the_same_workflow_with_no_green_run_is_still_red(tmp_path: Path) -> None:
    """The mirror. bin/idp-verify on a laptop is not inside the run, so nothing is exempt there:
    a workflow with no completed green run stays not-green (LAW 45 step 5)."""
    now = datetime.now(timezone.utc)
    b, cat = _estate(tmp_path, [("verify-drill.yml", 3)], {"verify-drill.yml": None},
                     {"verify-drill.yml": _hourly(24, now)})
    r = _run(tmp_path, b, cat)
    assert "no successful run of verify-drill.yml has ever been recorded" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 1, r.stdout


def test_only_the_workflow_in_flight_is_exempt_never_the_rest_of_the_catalogue(tmp_path: Path) -> None:
    """A run excuses itself and nothing else: a second drill with no green run is still red while
    verify-drill.yml is in flight."""
    now = datetime.now(timezone.utc)
    b, cat = _estate(tmp_path, [("verify-drill.yml", 3), ("login-drill.yml", 3)],
                     {"verify-drill.yml": None, "login-drill.yml": None},
                     {"verify-drill.yml": _hourly(24, now), "login-drill.yml": _hourly(24, now)})
    r = _run(tmp_path, b, cat, _in_ci())
    assert "verify-drill.yml is the run computing this row" in r.stdout, r.stdout + r.stderr
    assert "no successful run of login-drill.yml has ever been recorded" in r.stdout, r.stdout
    assert r.returncode == 1 and "1 of 1 stale: login-drill" in r.stdout, r.stdout


def test_the_run_in_flight_still_has_its_clock_graded(tmp_path: Path) -> None:
    """The exemption is freshness only. If the cron behind the workflow in flight has died, the
    schedule row is still red -- being the run computing the row buys no green."""
    now = datetime.now(timezone.utc)
    b, cat = _estate(tmp_path, [("verify-drill.yml", 3)], {"verify-drill.yml": None},
                     {"verify-drill.yml": _hourly(2, now)})
    r = _run(tmp_path, b, cat, _in_ci())
    assert "verify-drill.yml is the run computing this row" in r.stdout, r.stdout + r.stderr
    assert "verify-drill.yml fired 2 of 24 promised in 24h" in r.stdout, r.stdout
    assert r.returncode == 1, r.stdout


def test_the_workflow_name_identifies_the_run_when_the_ref_is_absent(tmp_path: Path) -> None:
    """GITHUB_WORKFLOW_REF names the file; GITHUB_WORKFLOW carries only the `name:` field. The row
    matches that against the catalogued files on disk, so no workflow name is written in the
    script (LAW 46)."""
    now = datetime.now(timezone.utc)
    b, cat = _estate(tmp_path, [("verify-drill.yml", 3)], {"verify-drill.yml": None},
                     {"verify-drill.yml": _hourly(24, now)}, names={"verify-drill.yml": "verify-drill"})
    r = _run(tmp_path, b, cat, {"GITHUB_RUN_ID": RUN_IN_FLIGHT, "GITHUB_WORKFLOW": "verify-drill"})
    assert "verify-drill.yml is the run computing this row" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0, r.stdout


def test_freshness_is_the_age_of_a_completed_green_run(tmp_path: Path) -> None:
    """Freshness is the age of a completed, green run, never of a run in flight. login-drill.yml
    is graded by its last green one either way: 1h ago is green, 9h ago is red."""
    now = datetime.now(timezone.utc)
    green = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    b, cat = _estate(tmp_path, [("login-drill.yml", 3)], {"login-drill.yml": green},
                     {"login-drill.yml": _hourly(24, now)})
    r = _run(tmp_path, b, cat, _in_ci())
    assert "login-drill.yml last green 1.0h ago (max 3h)" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0, r.stdout

    stale_green = (now - timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%SZ")
    b2, cat2 = _estate(tmp_path / "b", [("login-drill.yml", 3)], {"login-drill.yml": stale_green},
                       {"login-drill.yml": _hourly(24, now)})
    r2 = _run(tmp_path / "b", b2, cat2, _in_ci())
    assert "login-drill.yml last green 9.0h ago, older than 3h" in r2.stdout, r2.stdout + r2.stderr
    assert r2.returncode == 1, r2.stdout
