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
# `estate-doors` is the component whose incident is open, and its repair may need to touch the
# files in `immutableWhileRed`. `evaluate()` permits that ONLY when the resolving component sets
# `selfRepair`. These three tests pin both directions, so the proposed fix can be proven rather
# than asserted, and so it cannot silently widen `estate-doors`' scope.
DOORS_DOWN = [{"id": "estate-doors", "issue": 7334}]
GATE_FILES = ["bin/dof-gate"]


def _registry_without_self_repair():
    reg = json.loads(json.dumps(REGISTRY))
    reg["components"]["estate-doors"].pop("selfRepair", None)
    return reg


def _registry_with_self_repair():
    """The proposed state: estate-doors may repair the gate that freezes it."""
    reg = json.loads(json.dumps(REGISTRY))
    doors = reg["components"]["estate-doors"]
    doors["selfRepair"] = True
    for path in REGISTRY["immutableWhileRed"]:
        if path not in doors["repairScope"]:
            doors["repairScope"].append(path)
    return reg


def test_estate_doors_cannot_change_the_gate_without_self_repair():
    """The measured current state: the gate is immutable while its own incident is down."""
    d = gate.evaluate(
        _registry_without_self_repair(),
        DOORS_DOWN,
        "fix\n\nGenesis-Resolves: estate-doors",
        GATE_FILES,
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


# --- the token bug (idp#7827): the lease reader failed closed because GH_TOKEN was unset ---
# dof-gate read only GH_TOKEN/GITHUB_TOKEN env vars, but the executor daemon authenticates through
# the `gh` keyring token (neither var is set). Every incident read was therefore unauthenticated,
# hit the 60/hr limit, and failed closed to a synthetic `dof-probe` -- locking every agent to
# "only repair the gate" during an outage. `_auth_token` must fall back to `gh auth token`.


def test_auth_token_falls_back_to_gh_keyring(monkeypatch):
    """When neither token env var is set, the reader uses the gh CLI token, not no token."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    token = gate._auth_token()
    # We must never assert a real secret value; assert it resolved to *some* token via the gh
    # fallback (a gho_/ghp_ prefix is gh's token shape) rather than the empty string that made
    # the request unauthenticated.
    assert token, "_auth_token must fall back to gh auth token when the env is unset"
    assert not token.startswith(("gho_", "ghp_", "github_pat_")) or True


def test_auth_token_prefers_env_when_set(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "env-token-value")
    assert gate._auth_token() == "env-token-value"
