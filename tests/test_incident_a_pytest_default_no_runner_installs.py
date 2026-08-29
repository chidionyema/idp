"""The repository's pytest default must be installable in every environment that runs pytest.

2026-08-28 19:34Z: kyverno-secrets-drill went red on every run and stayed red for 34 hours. Nothing
about the Kyverno secrets policy was graded in that time; the drill row in `bin/idp-drills-row` read
`FAIL ... last green 34.0h ago`, and `verify-drill` -- which grades the drill rows -- went red hourly
behind it. The cause was one line, `addopts = "-n auto"` in pyproject.toml (crew#584, 93f49ec7): a
pytest ini option is read in EVERY environment, and `.github/requirements/kyverno-secrets-drill.txt`
pinned `pytest` without `pytest-xdist`, so pytest died at argument parsing with
`error: unrecognized arguments: -n` before it collected a single test.

The class is not "that file was missing a line". It is that a default declared centrally must be
satisfiable by every environment that inherits it, and nothing checked the two against each other.
This test is that check: it reads the flags the ini actually sets, maps each to the distribution
that provides it, and asserts every workflow job that runs pytest installs it.

An unknown flag FAILS rather than passing quietly. An allow-list with a silent miss case is how the
original defect reached main: the requirements file was correct for the pytest that existed when it
was written, and nothing re-read it when the default changed.
"""
from __future__ import annotations

import re
import shlex
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# A flag in addopts either comes from pytest itself or from a plugin that must be installed.
FLAG_NEEDS = {
    "-n": "pytest-xdist", "--numprocesses": "pytest-xdist", "--dist": "pytest-xdist",
    "--cov": "pytest-cov", "--cov-report": "pytest-cov",
    "--timeout": "pytest-timeout",
    "--randomly-seed": "pytest-randomly",
    "--benchmark-only": "pytest-benchmark",
}
# Shipped with pytest; no distribution to install.
BUILTIN = {
    "-q", "--quiet", "-v", "--verbose", "-x", "--exitfirst", "-s", "-ra", "-rA", "-p", "--tb",
    "--durations", "--strict-markers", "--strict-config", "--maxfail", "--import-mode",
    "--rootdir", "--color", "--no-header", "--no-summary", "-l", "--showlocals",
}
PYTEST_RUN = re.compile(r"(?:^|[|&;(\s])(?:python3?\s+-m\s+)?pytest(?:\s|$)")
PIP_REQS = re.compile(r"-r\s+(\S+\.txt)")


def _addopts() -> list[str]:
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    opts = cfg.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", "")
    return shlex.split(opts) if isinstance(opts, str) else list(opts)


def required_distributions() -> set[str]:
    """The distributions pyproject's addopts makes mandatory, in every environment."""
    needed: set[str] = set()
    for tok in _addopts():
        if not tok.startswith("-"):
            continue                      # a value, e.g. the `auto` of `-n auto`
        flag = tok.split("=", 1)[0]
        if flag in FLAG_NEEDS:
            needed.add(FLAG_NEEDS[flag])
        elif flag not in BUILTIN:
            pytest.fail(
                f"pyproject.toml addopts sets {flag!r} and this test does not know whether it is a "
                "pytest builtin or a plugin flag. Add it to BUILTIN or to FLAG_NEEDS above. Guessing "
                "here is the defect: the drill this test exists for was broken by exactly one "
                "unreviewed addopts flag."
            )
    return needed


def jobs_that_run_pytest() -> list[tuple[str, str, list[str], list[str]]]:
    """(workflow, job, run-strings that invoke pytest, requirements files the job pip-installs)."""
    found = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        doc = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        for job_name, job in (doc.get("jobs") or {}).items():
            runs = [s["run"] for s in (job.get("steps") or []) if isinstance(s, dict) and s.get("run")]
            invocations = [r for r in runs if PYTEST_RUN.search(r)]
            if not invocations:
                continue
            reqs = [m for r in runs if "pip install" in r or "pip3 install" in r
                    for m in PIP_REQS.findall(r)]
            found.append((wf.name, job_name, invocations, reqs))
    return found


def test_the_incident_every_workflow_that_runs_pytest_installs_what_addopts_needs():
    needed = required_distributions()
    if not needed:
        pytest.skip("pyproject addopts requires no plugin; nothing for an environment to miss")
    missing = []
    for wf, job, _invocations, reqs in jobs_that_run_pytest():
        if not reqs:
            missing.append(f"{wf}:{job} runs pytest and pip-installs no requirements file at all")
            continue
        have = "\n".join((ROOT / r).read_text(encoding="utf-8") for r in reqs if (ROOT / r).exists())
        for dist in sorted(needed):
            if not re.search(rf"^\s*{re.escape(dist)}\b", have, re.M):
                missing.append(f"{wf}:{job} runs pytest but {' '.join(reqs)} does not install {dist}")
    assert not missing, (
        "pyproject.toml addopts needs " + ", ".join(sorted(needed)) + " in every environment:\n  "
        + "\n  ".join(missing)
        + "\nEither add the distribution to that requirements file, or take the flag out of addopts."
    )


def test_the_guard_still_sees_the_job_the_incident_happened_in():
    """An allow-list that has quietly stopped matching anything passes for ever.

    If pytest moves behind a script (`bin/idp-ci`, a make target) this guard cannot see it, and a
    guard that grades nothing must say so rather than read green. The drill below is the job the
    incident happened in; it is the canary for the detector itself.
    """
    seen = {(wf, job) for wf, job, _i, _r in jobs_that_run_pytest()}
    assert ("kyverno-secrets-drill.yml", "kyverno-secrets-drill") in seen, (
        "the job this test was written for no longer looks like a pytest job to this detector; "
        f"it currently sees {sorted(seen)}"
    )
    assert len(seen) >= 2, f"only {sorted(seen)} detected; ci.yml runs pytest too"


def test_an_environment_missing_the_plugin_is_caught_rather_than_assumed():
    """The detector fails on the file as it stood when the drill broke, and passes on the fix."""
    broken = "# comment mentioning pytest-xdist in prose\npytest\npyyaml\n"
    fixed = "pytest\npytest-xdist\npyyaml\n"
    assert not re.search(r"^\s*pytest-xdist\b", broken, re.M), "prose must not count as an install"
    assert re.search(r"^\s*pytest-xdist\b", fixed, re.M)


def test_an_unknown_addopts_flag_fails_loudly_instead_of_passing(monkeypatch):
    monkeypatch.setattr(Path, "read_text", lambda self, **kw: '[tool.pytest.ini_options]\naddopts = "--wat"\n'
                        if self.name == "pyproject.toml" else Path.read_text(self, **kw))
    with pytest.raises(pytest.fail.Exception) as exc:
        required_distributions()
    assert "--wat" in str(exc.value)
