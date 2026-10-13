"""bin/idp-pr-age must never arm a Greenlane lane.

A lane is the Greenlane's to land (AGENTS.md:75). idp-pr-age arms every green PR it sees through
bin/idp-pr-arm, which merges outright where GitHub refuses to arm; skipping only flux/image-updates
left every lane PR -- #6069 was one, hand-raised on lane/backstage-release-immutable on 2026-10-13
-- open to a second lander racing the Greenlane.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader(
    "idp_pr_age", str(ROOT / "bin" / "idp-pr-age")
)
_spec = importlib.util.spec_from_loader("idp_pr_age", _loader)
pr_age = importlib.util.module_from_spec(_spec)
_loader.exec_module(pr_age)


def _pr(head: str = "feat/x", body: str = "") -> dict:
    return {
        "repo": "idp",
        "number": 1,
        "title": "t",
        "body": body,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "headRefName": head,
        "statusCheckRollup": [
            {"name": "ci", "conclusion": "SUCCESS", "status": "COMPLETED"}
        ],
    }


def test_a_green_lane_is_graded_as_the_greenlanes():
    assert pr_age.reason(_pr(head="lane/x")) == "greenlane"


@pytest.mark.parametrize(
    "stamp", ["Greenlane-Lane: lane/feat/x", "Greenlane-Batch: candidate abc"]
)
def test_a_pr_the_greenlane_stamped_is_graded_as_the_greenlanes(stamp):
    """An adopted PR keeps its own branch name; the body stamp is what marks it a lane."""
    assert pr_age.reason(_pr(body=f"work\n\n{stamp}\n")) == "greenlane"


def test_a_greenlane_row_is_never_armed_or_commented(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError(f"touched a Greenlane lane: {a}")

    monkeypatch.setattr(pr_age, "arm", refuse)
    monkeypatch.setattr(pr_age, "gh", refuse)
    assert (
        pr_age.act("idp", 1, 500.0, "greenlane", 4.0, head="lane/x")
        == "greenlane-untouched"
    )


def test_ordinary_green_work_is_still_green():
    assert pr_age.reason(_pr()) == "green"
