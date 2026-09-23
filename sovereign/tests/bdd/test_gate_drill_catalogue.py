"""Binds features/drills/drill-catalogue.feature (crew#292 CP2, crew#297): the catalogue names
only scheduled workflows. The PR-body rule drill_named that also read this catalogue was
deleted with the rest of the prose gates on 2026-09-08
over the checked-in policy/fixtures/opmodel-*.json, both the permitted and the refused shapes."""
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then

scenarios("features/drills/drill-catalogue.feature")

IDP = Path(__file__).resolve().parents[3]
FIX = IDP / "policy" / "fixtures"


@pytest.fixture
def state() -> dict:
    return {}


def _conftest(fixture: str) -> subprocess.CompletedProcess:
    assert shutil.which("conftest"), "conftest is not installed; the bdd job installs it"
    return subprocess.run(["conftest", "test", str(FIX / fixture), "-p", "policy/", "-n", "main", "--no-color"],
                          cwd=IDP, capture_output=True, text=True)


def _crons(workflow: str) -> set[str]:
    wf = yaml.safe_load((IDP / ".github/workflows" / workflow).read_text())
    on = wf.get("on") or wf.get(True) or {}
    return {s["cron"] for s in (on.get("schedule") or [])}


# --- The catalogue names only drills that are really scheduled --------------------------------

@given("drills/catalogue.yaml")
def _catalogue(state: dict) -> None:
    state["drills"] = yaml.safe_load((IDP / "drills/catalogue.yaml").read_text())["drills"]
    assert state["drills"]


@then("every entry names a file that exists under .github/workflows")
def _exists(state: dict) -> None:
    for d in state["drills"]:
        assert (IDP / ".github/workflows" / d["workflow"]).is_file(), d


@then("each entry's schedule string is the cron line that workflow declares")
def _schedule(state: dict) -> None:
    for d in state["drills"]:
        assert d["schedule"] in _crons(d["workflow"]), (d["name"], d["schedule"], _crons(d["workflow"]))


@then("no entry exists for a workflow that has no schedule block")
def _scheduled(state: dict) -> None:
    for d in state["drills"]:
        assert _crons(d["workflow"]), d["workflow"]


