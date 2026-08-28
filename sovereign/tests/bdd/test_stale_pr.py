"""Binds features/stale_pr.feature (crew#299, crew#504). actions/stale owns the clock; the estate owns
its inputs, so the steps read .github/workflows/stale.yml for real and grade what the action is told.
actions/stale v11 parses days-before-pr-close with parseInt, so a same-run close is 0, never 0.5."""
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/stale_pr.feature")

IDP = Path(__file__).resolve().parents[3]
WF = IDP / ".github" / "workflows" / "stale.yml"


def _workflow() -> dict:
    return yaml.safe_load(WF.read_text())


def _inputs() -> dict:
    wf = _workflow()
    steps = [s for j in wf["jobs"].values() for s in j["steps"] if str(s.get("uses", "")).startswith("actions/stale@")]
    assert len(steps) == 1, "stale.yml must run actions/stale exactly once"
    return steps[0]["with"]


@pytest.fixture
def state() -> dict:
    return {"with": _inputs()}


@given("a pull request with no push, comment or label change for 1 day")
def _idle(state: dict) -> None:
    state["idle_days"] = 1


@given('it does not carry the label "keep-open"')
def _not_exempt(state: dict) -> None:
    assert "keep-open" in str(state["with"]["exempt-pr-labels"]).split(",")


@given("a pull request closed by the stale workflow")
def _closed_pr(state: dict) -> None:
    assert int(state["with"]["days-before-pr-close"]) >= 0


@given('a pull request labelled "stale"')
def _warned(state: dict) -> None:
    assert state["with"]["stale-pr-label"] == "stale"


@given("an issue with no activity for 60 days")
def _issue(state: dict) -> None:
    state["issue_idle_days"] = 60


@when("the stale workflow runs")
def _runs(state: dict) -> None:
    wf = _workflow()
    schedule = (wf.get("on") or wf.get(True))["schedule"]  # YAML 1.1 reads `on` as True
    assert schedule, "stale.yml has no schedule"
    # Hourly: a 24-hour window checked once a day would let a PR sit up to 48 hours.
    assert schedule[0]["cron"].split()[1] == "*", schedule


@when("its author reads the close message")
def _reads(state: dict) -> None:
    state["message"] = state["with"]["close-pr-message"]


@when('someone pushes, comments, or adds the label "keep-open"')
def _activity(state: dict) -> None:
    # actions/stale removes the label on any update unless told not to.
    assert state["with"].get("remove-stale-when-updated", True) is not False
    assert "keep-open" in str(state["with"]["exempt-pr-labels"]).split(",")


@then('the pull request is labelled "stale" and closed in the same run')
def _labelled_and_closed(state: dict) -> None:
    assert float(state["with"]["days-before-pr-stale"]) == state["idle_days"]
    assert int(state["with"]["days-before-pr-close"]) == 0
    assert state["with"]["stale-pr-label"] == "stale"


@then("the branch is kept")
def _branch_kept(state: dict) -> None:
    assert state["with"]["delete-branch"] is False


@then('it names "gh pr reopen" and "Blocked-by"')
def _ways_back(state: dict) -> None:
    assert "gh pr reopen" in state["message"]
    assert "Blocked-by:" in state["message"]


@then('the "stale" label is removed and the pull request stays open')
def _stays(state: dict) -> None:
    assert state["with"].get("remove-stale-when-updated", True) is not False


@then("the issue is unchanged")
def _issue_untouched(state: dict) -> None:
    assert int(state["with"]["days-before-issue-stale"]) == -1
    assert int(state["with"]["days-before-issue-close"]) == -1
