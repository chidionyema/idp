"""Binds features/assurance/trace-matrix.feature (crew#495 CP1). Steps run bin/trace-matrix for
real over a throwaway git repository holding one bound and one unbound feature."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/assurance/trace-matrix.feature")

IDP = Path(__file__).resolve().parents[3]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True, capture_output=True)


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(IDP / "bin" / "trace-matrix"), *args],
                          env={**os.environ, "TRACE_MATRIX_ROOT": str(repo)}, capture_output=True, text=True)


@pytest.fixture
def state(tmp_path: Path) -> dict:
    return {"repo": tmp_path / "r"}


@given("a repository with one feature a test loads and one feature nothing loads")
def _repo(state: dict) -> None:
    repo = state["repo"]
    (repo / "features").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "features" / "bound.feature").write_text("Feature: bound\n  Scenario: runs\n    Given x\n")
    (repo / "features" / "prose.feature").write_text("Feature: prose\n  Scenario: one\n    Given x\n  Scenario: two\n    Given y\n")
    (repo / "tests" / "test_bound.py").write_text('from pytest_bdd import scenarios\nscenarios("features/bound.feature")\n')
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "features", "tests")
    _git(repo, "commit", "-q", "-m", "base (crew#495) (#1)")


@when("bin/trace-matrix renders it")
def _render(state: dict) -> None:
    state["check"] = _run(state["repo"], "--check")
    state["page"] = (state["repo"] / "docs" / "TRACE-MATRIX.md").read_text()


@when("the second feature gains a test that loads it")
def _bind(state: dict) -> None:
    (state["repo"] / "tests" / "test_prose.py").write_text('from pytest_bdd import scenarios\nscenarios("features/prose.feature")\n')
    _git(state["repo"], "add", "tests")
    _git(state["repo"], "commit", "-q", "-m", "bind prose (crew#495) (#2)")
    _render(state)


@then("the page lists the unbound feature before the bound one")
def _order(state: dict) -> None:
    page = state["page"]
    assert page.index("| UNBOUND | `features/prose.feature`") < page.index("| BOUND | `features/bound.feature`")
    assert "**1 UNBOUND** of 2" in page and "**1 run by a test** of 3" in page
    assert "#1 crew#495" in page


@then(parsers.parse("--check exits {code:d} naming one unbound feature"))
def _finding(state: dict, code: int) -> None:
    assert state["check"].returncode == code, state["check"].stdout + state["check"].stderr
    assert "1 unbound (2 scenarios nothing runs)" in state["check"].stdout


@then("--check exits 0 and the page has no UNBOUND row")
def _clean(state: dict) -> None:
    assert state["check"].returncode == 0, state["check"].stdout + state["check"].stderr
    assert "| UNBOUND |" not in state["page"] and "**0 UNBOUND** of 2" in state["page"]
