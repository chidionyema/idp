"""bin/idp-backstage-tsc answers clean, red or blind -- never "skipped".

2026-09-27: PR #4467 changed .tsx and no compiler read it; every local layer skipped tsc in a
worktree with no node_modules. These run the real script against throwaway repositories with a
stand-in tsc, so they execute in a second and need no yarn install.
"""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-backstage-tsc"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def repo(tmp_path, name):
    r = tmp_path / name
    (r / "backstage").mkdir(parents=True)
    git(r, "init", "-q")
    (r / "backstage" / "README").write_text("x")
    git(r, "add", ".")
    git(r, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
    return r


def fake_tsc(checkout, exit_code):
    bin_dir = checkout / "backstage" / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    tsc = bin_dir / "tsc"
    tsc.write_text(f"#!/bin/sh\necho ran-in-$(pwd)\nexit {exit_code}\n")
    tsc.chmod(0o755)


def run(cwd):
    return subprocess.run(
        [str(SCRIPT)], cwd=cwd, capture_output=True, text=True, env=os.environ
    )


def test_no_compiler_anywhere_is_blind_not_a_skip(tmp_path):
    r = repo(tmp_path, "main")
    out = run(r)
    assert out.returncode == 3, out
    assert "BLIND" in out.stderr


def test_worktree_borrows_main_node_modules_and_removes_the_link(tmp_path):
    main = repo(tmp_path, "main")
    fake_tsc(main, 0)
    wt = tmp_path / "wt"
    git(main, "worktree", "add", "-q", str(wt))
    out = run(wt)
    assert out.returncode == 0, out
    assert "borrowing node_modules" in out.stderr
    assert not (wt / "backstage" / "node_modules").exists()


def test_red_types_are_red(tmp_path):
    r = repo(tmp_path, "main")
    fake_tsc(r, 2)
    assert run(r).returncode == 2
