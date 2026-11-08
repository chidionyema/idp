"""tests/test_estate_substrate_gate.py -- the substrate-staleness admission gate, pinned.

The estate observed the same trap twice before this gate existed: a dated claim about the
substrate -- what hosts the estate, which kubeconfig context is live, whether a cluster is
"down" or "retired or "active"" -- survived in the session-start files (AGENTS.md) and was
quoted as *current* fact by the next agent. The 2026-10-28 "BLOCKED on the node half /
nodes-per-node-pool exceeded (idp#7318)" line is the canonical instance: a dated OKE-era
claim, re-asserted live after the estate left that substrate.

bin/estate-substrate-gate is what makes recurrence structurally impossible. The one rule:
a substrate/cluster-state assertion must carry either a fresh `<measured=<ISO>>` or the
literal marker `STALE` / `HISTORICAL`. A claim with neither is refused, and the gate names
the line so the fix is mechanical -- add a marker, never delete the dated fact a future
reader needs to know is not current.

A gate that cannot fail is not a gate (AGENTS.md 3), so this file holds two things to
account: the gate passes on the real tree, and the gate FAILS on a tree that breaks the
rule in each way the trap has travelled. The negative cases are not decoration -- they are
the proof that the PASS means something.

Run: bin/pytest or `python3 -m pytest tests/test_estate_substrate_gate.py`
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GATE = os.path.join(ROOT, "bin", "estate-substrate-gate")


def _load():
    """Load bin/estate-substrate-gate as a module (it carries no .py suffix by convention)."""
    spec = importlib.util.spec_from_loader(
        "estate_substrate_gate",
        importlib.machinery.SourceFileLoader("estate_substrate_gate", GATE),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()


# --- the gate passes on the real tree ----------------------------------------------------------
def test_gate_passes_on_this_tree():
    """The real tree's session-start files carry no unmarked substrate claim."""
    failures = [f for r in gate.run_all(ROOT) for f in r["failures"]]
    assert not failures, failures


def test_gate_self_test_passes():
    """The gate proves its own teeth: every check fails on a broken input."""
    problems = gate._self_test()
    assert not problems, problems


def test_gate_runs_as_a_program_and_passes():
    """The gate is a program, not a function: it runs, prints a verdict, and exits 0."""
    proc = subprocess.run(  # noqa: S603 -- list form, no shell
        [sys.executable, GATE, "--repo", ROOT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "estate-substrate-gate: PASS" in proc.stdout


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


# --- and it FAILS on a tree that breaks the rule -----------------------------------------------
def test_gate_refuses_a_bare_substrate_claim(tmp_path):
    """A bare "the estate runs on OKE" with no marker is the trap. It must be refused."""
    path = tmp_path / "AGENTS.md"
    path.write_text("the estate runs on OKE\n", encoding="utf-8")
    assert gate.check_file(str(path)), "a bare substrate claim was not refused"


def test_gate_accepts_a_stale_marked_claim(tmp_path):
    """A dated claim marked STALE is honest about being not-current. It must be accepted."""
    path = tmp_path / "AGENTS.md"
    path.write_text(
        "STALE: the estate runs on OKE (do not re-assert)\n", encoding="utf-8"
    )
    assert gate.check_file(str(path)) == [], gate.check_file(str(path))


def test_gate_accepts_a_measured_claim(tmp_path):
    """A claim carrying a fresh measured=<ISO> is a live measurement. It must be accepted."""
    path = tmp_path / "AGENTS.md"
    path.write_text(
        "the estate runs on OKE <measured=2026-11-08T21:00:00Z>\n", encoding="utf-8"
    )
    assert gate.check_file(str(path)) == [], gate.check_file(str(path))


def test_gate_refuses_a_cluster_state_claim(tmp_path):
    """A cluster/kubeconfig state assertion with no marker is the same trap. It must be refused."""
    path = tmp_path / "AGENTS.md"
    path.write_text("the cluster is not up\n", encoding="utf-8")
    assert gate.check_file(str(path)), "a bare cluster-state claim was not refused"


def test_gate_does_not_match_a_short_token_inside_another_word():
    """'oke' must not match 'invoke' / 'smoke' / 'revoke': a 3-letter token needs a boundary."""
    assert not gate._is_substrate_claim("estate_invoke -- intent")
    assert not gate._is_substrate_claim("the smoke test")
    assert gate._is_substrate_claim("the estate runs on OKE")
