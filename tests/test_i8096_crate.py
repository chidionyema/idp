"""The cage/i8096 crate must build, test and keep its own hash pin honest.

WHAT THIS GRADES, AND WHY IT EXISTS. `cage/i8096/src/certifier.rs` sat on canonical
main for months as an orphan file: hash-pinned in SHA256SUMS, referenced by nothing,
compiled by nothing, tested by nothing. A pin proves the bytes did not change; it
does not prove the bytes work. These tests make the cage a compiled artefact with a
falsifier, and they live in the ordinary pytest surface so that CI runs them
without anyone having to add a workflow.

Both directions are graded, the way every rule in this estate is:
  - the GOOD fixture is the untouched cage: it builds, its tests pass, its pins match;
  - the BAD fixture is a tampered copy of the cage: the hash gate MUST refuse it.
    A gate that cannot fail is not a gate.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAGE = os.path.join(ROOT, "cage", "i8096")
MANIFEST = os.path.join(CAGE, "Cargo.toml")
GATE = os.path.join(ROOT, "bin", "verify-i8096-cage")


def test_crate_builds_and_its_tests_pass():
    result = subprocess.run(
        ["cargo", "test", "--manifest-path", MANIFEST, "--locked", "--quiet"],
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]


def test_hash_gate_passes_on_the_untouched_cage():
    result = subprocess.run(
        ["bash", GATE], capture_output=True, text=True, timeout=120, cwd=ROOT
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_hash_gate_refuses_a_tampered_cage():
    with tempfile.TemporaryDirectory() as tmp:
        cage_copy = os.path.join(tmp, "cage", "i8096")
        shutil.copytree(CAGE, cage_copy)
        gate_copy = os.path.join(tmp, "bin", "verify-i8096-cage")
        os.makedirs(os.path.dirname(gate_copy), exist_ok=True)
        shutil.copy2(GATE, gate_copy)
        with open(
            os.path.join(cage_copy, "src", "lib.rs"), "a", encoding="utf-8"
        ) as fh:
            fh.write("\n// tampered\n")
        result = subprocess.run(
            ["bash", gate_copy], capture_output=True, text=True, timeout=120, cwd=tmp
        )
        assert result.returncode != 0, "the hash gate accepted a tampered cage"
        assert "MISMATCH" in (result.stdout + result.stderr)
