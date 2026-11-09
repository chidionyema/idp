"""bin/dof-gate: while a critical service is down, only its repair may land. Each test can fail."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader(
    "dof_gate", str(ROOT / "bin" / "dof-gate")
)
_spec = importlib.util.spec_from_loader("dof_gate", _loader)
gate = importlib.util.module_from_spec(_spec)
_loader.exec_module(gate)

REGISTRY = json.loads((ROOT / "catalog" / "dof-registry.json").read_text())
ROUTER_DOWN = [{"id": "llm-router", "issue": 7332}]


def test_no_incident_admits_anything():
    assert gate.evaluate(REGISTRY, [], "feat: x", ["README.md"])["admitted"]


def test_unrelated_work_is_refused_while_a_service_is_down():
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "feat: unrelated", ["web/app.tsx"])
    assert d["refused"] and d["required_trailer"] == "Genesis-Resolves: llm-router"


def test_a_resolving_commit_inside_scope_is_admitted():
    assert gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "fix\n\nGenesis-Resolves: llm-router",
        ["clusters/oke/pool.yaml"],
    )["admitted"]


def test_a_resolving_commit_that_strays_is_refused():
    d = gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "fix\n\nGenesis-Resolves: llm-router",
        ["clusters/a.yaml", "web/app.tsx"],
    )
    assert not d["admitted"] and d["files"] == ["web/app.tsx"]


def test_claiming_a_service_that_is_not_down_is_refused():
    assert not gate.evaluate(
        REGISTRY, ROUTER_DOWN, "Genesis-Resolves: otto", ["clusters/a.yaml"]
    )["admitted"]


def test_the_gate_cannot_unlock_itself():
    d = gate.evaluate(
        REGISTRY, ROUTER_DOWN, "Genesis-Resolves: llm-router", ["bin/dof-gate"]
    )
    assert not d["admitted"]


def test_an_unreadable_incident_list_fails_closed_to_gate_repair_only():
    blind = [{"id": "dof-probe", "issue": None}]
    assert not gate.evaluate(REGISTRY, blind, "feat: x", ["README.md"])["admitted"]
    assert gate.evaluate(
        REGISTRY, blind, "Genesis-Resolves: dof-probe", ["bin/dof-gate"]
    )["admitted"]


def test_glob_is_anchored():
    assert gate.glob_match("clusters/**", "clusters/a/b.yaml")
    assert not gate.glob_match("clusters/**", "clustersx/a.yaml")
    assert gate.glob_match("bin/idp-oke-*", "bin/idp-oke-rebuild")
    assert not gate.glob_match("bin/idp-oke-*", "bin/x/idp-oke-rebuild")


# --- the estate-doors deadlock (docs/diagnoses/2026-11-09-dof-freeze-deadlock-estate-doors.md) ---
# `test_the_gate_cannot_unlock_itself` above proves a normal component may not reach the frozen
# files. `test_an_unreadable_incident_list_fails_closed_to_gate_repair_only` proves `dof-probe`
# may, because its registry entry sets `selfRepair`. Neither covers the case that actually
# happened: the component whose incident is OPEN (`estate-doors`) has a repairScope of
# `@substrate`, which excludes the frozen files, so it may repair the service but not the gate
# that freezes it. These tests pin both directions of the proposed fix, so it can be proven
# rather than asserted -- and they pin the boundary, so the fix cannot become a licence.
DOORS_DOWN = [{"id": "estate-doors", "issue": 7334}]
GATE_FILES = ["bin/dof-gate"]


def _registry_with_self_repair():
    """The proposed state: estate-doors may repair the gate that is freezing it."""
    reg = json.loads(json.dumps(REGISTRY))
    doors = reg["components"]["estate-doors"]
    doors["selfRepair"] = True
    for path in reg["immutableWhileRed"]:
        if path not in doors["repairScope"]:
            doors["repairScope"].append(path)
    return reg


def test_estate_doors_cannot_change_the_gate_without_self_repair():
    """The measured current state: the gate is immutable while its own incident is down."""
    assert "selfRepair" not in REGISTRY["components"]["estate-doors"], (
        "estate-doors now declares selfRepair: this test is the falsifier for that change, so "
        "replace it with the two below rather than deleting it"
    )
    d = gate.evaluate(
        REGISTRY, DOORS_DOWN, "fix\n\nGenesis-Resolves: estate-doors", GATE_FILES
    )
    assert d["refused"], "a frozen file must be refused while estate-doors is red"
    assert "immutable" in d["reason"], d["reason"]
    assert d["files"] == GATE_FILES


def test_estate_doors_can_change_the_gate_once_it_declares_self_repair():
    """The proposed fix: the component that is down may repair the gate that freezes it."""
    d = gate.evaluate(
        _registry_with_self_repair(),
        DOORS_DOWN,
        "fix\n\nGenesis-Resolves: estate-doors",
        GATE_FILES,
    )
    assert d["admitted"], d["reason"]


def test_self_repair_does_not_widen_the_scope():
    """The fix must not become a licence: a path outside repairScope is still refused."""
    d = gate.evaluate(
        _registry_with_self_repair(),
        DOORS_DOWN,
        "fix\n\nGenesis-Resolves: estate-doors",
        ["web/app.tsx"],
    )
    assert d["refused"], "selfRepair must not admit work outside repairScope"
    assert "repairScope" in d["reason"], d["reason"]
