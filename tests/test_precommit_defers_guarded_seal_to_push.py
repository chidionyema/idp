"""Falsifier for the #8541 gate-timing fix.

Both sides are required (a gate that cannot fail is not a gate):
  (a) pre-commit semantics (--defer-guarded): an unsigned guarded-path change PASSES the commit
      gate and says which check enforces it. The commit and its X-Idp-Auth trailer do not exist yet.
  (b) without the flag the same change is still REFUSED. The lock is moved, never removed.
  (c) the check it names really exists and really runs: .github/workflows/guarded-paths.yml runs
      bin/idp-ci-guarded-paths. Rename either and (a) would defer to nothing, so this fails.
The file-count limit, the cross-subsystem limit and the blacklist are never deferred.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bin"))
from verify_three_proofs import verify_proof_2_boundary_and_gate  # noqa: E402

HEAD = "0" * 40  # pre-commit: the commit does not exist yet
GUARDED = [".github/workflows/sovereign-reconciler.yml"]


def test_precommit_defers_unsigned_guarded_path_to_the_ci_check():
    ok, report = verify_proof_2_boundary_and_gate(
        HEAD, GUARDED, defer_guarded_to_push=True
    )
    assert ok is True, report
    assert any("guarded-paths CI check" in d for d in report["deferred_to_push"]), (
        report
    )


def test_without_the_flag_an_unsigned_guarded_path_is_refused():
    ok, report = verify_proof_2_boundary_and_gate(
        HEAD, GUARDED, defer_guarded_to_push=False
    )
    assert ok is False and "Guarded path" in report["error"], report


def test_the_named_enforcer_exists_and_runs():
    workflow = (REPO / ".github/workflows/guarded-paths.yml").read_text()
    assert "bin/idp-ci-guarded-paths" in workflow
    assert (REPO / "bin/idp-ci-guarded-paths").is_file()


def test_oversize_and_cross_subsystem_are_never_deferred():
    files = [f"src/f{i}.py" for i in range(7)]
    ok, report = verify_proof_2_boundary_and_gate(
        HEAD, files, defer_guarded_to_push=True
    )
    assert ok is False and "MAX_FILES_PER_CHANGE" in report["error"], report
    ok2, report2 = verify_proof_2_boundary_and_gate(
        HEAD, ["ops/x.py", "greenlane/y.py"], defer_guarded_to_push=True
    )
    assert ok2 is False and "Cross-subsystem" in report2["error"], report2


def test_blacklist_is_never_deferred():
    bad = "937dda9d" + "0" * 32
    ok, report = verify_proof_2_boundary_and_gate(
        bad, ["ops/x.py"], defer_guarded_to_push=True
    )
    assert ok is False and "Blacklisted" in report["error"], report
