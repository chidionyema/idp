"""A check that ran twice must be graded once, on its later run (idp#1046).

`statusCheckRollup` returns one entry per RUN, not one per check name. When a newer push cancels
an older run, or a red run is re-run after a fix, the superseded entry stays in the list beside
the run that replaced it. Measured on the deploy itself, #1011: `open` carried a FAILURE from the
broken robot and a SUCCESS from the re-run that fixed it, and the unfiltered read called the pull
request failing while GitHub called it mergeable -- so the merge lane waited forever on a verdict
that had already been reached, and no image reached the cluster.

The three cases below are the whole contract: the stale red loses to the later green, a genuine
red still refuses, and a re-run that has not finished lands as "still running" rather than as the
stale pass it supersedes.
"""

import importlib.util
import os
from importlib.machinery import SourceFileLoader

# The tool has no `.py` suffix, so `spec_from_file_location` alone returns a spec with no loader
# and `module_from_spec` dies on None. Naming the loader is what imports an executable by path.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_path = os.path.join(ROOT, "bin", "idp-pr-landable")
_spec = importlib.util.spec_from_loader("idp_pr_landable", SourceFileLoader("idp_pr_landable", _path))
landable = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(landable)

REQUIRED = {"open"}


def _check(name, conclusion, completed, status="COMPLETED"):
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "startedAt": completed,
        "completedAt": completed,
    }


def _pr(checks):
    return {
        "isDraft": False,
        "mergeStateStatus": "BLOCKED",
        "labels": [],
        "statusCheckRollup": checks,
    }


def test_a_superseded_red_run_loses_to_the_later_green_run():
    pr = _pr(
        [
            _check("open", "FAILURE", "2026-08-31T04:00:00Z"),
            _check("open", "SUCCESS", "2026-08-31T05:00:00Z"),
        ]
    )
    assert landable.verdict(pr, REQUIRED) == ("MERGE", "green, clean, unblocked")


def test_a_genuine_red_is_still_refused_when_it_is_the_later_run():
    pr = _pr(
        [
            _check("open", "SUCCESS", "2026-08-31T04:00:00Z"),
            _check("open", "FAILURE", "2026-08-31T05:00:00Z"),
        ]
    )
    v, why = landable.verdict(pr, REQUIRED)
    assert v == "SKIP" and "open=FAILURE" in why


def test_a_rerun_that_has_not_finished_beats_the_pass_it_supersedes():
    pr = _pr(
        [
            _check("open", "SUCCESS", "2026-08-31T04:00:00Z"),
            _check("open", None, "", status="IN_PROGRESS"),
        ]
    )
    v, why = landable.verdict(pr, REQUIRED)
    assert v == "SKIP" and "still running" in why
