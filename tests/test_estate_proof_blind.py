"""A missing suite is BLIND, not a hundred failures."""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

# Load the proof script as a module, not by exec'ing its source: the script guards main()
# behind `if __name__ == "__main__"`, so importing it does not run the proof, and the estate
# python standard refuses exec (bandit S102).
_proof_path = Path.home() / ".estate/bin/estate-proof"
_loader = SourceFileLoader("estate_proof", str(_proof_path))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
mod = importlib.util.module_from_spec(_spec)
_loader.exec_module(mod)
verdict = mod.projector_verdict


def test_missing_script_is_blind_not_failed():
    state, passed, failed, why = verdict(
        1, 'npm error Missing script: "test:projector"'
    )
    assert state == "BLIND" and passed == 0 and failed == 0 and "not configured" in why


def test_a_real_failure_is_a_failure():
    state, passed, failed, _ = verdict(1, "pass 3\nfail 7")
    assert state == "FAIL" and failed == 7


def test_a_clean_run_passes():
    state, passed, _, _ = verdict(0, "pass 42\nfail 0")
    assert state == "PASS" and passed == 42


def test_a_lie_of_zero_results_is_not_a_pass():
    state, _, _, why = verdict(0, "")
    assert state == "BLIND" and "no results" in why
