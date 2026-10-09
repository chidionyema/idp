"""idp#5611: .githooks/pre-push runs claim-gate on a push to a lane, before it leaves the laptop.

PR #5606 was pushed by hand (git push + gh pr create, no lane-submit) with no Claim line and was
first refused in the merge queue, a batch later. These pushes are real: a bare origin, a clone
with the real hook, and bin/claim-gate stubbed so the proof costs no network.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-push"

STUB = """#!/bin/sh
echo "$GITHUB_REPOSITORY $1 $2" >> "$STUB_LOG"
case "$STUB_SAYS" in
  ok)    echo "ok    claim-gate  every change lands on a live claim"; exit 0 ;;
  fail)  echo "FAIL  claim-gate  no \\`Claim: <owner>/<repo>#<n>\\` line"; exit 1 ;;
  crash) echo "Traceback (most recent call last):"; echo "RuntimeError: gh: not logged in"; exit 1 ;;
esac
"""


def git(cwd: Path, *a: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


@pytest.fixture
def clone(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    hooks = work / ".hooks"
    hooks.mkdir()
    shutil.copy(HOOK, hooks / "pre-push")
    git(work, "config", "core.hooksPath", str(hooks))
    (work / "bin").mkdir()
    gate = work / "bin" / "claim-gate"
    gate.write_text(STUB)
    gate.chmod(0o755)
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt", "bin/claim-gate")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    (work / "b.txt").write_text("b\n")
    git(work, "add", "b.txt")
    git(work, "commit", "-q", "-m", "work")
    return work


def push(work: Path, branch: str, says: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_REPOSITORY"}
    env.update(STUB_SAYS=says, STUB_LOG=str(work.parent / "gate.log"))
    return git(work, "push", "origin", f"HEAD:{branch}", env=env, check=False)


def gate_calls(work: Path) -> list[str]:
    log = work.parent / "gate.log"
    return log.read_text().splitlines() if log.exists() else []


def test_a_lane_push_with_no_claim_is_refused_before_it_leaves(clone):
    p = push(clone, "lane/fix/no-claim", "fail")
    assert p.returncode != 0
    assert (
        "pre-push REFUSED: lane/fix/no-claim does not land on a live claim" in p.stderr
    )
    assert "FAIL  claim-gate  no `Claim:" in p.stderr
    assert git(clone, "ls-remote", "origin", "lane/fix/no-claim").stdout == ""


def test_the_gate_judges_the_lane_from_where_it_leaves_main(clone):
    push(clone, "lane/fix/judged", "ok")
    base = git(clone, "rev-parse", "origin/main").stdout.strip()
    head = git(clone, "rev-parse", "HEAD").stdout.strip()
    [call] = gate_calls(clone)
    repo, got_base, got_head = call.split()
    assert (got_base, got_head) == (base, head)
    assert (
        repo == f"{clone.parent.name}/origin"
    )  # owner/repo from the origin url, .git dropped


def test_a_lane_on_a_live_claim_goes_out(clone):
    p = push(clone, "lane/fix/claimed", "ok")
    assert p.returncode == 0, p.stderr
    assert git(clone, "ls-remote", "origin", "lane/fix/claimed").stdout


def test_a_branch_that_is_not_a_lane_is_not_judged(clone):
    p = push(clone, "scratch/try", "fail")
    assert p.returncode == 0, p.stderr
    assert gate_calls(clone) == []


def test_a_gate_that_cannot_judge_lets_the_push_through_blind(clone):
    p = push(clone, "lane/fix/offline", "crash")
    assert p.returncode == 0, p.stderr
    assert (
        "BLIND claim-gate could not judge lane/fix/offline: RuntimeError: gh: not logged in"
        in (p.stdout + p.stderr)
    )
