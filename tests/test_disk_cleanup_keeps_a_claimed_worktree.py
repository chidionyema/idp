#!/usr/bin/env python3
"""A worktree a live claim covers is never removed by the disk cleaner.

WHY. Measured 2026-10-24: the governed disk-cleanup intent (worktrees=true) removed a live
agent's worktree at ~/.estate/worktrees/deps-zod-mlflow while that agent was working in it. The
checkout is disposable -- the branch and its commits live in the shared repository -- so the
cleaner judged it settled and took it, and the agent's working directory vanished under it: every
job it then ran failed. The cleaner asks git; a claim is a GitHub comment with a heartbeat. The
estate's own focus register is what bridges the two (platform/estate/memory/focus.py writes
~/.estate/memory/focus-register.json), and the `Claim: owner/repo#N` trailer bin/claim-open
stamps into a commit names the claim a branch belongs to.

So: a worktree whose branch carries a Claim: trailer naming a live claim is kept, with the
reason printed, whatever the idle clock says -- and a worktree no live claim covers is still
removed. Both halves are proved here, because a cleaner that keeps everything is not a fix.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "estate"
    / "libexec"
    / "disk-cleanup.sh"
)
CLAIM = 4242


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp_path: Path) -> tuple[Path, Path, dict, Path]:
    """A fake HOME with a repo, a claimed worktree and an unclaimed one."""
    home = tmp_path / "home"
    repo = home / "Documents/code/repo"
    repo.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=repo)
    _git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "base",
        cwd=repo,
    )
    wts = {}
    for name in ("claimed", "unclaimed"):
        wt = home / "wt" / name
        _git("worktree", "add", "-q", "-b", name, str(wt), cwd=repo)
        wts[name] = wt
    # The claim: the branch's tip commit carries the trailer bin/claim-open stamps.
    _git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        f"work\n\nClaim: chidionyema/idp#{CLAIM}\nAgent: pi",
        cwd=wts["claimed"],
    )
    register = tmp_path / "focus-register.json"
    register.write_text(
        json.dumps(
            {
                "at": 0,
                "rows": [
                    {
                        "claim": f"idp#{CLAIM}",
                        "title": "the work the agent is doing",
                        "agent": "pi",
                        "live": True,
                        "heartbeat_age_s": 30,
                    }
                ],
            }
        )
    )
    return home, repo, wts, register


def _run(home: Path, repo: Path, register: Path) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "none"),
        "DISK_CLEANUP_WT_REPOS": str(repo),
        "DISK_CLEANUP_WT_IDLE_MIN": "0",
        "DISK_CLEANUP_WT_FRESH_MIN": "0",
        "DISK_CLEANUP_PHASES": "worktrees",
        "DISK_CLEANUP_TMP_ROOT": "",
        "DISK_CLEANUP_SYSTEM_SPOTS": "",
        "CLAIM_REGISTER": str(register),
    }
    return subprocess.run(
        ["bash", str(SCRIPT), "true", "false", "0", "true"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_claimed_worktree_is_kept_and_an_unclaimed_one_is_still_removed(tmp_path):
    home, repo, wts, register = _repo(tmp_path)
    r = _run(home, repo, register)
    assert r.returncode == 0, r.stdout + r.stderr
    # the claim is printed, with the reason
    assert f"idp#{CLAIM}" in r.stdout, r.stdout
    assert "claimed by pi" in r.stdout, r.stdout
    # the claimed worktree survives
    assert wts["claimed"].exists(), "the cleaner removed a live agent's worktree"
    # and the unclaimed one is still removed -- a cleaner that keeps everything is not a fix
    assert not wts["unclaimed"].exists(), (
        "the cleaner kept an unclaimed, settled worktree"
    )


def test_without_a_live_claim_the_worktree_is_removed(tmp_path):
    """The same worktree, with the claim no longer live: it is settled and goes."""
    home, repo, wts, register = _repo(tmp_path)
    register.write_text(json.dumps({"at": 0, "rows": []}))
    r = _run(home, repo, register)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not wts["claimed"].exists(), "a lapsed claim still pins the worktree"
