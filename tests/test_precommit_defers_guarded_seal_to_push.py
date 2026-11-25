"""Falsifier for the #8541 gate-timing fix.

Two sides, both required (R1/R2: a gate that cannot fail is not a gate):
  (a) pre-commit semantics (--defer-guarded): a guarded-path change with no seal
      PASSES the commit gate -- deferred to pre-push, where the real commit SHA
      exists and its X-Idp-Auth trailer can be verified.
  (b) pre-push semantics (no defer flag): the same unsigned guarded-path change is
      still REFUSED. The lock is moved, never removed.
The blacklist is never deferred on either side.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
from verify_three_proofs import verify_proof_2_boundary_and_gate  # noqa: E402

HEAD = "0" * 40  # pre-commit: the commit does not exist yet


def test_precommit_defers_unsigned_guarded_path_to_push():
    ok, report = verify_proof_2_boundary_and_gate(
        HEAD, [".github/workflows/sovereign-reconciler.yml"], defer_guarded_to_push=True
    )
    assert ok is True, report
    assert report["proof_2_status"] == "PASS"
    assert any("enforced at pre-push" in d for d in report["deferred_to_push"]), report


def test_prepush_still_refuses_unsigned_guarded_path():
    ok, report = verify_proof_2_boundary_and_gate(
        HEAD, [".github/workflows/sovereign-reconciler.yml"], defer_guarded_to_push=False
    )
    assert ok is False, report
    assert "Guarded path" in report["error"], report


def test_prepush_still_refuses_oversize_and_cross_subsystem():
    files = [f"src/f{i}.py" for i in range(7)]
    ok, report = verify_proof_2_boundary_and_gate(HEAD, files, defer_guarded_to_push=False)
    assert ok is False and "MAX_FILES_PER_CHANGE" in report["error"], report
    ok2, report2 = verify_proof_2_boundary_and_gate(
        HEAD, ["ops/x.py", "greenlane/y.py"], defer_guarded_to_push=False
    )
    assert ok2 is False and "Cross-subsystem" in report2["error"], report2


def test_blacklist_is_never_deferred():
    bad = "937dda9d" + "0" * 32
    ok, report = verify_proof_2_boundary_and_gate(
        bad, ["ops/x.py"], defer_guarded_to_push=True
    )
    assert ok is False and "Blacklisted" in report["error"], report
