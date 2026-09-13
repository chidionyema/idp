"""bin/idp-pr-landable: which pull requests may land, and which need refreshing first.

The defect these tests pin down (measured 2026-09-12): eight pull requests were failing their
builds because they were behind main and lacked a fix that had already merged. merge-when-green
refreshes a branch when the verdict is UPDATE, and UPDATE was issued only when GitHub reported
`mergeStateStatus == "BEHIND"`.

A pull request that is behind main AND has a failing check does not report BEHIND -- it reports
UNSTABLE or BLOCKED. Measured on the eight: #3253 UNSTABLE, #3254 UNSTABLE, #3243 BLOCKED, every
one of them 2 to 21 commits behind. So the refresh never fired for exactly the population that
needed it, and a red pull request could never pick up the fix that would make it green. That is
a deadlock: the only way out is a refresh, and the refresh waits for green.

The tests below are behaviour on `verdict()`, with no repository and no network (its docstring
says the file exists so it can be graded that way).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def landable():
    """The module under test, loaded by path because bin/ has no .py suffix."""
    tool = ROOT / "bin" / "idp-pr-landable"
    loader = importlib.machinery.SourceFileLoader("landable", str(tool))
    spec = importlib.util.spec_from_file_location("landable", str(tool), loader=loader)
    assert spec and spec.loader, f"could not load {tool}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REQUIRED = {"ci", "bdd"}


def pr(state: str, checks: list[tuple[str, str]], behind_by: int = 0, **extra) -> dict:
    """A pull request as GitHub returns it, plus `behind_by`.

    `behind_by` is not in gh's `pr list` output; the workflow fetches it from the compare API
    (main...<branch>), which answers 9 for a branch nine commits behind and 0 for a current one.

    A check whose conclusion is the sentinel `RUNNING` is reported as still in flight, which is
    the state that decides whether a refresh is safe to take. Every other conclusion is COMPLETED.
    """
    return {
        "number": 1,
        "headRefName": "feat/x",
        "isDraft": False,
        "labels": [],
        "mergeStateStatus": state,
        "behind_by": behind_by,
        "statusCheckRollup": [
            {
                "name": n,
                "status": "IN_PROGRESS" if c == "RUNNING" else "COMPLETED",
                "conclusion": None if c == "RUNNING" else c,
            }
            for n, c in checks
        ],
        **extra,
    }


GREEN = [("ci", "SUCCESS"), ("bdd", "SUCCESS")]


class TestABehindPullRequestIsRefreshed:
    def test_behind_is_updated(self, landable):
        """The original behaviour, kept: a clean branch behind main gets refreshed."""
        assert landable.verdict(pr("BEHIND", GREEN), REQUIRED)[0] == "UPDATE"

    def test_behind_with_a_failing_check_is_still_updated(self, landable):
        """The defect. GitHub does not report BEHIND here -- it reports UNSTABLE, 9 behind.

        Measured 2026-09-12 on #3253 and #3254: both UNSTABLE, both behind main, both failing
        their build because they lacked the merged fix. Without this the refresh cannot fire,
        so the pull request can never become green.
        """
        v = landable.verdict(
            pr("UNSTABLE", [("ci", "FAILURE"), ("bdd", "SUCCESS")], behind_by=9),
            REQUIRED,
        )
        assert v[0] == "UPDATE", (
            "a branch behind main with a failing check was not refreshed, so it can never pick "
            "up the fix on main and never becomes green"
        )

    def test_blocked_and_behind_is_updated(self, landable):
        """#3243 reported BLOCKED while 14 commits behind. Blocked by what matters: refresh it."""
        v = landable.verdict(
            pr("BLOCKED", [("ci", "FAILURE"), ("bdd", "SUCCESS")], behind_by=14),
            REQUIRED,
        )
        assert v[0] == "UPDATE"

    def test_it_reports_it_is_refreshing_not_failing(self, landable):
        """The reason must read as a refresh, so a reader does not chase a red check."""
        v = landable.verdict(
            pr("UNSTABLE", [("ci", "FAILURE"), ("bdd", "SUCCESS")], behind_by=9),
            REQUIRED,
        )
        assert "behind" in v[1].lower() or "refresh" in v[1].lower()


