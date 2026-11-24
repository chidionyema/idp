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
import json
import os
import shutil
import subprocess
import sys
import time

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


# --- the route prefilter and the fast loader must not open a hole --------------------------------
# Measured 2026-11-23: the gate took 47.8 s and was killed mid-run with NO output, because 47 s
# of it was PyYAML's pure-python loader parsing 779 manifests. The fix parses with libyaml and
# skips manifests that cannot hold a route. A skip that hid a route would be a gate that fails
# OPEN, so these two cases are the proof that it does not: one with the kind written plainly,
# one with it written as an escape.
def _platform_with(tmp_path, manifest: str) -> str:
    platform = tmp_path / "platform"
    platform.mkdir(parents=True, exist_ok=True)
    (platform / "engine-route.yaml").write_text(manifest, encoding="utf-8")
    return str(platform)


def test_gate_fails_a_manifest_that_routes_the_engine(tmp_path):
    """A Service that points at the engine is a route, and the gate must name it."""
    platform = _platform_with(
        tmp_path,
        "apiVersion: v1\n"
        "kind: Service\n"
        "metadata:\n"
        "  name: gortex-engine\n"
        "spec:\n"
        "  ports:\n"
        "    - port: 7411\n",
    )
    failures = gate.check_no_public_engine(platform)
    assert failures, "a Service that routes the engine was not refused"


def test_gate_fails_a_route_written_as_an_escape(tmp_path):
    """The kind is compared as a string, so an escape must not hide it."""
    platform = _platform_with(
        tmp_path,
        'apiVersion: v1\nkind: "\\x53ervice"\nmetadata:\n  name: gortex-engine\n',
    )
    failures = gate.check_no_public_engine(platform)
    assert failures, "a route whose kind is written as an escape was not refused"


def test_gate_survives_a_malformed_manifest(tmp_path):
    """A manifest that does not parse is a skipped file, not a crashed gate.

    Measured 2026-11-23: `load_all` is lazy, so the parse error surfaced in the iteration and
    the gate died with a raw ParserError. The iteration belongs inside the try.
    """
    platform = _platform_with(
        tmp_path,
        "kind: {Service\n  name: gortex-engine\n  ports: [unclosed\n",
    )
    failures = gate.check_no_public_engine(platform)
    assert failures == [], failures
    manifest = os.path.join(platform, "engine-route.yaml")
    with open(manifest, encoding="utf-8") as fh:
        assert gate._yaml_documents(fh.read()) == []


def test_the_gate_answers_inside_the_estate_ceiling():
    """AGENTS.md P0: no foreground command may run past 20 s. The gate used to take 47.8."""
    started = time.monotonic()
    proc = subprocess.run(  # noqa: S603 -- list form, no shell
        [sys.executable, GATE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.monotonic() - started
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert elapsed < 20, "the gate took {:.1f}s, over the estate's 20s ceiling".format(
        elapsed
    )
    assert gate.GATE_CEILING_SECONDS <= 20
    assert gate.GATE_BUDGET_SECONDS <= gate.GATE_CEILING_SECONDS


def test_the_gate_always_prints_a_verdict(tmp_path):
    """A gate that dies silently is the failure this whole change exists to remove."""
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = subprocess.run(  # noqa: S603 -- list form, no shell
        [sys.executable, GATE, "--repo", str(empty)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "estate-context-gate: FAIL" in proc.stdout, proc.stdout
    payload = subprocess.run(  # noqa: S603 -- list form, no shell
        [sys.executable, GATE, "--repo", str(empty), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert payload.returncode == 1, payload.stdout + payload.stderr
    body = json.loads(payload.stdout)
    assert body["verdict"] == "FAIL"
    assert body["checks"], "a verdict with no checks is not a verdict"


# --- the index, when there is an engine ---------------------------------------------------------
def test_the_gate_fails_an_index_it_cannot_prove():
    """An engine that answers but holds no index for this tree is a refusal."""
    failures, warnings = gate.check_index_freshness(
        None, ROOT, True, "the engine does not track this tree"
    )
    assert failures, "an unproven index was not refused"
    assert not warnings


def test_the_gate_warns_when_the_index_cannot_be_read():
    """An index that could not be READ is not a bad index. The gate says what it could not take."""
    failures, warnings = gate.check_index_freshness(
        None, ROOT, True, "the engine's index list could not be read: timed out"
    )
    assert not failures, "an unreadable index was treated as a bad index"
    assert warnings


def test_the_gate_fails_a_stale_index():
    """The engine's index must be at the tree's commit."""
    stale = {
        "indexed": True,
        "indexed_commit": "a" * 40,
        "head_commit": "b" * 40,
        "stale": True,
    }
    failures, _ = gate.check_index_freshness(stale, ROOT, True)
    assert failures, "a stale index was not refused"


def test_the_gate_only_warns_when_there_is_no_engine():
    """CI has no engine daemon. "No engine" is not "a bad index", and must not turn CI red."""
    failures, warnings = gate.check_index_freshness(None, ROOT, False)
    assert not failures, "no engine was treated as a bad index"
    assert warnings


def test_the_gate_admits_an_index_at_the_trees_commit():
    fresh = {
        "indexed": True,
        "indexed_commit": "b" * 40,
        "head_commit": "b" * 40,
        "stale": False,
    }
    failures, warnings = gate.check_index_freshness(fresh, ROOT, True)
    assert not failures, failures
    assert not warnings
