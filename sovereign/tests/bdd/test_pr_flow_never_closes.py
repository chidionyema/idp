"""Binds features/pr_flow_never_closes.feature (founder 2026-09-29). The steps load bin/idp-pr-age
for real, grade its reason() on PR rows shaped like `gh pr list --json`, run act() with gh stubbed to
record every call, and read every workflow file for a closer."""

import importlib.machinery
import importlib.util
import re
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/pr_flow_never_closes.feature")

IDP = Path(__file__).resolve().parents[3]
_loader = importlib.machinery.SourceFileLoader(
    "idp_pr_age", str(IDP / "bin/idp-pr-age")
)
_spec = importlib.util.spec_from_loader("idp_pr_age", _loader)
pr_age = importlib.util.module_from_spec(_spec)
_loader.exec_module(pr_age)

CLOSERS = re.compile(
    r"gh pr close|actions/stale@|\"state\"\s*:\s*\"closed\"|state=closed\"|-f state=closed"
)


def _pr(state: str, failed: str) -> dict:
    return {
        "repo": "idp",
        "number": 1,
        "title": "t",
        "body": "",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": state,
        "headRefName": "feat/x",
        "statusCheckRollup": [
            {"name": "fast-gate", "conclusion": "SUCCESS", "status": "COMPLETED"},
            {"name": failed, "conclusion": "FAILURE", "status": "COMPLETED"},
        ],
    }


@pytest.fixture
def state() -> dict:
    return {}


@given("an open PR whose required checks pass and whose shadow-verify check failed")
def _advisory(state: dict) -> None:
    state["pr"] = _pr("UNSTABLE", "shadow-verify")


@given("an open PR that GitHub blocks and whose bdd check failed")
def _blocked(state: dict) -> None:
    state["pr"] = _pr("BLOCKED", "bdd")


@given("an open PR that GitHub blocks, 100 hours old")
def _old_red(state: dict) -> None:
    state["pr"] = _pr("BLOCKED", "bdd")
    state["age_h"] = 100.0


@when("bin/idp-pr-age grades it")
def _grade(state: dict) -> None:
    state["reason"] = pr_age.reason(state["pr"])


@when("bin/idp-pr-age acts on it")
def _act(state: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    class Done:
        returncode, stdout, stderr = 0, "", ""

    def fake_gh(*args: str) -> Done:
        calls.append(args)
        return Done()

    monkeypatch.setattr(pr_age, "gh", fake_gh)
    why = pr_age.reason(state["pr"])
    state["action"] = pr_age.act("idp", 1, state["age_h"], why, 4.0, "feat/x")
    state["calls"] = calls


@then(parsers.parse('its reason is "{want}"'))
def _reason_is(state: dict, want: str) -> None:
    assert state["reason"] == want


@then("no close and no draft is sent to GitHub")
def _no_close(state: dict) -> None:
    for args in state["calls"]:
        assert args[:2] != ("pr", "close"), args
        assert not (args[:2] == ("pr", "ready") and "--undo" in args), args
    assert state["action"] in {"commented", "quiet"}, state["action"]


@when("bin/idp-pr-age arms it")
def _arm(state: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> object:
        calls.append(cmd)
        return pr_age.subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(pr_age.subprocess, "run", fake_run)
    pr_age.arm("chidionyema/idp", 1)
    state["arm_calls"] = calls


@then("bin/idp-pr-arm is asked for a squash merge")
def _squash(state: dict) -> None:
    [cmd] = state["arm_calls"]
    assert cmd[0].endswith("idp-pr-arm") and cmd[1:] == ["1", "--squash"], cmd


@given("every workflow under .github/workflows")
def _workflows(state: dict) -> None:
    state["files"] = sorted((IDP / ".github/workflows").glob("*.y*ml"))
    assert state["files"], "no workflows found"


@when("each is read")
def _read(state: dict) -> None:
    state["hits"] = [
        f"{f.name}:{i}"
        for f in state["files"]
        for i, line in enumerate(f.read_text().splitlines(), 1)
        if not line.lstrip().startswith("#") and CLOSERS.search(line)
    ]


@then(
    'none runs "gh pr close", closes a pull request through the API, or runs actions/stale'
)
def _none_close(state: dict) -> None:
    assert state["hits"] == [], state["hits"]
