"""Binds features/stale_pr.feature (crew#299, crew#297). actions/stale owns the clock; the estate owns
its inputs, so the steps read .github/workflows/stale.yml for real and grade what the action is told."""
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/stale_pr.feature")

IDP = Path(__file__).resolve().parents[3]
WF = IDP / ".github" / "workflows" / "stale.yml"


def _inputs() -> dict:
    wf = yaml.safe_load(WF.read_text())
    steps = [s for j in wf["jobs"].values() for s in j["steps"] if str(s.get("uses", "")).startswith("actions/stale@")]
    assert len(steps) == 1, "stale.yml must run actions/stale exactly once"
    return steps[0]["with"]


@pytest.fixture
def state() -> dict:
    return {"with": _inputs()}


@given("a pull request with no push, comment or label change for 7 days")
def _idle(state: dict) -> None:
    state["idle_days"] = 7


@given('it does not carry the label "keep-open"')
def _not_exempt(state: dict) -> None:
    assert "keep-open" in str(state["with"]["exempt-pr-labels"]).split(",")


@given('a pull request labelled "stale" with no activity for a further 7 days')
def _warned_idle(state: dict) -> None:
    state["idle_days_after_warning"] = 7


@given('a pull request labelled "stale"')
def _warned(state: dict) -> None:
    assert state["with"]["stale-pr-label"] == "stale"


@given("an issue with no activity for 60 days")
def _issue(state: dict) -> None:
    state["issue_idle_days"] = 60


@when("the stale workflow runs")
def _runs(state: dict) -> None:
    wf = yaml.safe_load(WF.read_text())
    assert (wf.get("on") or wf.get(True))["schedule"], "stale.yml has no schedule"  # YAML 1.1 reads `on` as True


@when('someone pushes, comments, or adds the label "keep-open"')
def _activity(state: dict) -> None:
    # actions/stale removes the label on any update unless told not to.
    assert state["with"].get("remove-stale-when-updated", True) is not False
    assert "keep-open" in str(state["with"]["exempt-pr-labels"]).split(",")


@then('the pull request is labelled "stale"')
def _labelled(state: dict) -> None:
    assert int(state["with"]["days-before-pr-stale"]) == state["idle_days"]
    assert state["with"]["stale-pr-label"] == "stale"


@then("a comment says it closes in 7 more days")
def _warns(state: dict) -> None:
    assert "7 more days" in state["with"]["stale-pr-message"]
    assert int(state["with"]["days-before-pr-close"]) == 7


@then("the pull request is closed and its branch deleted")
def _closed(state: dict) -> None:
    assert int(state["with"]["days-before-pr-close"]) == state["idle_days_after_warning"]
    assert state["with"]["delete-branch"] is True


@then('the "stale" label is removed and the pull request stays open')
def _stays(state: dict) -> None:
    assert state["with"].get("remove-stale-when-updated", True) is not False


@then("the issue is unchanged")
def _issue_untouched(state: dict) -> None:
    assert int(state["with"]["days-before-issue-stale"]) == -1
    assert int(state["with"]["days-before-issue-close"]) == -1
