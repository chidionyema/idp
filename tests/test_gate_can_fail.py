"""Falsifiers for bin/gate-can-fail -- the door that proves a gate can fail.

WHY THIS FILE EXISTS. On 2026-11-10 a falsifier passed 7/7 against deliberately broken code, and a
protocol gate answered "allow" when it could not evaluate itself. Both are R1: a gate that cannot
fail is not a gate. `bin/gate-can-fail` is the class repair -- a gate may not be trusted to pass
until it has been shown to fail.

A door that certifies other gates must itself be shown able to fail, so these tests include a
mutation test: break the door's own verdict logic and the suite must go RED.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DOOR = REPO / "bin" / "gate-can-fail"


def load():
    loader = importlib.machinery.SourceFileLoader("gate_can_fail", str(DOOR))
    spec = importlib.util.spec_from_loader("gate_can_fail", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


m = load()


# ---------------------------------------------------------------- the verdict itself
def test_a_gate_that_accepts_known_bad_is_disqualified():
    r = m.judge("x", "true", "true")
    assert r["ok"] is False
    assert any("ACCEPTED KNOWN-BAD" in f for f in r["findings"])


def test_a_gate_that_rejects_known_bad_and_accepts_known_good_passes():
    r = m.judge("x", "false", "true")
    assert r["ok"] is True
    assert r["findings"] == []


def test_a_gate_that_rejects_known_good_is_disqualified():
    r = m.judge("x", "false", "false")
    assert r["ok"] is False
    assert any("REJECTED KNOWN-GOOD" in f for f in r["findings"])


def test_a_gate_that_cannot_run_is_never_a_pass():
    """The bug this door had: /bin/sh exits 127 for a missing binary, which looked like a
    rejection and certified a gate that never ran. BLIND is not a pass."""
    r = m.judge("x", "/nonexistent/binary-that-does-not-exist", "true")
    assert r["ok"] is False
    assert any("could not be executed" in f or "BLIND" in f for f in r["findings"])


def test_exit_126_is_not_executable_and_is_blind():
    """126 is 'found but not executable' -- also could not run, not a rejection."""
    r = m.judge("x", "sh -c 'exit 126'", "true")
    assert r["ok"] is False


def test_exit_127_from_a_missing_binary_is_blind_not_rejection():
    rc, _ = m.run("/nonexistent/binary", timeout=10)
    assert rc == 127, (
        "if /bin/sh stops returning 127 this guard's reason changes, not its rule"
    )


# ---------------------------------------------------------------- the CLI contract
def run_door(*args):
    return subprocess.run(
        [sys.executable, str(DOOR), *args], capture_output=True, text=True, timeout=120
    )


def test_self_test_passes():
    r = run_door("--self-test")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VERDICT: PASS" in r.stdout


def test_no_gate_named_is_blind_exit_2_not_a_pass():
    r = run_door()
    assert r.returncode == 2, "BLIND must be 2, never 0"
    assert "BLIND" in r.stderr


def test_only_a_bad_command_is_blind_because_neither_direction_was_measured():
    r = run_door("--gate", "g", "--bad-cmd", "false")
    assert r.returncode == 2
    assert "only one" in r.stderr


def test_a_disqualified_gate_exits_1():
    r = run_door("--gate", "g", "--bad-cmd", "true", "--good-cmd", "true")
    assert r.returncode == 1
    assert "disqualified" in r.stderr


def test_a_proved_gate_exits_0_and_writes_a_receipt():
    r = run_door("--gate", "g", "--bad-cmd", "false", "--good-cmd", "true")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "receipt:" in r.stdout
    assert "rejected known-bad" in r.stdout


def test_blind_uses_the_declared_exit_code_not_sys_exit_string():
    """`sys.exit("string")` exits 1. A blind verdict carried by a string would silently become 1
    and be read as 'the gate is disqualified' when the truth is 'nothing was measured'.

    The check parses the AST rather than grepping the text: this module's own docstring QUOTES the
    defect to explain it, and a text search would flag the explanation -- a guard that refuses its
    own documentation is the R14 class (a guard that taxes the people using it).
    """
    import ast

    tree = ast.parse(DOOR.read_text())
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if getattr(fn, "attr", "") != "exit":
            continue
        if getattr(fn, "value", None) is None or getattr(fn.value, "id", "") != "sys":
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            offenders.append(node.lineno)
    assert not offenders, f"a string exit cannot carry an exit code (lines {offenders})"
    assert "sys.exit(EXIT_BLIND)" in DOOR.read_text()


# ---------------------------------------------------------------- the door can fail (mutation)
def _mutated_copy(tmp_path: Path, old: str, new: str) -> Path:
    dst = tmp_path / "gate-can-fail"
    text = DOOR.read_text()
    assert old in text, (
        f"mutation anchor not present, so the mutation grades nothing: {old!r}"
    )
    dst.write_text(text.replace(old, new, 1))
    dst.chmod(0o755)
    return dst


def test_a_door_that_accepts_known_bad_goes_red(tmp_path):
    """Mutate the verdict so known-bad is always accepted. The self-test must FAIL."""
    bad = _mutated_copy(
        tmp_path,
        "elif bad_rc == 0:",
        "elif bad_rc != 999999:  # MUTANT: any exit reads as rejection",
    )
    r = subprocess.run(
        [sys.executable, str(bad), "--self-test"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode != 0, "the door certified a gate that accepts known-bad"
    assert "FAIL" in r.stdout


def test_a_door_blind_to_127_goes_red(tmp_path):
    """Mutate away the 126/127 blindness. The self-test must FAIL on the cannot-run case."""
    bad = _mutated_copy(
        tmp_path, "elif bad_rc in (126, 127):", "elif bad_rc == 124:  # MUTANT"
    )
    r = subprocess.run(
        [sys.executable, str(bad), "--self-test"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode != 0, "the door certified a gate that never ran"
    assert "FAIL" in r.stdout


def test_the_receipt_carries_a_sha256(tmp_path, monkeypatch):
    """A receipt without a hash is a note, not evidence a later session can check."""
    monkeypatch.setattr(m, "DEFAULT_RECEIPTS", tmp_path)
    path = m.write_receipt(m.judge("g", "false", "true"))
    import json

    d = json.loads(path.read_text())
    assert len(d["sha256"]) == 64
    assert d["ok"] is True
    assert d["gate"] == "g"
