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


# --- the founder's disable switch (2026-11-09) -----------------------------------------------
#
# DoF was switched off on the founder's order: it was holding 28 lanes and main could not go green,
# because estate-doors cannot repair the gate that freezes it. These tests are the falsifier for
# that switch in BOTH directions, because a disable that cannot be undone is not a switch, it is a
# deletion -- and a disable nobody can see is worse than no guard at all.

import os as _os  # noqa: E402
import subprocess as _subprocess  # noqa: E402
import sys as _sys  # noqa: E402


def _reload_with(value):
    """Load bin/dof-gate afresh with ESTATE_DOF_DISABLED set to `value` (None = unset).

    The gate is executed by SourceFileLoader and never registered in sys.modules, so importlib.reload
    cannot be used on it (it fails "module dof_gate not in sys.modules"). Re-exec the same way the
    module-level loader did, which is also closer to what CI does: a fresh process reading the env.
    """
    prev = _os.environ.get("ESTATE_DOF_DISABLED")
    try:
        if value is None:
            _os.environ.pop("ESTATE_DOF_DISABLED", None)
        else:
            _os.environ["ESTATE_DOF_DISABLED"] = value
        loader = importlib.machinery.SourceFileLoader(
            "dof_gate_reload", str(ROOT / "bin" / "dof-gate")
        )
        spec = importlib.util.spec_from_loader("dof_gate_reload", loader)
        fresh = importlib.util.module_from_spec(spec)
        loader.exec_module(fresh)
        return fresh
    finally:
        if prev is None:
            _os.environ.pop("ESTATE_DOF_DISABLED", None)
        else:
            _os.environ["ESTATE_DOF_DISABLED"] = prev


def test_dof_is_disabled_by_default_so_the_estate_can_do_its_work():
    """The switch must default ON (disabled): the order is 'disable dof', not 'disable it when asked'."""
    g = _reload_with(None)
    assert g.DISABLED is True, "DoF must default to disabled per the founder's order"
    _reload_with(None)


def test_an_admitted_decision_is_what_the_gate_returns_when_disabled(tmp_path):
    """Run the real entry point: a commit that DoF refuses today must exit 0 with DoF off."""
    repo = tmp_path / "r"
    repo.mkdir()
    run = lambda *a, **k: _subprocess.run(
        a, cwd=repo, capture_output=True, text=True, **k
    )
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t.t")
    run("git", "config", "user.name", "t")
    (repo / "README.md").write_text("base\n")
    run("git", "add", ".")
    run("git", "commit", "-qm", "base")
    base = run("git", "rev-parse", "HEAD").stdout.strip()
    (repo / "web").mkdir()
    (repo / "web" / "app.tsx").write_text("x\n")
    run("git", "add", ".")
    # An unrelated change with no Genesis-Resolves trailer: refused while DoF is armed.
    run("git", "commit", "-qm", "feat: unrelated work")
    head = run("git", "rev-parse", "HEAD").stdout.strip()

    env = {**_os.environ, "ESTATE_DOF_DISABLED": "1"}
    off = _subprocess.run(
        [_sys.executable, str(ROOT / "bin" / "dof-gate"), base, head],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert off.returncode == 0, off.stderr
    assert "DISABLED" in off.stderr, (
        "a switched-off guard must say so, never pass silently"
    )

    env = {**_os.environ, "ESTATE_DOF_DISABLED": "0"}
    on = _subprocess.run(
        [_sys.executable, str(ROOT / "bin" / "dof-gate"), base, head],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert on.returncode == 1, "with DoF armed the same commit must be refused again"
    assert "DISABLED" not in on.stderr


def test_the_lease_is_full_while_disabled_so_no_agent_is_narrowed():
    g = _reload_with("1")
    rc = g.main(["--lease"])
    assert rc == 0, (
        "a disabled DoF must grant a full lease (exit 0), never repair-only (exit 3)"
    )
    _reload_with(None)
