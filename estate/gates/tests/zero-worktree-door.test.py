#!/usr/bin/env python3
"""zero-worktree-door.test.py -- the shell door refuses a local checkout, and can be seen to fail.

WHY. The founder's order of 2026-11-11 ("the MacBook is a stateless thin client") is judged by
bin/estate-zero-worktree, but on 2026-11-28 nothing on an agent's path asked it: the wiring lived
in mcp/plugins/estate_executor.py, whose diff runtime-sync discarded, and the shell door
(estate/gates/shell-guard.sh) judged kills only. This test runs the REAL door and the REAL judge
against a decoy `git` that records its argv and builds nothing, so it can never make a checkout.

  refuse     worktree add, -C worktree add, clone         -> rc != 0, the decoy never sees them
  allow      status, worktree list, -C log                -> rc == 0, the decoy sees them
  fail-open  judge missing, judge crashes (rc 3)          -> the real command runs (door policy)
  falsifier  the door as it was before (kills only)       -> the decoy DOES see the spawn

  python3 estate/gates/tests/zero-worktree-door.test.py            run the tests
  python3 estate/gates/tests/zero-worktree-door.test.py --optimus [--source PATH]
      prints optimus.thin_client.unguarded_worktree_spawn=1|0 : 1 when any spawn-shaped git
      command reaches git through the door at PATH (default: the tracked door).
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DOOR = ROOT / "estate" / "gates" / "shell-guard.sh"
OLD_DOOR = HERE / "fixtures" / "shell-guard-kills-only.sh"
JUDGE = ROOT / "bin" / "estate-zero-worktree"

SPAWNS = (
    ("worktree", "add", "/nonexistent/w"),
    ("-C", ".", "worktree", "add", "/nonexistent/w"),
    ("clone", "https://example.invalid/r.git", "/nonexistent/c"),
)
READS = (("status", "--short"), ("worktree", "list"), ("-C", ".", "log", "-1"))


def _decoy(tmp: Path) -> Path:
    bindir = tmp / "bin"
    bindir.mkdir()
    git = bindir / "git"
    git.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DECOY_LOG"\nexit 0\n')
    git.chmod(git.stat().st_mode | stat.S_IXUSR)
    return bindir


def _run(shell, door, argv, judge=None):
    """Run `git ARGV` through DOOR in SHELL with a decoy git. Returns (rc, [decoy argv lines])."""
    tmp = Path(tempfile.mkdtemp(prefix="zwdoor-"))
    try:
        bindir = _decoy(tmp)
        log = tmp / "log"
        log.write_text("")
        env = {
            "PATH": "%s:/usr/bin:/bin" % bindir,
            "HOME": str(tmp),
            "DECOY_LOG": str(log),
            "ESTATE_ZERO_WORKTREE": str(judge if judge is not None else JUDGE),
        }
        quoted = " ".join("'%s'" % a for a in argv)
        p = subprocess.run(
            [shell, "-c", ". '%s'; git %s" % (door, quoted)],
            env=env, capture_output=True, text=True, timeout=60,
        )
        return p.returncode, log.read_text().splitlines()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _spawn_lines(lines):
    return [x for x in lines if x.startswith("worktree add") or " worktree add " in x or x.startswith("clone")]


def spawn_reaches_git(door, shell="bash"):
    """1 when any spawn-shaped git command gets through DOOR to git, else 0."""
    for argv in SPAWNS:
        _rc, lines = _run(shell, door, argv)
        if _spawn_lines(lines):
            return 1
    return 0


SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]


class ZeroWorktreeDoor(unittest.TestCase):
    def test_spawns_are_refused_and_never_reach_git(self):
        for shell in SHELLS:
            for argv in SPAWNS:
                rc, lines = _run(shell, DOOR, argv)
                self.assertNotEqual(rc, 0, (shell, argv))
                self.assertEqual(_spawn_lines(lines), [], (shell, argv))

    def test_ordinary_git_runs(self):
        for shell in SHELLS:
            for argv in READS:
                rc, lines = _run(shell, DOOR, argv)
                self.assertEqual(rc, 0, (shell, argv))
                self.assertIn(" ".join(argv), lines, (shell, argv))

    def test_a_missing_judge_does_not_stop_the_shell(self):
        rc, lines = _run("bash", DOOR, SPAWNS[0], judge=Path("/nonexistent/judge"))
        self.assertEqual(rc, 0)
        self.assertTrue(_spawn_lines(lines))

    def test_a_crashing_judge_does_not_stop_the_shell(self):
        tmp = Path(tempfile.mkdtemp(prefix="zwjudge-"))
        try:
            crash = tmp / "judge"
            crash.write_text("import sys\nsys.exit(3)\n")
            rc, lines = _run("bash", DOOR, SPAWNS[0], judge=crash)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(rc, 0)
        self.assertTrue(_spawn_lines(lines))

    def test_falsifier_the_door_before_the_fix_lets_every_spawn_through(self):
        for argv in SPAWNS:
            rc, lines = _run("bash", OLD_DOOR, argv)
            self.assertEqual(rc, 0, argv)
            self.assertTrue(_spawn_lines(lines), argv)
        self.assertEqual(spawn_reaches_git(OLD_DOOR), 1)
        self.assertEqual(spawn_reaches_git(DOOR), 0)


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        src = DOOR
        if "--source" in sys.argv:
            src = Path(sys.argv[sys.argv.index("--source") + 1]).resolve()
        print("optimus.thin_client.unguarded_worktree_spawn=%d" % spawn_reaches_git(src))
        sys.exit(0)
    unittest.main(argv=[sys.argv[0]])
