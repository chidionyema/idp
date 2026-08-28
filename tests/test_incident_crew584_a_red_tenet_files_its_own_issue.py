"""crew#584 -- a red tenet row is work, not a report.

Founder, 2026-08-28: "why did i need to tel the crew to optinise the tests ... the engineerig
phisolophi is weak. we should not be renided for the engineering tenents"; "we neasure everything
but we dont act ont i". conscience/tenets.yaml held seven ethos rows and no engineering row, the
grade ran only as a CI selftest, and a 9-minute CI was red nowhere. Now the engineering rows sit in
the same file, bin/idp-conscience --act files one crew issue per red row (created once, updated
every later hour), and bin/idp-verify-drill runs it hourly.

Tests never open a socket: `gh` is a shim on PATH that records its argv and answers from a file.
"""
import json
import os
import pathlib
import subprocess
import sys

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
CONSCIENCE = IDP / "bin" / "idp-conscience"
FX = IDP / "tests" / "fixtures" / "conscience"

GH_SHIM = """#!/bin/sh
# records every call; answers `issue list` from GH_LIST_ANSWER, `issue create` with a URL, `repo view` with an owner
printf '%s\\n' "$*" >> "$GH_CALLS"
case "$1 $2" in
  "issue list") printf '%s' "${GH_LIST_ANSWER:-}" ;;
  "issue create") echo "https://example.invalid/board/issues/77" ;;
  "repo view") echo "someone" ;;
  "run list") cat "$GH_RUNS" ;;
  "pr list") cat "$GH_PRS" ;;
esac
"""


def shim(tmp_path: pathlib.Path) -> dict:
    b = tmp_path / "bin"; b.mkdir()
    (b / "gh").write_text(GH_SHIM); (b / "gh").chmod(0o755)
    calls = tmp_path / "calls.txt"; calls.write_text("")
    return {**os.environ, "PATH": f"{b}:{os.environ['PATH']}", "GH_CALLS": str(calls),
            "GH_RUNS": str(tmp_path / "runs.json"), "GH_PRS": str(tmp_path / "prs.json")}


def run(args, env, tenets=None, tmp_path=None):
    if tenets is not None:
        env = {**env, "CONSCIENCE_TENETS": str(tenets), "CONSCIENCE_REPORT": str(tmp_path / "r.json")}
    return subprocess.run([sys.executable, str(CONSCIENCE), *args], capture_output=True, text=True, env=env, cwd=IDP)


def test_a_red_row_files_one_issue_on_the_board_and_a_green_row_files_nothing(tmp_path):
    env = shim(tmp_path)
    p = run(["--act"], env, FX / "bad.yaml", tmp_path)
    assert p.returncode == 1, p.stdout + p.stderr           # still red: --act never launders the grade
    calls = pathlib.Path(env["GH_CALLS"]).read_text().splitlines()
    creates = [c for c in calls if c.startswith("issue create")]
    assert len(creates) == 1 and "conscience: b is red" in creates[0] and "--repo someone/crew" in creates[0]
    assert not any("conscience: a is red" in c for c in calls), "the green row must file nothing"
    assert "filed b" in p.stdout and "issues/77" in p.stdout


def test_a_row_already_filed_is_updated_not_duplicated(tmp_path):
    env = {**shim(tmp_path), "GH_LIST_ANSWER": "41"}
    p = run(["--act"], env, FX / "bad.yaml", tmp_path)
    calls = pathlib.Path(env["GH_CALLS"]).read_text().splitlines()
    assert not any(c.startswith("issue create") for c in calls)
    assert any(c.startswith("issue comment 41 --repo someone/crew") for c in calls)
    assert "someone/crew#41 (updated)" in p.stdout


def test_without_act_nothing_is_filed(tmp_path):
    env = shim(tmp_path)
    run([], env, FX / "bad.yaml", tmp_path)
    assert pathlib.Path(env["GH_CALLS"]).read_text() == ""


def test_the_board_is_derived_from_the_checkout_never_typed():
    src = CONSCIENCE.read_text()
    assert "CONSCIENCE_BOARD" in src and "/crew" in src
    assert "chidionyema" not in src, "LAW 46: the board owner comes from gh repo view"


def test_ci_minutes_reads_the_latest_green_run_and_flakes_count_reruns(tmp_path):
    env = shim(tmp_path)
    runs = [
        {"createdAt": "2026-08-28T17:41:48Z", "updatedAt": "2026-08-28T17:49:16Z", "conclusion": "success", "attempt": 1, "databaseId": 1},
        {"createdAt": "2026-08-28T17:31:45Z", "updatedAt": "2026-08-28T17:40:55Z", "conclusion": "success", "attempt": 2, "databaseId": 2},
    ]
    (tmp_path / "runs.json").write_text(json.dumps(runs))
    p = run(["--ci-minutes"], env)
    assert p.returncode == 0 and p.stdout.strip().splitlines()[-1] == "8", p.stdout + p.stderr   # 7.5 min rounds up
    p = run(["--flakes-days", "365000"], env)
    assert p.returncode == 0 and p.stdout.strip().splitlines()[-1] == "1", p.stdout + p.stderr


def test_pr_age_counts_only_old_open_prs(tmp_path):
    env = shim(tmp_path)
    (tmp_path / "prs.json").write_text(json.dumps([
        {"number": 5, "createdAt": "2000-01-01T00:00:00Z"}, {"number": 6, "createdAt": "2999-01-01T00:00:00Z"}]))
    p = run(["--pr-older-hours", "24"], env)
    assert p.returncode == 0 and p.stdout.strip().splitlines()[-1] == "1" and "#5" in p.stdout


def test_gh_missing_is_blind_never_green(tmp_path):
    env = {**os.environ, "PATH": str(tmp_path)}   # no gh anywhere
    for args in (["--ci-minutes"], ["--flakes-days", "7"], ["--pr-older-hours", "24"], ["--ci-minutes-day"]):
        p = run(args, env)
        assert p.returncode == 2 and "BLIND" in p.stdout, (args, p.stdout, p.stderr)


def test_the_engineering_rows_are_in_the_same_file_as_the_ethos():
    rows = {r["name"]: r for r in yaml.safe_load((IDP / "conscience" / "tenets.yaml").read_text())["tenets"]}
    for name in ("fast-ci", "fast-loop", "main-green", "short-lived-prs", "no-flake", "cost", "performance", "no-toil", "battle-tested"):
        assert name in rows and rows[name]["measure"], name
    assert rows["fast-ci"]["green"] == "<= 5" and "portable" in rows


def test_verify_drill_runs_the_conscience_with_act_every_hour():
    src = (IDP / "bin" / "idp-verify-drill").read_text()
    assert 'idp-conscience" --act' in src
