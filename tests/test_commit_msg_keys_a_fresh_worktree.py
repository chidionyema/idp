"""#5814: the first commit in a fresh `git worktree add` tree is signed, not refused.

A worktree's git dir is new, so it holds no idp-hook-secret, and .githooks/commit-msg refused every
commit there with "run bin/idp-install-hooks" -- twice in one session on 2026-10-14. The hook now
makes the key itself. These commit through the real hook in a real worktree.
"""

import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "commit-msg"


def git(cwd: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


def worktree(tmp_path: Path) -> Path:
    main = tmp_path / "main"
    git(tmp_path, "init", "-q", str(main))
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "commit-msg").write_bytes(HOOK.read_bytes())
    (hooks / "commit-msg").chmod(0o755)
    for k, v in [
        ("user.email", "t@t"),
        ("user.name", "t"),
        ("core.hooksPath", str(hooks)),
    ]:
        git(main, "config", k, v)
    (main / "a").write_text("a\n")
    git(main, "add", "a")
    assert git(main, "commit", "-q", "-m", "base").returncode == 0
    wt = tmp_path / "wt"
    git(main, "worktree", "add", "-q", "-b", "w", str(wt))
    return wt


def key(wt: Path) -> Path:
    return Path(
        git(
            wt, "rev-parse", "--path-format=absolute", "--git-path", "idp-hook-secret"
        ).stdout.strip()
    )


def test_the_first_commit_in_a_fresh_worktree_is_signed(tmp_path):
    wt = worktree(tmp_path)
    assert not key(wt).exists()
    (wt / "b").write_text("b\n")
    git(wt, "add", "b")
    done = git(wt, "commit", "-q", "-m", "first")
    assert done.returncode == 0, done.stderr
    signed = git(
        wt, "log", "-1", "--format=%(trailers:key=X-Idp-Signed,valueonly)"
    ).stdout
    assert signed.strip()


def test_the_key_it_makes_is_private_and_kept(tmp_path):
    wt = worktree(tmp_path)
    for name in ("b", "c"):
        (wt / name).write_text(name)
        git(wt, "add", name)
        git(wt, "commit", "-q", "-m", name)
        made = key(wt).read_text()
        assert stat.S_IMODE(key(wt).stat().st_mode) == 0o600
    # the second commit reused the first commit's key rather than minting another
    assert made == key(wt).read_text() and len(made.strip()) == 64
