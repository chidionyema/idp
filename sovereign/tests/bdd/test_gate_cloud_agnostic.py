"""Binds features/cloud-agnostic/disposable-compute-universal-state.feature (crew#250 R36, crew#297).
Steps run bin/cloud-agnostic-gate for real over tests/fixtures/cloud-agnostic/{good,bad}."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/cloud-agnostic/disposable-compute-universal-state.feature")

IDP = Path(__file__).resolve().parents[3]
FIX = IDP / "tests" / "fixtures" / "cloud-agnostic"


def _gate(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(IDP / "bin" / "cloud-agnostic-gate")], env={**os.environ, "CLOUD_AGNOSTIC_ROOT": str(root)}, capture_output=True, text=True)


@pytest.fixture
def state() -> dict:
    return {}


@given("a platform tree with no provider-specific reference outside platform/oci, platform/secret-store and clusters/")
def _good(state: dict) -> None:
    assert (FIX / "good" / "platform").is_dir(); state["root"] = FIX / "good"


@when("bin/cloud-agnostic-gate counts provider-specific annotations, services and API groups")
def _count(state: dict) -> None:
    state["run"] = _gate(state["root"])


@then("the count is zero and it exits 0")
def _zero(state: dict) -> None:
    r = state["run"]; assert r.returncode == 0, r.stdout + r.stderr


@then("a tree that adds one is refused with the file and line that introduced it")
def _bad(state: dict, tmp_path: Path) -> None:
    r = _gate(FIX / "bad")
    assert r.returncode == 1, r.stdout + r.stderr
    assert any(":" in line and "platform/" in line for line in r.stdout.splitlines()), r.stdout


@then("a root that cannot be read is BLIND, never zero")
def _blind(state: dict, tmp_path: Path) -> None:
    r = _gate(tmp_path / "missing")
    assert r.returncode == 2 and r.stdout.startswith("BLIND"), r.stdout + r.stderr
