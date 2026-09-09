"""Prove the shadow-verify convergence assertion (spec W2.2, LAW 3).

The rule under test: 'bin/idp-shadow-verify' (agent-infra-safety-spec.md W2.2). A change is proven
in the shadow dimension only when the workload still converges after the diff is applied: Ready, at
its previous replica count, probes green, its own tests green. The grader is fail-closed -- a
shadow observation that is silent about an assertion has proved nothing and is refused, never
passed on a guess.

These tests drive the grader with observation fixtures. The live executor (apply the diff inside a
real vcluster, read the state back into this JSON) is W2.2's second half; this is the assertion
contract it must satisfy.
"""

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-shadow-verify")
# Contiguous literal on purpose: the estate's rule-coverage gate (LAW 3) grades a fixture only
# when some repo file names it with the contiguous path tests/fixtures/shadow-verify; a split
# os.path.join would leave these fixtures 'graded by nothing' and the run red.
FIX = os.path.join(ROOT, "tests/fixtures/shadow-verify")


def _run(name):
    return subprocess.run(
        ["python3", BIN, os.path.join(FIX, name)], capture_output=True, text=True
    )


def test_binary_exists():
    assert os.path.exists(BIN)


def test_converged_workload_passes():
    r = _run("converged.json")
    assert r.returncode == 0, r.stdout
    assert "ok" in r.stdout


def test_not_ready_is_refused_and_names_why():
    r = _run("not-ready.json")
    assert r.returncode == 1, r.stdout
    assert "not Ready" in r.stdout


def test_failed_probe_is_refused():
    r = _run("probe-fails.json")
    assert r.returncode == 1, r.stdout
    assert "probe for worker" in r.stdout


def test_silent_observation_is_fail_closed_not_a_pass():
    r = _run("silent.json")
    assert r.returncode == 1, r.stdout
    assert "silent about readiness" in r.stdout
