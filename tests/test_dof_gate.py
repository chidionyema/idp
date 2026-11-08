"""bin/dof-gate: while a critical service is down, only its repair may land. Each test can fail."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("dof_gate", str(ROOT / "bin" / "dof-gate"))
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
    assert gate.evaluate(REGISTRY, ROUTER_DOWN, "fix\n\nGenesis-Resolves: llm-router", ["clusters/oke/pool.yaml"])["admitted"]


def test_a_resolving_commit_that_strays_is_refused():
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "fix\n\nGenesis-Resolves: llm-router", ["clusters/a.yaml", "web/app.tsx"])
    assert not d["admitted"] and d["files"] == ["web/app.tsx"]


def test_claiming_a_service_that_is_not_down_is_refused():
    assert not gate.evaluate(REGISTRY, ROUTER_DOWN, "Genesis-Resolves: otto", ["clusters/a.yaml"])["admitted"]


def test_the_gate_cannot_unlock_itself():
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "Genesis-Resolves: llm-router", ["bin/dof-gate"])
    assert not d["admitted"]


def test_an_unreadable_incident_list_fails_closed_to_gate_repair_only():
    blind = [{"id": "dof-probe", "issue": None}]
    assert not gate.evaluate(REGISTRY, blind, "feat: x", ["README.md"])["admitted"]
    assert gate.evaluate(REGISTRY, blind, "Genesis-Resolves: dof-probe", ["bin/dof-gate"])["admitted"]


def test_glob_is_anchored():
    assert gate.glob_match("clusters/**", "clusters/a/b.yaml")
    assert not gate.glob_match("clusters/**", "clustersx/a.yaml")
    assert gate.glob_match("bin/idp-oke-*", "bin/idp-oke-rebuild")
    assert not gate.glob_match("bin/idp-oke-*", "bin/x/idp-oke-rebuild")
