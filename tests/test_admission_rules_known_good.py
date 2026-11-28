"""Every admission rule, one standard set of known-good changes, both directions.

The estate carried THREE copies of "one subsystem per change" and a fourth rule that
refuses any new Python file outside tests/. A code change with its test in tests/ was
refused by all of them, so no agent could land one and every hand-back was structural
(idp#8649, measured 2026-11-27: PROOF_2_FAILED cross-subsystem mutation
['platform', 'tests']).

This file is the check the founder asked for: it runs EVERY admission rule together
against a standard set of known-good changes. If any rule refuses a known-good change,
that rule cannot land. Each known-bad change is still refused by the set -- the boundary
MOVES, it does not disappear -- and the pre-fix predicate is frozen inside this file so
the differential is proved in both directions on any tree, not only on the tree that
carried the fix.

The rules, and the door each one is:

  proof 2      bin/verify_three_proofs.py     the commit boundary (subsystem, seal)
  ADMISSION    bin/idp-bdd-proof-gate         the scope a claim may declare
  scope        bin/idp-agent-base-apply.py    the trusted scope the cloud door admits
  binding      bin/idp-differential-falsifier which changed subsystem needs a bound test
  language     bin/legion-admit               a new Python file may only land in tests/
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

SHA = "0" * 40


def _load(name: str, path: pathlib.Path):
    """Load an extensionless estate script as a module (the door runs it the same way)."""
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


V3P = _load("verify_three_proofs", BIN / "verify_three_proofs.py")
# Registered under its own name so the gates that read the limit bind to THIS module
# object: one source, proved by identity rather than by a comment.
sys.modules["verify_three_proofs"] = V3P
BDD = _load("admission_bdd_gate", BIN / "idp-bdd-proof-gate")
DIFF = _load("admission_diff_falsifier", BIN / "idp-differential-falsifier")
LEGION = _load("admission_legion_admit", BIN / "legion-admit")
APPLY = _load("admission_agent_base_apply", BIN / "idp-agent-base-apply.py")

# The standard set: a code change and the test that proves it, one top-level directory.
KNOWN_GOOD = [
    ("platform/estate/memory/leases.py", "tests/test_leases.py"),
    ("bin/verify_three_proofs.py", "tests/test_verify_three_proofs.py"),
    ("platform/unified-memory-server/store.py", "tests/test_store.py"),
]

# The standard set of changes that must still be refused, and by which rule.
KNOWN_BAD = [
    (
        "two code subsystems",
        ("platform/estate/memory/leases.py", "bin/verify_three_proofs.py"),
    ),
    ("code and docs", ("platform/estate/memory/leases.py", "docs/decisions/x.md")),
    (
        "a guarded path without a seal",
        (".github/workflows/ci.yml", "tests/test_ci.yml"),
    ),
    ("more files than the lane allows", tuple(f"platform/x/f{i}.py" for i in range(6))),
]


def _admission_body(scope: tuple[str, ...], base: str = SHA) -> str:
    """The ADMISSION block a session declares, with the digest the gate recomputes."""
    digest = hashlib.sha256(
        json.dumps({"base": base, "scope": sorted(scope)}, sort_keys=True).encode()
    ).hexdigest()
    return (
        "ADMISSION\n"
        f"base: {base}\n"
        f"scope: {json.dumps(sorted(scope))}\n"
        f"digest: {digest}\n"
        "END-ADMISSION\n"
    )


def _old_subsystems(paths: tuple[str, ...]) -> set[str]:
    """The predicate as it stood BEFORE idp#8649: every path's top-level directory.

    Frozen here so the differential is proved on any tree. The estate's rule moved; the
    old answer did not become true again.
    """
    out = set()
    for path in paths:
        parts = path.strip("/").split("/")
        out.add(parts[0] if len(parts) > 1 else "root")
    return out


@pytest.mark.parametrize("scope", KNOWN_GOOD)
def test_every_admission_rule_admits_a_code_change_with_its_test(scope) -> None:
    """The known-good set must pass EVERY rule. A rule that refuses it cannot land."""
    paths = list(scope)

    ok, report = V3P.verify_proof_2_boundary_and_gate(SHA, paths, False)
    assert ok is True, report
    assert report["proof_2_status"] == "PASS"

    admitted, why = BDD.verify_admission_block(_admission_body(scope))
    assert admitted is True, why

    APPLY.validate_scope(SHA, paths)

    # The companion is the PROOF: it must not demand a bound test of its own.
    assert DIFF.required_subsystems(paths) == {DIFF.subsystem_of(scope[0])}


@pytest.mark.parametrize("scope", KNOWN_GOOD)
def test_the_pre_fix_predicate_refused_exactly_what_the_fix_admits(scope) -> None:
    """The fix must be load-bearing: the old answer refused this scope."""
    assert len(_old_subsystems(scope)) > 1, (
        "the frozen old predicate no longer refuses it"
    )
    ok, report = V3P.verify_proof_2_boundary_and_gate(SHA, list(scope), False)
    assert ok is True, report


@pytest.mark.parametrize(("why", "scope"), KNOWN_BAD)
def test_a_known_bad_change_is_still_refused(why, scope) -> None:
    """The boundary moved; it did not disappear."""
    ok, report = V3P.verify_proof_2_boundary_and_gate(SHA, list(scope), False)
    if why == "a guarded path without a seal":
        assert ok is False and "Guarded path" in report["error"], report
        return
    if why == "more files than the lane allows":
        assert ok is False and "MAX_FILES_PER_CHANGE" in report["error"], report
        return
    assert ok is False and "Cross-subsystem" in report["error"], report
    admitted, message = BDD.verify_admission_block(_admission_body(scope))
    assert admitted is False and "cross-subsystem" in message, message


def test_the_claim_scope_of_a_code_change_with_its_test_is_admitted() -> None:
    """The claim declares the code AND the test; the door must take the declaration."""
    scope = ("platform/estate/memory/leases.py", "tests/test_leases.py")
    admitted, why = BDD.verify_admission_block(_admission_body(scope))
    assert admitted is True, why
    assert "ADMITTED 2 path(s)" in why


def test_a_new_python_file_may_only_land_in_tests() -> None:
    """The language door: the one place a new Python file can land is tests/."""
    LEGION.refuse_new_python(["tests/test_a_new_probe.py"])
    with pytest.raises(ValueError) as exc:
        LEGION.refuse_new_python(["platform/estate/memory/a_new_probe.py"])
    assert "LANGUAGE_GATE" in str(exc.value)


def test_the_known_good_set_is_not_trivially_admitted() -> None:
    """A check that cannot fail is not a check: swap the companion for a second code
    subsystem and the same rule must refuse it."""
    scope = ("platform/estate/memory/leases.py", "bin/verify_three_proofs.py")
    ok, report = V3P.verify_proof_2_boundary_and_gate(SHA, list(scope), False)
    assert ok is False and "Cross-subsystem" in report["error"], report
    admitted, message = BDD.verify_admission_block(_admission_body(scope))
    assert admitted is False and "cross-subsystem" in message, message


def test_the_owner_of_the_limit_is_the_only_copy() -> None:
    """One source of the limit: the other gates read it, they do not restate it."""
    assert V3P.subsystems_of(["platform/x.py", "tests/test_x.py"]) == {"platform"}
    assert BDD.subsystems_of is V3P.subsystems_of
    assert DIFF.is_companion_path is V3P.is_companion_path


def _json_mode(body: str) -> tuple[int, str]:
    """Grade a pull request through the gate's real JSON mode, as a process."""
    import subprocess

    done = subprocess.run(
        [sys.executable, str(BIN / "idp-bdd-proof-gate")],
        input=json.dumps({"title": "t", "headRefOid": SHA, "body": body}),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return done.returncode, (done.stdout + done.stderr).strip()


def test_the_json_mode_admits_a_proof_that_declares_a_known_good_scope() -> None:
    """The scope declaration, through the real gate: a known-good scope is admitted."""
    body = (
        f"BDD-PROOF\nhead: {SHA}\n31 scenarios (31 passed)\nEND-BDD-PROOF\n"
        + _admission_body(("platform/estate/memory/leases.py", "tests/test_leases.py"))
    )
    rc, out = _json_mode(body)
    assert rc == 0, out


def test_the_json_mode_refuses_a_proof_that_declares_no_scope() -> None:
    """The rule is not decorative: a body with no scope declaration is refused."""
    body = f"BDD-PROOF\nhead: {SHA}\n31 scenarios (31 passed)\nEND-BDD-PROOF\n"
    rc, out = _json_mode(body)
    assert rc != 0 and "ADMISSION_MISSING" in out, out


def test_the_json_mode_refuses_a_scope_that_spans_two_code_subsystems() -> None:
    """Two code subsystems are still refused by the scope rule, in both directions."""
    body = (
        f"BDD-PROOF\nhead: {SHA}\n31 scenarios (31 passed)\nEND-BDD-PROOF\n"
        + _admission_body(
            ("platform/estate/memory/leases.py", "bin/verify_three_proofs.py")
        )
    )
    rc, out = _json_mode(body)
    assert rc != 0 and "cross-subsystem" in out, out


def known_good_refusals() -> int:
    """How many admission rules refuse the known-good change (a code change + its test).

    This is the measure the registry names (admission.code_plus_test_refusals): 1
    before idp#8649 (proof 2 refused a platform/ change whose test lives in tests/),
    0 after. Every rule is asked the same question, so the number means one thing.
    """
    scope = ("platform/estate/memory/leases.py", "tests/test_leases.py")
    paths = list(scope)
    refusals = 0
    ok, _report = V3P.verify_proof_2_boundary_and_gate(SHA, paths, False)
    refusals += 0 if ok else 1
    admitted, _why = BDD.verify_admission_block(_admission_body(scope))
    refusals += 0 if admitted else 1
    try:
        APPLY.validate_scope(SHA, paths)
    except Exception:  # noqa: BLE001 - a refusal is a raise here
        refusals += 1
    # The path binding refuses when a companion demands a bound test of its own.
    if DIFF.subsystem_of(scope[1]) in DIFF.required_subsystems(paths):
        refusals += 1
    return refusals


def test_no_admission_rule_refuses_the_known_good_change() -> None:
    """The class, measured as a number: zero rules refuse a code change with its test."""
    assert known_good_refusals() == 0


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(f"optimus.admission.code_plus_test_refusals={known_good_refusals()}")
        sys.exit(0)
    raise SystemExit("run this module with pytest, or with --optimus for the measure")
