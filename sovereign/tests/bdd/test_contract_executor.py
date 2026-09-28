"""Binds features/gates/contract-executor.feature (founder essay 2026-09-14, the Reasoning
Gateway; docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D3).

Every step runs the real gate over a real contract file written to a temp file -- no mocks, no
import of the library under test.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/contract-executor.feature")

IDP = Path(__file__).resolve().parents[3]
CONTRACT = IDP / "bin" / "idp-contract"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603,S607 -- fixed argv, no shell, path from this checkout
        [sys.executable, str(CONTRACT), "--run", *args],
        cwd=IDP,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _write(tmp_path: Path, record: dict) -> Path:
    p = tmp_path / "contract.json"
    p.write_text(json.dumps(record))
    return p


@pytest.fixture
def state() -> dict:
    return {}


@given(
    "a contract whose pre-condition holds and whose post-condition never passes within its deadline"
)
def _never_holds(state, tmp_path):
    state["path"] = _write(
        tmp_path,
        {
            "tool": "restart_pod",
            "pre": "pod uptime > 0s",
            "post": "readiness probe passes within 30s",
            "observations": {
                "pod uptime": [[0, 5]],
                "readiness probe": [[10, False], [20, False], [45, True]],
            },
        },
    )


@given(
    "a contract whose pre-condition holds and whose post-condition passes before its deadline"
)
def _holds(state, tmp_path):
    state["path"] = _write(
        tmp_path,
        {
            "tool": "restart_pod",
            "pre": "pod uptime > 0s",
            "post": "readiness probe passes within 30s",
            "observations": {
                "pod uptime": [[0, 5]],
                "readiness probe": [[10, False], [20, True]],
            },
        },
    )


@given("a contract whose post-condition names a subject with no observation")
def _no_observation(state, tmp_path):
    state["path"] = _write(
        tmp_path,
        {
            "tool": "restart_pod",
            "pre": "pod uptime > 0s",
            "post": "readiness probe passes within 30s",
            "observations": {"pod uptime": [[0, 5]]},
        },
    )


@given("a contract file that does not exist")
def _missing(state, tmp_path):
    state["path"] = tmp_path / "does-not-exist.json"


@when("bin/idp-contract runs it")
def _grade(state):
    state["result"] = _run([str(state["path"])])


@then("it exits 1 and names the post-condition as the cause")
def _refused(state):
    r = state["result"]
    if r.returncode != 1:
        raise AssertionError(r.stdout + r.stderr)
    out = r.stdout + r.stderr
    if "post_condition_failed" not in out:
        raise AssertionError(out)


@then("it exits 0, because the post-condition was confirmed by a real observation")
def _passed(state):
    r = state["result"]
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)


@then("it exits 2, because a missing observation is BLIND, never assumed to hold")
def _blind_observation(state):
    r = state["result"]
    if r.returncode != 2:
        raise AssertionError(r.stdout + r.stderr)


@then("it exits 2, because an unreadable contract is never a clean bill")
def _blind_missing(state):
    r = state["result"]
    if r.returncode != 2:
        raise AssertionError(r.stdout + r.stderr)
