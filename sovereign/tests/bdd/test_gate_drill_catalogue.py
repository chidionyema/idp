"""Binds features/drills/drill-catalogue.feature (crew#292 CP2, crew#297): the catalogue names
only scheduled workflows, and policy/operating_model.rego rule drill_named is judged by conftest
over the checked-in policy/fixtures/opmodel-*.json, both the permitted and the refused shapes."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

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


# --- A pull request names the drill it adds to the catalogue ------------------------------------

@given('a PR that changes platform/ and adds a "- name: <drill>" row to drills/catalogue.yaml')
def _added(state: dict) -> None:
    fx = json.loads((FIX / "opmodel-drill-added-in-pr.json").read_text())
    pr = fx["pr"]
    assert any(f.startswith(("platform/", "clusters/")) for f in pr["files"]), pr["files"]
    assert "drills/catalogue.yaml" in pr["files"]
    m = re.search(r"(?m)^\+\s*-\s*name:\s*(\S+)", pr["added"])
    assert m, pr["added"]
    state["drill"] = m.group(1)
    state["pr"] = pr


@given('its body says "Drill: <drill>"')
def _body(state: dict) -> None:
    assert f"Drill: {state['drill']}" in state["pr"]["body"], state["pr"]["body"]


@when("the operating-model gate judges it against the catalogue on main")
def _judge(state: dict) -> None:
    state["run"] = _conftest("opmodel-drill-added-in-pr.json")


@then("rule drill_named allows it, because the row is in the PR's own diff")
def _allowed(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 0 and "drill_named" not in r.stdout, r.stdout + r.stderr


@then('a "Drill:" line naming a row in neither place is still refused')
def _unknown_refused(state: dict) -> None:
    r = _conftest("opmodel-unknown-drill.json")
    assert r.returncode != 0 and "rule=drill_named" in r.stdout, r.stdout + r.stderr


# --- A platform change names the drill that exercises it ----------------------------------------

@given("a pull request changes a file under platform/ or clusters/")
def _platform_pr(state: dict) -> None:
    for name in ("opmodel-no-drill.json", "opmodel-unknown-drill.json", "opmodel-ok.json"):
        files = json.loads((FIX / name).read_text())["pr"]["files"]
        assert any(f.startswith(("platform/", "clusters/")) for f in files), (name, files)


@when("bin/pr-report runs the operating-model gate")
def _gate(state: dict) -> None:
    state["runs"] = {n: _conftest(n) for n in ("opmodel-no-drill.json", "opmodel-unknown-drill.json", "opmodel-ok.json")}


@then('a body with no "Drill: <name>" line is refused with rule=drill_named')
def _no_drill(state: dict) -> None:
    fx = json.loads((FIX / "opmodel-no-drill.json").read_text())
    assert "Drill:" not in fx["pr"]["body"]
    r = state["runs"]["opmodel-no-drill.json"]
    assert r.returncode != 0 and "rule=drill_named" in r.stdout, r.stdout


@then('a "Drill:" line naming nothing in drills/catalogue.yaml is refused with rule=drill_named')
def _unknown(state: dict) -> None:
    r = state["runs"]["opmodel-unknown-drill.json"]
    assert r.returncode != 0 and "rule=drill_named" in r.stdout, r.stdout


@then('a "Drill:" line naming a catalogued drill passes')
def _ok(state: dict) -> None:
    r = state["runs"]["opmodel-ok.json"]
    assert r.returncode == 0, r.stdout + r.stderr


@then("the gate reads the catalogue names itself; a PR cannot invent one")
def _reads_catalogue(state: dict) -> None:
    fx = json.loads((FIX / "opmodel-ok.json").read_text())
    m = re.search(r"Drill:\s*(\S+)", fx["pr"]["body"])
    assert m and m.group(1) in fx["drills"], (m and m.group(1), fx.get("drills"))
    catalogue = {d["name"] for d in yaml.safe_load((IDP / "drills/catalogue.yaml").read_text())["drills"]}
    assert m.group(1) in catalogue, (m.group(1), catalogue)
