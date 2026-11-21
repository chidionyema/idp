"""Falsifiers for Proof 2 (boundary) — the rule that decides what one commit may touch.

The defect this locks closed (2026-11-21): `tests/` counted as a second subsystem, so a change
that carried its own falsifier was refused while the same change without one passed:

    --files bin/x tests/x   ->  PROOF_2_FAILED: Cross-subsystem mutation ['bin', 'tests']
    --files bin/x           ->  APPROVED_BY_3_PROOFS

That made an untested commit the only legal commit. A test is the evidence half of the change it
tests, not a mutation of another subsystem.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "bin" / "verify_three_proofs.py"
MAX_FILES = 5


@pytest.fixture(scope="module")
def gate():
    spec = importlib.util.spec_from_loader(
        "three_proofs", importlib.machinery.SourceFileLoader("three_proofs", str(GATE))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _exists(monkeypatch):
    """The boundary rule is about paths, not bytes; make every path look present."""
    monkeypatch.setattr(Path, "exists", lambda self: True)


def test_a_change_and_its_test_are_one_unit(gate) -> None:
    ok, report = gate.verify_proof_2_boundary_and_gate(
        "abc123", ["bin/x", "tests/estate/test_x.py"]
    )
    assert ok, report
    assert report["subsystem"] == "bin"
    assert report["file_count"] == 2


def test_two_real_subsystems_are_still_refused(gate) -> None:
    ok, report = gate.verify_proof_2_boundary_and_gate(
        "abc123", ["bin/x", "platform/y/z.yaml"]
    )
    assert not ok
    assert "Cross-subsystem mutation" in report["error"]
    assert "['bin', 'platform']" in report["error"]


def test_a_test_alone_is_labelled_and_admitted(gate) -> None:
    ok, report = gate.verify_proof_2_boundary_and_gate(
        "abc123", ["tests/estate/test_x.py"]
    )
    assert ok, report
    assert report["subsystem"] == "tests"


def test_a_guarded_path_still_needs_the_founder_seal(gate) -> None:
    ok, report = gate.verify_proof_2_boundary_and_gate(
        "abc123", [".github/workflows/x.yml", "tests/estate/test_x.py"]
    )
    assert not ok
    assert "without Founder seal" in report["error"]
    sealed, _ = gate.verify_proof_2_boundary_and_gate(
        "abc123",
        [".github/workflows/x.yml", "tests/estate/test_x.py"],
        founder_seal_verified=True,
    )
    assert sealed


def test_the_file_ceiling_is_unchanged(gate) -> None:
    many = [
        "bin/a",
        "tests/estate/test_a.py",
        "tests/estate/test_b.py",
        "tests/estate/test_c.py",
        "tests/estate/test_d.py",
        "tests/estate/test_e.py",
    ]
    assert len(many) > MAX_FILES
    ok, report = gate.verify_proof_2_boundary_and_gate("abc123", many)
    assert not ok
    assert "exceeds MAX_FILES_PER_CHANGE" in report["error"]
