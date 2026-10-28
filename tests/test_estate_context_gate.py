"""tests/test_estate_context_gate.py -- the context plane's admission gate, pinned.

The estate has ONE context engine and ONE door to it. bin/estate-context-gate is what says so
out loud, and it says it by refusing: a second ranker in the compiler, a mutating tool on the
broker's read-only allowlist, an engine bound to anything but loopback, a policy that stops
refusing, a plan that reorders the engine's answer or over-runs its budget.

A gate that cannot fail is not a gate (AGENTS.md 3), so this file holds two things to account:
the gate passes on the real tree, and the gate FAILS on a tree that breaks each rule in turn.
The negative cases are not decoration -- they are the proof that the PASS means something.

Run: bin/pytest or `python3 -m pytest tests/test_estate_context_gate.py`
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GATE = os.path.join(ROOT, "bin", "estate-context-gate")


def _load():
    """Load bin/estate-context-gate as a module (it carries no .py suffix by convention)."""
    spec = importlib.util.spec_from_loader(
        "estate_context_gate",
        importlib.machinery.SourceFileLoader("estate_context_gate", GATE),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()


# --- the gate passes on the real tree ----------------------------------------------------------
def test_gate_passes_on_this_tree():
    """The real tree satisfies every rule the gate enforces."""
    results = gate.run_all(
        ROOT, catalogue=None, catalogue_reason="not read in this test"
    )
    failures = [(r["check"], f) for r in results for f in r["failures"]]
    assert not failures, failures


def test_gate_self_test_passes():
    """The gate proves its own teeth: every check fails on a broken input."""
    problems = gate._self_test()
    assert not problems, problems


def test_gate_runs_as_a_program_and_passes():
    """The gate is a program, not a function: it runs, prints a verdict, and exits 0."""
    proc = subprocess.run(  # noqa: S603 -- list form, no shell
        [sys.executable, GATE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "estate-context-gate: PASS" in proc.stdout


def test_gate_self_test_runs_as_a_program():
    proc = subprocess.run(  # noqa: S603 -- list form, no shell
        [sys.executable, GATE, "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS  self-test" in proc.stdout


# --- and it FAILS on a tree that breaks the rules -----------------------------------------------
def _fake_tree(tmp_path, **mutations):
    """A copy of the tree's context plane, with the given mutations applied."""
    root = tmp_path / "tree"
    (root / "bin").mkdir(parents=True)
    (root / "platform" / "estate" / "context").mkdir(parents=True)
    (root / "platform" / "mcp").mkdir(parents=True)
    shutil.copy(
        os.path.join(ROOT, "bin", "estate-context-compile"),
        root / "bin" / "estate-context-compile",
    )
    for name in os.listdir(os.path.join(ROOT, "platform", "estate", "context")):
        if name.endswith(".py"):
            shutil.copy(
                os.path.join(ROOT, "platform", "estate", "context", name),
                root / "platform" / "estate" / "context" / name,
            )
    shutil.copy(
        os.path.join(ROOT, "platform", "mcp", "estate-context-broker.yaml"),
        root / "platform" / "mcp" / "estate-context-broker.yaml",
    )
    for rel, text in mutations.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_gate_fails_a_second_ranker(tmp_path):
    """A ranker in the compiler is the stitching AGENTS.md 6 forbids. The gate refuses it."""
    compiler = open(  # noqa: SIM115 -- read, then closed
        os.path.join(ROOT, "bin", "estate-context-compile"), encoding="utf-8"
    ).read()
    broken = compiler + "\n\n# a second ranker, creeping back in\nTFIDF = {}\n"
    root = _fake_tree(tmp_path, **{"bin/estate-context-compile": broken})
    failures = [
        f for r in gate.run_all(str(root), catalogue=None) for f in r["failures"]
    ]
    assert any("second ranker" in f for f in failures), failures


def test_gate_fails_a_mutating_tool_on_the_read_only_allowlist():
    """The allowlist and the engine's catalogue must agree, in the direction that matters."""
    failures, _ = gate.check_read_only(
        {"edit_file"}, set(), {"edit_file": {"name": "edit_file", "mutating": True}}
    )
    assert failures, "a mutating tool on the read-only allowlist was not refused"


def test_gate_fails_an_engine_that_is_not_private():
    """An engine on 0.0.0.0, or with a Service, is a route to the context plane."""
    open_engine = [
        {
            "kind": "Deployment",
            "metadata": {"name": "estate-context-broker"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "engine",
                                "command": ["sh", "-c"],
                                "args": [
                                    "gortex daemon start --http-addr 0.0.0.0:7411"
                                ],
                            }
                        ]
                    }
                }
            },
        }
    ]
    assert gate.check_engine_private(open_engine)

    engine_service = [
        {
            "kind": "Service",
            "metadata": {"name": "gortex-engine"},
            "spec": {"type": "ClusterIP", "selector": {"app": "engine"}},
        }
    ]
    assert gate.check_engine_private(engine_service)


def test_gate_fails_a_policy_that_stops_refusing():
    """A policy that allows everything is not a policy."""
    assert gate.check_policy_strictness(gate._LaxBroker())


def test_gate_fails_a_plan_that_reorders_the_engine():
    """The plan keeps the engine's order. A plan that reorders it is a second ranker."""
    original = gate.PLAN.assemble

    def _reordering(inp):
        plan = original(inp)
        plan["items"] = list(reversed(plan.get("items") or []))
        return plan

    assert gate.check_plan_contract(_reordering, ROOT)


