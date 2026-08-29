"""crew#584, 2026-08-28, measured on run 33202098401 (idp#632): offline-gate's `bin/idp-ci` took
211 s, of which the incident suite was 67 s and the bdd suite 65 s -- and ci.yml's bdd job ran
the same two suites again, strictly, at the same time. Nothing in the run said where the 211 s
went; it was dug out of the job log with a script. Founder: "2 faster is ok not good enough",
"we should already have diagnostics", "get faster at getting faster".

Rules:
  1. In CI the two suites run once: offline-gate sets IDP_CI_SKIP_PYTEST=1 and the rung says so
     instead of running pytest. Locally (no variable) the rung runs as before.
  2. Every `say` line carries the seconds the rung before it took when that is 3 s or more, and
     the run ends with a `timing` block of the slowest rungs -- also written to the GitHub step
     summary when there is one.
  3. The bdd job prints pytest's own ten slowest tests (--durations), so the next cut is read.

The say/timing functions and the pytest rung are lifted out of bin/idp-ci and executed, so a
change to that file is graded by these tests and not by a paraphrase of it."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "bin" / "idp-ci"
WF = ROOT / ".github" / "workflows" / "ci.yml"


def _lines() -> list[str]:
    return CI.read_text().splitlines()


def _say_block() -> str:
    lines = _lines()
    a = next(i for i, l in enumerate(lines) if l.startswith("_T_LAST=$SECONDS"))
    b = next(i for i in range(a, len(lines)) if lines[i] == "}" and lines[i - 1].startswith("\tif [ -n \"${GITHUB_STEP_SUMMARY"))
    return "\n".join(lines[a:b + 1]) + "\n"


def _pytest_rung() -> str:
    lines = _lines()
    a = next(i for i, l in enumerate(lines) if l.startswith('if [ "${IDP_CI_SKIP_PYTEST:-0}" = 1 ]'))
    b = next(i for i in range(a, len(lines)) if lines[i].startswith("fi # IDP_CI_SKIP_PYTEST"))
    return "\n".join(lines[a:b + 1]) + "\n"


def _bash(script: str, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, cwd=cwd)


def test_in_ci_the_two_suites_run_once_and_the_rung_says_so(tmp_path):
    fake = tmp_path / "bin"; fake.mkdir()
    (fake / "python3").write_text("#!/bin/sh\necho PYTEST-RAN >&2; exit 1\n"); (fake / "python3").chmod(0o755)
    script = _say_block() + 'fail=0; IDP="$PWD"; MPY="' + str(fake / "python3") + '"\n' + _pytest_rung() + 'echo fail=$fail\n'
    out = _bash(script, {"IDP_CI_SKIP_PYTEST": "1", "PATH": f"{fake}:{os.environ['PATH']}"}, tmp_path)
    assert out.returncode == 0, out.stderr
    assert "skip  bdd+incident" in out.stdout and "IDP_CI_SKIP_PYTEST=1" in out.stdout, out.stdout
    assert "PYTEST-RAN" not in out.stderr and "fail=0" in out.stdout, out.stderr


def test_locally_the_rung_still_runs_pytest(tmp_path):
    fake = tmp_path / "bin"; fake.mkdir()
    (fake / "python3").write_text("#!/bin/sh\necho PYTEST-RAN >&2; exit 1\n"); (fake / "python3").chmod(0o755)
    script = _say_block() + 'fail=0; IDP="$PWD"; MPY="' + str(fake / "python3") + '"\n' + _pytest_rung() + 'echo fail=$fail\n'
    env = {"PATH": f"{fake}:{os.environ['PATH']}"}
    out = _bash(script, env, tmp_path)
    assert "skip  bdd+incident" not in out.stdout, out.stdout
    assert "PYTEST-RAN" in out.stderr or "fail=1" in out.stdout, (out.stdout, out.stderr)


def test_offline_gate_sets_the_skip_and_the_bdd_job_prints_durations():
    wf = yaml.safe_load(WF.read_text())
    step = next(s for s in wf["jobs"]["offline-gate"]["steps"] if s.get("run") == "bin/idp-ci")
    assert step["env"]["IDP_CI_SKIP_PYTEST"] == "1", step["env"]
    runs = [s["run"] for s in wf["jobs"]["bdd-suites"]["steps"] if "pytest" in s.get("run", "")]
    assert len(runs) >= 2 and all("--durations=10" in r for r in runs), runs


def test_a_slow_rung_is_timed_on_its_line_and_in_the_summary(tmp_path):
    summary = tmp_path / "summary.md"
    script = _say_block() + '''
say "ok    fast     nothing"
sleep 3; say "ok    slow     three seconds of work"
say "ok    quick    also nothing"
timing_summary
'''
    out = _bash(script, {"GITHUB_STEP_SUMMARY": str(summary)})
    assert out.returncode == 0, out.stderr
    # a loaded runner measures 3s of sleep as 4s (main run 33243604531); the claim is "timed, at least 3s"
    m = re.search(r"ok    slow     three seconds of work  \((\d+)s\)", out.stdout)
    assert m and int(m.group(1)) >= 3, out.stdout
    assert "ok    fast     nothing\n" in out.stdout and "nothing  (" not in out.stdout, out.stdout
    assert "timing" in out.stdout and "slowest rungs" in out.stdout, out.stdout
    assert re.search(r"[3-9]s  ok    slow", summary.read_text()), summary.read_text()
