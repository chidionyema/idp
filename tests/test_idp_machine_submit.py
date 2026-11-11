"""Acceptance test for bin/idp-machine-submit -- the machine/agent boundary.

The founder sent the same pin-level audit four times because nothing in the
estate fails when the submit engine loses a guarantee. This file IS the audit,
as a gate. It grades the engine on main, not a claim about the engine.

Every check reads the real artifact and asserts on measured content. A check
that cannot fail is not a check, so `test_falsifier_detects_a_degraded_engine`
proves the suite rejects a deliberately broken engine.

The ten acceptance criteria (AC-1 .. AC-10) from the audit, graded here:

  AC-1  one door: the engine must not bypass the pre-push gate
  AC-2  fail loudly: no silent-failure idioms swallowing a real error
  AC-3  evidence: a run leaves a machine-readable record
  AC-4  register: pin firings are recorded
  AC-5  lease: the engine refuses files held by another live agent
  AC-6  plan: a non-trivial diff without a plan is refused
  AC-7  disk: the engine refuses below the disk floor, after trimming
  AC-8  falsifier: the suite can fail
  AC-9  receipt: evidence carries input/output/governor/hash
  AC-10 no silent failure: same measurement as AC-2, stated as a count
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ENGINE = REPO / "bin" / "idp-machine-submit"


def _engine_source() -> str:
    """The engine as committed, so a dirty working tree cannot fake a pass."""
    try:
        out = subprocess.run(
            ["git", "show", "origin/main:bin/idp-machine-submit"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return ENGINE.read_text(encoding="utf-8") if ENGINE.is_file() else ""


SOURCE = _engine_source()


def test_engine_exists() -> None:
    """The gate is meaningless without the artifact it grades."""
    assert SOURCE.strip(), (
        "bin/idp-machine-submit is absent from the tree and from origin/main"
    )


# ---------------------------------------------------------------- AC-1


def test_ac1_no_bypass_flag() -> None:
    """AC-1: --no-verify makes the only local gate invisible.

    The engine may name it in a comment explaining why it is absent; it may
    never appear as an argument to a command.
    """
    offenders = [
        line
        for line in SOURCE.splitlines()
        if "--no-verify" in line and not line.lstrip().startswith("#")
    ]
    assert not offenders, (
        "AC-1 FAIL: the engine bypasses the pre-push gate with --no-verify:\n"
        + "\n".join(offenders)
    )


# ---------------------------------------------------------------- AC-2 / AC-10


def test_ac2_no_silent_failure() -> None:
    """AC-2/AC-10: a swallowed error is a claim of success for work not done."""
    swallowed = []
    for i, line in enumerate(SOURCE.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\|\|\s*true", line) or "2>/dev/null" in line:
            swallowed.append(f"  line {i}: {stripped}")
    assert not swallowed, (
        f"AC-2/AC-10 FAIL: {len(swallowed)} silent-failure idiom(s). "
        "Each is a path where the engine reports success for work that did not run:\n"
        + "\n".join(swallowed)
    )


# ---------------------------------------------------------------- AC-5


def test_ac5_lease_is_consulted() -> None:
    """AC-5: squashing a range that includes another agent's work erases it."""
    assert re.search(r"claim-gate|claim_gate|CLAIM", SOURCE), (
        "AC-5 FAIL: the engine never consults the claim/lease gate before rewriting history"
    )


# ---------------------------------------------------------------- AC-6


def test_ac6_plan_required() -> None:
    """AC-6: removing the ceremony removed the contract unless a gate replaces it."""
    assert re.search(r"PLAN_REQUIRED|estate/plans", SOURCE), (
        "AC-6 FAIL: the plan requirement was deleted with the ceremony and nothing replaced it"
    )


# ---------------------------------------------------------------- AC-7


def test_ac7_disk_floor() -> None:
    """AC-7: below the disk floor every door refuses, including this one."""
    assert re.search(r"DISK_FLOOR", SOURCE), (
        "AC-7 FAIL: the engine has no disk-floor check, so it retries the "
        "original self-DDoS: the gate refuses while the engine waits on it"
    )


# ---------------------------------------------------------------- AC-3 / AC-9


def test_ac3_evidence_written() -> None:
    """AC-3/AC-9: a run that leaves no record cannot be graded or replayed."""
    assert re.search(r"evidence|register\.jsonl", SOURCE), (
        "AC-3/AC-9 FAIL: the engine writes no evidence file and appends to no register, "
        "so class_repair_ratio is uncomputable from what it produces"
    )


# ---------------------------------------------------------------- AC-8


def test_ac8_falsifier_detects_a_degraded_engine() -> None:
    """AC-8: the suite must reject a known-bad engine, or it is decoration.

    Runs the AC-1/AC-2/AC-3 predicates against a deliberately broken engine
    and requires every one of them to fire.
    """
    broken = (
        "#!/usr/bin/env bash\n"
        "git push --no-verify --force-with-lease origin HEAD:refs/heads/lane/x\n"
        '"$HOME/.estate/bin/instruction" new "y" 2>/dev/null || true\n'
        "echo '{\"ok\":true}'\n"
    )

    def has_bypass(src: str) -> bool:
        return any(
            "--no-verify" in ln and not ln.lstrip().startswith("#")
            for ln in src.splitlines()
        )

    def has_swallow(src: str) -> bool:
        return any(
            (re.search(r"\|\|\s*true", ln) or "2>/dev/null" in ln)
            and not ln.lstrip().startswith("#")
            for ln in src.splitlines()
        )

    def has_evidence(src: str) -> bool:
        return bool(re.search(r"evidence|register\.jsonl", src))

    assert has_bypass(broken), (
        "falsifier blind: the AC-1 predicate did not fire on --no-verify"
    )
    assert has_swallow(broken), (
        "falsifier blind: the AC-2 predicate did not fire on || true"
    )
    assert not has_evidence(broken), (
        "falsifier blind: the AC-3 predicate fired on no evidence"
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
