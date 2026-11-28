"""landed-worktrees.py reaps a worktree only when it is landed, clean, unlocked and idle.

Each case builds a real throwaway repo with a real origin/main, so the verdicts are git's own.
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "platform/estate/libexec/landed-worktrees.py"
)
# A clean git: the developer's global core.hooksPath (an agent gate) must not run inside a throwaway repo.
ENV = {
    **{k: v for k, v in os.environ.items() if k != "BASH_ENV"},
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "CLAIM_REGISTER": "/nonexistent",
}


def git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
        env=ENV,
    ).stdout


def run(repo, *flags):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(repo), *flags],
        capture_output=True,
        text=True,
        env=ENV,
        check=False,
    )


def publish(repo):
    """Stand in for `git push origin main`: origin/main now points at local main."""
    git(repo, "update-ref", "refs/remotes/origin/main", "main")


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, env=ENV)
    (repo / "a.txt").write_text("a")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-q", "-m", "base")
    publish(repo)
    return repo


def add_worktree(repo, tmp_path, name, *, landed):
    path = tmp_path / name
    git(repo, "worktree", "add", "-q", "-b", name, str(path))
    (path / f"{name}.txt").write_text(name)
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", name)
    if landed:
        git(repo, "merge", "-q", "--no-edit", name)
        publish(repo)
    return path


def test_a_landed_clean_idle_worktree_is_reaped_and_only_that_one(tmp_path):
    repo = make_repo(tmp_path)
    gone = add_worktree(repo, tmp_path, "gone", landed=True)
    live = add_worktree(repo, tmp_path, "live", landed=False)
    out = run(repo, "--remove", "--min-idle-min", "0")
    assert out.returncode == 0, out.stdout + out.stderr
    assert f"removed  {gone}" in out.stdout
    assert not gone.exists()
    assert f"keep     {live}" in out.stdout and "NOT landed" in out.stdout
    assert live.exists()


def test_the_default_only_reports(tmp_path):
    repo = make_repo(tmp_path)
    gone = add_worktree(repo, tmp_path, "gone", landed=True)
    out = run(repo, "--min-idle-min", "0")
    assert f"would    remove {gone}" in out.stdout
    assert gone.exists()


def test_uncommitted_or_untracked_bytes_keep_a_landed_worktree(tmp_path):
    repo = make_repo(tmp_path)
    dirty = add_worktree(repo, tmp_path, "dirty", landed=True)
    (dirty / "scratch.txt").write_text("someone's work")
    out = run(repo, "--remove", "--min-idle-min", "0")
    assert dirty.exists()
    assert "not clean" in out.stdout


def test_a_locked_worktree_is_kept(tmp_path):
    repo = make_repo(tmp_path)
    locked = add_worktree(repo, tmp_path, "locked", landed=True)
    git(repo, "worktree", "lock", str(locked))
    out = run(repo, "--remove", "--min-idle-min", "0")
    assert locked.exists()
    assert "locked" in out.stdout


def test_a_fresh_worktree_is_not_waste_even_though_main_contains_it(tmp_path):
    repo = make_repo(tmp_path)
    fresh = add_worktree(repo, tmp_path, "fresh", landed=True)
    out = run(repo, "--remove")  # default idle window: 120 minutes
    assert fresh.exists()
    assert "idle" in out.stdout


def test_a_process_working_inside_it_keeps_it(tmp_path):
    repo = make_repo(tmp_path)
    busy = add_worktree(repo, tmp_path, "busy", landed=True)
    holder = subprocess.Popen(["sleep", "30"], cwd=busy)  # noqa: S603, S607
    try:
        out = run(repo, "--remove", "--min-idle-min", "0")
    finally:
        holder.kill()
        holder.wait()
    assert busy.exists()
    assert "a process is working inside it" in out.stdout


def test_a_live_claim_keeps_it(tmp_path):
    repo = make_repo(tmp_path)
    path = tmp_path / "claimed"
    git(repo, "worktree", "add", "-q", "-b", "claimed", str(path))
    (path / "c.txt").write_text("c")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "work\n\nClaim: o/r#42\nAgent: x")
    git(repo, "merge", "-q", "--no-edit", "claimed")
    publish(repo)
    register = tmp_path / "register.json"
    register.write_text('{"rows": [{"live": true, "claim": "o/r#42", "agent": "x"}]}')
    env = {**ENV, "CLAIM_REGISTER": str(register)}
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(repo), "--remove", "--min-idle-min", "0"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert path.exists()
    assert "a live claim covers it" in out.stdout


def test_an_unreadable_base_is_blind_not_clean(tmp_path):
    repo = make_repo(tmp_path)
    out = run(repo, "--base", "origin/nope")
    assert out.returncode == 2
    assert "BLIND" in out.stdout
