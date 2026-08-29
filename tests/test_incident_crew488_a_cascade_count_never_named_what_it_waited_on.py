"""crew#488: `cascaded 26` was one opaque number, and the whole portability claim hid inside it.

Run 33232172215 (2026-08-29) read `ok portability ready 11/42 (root-red 2 all named, cascaded 25,
pending 4)`. Eleven of forty-two is the number the founder and a buyer's engineer read, and it
says the estate barely ports. The receipt could not answer the one question anybody asks next --
behind *what* -- so nobody could tell twenty-five rows each broken on their own (a platform that
does not port) from twenty-five rows queued behind a single door (a platform that ports the
moment that door opens). Graded against the same receipt, it is the second: 22 of the 25 wait on
`secret-store`, 2 on `observability`, 1 on `chaos-mesh`.

The grader now walks each cascade to the row at the end of its chain and prints the tally. It
changes no count and no prefix -- `cascaded` rows are still cascaded rows -- so the floor, the
root-red rule and every assertion in the two older files grade exactly as before.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("drill", str(ROOT / "bin" / "idp-portability-drill"))
drill = importlib.util.module_from_spec(importlib.util.spec_from_loader("drill", _loader))
_loader.exec_module(drill)

REDS = drill.read_reds(str(ROOT / "drills" / "portability-oci-reds.txt"))


def _ks(name: str, ready: bool, msg: str = "") -> dict:
    return {
        "metadata": {"name": name, "namespace": "flux-system"},
        "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "False", "message": msg}]},
    }


def _waits_on(dep: str) -> str:
    return f"dependency 'flux-system/{dep}' is not ready"


def test_the_incident_a_cascade_is_attributed_to_the_row_at_the_end_of_its_chain():
    """The shape of run 33232172215: rows two and three deep still name the vault door."""
    items = [
        _ks("external-secrets", True),
        _ks("secret-store", False, "post build failed: substitute from 'ConfigMap/estate-vars' error"),
        _ks("llm", False, _waits_on("secret-store")),           # one deep
        _ks("healing", False, _waits_on("llm")),                # two deep
        _ks("healing-analyzer", False, _waits_on("healing")),   # three deep
        # the other named red of the real run, so the verdict is the ok line that carries the tally
        _ks("estate-catalog", False, "Source artifact not found, retrying in 30s"),
    ]
    verdict, lines = drill.grade(items, floor=1, reds=REDS)
    assert "the cascade waits 3 on secret-store" in verdict, verdict
    for row in ("llm", "healing", "healing-analyzer"):
        assert any(f"flux-system/{row}:" in ln and ln.endswith("-> root secret-store") for ln in lines), row


def test_the_tally_is_ordered_by_size_so_the_biggest_door_is_read_first():
    items = [_ks("edge", True),
             _ks("secret-store", False, "substitute from 'ConfigMap/estate-vars' error"),
             _ks("estate-catalog", False, "Source artifact not found, retrying in 30s")]
    items += [_ks(f"a{i}", False, _waits_on("secret-store")) for i in range(4)]
    items += [_ks(f"b{i}", False, _waits_on("estate-catalog")) for i in range(9)]
    verdict, _ = drill.grade(items, floor=1, reds=REDS)
    assert verdict.endswith("; the cascade waits 9 on estate-catalog, 4 on secret-store"), verdict


def test_attribution_changes_no_count_and_no_prefix():
    """The floor, the root-red rule and the older assertions all read these; none may move."""
    items = [_ks("edge", True), _ks("secret-store", False, "substitute from 'ConfigMap/estate-vars'"),
             _ks("backstage", False, _waits_on("secret-store"))]
    verdict, lines = drill.grade(items, floor=1, reds=REDS)
    assert verdict.startswith("ok      portability  ready 1/3 (root-red 1 all named, cascaded 1, pending 0)"), verdict
    assert sum(ln.startswith("  cascaded   ") for ln in lines) == 1
    assert sum(ln.startswith("  oci-red    ") for ln in lines) == 1


def test_a_dependson_cycle_prints_a_name_instead_of_hanging():
    """Flux permits a dependsOn loop and reports both ends waiting on the other. The drill has to
    finish and say something; spinning would take the receipt with it."""
    items = [_ks("a", False, _waits_on("b")), _ks("b", False, _waits_on("a")), _ks("ok", True)]
    verdict, lines = drill.grade(items, floor=1, reds=REDS)
    assert "the cascade waits" in verdict, verdict
    assert len(lines) == 2 and all(ln.endswith(("-> root a", "-> root b")) for ln in lines), lines


def test_a_run_with_nothing_cascaded_says_nothing_about_a_cascade():
    items = [_ks("edge", True), _ks("secret-store", False, "substitute from 'ConfigMap/estate-vars'")]
    verdict, _ = drill.grade(items, floor=1, reds=REDS)
    assert verdict.endswith("(floor 1)"), verdict
