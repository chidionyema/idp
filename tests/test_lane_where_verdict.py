"""The gate must not report a lane RED for a vendor's rate limit (R10/R11).

Measured defect, 2026-11-10, on lane/prepush-toml-classifier. The lane was code-green --
`ci.status` on d62a3a833 reported "1 passed, all green, merge_ready true" -- and
`bin/lane-where` still answered:

    RED   lane-where  lane/prepush-toml-classifier  d62a3a833ef9 is NOT in main; the lane
          says failure
          Vercel: https://vercel.com/.../upgradeToPro=build-rate-limit
            Deployment rate limited -- retry in 24 hours.

The change was one shell script and one pytest file. Vercel has no verdict to give on it,
and "retry in 24 hours" is a vendor quota, not a fact about the change. Reporting it as a
FAILURE is the defect AGENTS.md 9 R10 names (wait and poll instead of diagnosing) and R11
(a claim made without measuring): it tells the agent to redo work that is already correct.

The lane's verdict is the `greenlane` context. A failing status on any OTHER context is
kept and named as advisory -- nothing is hidden -- but it does not make the lane RED.

These tests import the shipped function, so a regression in bin/lane-where fails them.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOOR = REPO / "bin" / "lane-where"


def _load():
    spec = importlib.util.spec_from_loader(
        "lane_where_door",
        importlib.machinery.SourceFileLoader("lane_where_door", str(DOOR)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def door():
    return _load()


def test_door_has_the_verdict_separator(door):
    assert hasattr(door, "split_verdict"), "bin/lane-where lost split_verdict"


def test_vercel_rate_limit_is_advisory_not_a_refusal(door):
    """THE FALSIFIER: the measured case. Not RED, and not silently dropped either."""
    status = {
        "state": "failure",
        "statuses": [
            {
                "context": "greenlane",
                "state": "success",
                "target_url": "u",
                "description": "landed in b1234",
            },
            {
                "context": "Vercel",
                "state": "error",
                "target_url": "https://vercel.com/x?upgradeToPro=build-rate-limit",
                "description": "Deployment rate limited -- retry in 24 hours.",
            },
        ],
    }
    _, failing, advisory, _, _ = door.split_verdict(status)
    assert failing == [], "a vendor rate limit was counted as a lane failure"
    assert len(advisory) == 1, "the advisory was dropped instead of named"


def test_a_real_greenlane_failure_is_still_red(door):
    """The fix must not mute the gate it exists to protect."""
    status = {
        "state": "failure",
        "statuses": [
            {
                "context": "greenlane",
                "state": "failure",
                "target_url": "u",
                "description": "ci-success failed",
            }
        ],
    }
    _, failing, advisory, ctx, _ = door.split_verdict(status)
    assert len(failing) == 1, "a failing greenlane status stopped making the lane RED"
    assert advisory == []
    assert ctx == "greenlane"


def test_a_greenlane_error_is_still_red(door):
    status = {
        "state": "error",
        "statuses": [
            {
                "context": "greenlane",
                "state": "error",
                "target_url": "u",
                "description": "engine crashed",
            }
        ],
    }
    _, failing, _, _, _ = door.split_verdict(status)
    assert len(failing) == 1


def test_mixed_keeps_both(door):
    """A greenlane failure wins the verdict; the advisory is still reported."""
    status = {
        "state": "failure",
        "statuses": [
            {
                "context": "Vercel",
                "state": "error",
                "target_url": "u",
                "description": "rate limit",
            },
            {
                "context": "greenlane",
                "state": "failure",
                "target_url": "u",
                "description": "red",
            },
        ],
    }
    _, failing, advisory, ctx, _ = door.split_verdict(status)
    assert len(failing) == 1 and len(advisory) == 1
    assert ctx == "greenlane", (
        "the lane verdict must win over the advisory for the headline"
    )


def test_all_green_is_neither(door):
    status = {
        "state": "success",
        "statuses": [
            {
                "context": "greenlane",
                "state": "success",
                "target_url": "u",
                "description": "landed in b1",
            },
            {
                "context": "Vercel",
                "state": "success",
                "target_url": "u",
                "description": "ok",
            },
        ],
    }
    landed, failing, advisory, _, _ = door.split_verdict(status)
    assert failing == [] and advisory == []
    assert landed == "landed in b1", "the landing record must still be read"


def test_no_statuses_is_empty(door):
    _, failing, advisory, _, _ = door.split_verdict({"state": "pending"})
    assert failing == [] and advisory == []


def _verdict(landed, st_state, failing, advisory):
    """The door's verdict rule, as main() composes it (line for line)."""
    if landed:
        return "LANDED"
    if failing or (st_state == "failure" and not advisory):
        return "RED"
    return "PENDING"


def test_aggregate_failure_from_a_vendor_alone_is_pending(door):
    """THE SECOND FALSIFIER: GitHub's aggregate state is not the lane's verdict.

    GitHub sets the commit's aggregate state to "failure" when ANY context failed.
    Measured on lane/lane-where-vendor-verdict: aggregate "failure", the only failing
    context Vercel's rate limit, no greenlane failure at all. The lane is not red.
    """
    status = {
        "state": "failure",
        "statuses": [
            {
                "context": "Vercel",
                "state": "error",
                "target_url": "u",
                "description": "Deployment rate limited -- retry in 24 hours.",
            }
        ],
    }
    _, failing, advisory, _, _ = door.split_verdict(status)
    assert _verdict(False, status["state"], failing, advisory) == "PENDING"


def test_aggregate_failure_with_a_greenlane_failure_is_red(door):
    status = {
        "state": "failure",
        "statuses": [
            {
                "context": "greenlane",
                "state": "failure",
                "target_url": "u",
                "description": "ci-success failure -- offline-gate",
            }
        ],
    }
    _, failing, advisory, _, _ = door.split_verdict(status)
    assert _verdict(False, status["state"], failing, advisory) == "RED"


def test_aggregate_failure_with_nothing_explaining_it_is_still_red(door):
    """Fail closed: a failure this door cannot attribute is not waved through."""
    status = {"state": "failure", "statuses": []}
    _, failing, advisory, _, _ = door.split_verdict(status)
    assert _verdict(False, status["state"], failing, advisory) == "RED"


def test_landed_beats_everything(door):
    assert _verdict(True, "failure", [], []) == "LANDED"
