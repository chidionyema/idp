"""Prove the Proof-of-Convergence gate both ways (spec W2.3, LAW 3).

The rule under test: 'bin/idp-convergence-proof' (agent-infra-safety-spec.md W2.3). A pull
request whose body carries no well-formed Proof-of-Convergence block -- or whose proof's run is
not a green run on this pull request's head commit -- is refused, fail-closed. A well-formed
block whose witness is green on the head commit passes.

These tests grade the gate's exit code for structural cases the fixtures and a deterministic
witness can reach without a running shadow vcluster. The live-witness seam (CONVERGENCE_* env)
is the path a real shadow-verify CI run will drive; the default refuses rather than assumes.
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repository root
BIN = os.path.join(ROOT, "bin", "idp-convergence-proof")
BODIES = os.path.join(ROOT, "tests", "fixtures", "convergence")

HEAD = "abc123def4567890"
OTHER = "9999999999999999"


def _invoke(body_name, env=None):
    e = {"CONVERGENCE_RUN_GREEN": "1", "CONVERGENCE_RUN_HEAD": HEAD}
    if env:
        e.update(env)
    return subprocess.run(
        ["python3", BIN, os.path.join(BODIES, body_name), HEAD],
        capture_output=True,
        text=True,
        env={**os.environ, **e},
    )


def test_gate_binary_exists():
    assert os.path.exists(BIN), f"gate binary missing: {BIN}"


def test_no_proof_block_is_refused_fail_closed():
    r = _invoke("no-proof.md")
    assert r.returncode == 1
    assert "REFUSE" in r.stdout
    assert "no Proof-of-Convergence" in r.stdout


def test_well_formed_green_proof_on_head_passes():
    r = _invoke("proved.md")
    assert r.returncode == 0
    assert "proved" in r.stdout


def test_green_run_on_wrong_head_commit_is_refused():
    # the proof's witness (CONVERGENCE_RUN_HEAD) is a different commit than the reviewed head
    r = _invoke("proved.md", env={"CONVERGENCE_RUN_HEAD": OTHER})
    assert r.returncode == 1
    assert "not this pull request" in r.stdout


def test_missing_green_witness_is_fail_closed_not_a_pass():
    # the default must never guess: without a witnessed green run the proof is refused
    r = _invoke("proved.md", env={"CONVERGENCE_RUN_GREEN": "0"})
    assert r.returncode == 1
    assert "not green" in r.stdout
