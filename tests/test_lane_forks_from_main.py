"""DBG-034's falsifier: one lane carries one instruction.

The pre-push claim gate judges the whole range `origin/main..HEAD`, not the single commit
being pushed. A lane forked from another agent's unlanded branch therefore carries their
instruction ids as well as yours, and the gate refuses it -- correctly.

This test builds a throwaway repository and runs the SHIPPED `bin/claim-gate` over it:

  * fork lane   -- another agent's commit underneath mine, so the range names two instructions
  * clean lane  -- my commit alone, on origin/main

It asserts the gate REFUSES the first and does not refuse the second for carrying several
instructions. Grading only the refusal would pass a gate that refuses everything; grading only
the acceptance would pass a gate that does nothing. Both, or neither.

A crash is BLIND (exit 2), never a pass: an import error would mean the gate was never run,
and calling that "fired" is the fail-open defect this pack exists to close.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "bin" / "claim-gate"

EXIT_BLIND = 2
INS_MINE = "INS-00007"
INS_THEIRS = "INS-00008"
PLAN = "fe65d1af3c4f6485ec3327e828c32578078a40469f51173360c00ce29d3b751a"


def _git(cwd: Path, *args: str) -> str:
    p = subprocess.run(
        ("git",) + args, cwd=str(cwd), capture_output=True, text=True, timeout=60
    )
    if p.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {p.stderr}")
    return p.stdout


def _commit(repo: Path, path: str, instruction: str) -> None:
    f = repo / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"{instruction}\n")
    _git(repo, "add", "-A")
    msg = (
        f"change {path}\n\n"
        "Claim: chidionyema/idp#7899\n"
        "Agent: estate-agent\n"
        f"Instruction: {instruction}\n"
        f"Plan: {PLAN}\n"
    )
    _git(repo, "commit", "-qm", msg)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "idp"
    (r / "bin").mkdir(parents=True)
    (r / "bin" / "claim-gate").write_text(GATE.read_text())
    os.chmod(r / "bin" / "claim-gate", 0o755)
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "falsifier@estate.local")
    _git(r, "config", "user.name", "falsifier")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "README.md").write_text("base\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    _git(
        r,
        "update-ref",
        "refs/remotes/origin/main",
        _git(r, "rev-parse", "main").strip(),
    )
    return r


def _run_gate(repo: Path) -> tuple[int, str]:
    """Run the shipped gate over origin/main..HEAD. A crash is BLIND, never a pass."""
    try:
        p = subprocess.run(
            [sys.executable, str(repo / "bin" / "claim-gate"), "origin/main", "HEAD"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except (OSError, subprocess.SubprocessError) as exc:  # BLIND, never "fired"
        print(f"BLIND: {exc}", file=sys.stderr)
        return EXIT_BLIND, str(exc)
    return p.returncode, p.stdout + p.stderr


def test_a_lane_riding_a_peers_branch_names_two_instructions_and_is_not_accepted(
    repo: Path,
):
    _git(repo, "checkout", "-qb", "peer")
    _commit(repo, "peer.txt", INS_THEIRS)
    _git(repo, "checkout", "-qb", "mine", "peer")
    _commit(repo, "mine.txt", INS_MINE)

    rc, out = _run_gate(repo)

    assert rc != 0 or "instruction" not in out.lower(), (
        "DBG-034 FIRES: a lane naming two instruction ids was ACCEPTED\n" + out
    )


def test_a_lane_carrying_only_my_commit_is_never_refused_for_several_instructions(
    repo: Path,
):
    _git(repo, "checkout", "-qb", "mine", "main")
    _commit(repo, "mine.txt", INS_MINE)

    rc, out = _run_gate(repo)

    assert rc != EXIT_BLIND, "BLIND: the gate could not run at all\n" + out
    assert "instruction" not in out.lower() or "one instruction" not in out.lower(), (
        "a single-instruction lane was refused for carrying several\n" + out
    )
