"""Binds features/gates/spec-gate.feature (crew#297). Steps drive bin/spec-gate for real against a
temporary git repository; nothing is mocked."""
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/spec-gate.feature")

GATE = Path(__file__).resolve().parents[3] / "bin" / "spec-gate"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, capture_output=True, text=True, check=True)


def _commit(repo: Path, files: dict[str, str], msg: str) -> None:
    for name, body in files.items():
        p = repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(body)
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", msg)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"; r.mkdir(); _git(r, "init", "-q", "-b", "main")
    _commit(r, {"app.py": "x=1\n", "features/old.feature": "Feature: old\n"}, "base")
    _git(r, "checkout", "-q", "-b", "pr")
    return r


@pytest.fixture
def runs() -> dict:
    return {}


@given("a PR that changes code and a *.feature file no tracked test names")
def _pr(repo: Path) -> None:
    _commit(repo, {"app.py": "x=2\n", "features/old.feature": "Feature: old, edited\n"}, "touched only")


@when("bin/spec-gate runs")
def _run(repo: Path, runs: dict) -> None:
    runs["first"] = subprocess.run(["bash", str(GATE), "main"], cwd=repo, capture_output=True, text=True)


@then("the feature does not count as executable spec and the gate prints FAIL")
def _fail(runs: dict) -> None:
    r = runs["first"]
    assert r.returncode == 1 and "FAIL  spec-gate 1 code file(s) changed and no executable spec" in r.stdout, r.stdout + r.stderr


@then("a new *.feature file no test names is refused with the pytest-bdd binding shown")
def _new(repo: Path, runs: dict) -> None:
    _commit(repo, {"features/new.feature": "Feature: nobody runs me\n", "tests/test_x.py": "def test_x(): pass\n"}, "new prose plus a test")
    r = subprocess.run(["bash", str(GATE), "main"], cwd=repo, capture_output=True, text=True)
    runs["second"] = r
    assert r.returncode == 1 and "FAIL  spec-gate new *.feature" in r.stdout and "features/new.feature" in r.stdout and "scenarios(" in r.stdout, r.stdout


@then(parsers.parse('every run prints "{prefix}"'))
def _residual(runs: dict, prefix: str) -> None:
    head = prefix.split(" N ")[0]
    for r in runs.values():
        assert head in r.stdout and "feature file(s) named by no test" in r.stdout, r.stdout
