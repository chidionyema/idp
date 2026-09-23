"""Binds features/gates/estate-zone.feature (crew#269, crew#297). Steps run bin/estate-zone-gate
for real over tests/fixtures/estate-zone/{good,bad} and an empty root."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/estate-zone.feature")

IDP = Path(__file__).resolve().parents[3]
FIX = IDP / "tests" / "fixtures" / "estate-zone"


def _gate(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(IDP / "bin" / "estate-zone-gate"), *args],
                          env={**os.environ, "ESTATE_ZONE_ROOT": str(root)}, capture_output=True, text=True)


@pytest.fixture
def state() -> dict:
    return {}


@given("clusters/x/estate-config.yaml declares ESTATE_ZONE")
def _declares(state: dict) -> None:
    cfgs = list((FIX / "bad" / "clusters").glob("*/estate-config.yaml"))
    assert cfgs and "ESTATE_ZONE:" in cfgs[0].read_text()


@given("platform/edge/route.yaml lists the hostname catalogue.<zone> spelled out")
def _literal(state: dict) -> None:
    state["root"] = FIX / "bad"
    assert "${ESTATE_ZONE}" not in (state["root"] / "platform" / "edge" / "route.yaml").read_text()


@given("the same config")
def _same(state: dict) -> None:
    cfgs = list((FIX / "good" / "clusters").glob("*/estate-config.yaml"))
    assert cfgs and "ESTATE_ZONE:" in cfgs[0].read_text()


@given("platform/edge/route.yaml lists the hostname catalogue.${ESTATE_ZONE}")
def _subst(state: dict) -> None:
    state["root"] = FIX / "good"
    assert "${ESTATE_ZONE}" in (state["root"] / "platform" / "edge" / "route.yaml").read_text()


@given("a diff that adds the hostname catalogue.<zone> spelled out")
def _diff_literal(state: dict) -> None:
    state["root"], state["diff"] = FIX / "bad", FIX / "added-literal.diff"
    assert "+    - catalogue.mumchimp.com" in state["diff"].read_text()


@given("a diff that adds the hostname catalogue.${ESTATE_ZONE}")
def _diff_subst(state: dict) -> None:
    state["root"], state["diff"] = FIX / "bad", FIX / "added-substituted.diff"
    assert "+    - catalogue.${ESTATE_ZONE}" in state["diff"].read_text()


@when("bin/estate-zone-gate grades the diff")
def _run_diff(state: dict) -> None:
    state["run"] = _gate(state["root"], "--diff", str(state["diff"]))


@given("no clusters/*/estate-config.yaml")
def _none(state: dict, tmp_path: Path) -> None:
    (tmp_path / "platform").mkdir()
    state["root"] = tmp_path


@when("bin/estate-zone-gate runs")
def _run(state: dict) -> None:
    state["run"] = _gate(state["root"])


@then("it exits 1 and prints that file and line")
def _one(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 1 and "platform/edge/route.yaml:" in r.stdout, r.stdout + r.stderr


@then("it exits 0")
def _zero(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 0, r.stdout + r.stderr


@then("it exits 2 and prints BLIND, not a verdict")
def _blind(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 2 and "BLIND" in r.stdout + r.stderr, r.stdout + r.stderr
