"""A switched-off feature is not a broken one, and the portability drill used to say it was.

Found while adding the commerce layer dark (founder 2026-08-29: "build it dark, on branch and
lets review"). Flux writes no Ready condition on a Kustomization with `suspend: true`, so the
grader's message defaulted to "no Ready condition yet", matched none of the pending, cascade or
named-red branches, and fell through to ROOT-RED. Measured against origin/main's grade() with
ten ready rows and one suspended row:

    ROOT-RED   flux-system/commerce: no Ready condition yet
    FAIL    portability  root-red not on drills/portability-oci-reds.txt: commerce (ready 10/11)

So adding ANY feature the estate had deliberately not switched on would have failed the weekly
portability drill, and the person who added it would have been told their layer was broken.

The class of mistake (LAW 6): an else-branch that treats "I have no information about this" as
"this is broken". The same shape as the one-sided bound in silent-green. Off, pending, cascaded
and broken are four states, and a grader that knows three of them invents the fourth.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _drill():
    """The grader is a bin/ script with no .py suffix; load it the way the estate's other
    tests load one (tests/test_estate_diagram.py), not with exec."""
    path = ROOT / "bin" / "idp-portability-drill"
    loader = importlib.machinery.SourceFileLoader("idp_portability_drill", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _row(name, *, suspend=False, ready=True, message=""):
    doc = {"metadata": {"name": name, "namespace": "flux-system"}, "spec": {}}
    if suspend:
        doc["spec"]["suspend"] = True
    else:
        doc["status"] = {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True" if ready else "False",
                    "message": message,
                }
            ]
        }
    return doc


def test_a_suspended_row_is_never_a_root_red():
    items = [_row(f"ok{i}") for i in range(10)] + [_row("commerce", suspend=True)]
    verdict, lines = _drill().grade(items, 10, [])
    assert "ROOT-RED" not in verdict and not any("ROOT-RED" in l for l in lines), (
        f"a switched-off feature was graded as a broken one: {verdict}"
    )
    assert verdict.startswith("ok"), verdict


def test_a_suspended_row_leaves_the_denominator():
    """A floor is a promise about layers that are meant to run. Counting a row nobody asked to
    run makes the ratio worse every time a feature is added dark, which would push a truthful
    drill under its floor for a change that altered nothing on the cluster."""
    drill = _drill()
    ten_ready = [_row(f"ok{i}") for i in range(10)]
    plain, _ = drill.grade(ten_ready, 10, [])
    dark, _ = drill.grade(ten_ready + [_row("commerce", suspend=True)], 10, [])
    assert "ready 10/10" in plain
    assert "ready 10/10" in dark, (
        f"adding a suspended row changed the graded population: {dark}"
    )


def test_the_verdict_says_how_many_rows_were_skipped():
    """LAW 28 and the no-silent-caps rule: a grader that quietly drops rows from its own
    denominator is indistinguishable from one that covered everything."""
    items = [_row(f"ok{i}") for i in range(10)] + [
        _row("commerce", suspend=True),
        _row("event-bus", suspend=True),
    ]
    verdict, lines = _drill().grade(items, 10, [])
    assert "2 suspended" in verdict, verdict
    assert sum("suspended" in l for l in lines) == 2


def test_a_row_that_is_genuinely_broken_still_fails():
    """The fence must not become the hole. Only `suspend: true` is skipped; a row with no Ready
    condition and no suspend flag is still a root red."""
    items = [_row(f"ok{i}") for i in range(10)] + [
        {"metadata": {"name": "mystery", "namespace": "flux-system"}, "spec": {}}
    ]
    verdict, lines = _drill().grade(items, 10, [])
    assert verdict.startswith("FAIL"), verdict
    assert any("ROOT-RED" in l and "mystery" in l for l in lines), lines


@pytest.mark.parametrize("value", [False, "true", None, 0])
def test_only_a_real_boolean_true_switches_a_row_off(value):
    """`suspend: "true"` is a string and Flux does not honour it. If the grader honoured it the
    two would disagree, and the drill would report a layer as off while Flux ran it."""
    row = {
        "metadata": {"name": "half", "namespace": "flux-system"},
        "spec": {"suspend": value},
    }
    verdict, lines = _drill().grade([_row(f"ok{i}") for i in range(10)] + [row], 10, [])
    assert "suspended" not in verdict, (
        f"{value!r} was treated as switched off: {verdict}"
    )
    assert any("ROOT-RED" in l for l in lines)