def test_gate_fails_a_plan_that_overruns_its_budget():
    """A plan that uses more tokens than its budget is refused."""
    original = gate.PLAN.assemble

    def _over_budget(inp):
        plan = original(inp)
        plan["used_tokens"] = plan.get("budget_tokens", 0) + 1
        return plan

    assert gate.check_plan_contract(_over_budget, ROOT)


def test_gate_fails_a_plan_over_the_ceiling():
    """The per-request ceiling is a refusal, not a clamp."""
    import dataclasses

    inp = gate.PLAN.PlanInput(
        task="over the ceiling",
        surface="pi",
        tier="free",
        budget_tokens=250000,
        repo_root=ROOT,
        commit="c" * 40,
        index_commit="c" * 40,
        engine_payload={"working_set": []},
        chars_per_token=4,
        ceiling=200000,
        door="local",
    )
    with pytest.raises(gate.PLAN.PlanError):
        gate.PLAN.assemble(inp)
    assert dataclasses is not None


# --- the read-only surface, against the engine's OWN catalogue when it is there ----------------
def test_gate_fails_a_tool_the_engine_does_not_have():
    """A name the estate invented is a client that gets 'unknown tool' and a broken door.

    Measured 2026-10-27: `affected` was on the broker's read-only allowlist, and the engine
    answered 'unknown tool "affected"'. The gate asks the engine about every name now.
    """
    failures = gate.check_tool_existence(
        {"affected": 'Error: unknown tool "affected" — did you mean: analyze, review?'}
    )
    assert failures, "a tool the engine does not have was not refused"


def test_gate_passes_a_tool_the_engine_has():
    """The engine refusing a tool on its own arguments is the tool existing."""
    assert gate.check_tool_existence({"smart_context": "Error: task is required"}) == []


def test_the_engine_being_absent_is_not_a_failure():
    """No daemon is a skipped check, never a green one."""
    assert gate.classify_probe("no gortex daemon is running") == "unreachable"
    assert gate.classify_probe("the gortex daemon does not track /tmp/x") == "untracked"
    assert gate.classify_probe('Error: unknown tool "affected"') == "unknown"


def test_every_allowlisted_tool_is_a_tool_the_engine_has():
    """Live check: the engine is asked about every name on the allowlist.

    Skipped, not passed, when the engine is not there.
    """
    answers, unreachable = gate.probe_read_only_existence(
        set(gate.BROKER.READ_ONLY_TOOLS), ROOT
    )
    if unreachable:
        pytest.skip("the engine is not reachable: {}".format(unreachable))
    failures = gate.check_tool_existence(answers)
    assert not failures, failures


def test_read_only_allowlist_has_no_mutating_tool_in_the_live_catalogue():
    """Live check: the engine's catalogue, when the daemon is there, must agree.

    The catalogue is read from the engine itself. When the daemon is not running, the check
    is skipped -- and SKIPPED, not passed: a test that quietly passes because the thing it
    measures is missing is a false green.
    """
    catalogue, reason = gate.engine_catalogue(ROOT, timeout=30.0)
    if catalogue is None:
        pytest.skip("the engine's catalogue is not reachable: {}".format(reason))
    failures, _ = gate.check_read_only(
        set(gate.BROKER.READ_ONLY_TOOLS), set(gate.BROKER.MUTATING_TOOLS), catalogue
    )
    assert not failures, failures


# --- the recorded surface: the allowlist, the engine and the image must agree ------------------
def test_the_allowlist_is_inside_the_recorded_engine_surface():
    """Every name the broker allows is a name the measured engine surface has.

    Measured 2026-10-27 against gortex v0.64.11+c7abb9b on POST /v1/tools/{name}: the engine
    names the tools it serves when asked for one it does not have, and all 81 of those names
    are served. The allowlist is a subset of them.
    """
    failures = gate.check_recorded_surface(
        set(gate.BROKER.READ_ONLY_TOOLS),
        gate.BROKER.ENGINE_SURFACE,
        open(  # noqa: SIM115 -- read, then closed
            os.path.join(ROOT, "gortex-engine.Dockerfile"), encoding="utf-8"
        ).read(),
    )
    assert not failures, failures


def test_the_gate_fails_a_name_outside_the_recorded_surface():
    """A name the measured surface does not have is a promise the door cannot keep."""
    failures = gate.check_recorded_surface(
        {"affected"},
        {"engine_version": "v0.64.11", "tools": frozenset({"smart_context"})},
        "ARG GORTEX_VERSION=v0.64.11\n",
    )
    assert failures, "a name outside the measured surface was not refused"


def test_the_gate_fails_an_image_pinned_to_another_engine():
    """The allowlist was measured on one engine build; the image must be that build."""
    failures = gate.check_recorded_surface(
        {"smart_context"},
        {"engine_version": "v0.64.11", "tools": frozenset({"smart_context"})},
        "ARG GORTEX_VERSION=v0.60.0\n",
    )
    assert failures, "an image pinned to another engine was not refused"


def test_the_gate_fails_a_broker_that_records_no_surface():
    """No record means no claim, and a claim that cannot be checked is not one."""
    failures = gate.check_recorded_surface(
        {"smart_context"}, {}, "ARG GORTEX_VERSION=v0.64.11\n"
    )
    assert failures, "a broker with no recorded surface was not refused"


def test_the_engine_image_pins_the_version_the_surface_was_measured_on():
    """The Dockerfile and the record are the same fact, written twice."""
    pinned = gate.dockerfile_gortex_version(
        open(  # noqa: SIM115 -- read, then closed
            os.path.join(ROOT, "gortex-engine.Dockerfile"), encoding="utf-8"
        ).read()
    )
    assert pinned == gate.BROKER.ENGINE_SURFACE["engine_version"], (
        pinned,
        gate.BROKER.ENGINE_SURFACE["engine_version"],
    )
