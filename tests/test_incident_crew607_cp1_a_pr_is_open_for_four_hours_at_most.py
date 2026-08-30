"""crew#607 CP1: founder 2026-08-28 "why do we have open PRs not merged" / "4 maximum". 24 open PRs,
oldest four days, four green and waiting for nobody. `bin/idp-pr-age` names the reason per PR and is
red when any is over PR_AGE_MAX_H (4)."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "bin/idp-pr-age"
NOW = "2026-08-28T22:00:00Z"


def _pr(repo, n, hours_old, **kw):
    created = f"2026-08-28T{22 - hours_old:02d}:00:00Z" if hours_old < 22 else "2026-08-24T00:00:00Z"
    d = {"repo": repo, "number": n, "title": f"pr {n}", "body": "", "createdAt": created,
         "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", "isDraft": False, "statusCheckRollup": []}
    d.update(kw)
    return d


def _run(tmp_path, prs, env=None):
    f = tmp_path / "prs.json"
    f.write_text(json.dumps(prs))
    p = subprocess.run([str(BIN), "--json", str(f), "--now", NOW], capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    return p.returncode, p.stdout


def test_the_measured_day_is_red_and_every_reason_is_named(tmp_path):
    prs = [
        _pr("idp", 647, 1),
        _pr("idp", 641, 3, mergeStateStatus="BLOCKED"),
        _pr("idp", 623, 5, mergeable="CONFLICTING"),
        _pr("crew", 605, 2, statusCheckRollup=[{"name": "review-gate", "conclusion": "FAILURE"}]),
        _pr("idp", 648, 1, statusCheckRollup=[{"name": "hydrate", "status": "IN_PROGRESS", "conclusion": None}]),
        _pr("idp", 650, 1, body="Stacked on idp#648 (merge that first)"),
        _pr("claude-guards", 46, 99),
    ]
    rc, out = _run(tmp_path, prs)
    assert rc == 1, out
    assert "FAIL    pr-age  7 open, 2 over 4h" in out
    for needle in ("647      1.0  green", "641      3.0  blocked-by-policy", "623      5.0  conflict",
                   "605      2.0  red:review-gate", "648      1.0  pending:hydrate", "650      1.0  stacked-on:idp#648"):
        assert needle in out, (needle, out)
    assert out.splitlines()[1].startswith("claude-guards     46"), "oldest first"


def test_under_four_hours_is_ok_and_the_bound_is_the_founders_number(tmp_path):
    rc, out = _run(tmp_path, [_pr("idp", 1, 3)])
    assert rc == 0 and "ok      pr-age  1 open, 0 over 4h" in out
    rc, out = _run(tmp_path, [_pr("idp", 1, 3)], env={"PR_AGE_MAX_H": "2"})
    assert rc == 1 and "1 over 2h" in out


def test_no_authority_clock_is_blind_never_green(tmp_path, monkeypatch):
    f = tmp_path / "prs.json"
    f.write_text("[]")
    (tmp_path / "gh").write_text("#!/bin/sh\nexit 1\n")  # gh answers nothing -> no Date header
    (tmp_path / "gh").chmod(0o755)
    p = subprocess.run([sys.executable, str(BIN), "--json", str(f)], capture_output=True, text=True,
                       env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"})
    assert p.returncode == 2 and p.stdout.startswith("BLIND pr-age: no clock")
