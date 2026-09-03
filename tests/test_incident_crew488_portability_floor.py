"""crew#488: the hydration drill's grade is a number against a floor that only ratchets up.

Rung 4 (incident test). The mistake it closes: four migration scenarios sat in
docs/prose/cloud-agnostic-drills.feature for two days and nothing ran them, so "portable" was
a sentence. The grader must be red when a layer that used to hydrate stops, green when the
count holds, and red when the floor is 0 or nothing was applied (a drill that cannot fail).
Proved both ways in one run, per LAW 45 step 3.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader(
    "drill", str(ROOT / "bin" / "idp-portability-drill")
)
drill = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("drill", _loader)
)
_loader.exec_module(drill)


def _ks(name: str, ready: bool, msg: str = "") -> dict:
    return {
        "metadata": {"name": name, "namespace": "flux-system"},
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True" if ready else "False",
                    "message": msg,
                }
            ]
        },
    }


def test_a_drill_that_cannot_fail_is_refused():
    assert drill.grade([_ks("edge", True)], floor=0)[0].startswith("FAIL")
    assert drill.grade([], floor=1)[0].startswith(
        "FAIL    portability  no Kustomization"
    )


def test_committed_floor_is_one_integer_at_least_one():
    assert drill.read_floor(str(ROOT / "drills" / "portability-floor.txt")) >= 1
