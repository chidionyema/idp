"""The adaptive bound resolver: the door's decision half, proven before it is wired.

The resolver is pure. These tests are its falsifiers: they prove that the hard cap holds, that
a caller's numeric bound is honoured exactly, that an unmeasured shape gets a conservative leash
and is labelled UNKNOWN rather than dressed up as a measurement, and that a job killed at the
ceiling is never counted as evidence that a bigger ceiling would have worked.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BOUNDS_PATH = REPO_ROOT / "platform" / "executor" / "bounds.py"
EXECUTOR_PATH = REPO_ROOT / "mcp" / "plugins" / "estate_executor.py"


def _load():
    spec = importlib.util.spec_from_file_location("bounds_under_test", BOUNDS_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def bounds():
    return _load()


def _receipts(
    bounds, count, elapsed, exit_code=0, killed=False, shape="pytest", repo="idp"
):
    return [
        bounds.Receipt(
            shape=shape,
            elapsed_sec=elapsed,
            exit_code=exit_code,
            killed_at_ceiling=killed,
            repo=repo,
        )
        for _ in range(count)
    ]


# ----------------------------------------------------------------------------------
# The hard cap is the one number that cannot move.
# ----------------------------------------------------------------------------------


def test_the_mirrored_cap_matches_the_executor(bounds):
    """The resolver's cap and the executor's CEILING_SEC are the same number, or one is a lie."""
    text = EXECUTOR_PATH.read_text(encoding="utf-8")
    match = re.search(r"^CEILING_SEC\s*=\s*(\d+)", text, re.MULTILINE)
    assert match, "the executor no longer declares CEILING_SEC"
    assert int(match.group(1)) == bounds.HARD_CAP_SEC


def test_no_bound_can_exceed_the_hard_cap(bounds):
    """THE KNOWN-BAD FIXTURE: a caller cannot buy itself more time."""
    for text in ["100000", "need:100000", "deep", "range:1..99999", "auto", "quick"]:
        resolution = bounds.resolve(text, receipts=[], shape="pytest")
        assert (
            resolution.effective is None or resolution.effective <= bounds.HARD_CAP_SEC
        ), text


def test_a_need_beyond_the_cap_routes_instead_of_granting(bounds):
    """The refusal becomes a routing: the answer names the door that can hold the work."""
    resolution = bounds.resolve("need:600", receipts=[], shape="pytest")

    assert resolution.state == bounds.ROUTE
    assert resolution.seconds is None
    assert resolution.route in bounds.route_targets()
    assert "does not fit" in resolution.reason


def test_a_need_inside_the_cap_is_granted(bounds):
    resolution = bounds.resolve("need:45", receipts=[], shape="pytest")

    assert resolution.state == bounds.ALLOW
    assert resolution.effective == 45


# ----------------------------------------------------------------------------------
# A caller's numeric bound is honoured exactly, and never rewritten.
# ----------------------------------------------------------------------------------


def test_a_numeric_bound_is_honoured_exactly(bounds):
    resolution = bounds.resolve("30", receipts=[], shape="pytest")

    assert resolution.state == bounds.ALLOW
    assert resolution.effective == 30
    assert resolution.evidence == "caller"


def test_a_numeric_bound_above_the_cap_is_clamped_and_says_so(bounds):
    resolution = bounds.resolve("300", receipts=[], shape="pytest")

    assert resolution.effective == bounds.HARD_CAP_SEC
    assert "hard cap" in resolution.reason


# ----------------------------------------------------------------------------------
# Unmeasured is UNKNOWN, not a guess dressed as a measurement.
# ----------------------------------------------------------------------------------


def test_an_unmeasured_shape_is_unknown_and_conservative(bounds):
    resolution = bounds.resolve("auto", receipts=[], shape="never-seen")

    assert resolution.state == bounds.UNKNOWN
    assert resolution.evidence == "none"
    assert resolution.effective <= bounds.DEFAULT_UNMEASURED_SEC


def test_a_named_class_for_an_unmeasured_shape_is_unknown_and_conservative(bounds):
    resolution = bounds.resolve("deep", receipts=[], shape="never-seen")

    assert resolution.state == bounds.UNKNOWN
    assert resolution.effective <= bounds.NAMED_CLASSES["deep"]
    assert resolution.effective <= bounds.DEFAULT_UNMEASURED_SEC


def test_an_unparseable_bound_is_denied(bounds):
    resolution = bounds.resolve("as-long-as-it-takes", receipts=[], shape="pytest")

    assert resolution.state == bounds.DENY
    assert resolution.seconds is None


# ----------------------------------------------------------------------------------
# Learning is from observable outcomes only.
# ----------------------------------------------------------------------------------


def test_auto_grants_the_measured_p95(bounds):
    receipts = _receipts(bounds, 20, 8.0)
    resolution = bounds.resolve("auto", receipts=receipts, shape="pytest")

    assert resolution.state == bounds.ALLOW
    assert resolution.evidence == "measured"
    assert resolution.effective == 8


def test_a_named_class_never_exceeds_its_ceiling(bounds):
    """Measurement may lower a class, never raise it."""
    receipts = _receipts(bounds, 20, 95.0)
    resolution = bounds.resolve("quick", receipts=receipts, shape="pytest")

    assert resolution.state == bounds.ALLOW
    assert resolution.effective <= bounds.NAMED_CLASSES["quick"]


def test_a_job_killed_at_the_ceiling_is_not_evidence_that_a_bigger_ceiling_would_work(
    bounds,
):
    """THE SECOND KNOWN-BAD FIXTURE: a kill is a failure, never a measurement."""
    receipts = _receipts(bounds, 20, 100.0, exit_code=124, killed=True)
    resolution = bounds.resolve("auto", receipts=receipts, shape="pytest")

    assert resolution.state == bounds.UNKNOWN
    assert resolution.evidence == "none"
    assert resolution.effective <= bounds.DEFAULT_UNMEASURED_SEC


def test_failed_jobs_are_not_evidence_of_feasibility(bounds):
    receipts = _receipts(bounds, 20, 12.0, exit_code=1)
    resolution = bounds.resolve("auto", receipts=receipts, shape="pytest")

    assert resolution.state == bounds.UNKNOWN


def test_evidence_is_not_pooled_across_repositories(bounds):
    """A fast repository must not teach the slow one."""
    receipts = _receipts(bounds, 20, 2.0, repo="fast-repo")
    resolution = bounds.resolve(
        "auto", receipts=receipts, shape="pytest", repo="slow-repo"
    )

    assert resolution.state == bounds.UNKNOWN


def test_evidence_for_another_shape_is_not_used(bounds):
    receipts = _receipts(bounds, 20, 2.0, shape="docker-build")
    resolution = bounds.resolve("auto", receipts=receipts, shape="pytest")

    assert resolution.state == bounds.UNKNOWN


# ----------------------------------------------------------------------------------
# The grammar.
# ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,kind",
    [
        ("30", "exact"),
        ("auto", "auto"),
        ("quick", "named"),
        ("standard", "named"),
        ("deep", "named"),
        ("range:10..45", "range"),
        ("need:120", "need"),
        ("none", "none"),
        ("", "none"),
    ],
)
def test_the_grammar(bounds, text, kind):
    assert bounds.parse_bound(text).kind == kind


def test_an_inverted_range_is_invalid(bounds):
    assert bounds.parse_bound("range:90..10").kind == "invalid"


def test_the_range_grants_at_most_its_high_water_mark(bounds):
    receipts = _receipts(bounds, 20, 80.0)
    resolution = bounds.resolve("range:10..45", receipts=receipts, shape="pytest")

    assert resolution.effective <= 45


def test_no_bound_means_the_door_default(bounds):
    resolution = bounds.resolve("none", receipts=[], shape="pytest")

    assert resolution.state == bounds.ALLOW
    assert resolution.effective == bounds.HARD_CAP_SEC
    assert resolution.evidence == "caller"
