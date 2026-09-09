"""Prove the W2.2 shadow-run producer logic both ways (LAW 3).

bin/idp-shadow-run is the deterministic producer of the green/shadowerify check that a merged
auto-remediation PR must carry (#2751 / pr-landable refuses an auto-remediation PR without a
SUCCESS shadow-verify on its own head). The live part (applying a real PR's diff into the sandbox
vcluster, reading state back) is exercised by an in-cluster runner the estate approves; what a
fixture proves is the production of the verdict from an observation + the head it claims.

These tests grade the producer's exit and the gate-facing line over deterministic observations.
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-shadow-run")
FIX = os.path.join(ROOT, "tests/fixtures/shadow-run")
HEAD = "abc123def"


def _run(obs, head):
    return subprocess.run(
        ["python3", BIN, os.path.join(FIX, obs), head], capture_output=True, text=True
    )


def test_binary_present():
    assert os.path.exists(BIN)


def test_converged_on_its_own_head_makes_the_required_green_check():
    r = _run("converged.json", HEAD)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok" in r.stdout and "shadow-verify SUCCESS" in r.stdout


def test_a_broken_change_produces_red_never_green():
    r = _run("broken.json", HEAD)
    assert r.returncode == 1, r.stdout
    assert "FAIL" in r.stdout


def test_a_proof_not_on_this_head_cannot_pass_even_if_converged():
    # converged.json claims head abc123def but we ask for a different head -> the proof does not
    # cover this PR and must not produce a green.
    r = _run("converged.json", "ffe000")
    assert r.returncode == 1, r.stdout
    assert "does not cover this PR" in r.stdout


def test_missing_observation_is_blind_not_a_pass():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        # point at a file that does not exist
        bad = subprocess.run(
            ["python3", BIN, os.path.join(d, "absent.json"), HEAD],
            capture_output=True,
            text=True,
        )
        assert bad.returncode == 2, bad.stdout
        assert "BLIND" in bad.stdout
