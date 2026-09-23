"""Binds features/gates/github-app-per-lane.feature (crew#286 CP7, crew#297). Steps read the real
platform/github-app JSON and run bin/idp-github-app for real with an unknown lane."""
import json
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/github-app-per-lane.feature")

IDP = Path(__file__).resolve().parents[3]
D = IDP / "platform" / "github-app"
LEVEL = {"none": 0, "read": 1, "write": 2, "admin": 3}


@pytest.fixture
def state() -> dict:
    return {}


@given("every lane in platform/github-app/lanes.json")
def _lanes(state: dict) -> None:
    state["lanes"] = json.loads((D / "lanes.json").read_text())
    assert state["lanes"], "lanes.json names no lane"


@then("each permission it names is in manifest.json default_permissions at the same or a lower level")
def _subset(state: dict) -> None:
    held = json.loads((D / "manifest.json").read_text())["default_permissions"]
    for lane, perms in state["lanes"].items():
        if lane.startswith("_"):
            continue
        for perm, level in perms.items():
            assert perm in held, f"lane {lane} asks for {perm}, which the App does not hold"
            assert LEVEL[level] <= LEVEL[held[perm]], f"lane {lane} asks {perm}:{level}, App holds {held[perm]}"


@when("bin/idp-github-app token no-such-lane runs")
def _unknown(state: dict, tmp_path: Path) -> None:
    # HOME is empty so any vault or gh access after the refusal would fail loudly, not silently.
    state["run"] = subprocess.run([str(IDP / "bin" / "idp-github-app"), "token", "no-such-lane"],
                                  env={"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(tmp_path)},
                                  capture_output=True, text=True)


@then("it prints REFUSED and exits 2 before touching the vault")
def _refused(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 2 and r.stdout.startswith("REFUSED"), r.stdout + r.stderr