class TestItStillRefusesUnsafeWork:
    def test_a_held_label_is_never_refreshed(self, landable):
        """A hold outranks a refresh: the one-word stop must not be overridden by automation."""
        assert (
            landable.verdict(pr("BEHIND", GREEN, labels=[{"name": "hold"}]), REQUIRED)[
                0
            ]
            == "SKIP"
        )

    def test_a_draft_is_not_refreshed_into_a_merge(self, landable):
        p = pr("UNSTABLE", [("ci", "FAILURE"), ("bdd", "SUCCESS")])
        p["isDraft"] = True
        assert landable.verdict(p, REQUIRED)[0] == "SKIP"

    def test_a_real_conflict_is_never_auto_refreshed(self, landable):
        """DIRTY means a person has to choose; an automatic update would pick silently."""
        v = landable.verdict(
            pr("DIRTY", [("ci", "FAILURE"), ("bdd", "SUCCESS")], behind_by=3), REQUIRED
        )
        assert v[0] == "SKIP"
        assert "conflict" in v[1].lower()

    def test_a_current_branch_is_not_told_it_is_behind(self, landable):
        """behind_by 0 means up to date; a red check there is a real failure, not staleness."""
        v = landable.verdict(
            pr("UNSTABLE", [("ci", "FAILURE"), ("bdd", "SUCCESS")], behind_by=0),
            REQUIRED,
        )
        assert v[0] == "SKIP"

    def test_a_behind_branch_with_checks_running_is_never_refreshed(self, landable):
        """The defect that held nine pull requests out of main, measured 2026-09-13.

        `update-branch` pushes a merge commit, which starts a new CI run and CANCELS the one in
        flight. A branch that was behind and mid-CI was therefore refreshed, had its own
        `bdd-suites` killed, came back behind on the next tick, and was refreshed again. Nine pull
        requests sat BLOCKED, each with every job green except the two that never got to finish:

            run 34744625012   bdd-suites (tests) success   bdd-suites (acceptance) success
            run 34745350461   cancelled                  cancelled
            run 34745730840   cancelled                  success

        So the population that must never be refreshed is exactly the one the old code refreshed
        first, because `behind` was judged before the checks were ever read. The refresh is only
        ever useful for a branch whose checks FINISHED with something red.
        """
        v = landable.verdict(
            pr(
                "BLOCKED",
                [("bdd-suites (tests)", "RUNNING"), ("bdd", "SUCCESS")],
                behind_by=3,
            ),
            REQUIRED,
        )
        assert v[0] == "SKIP", (
            "a branch behind main whose checks are still running was refreshed, which cancels the "
            "run that would have proved it and puts it back in the same queue behind main"
        )
        assert "cancel" in v[1] or "running" in v[1], v[1]

    def test_a_behind_branch_whose_checks_finished_red_is_still_refreshed(
        self, landable
    ):
        """The case the refresh exists for, and it must survive the fix above.

        Measured 2026-09-12 on #3253 and #3254: both UNSTABLE, both behind main, both red only
        because they lacked a fix that had already merged. Nothing is running, so the refresh
        cannot destroy evidence, and it is the only way the branch becomes green.
        """
        v = landable.verdict(
            pr("UNSTABLE", [("ci", "FAILURE"), ("bdd", "SUCCESS")], behind_by=9),
            REQUIRED,
        )
        assert v[0] == "UPDATE", (
            "finished-red is the population the refresh exists for; refusing it there would once "
            "again make the fix on main unreachable"
        )

    def test_a_behind_branch_with_every_check_finished_green_is_refreshed(
        self, landable
    ):
        """Behind, all green, nothing running: refreshing loses no evidence and lets it merge."""
        assert (
            landable.verdict(pr("CLEAN", GREEN, behind_by=4), REQUIRED)[0] == "UPDATE"
        )

    def test_a_green_clean_pull_request_still_merges(self, landable):
        assert landable.verdict(pr("CLEAN", GREEN), REQUIRED)[0] == "MERGE"

    def test_no_checks_is_unproven_not_green(self, landable):
        assert landable.verdict(pr("CLEAN", []), REQUIRED)[0] == "SKIP"
