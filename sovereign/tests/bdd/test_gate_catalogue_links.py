"""Binds features/gates/catalogue-links.feature (crew#269, crew#297). Steps run bin/catalog-gen and
bin/catalog-links-check for real over the tracked inventory fixtures; nothing is mocked."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/catalogue-links.feature")

IDP = Path(__file__).resolve().parents[3]


@pytest.fixture
def state(tmp_path: Path) -> dict:
    return {"out": tmp_path / "out"}


@given(parsers.parse("{fixture}, where every repo has a github remote"))
def _clean(state: dict, fixture: str) -> None:
    state["inv"] = IDP / fixture; assert state["inv"].is_file()


@given(parsers.parse('{fixture}, one repo with remote "(none)"'))
def _no_remote(state: dict, fixture: str) -> None:
    state["inv"] = IDP / fixture; assert '"(none)"' in state["inv"].read_text()


@given("catalog/catalog-info.yaml does not exist")
def _missing(state: dict) -> None:
    state["path"] = state["out"] / "catalog-info.yaml"; assert not state["path"].exists()


@when("bin/catalog-gen writes the catalogue and bin/catalog-links-check reads it")
def _gen_then_check(state: dict) -> None:
    state["out"].mkdir(exist_ok=True)
    g = subprocess.run([sys.executable, str(IDP / "bin" / "catalog-gen")], env={**os.environ, "INV": str(state["inv"]), "OUT": str(state["out"]), "ESTATE_ENV": "dev"}, capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
    state["run"] = subprocess.run([sys.executable, str(IDP / "bin" / "catalog-links-check"), str(state["out"] / "catalog-info.yaml")], capture_output=True, text=True)


@when("bin/catalog-links-check runs")
def _check_only(state: dict) -> None:
    state["run"] = subprocess.run([sys.executable, str(IDP / "bin" / "catalog-links-check"), str(state["path"])], capture_output=True, text=True)


@then(parsers.parse('it prints "{line}" and exits 0'))
def _ok(state: dict, line: str) -> None:
    r = state["run"]; assert r.returncode == 0 and line in r.stdout, r.stdout + r.stderr


@then("it names the Component and its path and exits 1")
def _named(state: dict) -> None:
    r = state["run"]; out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert "Components carry no URL" in out and "orphan-checkout (/" in out, out


@then("it prints BLIND and exits 2, never ok")
def _blind(state: dict) -> None:
    r = state["run"]; assert r.returncode == 2 and "BLIND" in (r.stdout + r.stderr), r.stdout + r.stderr
