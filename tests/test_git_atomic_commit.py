"""Commit without a checkout, so a peer's branch switch cannot destroy the work (#7918).

Measured 2026-11-11: uncommitted work in the shared idp checkout was discarded TWICE when a peer's
branch operation moved HEAD underneath it. The only defence agents had was a /tmp worktree, which
costs ~294 MB and gets reaped under disk pressure -- so the work was lost either way.

A commit is a tree plus a ref. This grades the shipped door: it must build the commit from blobs,
leave HEAD and the working tree untouched, and refuse bad input instead of half-committing.
"""

import os
import subprocess
from pathlib import Path

# The door under test is the one that SHIPS WITH THIS TEST, not a checkout that happens to sit
# on the founder's laptop. A hardcoded path grades a stranger's tree on CI (where the path does
# not exist) and the founder's dirty tree locally (where it does, and may be mid-edit). A gate
# that asserts against the wrong repository is not a gate.
REPO = Path(__file__).resolve().parents[1]
DOOR = REPO / "bin" / "git-atomic-commit"


def _door():
    assert DOOR.is_file(), f"the atomic-commit door is missing at {DOOR}"
    return DOOR


def _run(args, cwd, env=None):
    return subprocess.run(
        args, cwd=str(cwd), capture_output=True, text=True, timeout=90, env=env
    )


def _scratch_repo(tmp_path):
    """A throwaway repo with one commit, so the test never touches the estate's checkout."""
    r = tmp_path / "repo"
    r.mkdir()
    g = lambda *a: _run(["git", *a], cwd=r)  # noqa: E731
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "T")
    (r / "existing.txt").write_text("hello\n")
    g("add", "existing.txt")
    g("commit", "-q", "-m", "init")
    return r


def test_the_door_exists_and_is_executable():
    assert os.access(_door(), os.X_OK), f"{DOOR} is not executable"


def test_commits_without_moving_head_or_writing_the_tree(tmp_path):
    r = _scratch_repo(tmp_path)
    head_before = _run(["git", "rev-parse", "HEAD"], r).stdout.strip()

    src = tmp_path / "newfile.txt"
    src.write_text("from the door\n")
    msg = tmp_path / "msg.txt"
    msg.write_text("feat: added by the atomic door\n")

    out = _run(
        ["bash", str(_door()), str(r), "lane/x", str(msg), f"newfile.txt:{src}"], r
    )
    assert out.returncode == 0, f"door failed: {out.stderr[-800:]}"

    # HEAD is exactly where it was: no checkout happened.
    assert _run(["git", "rev-parse", "HEAD"], r).stdout.strip() == head_before, (
        "HEAD MOVED"
    )
    # The working tree has no new file: the commit was built from blobs, not staged from disk.
    assert not (r / "newfile.txt").exists(), "the door wrote into the working tree"
    # But the branch really does contain the file.
    show = _run(["git", "show", "lane/x:newfile.txt"], r)
    assert show.returncode == 0 and "from the door" in show.stdout


def test_the_commit_preserves_the_parent_history(tmp_path):
    r = _scratch_repo(tmp_path)
    src = tmp_path / "f.txt"
    src.write_text("x\n")
    msg = tmp_path / "m.txt"
    msg.write_text("feat: one\n")
    _run(["bash", str(_door()), str(r), "lane/y", str(msg), f"f.txt:{src}"], r)

    parents = _run(
        ["git", "rev-list", "--parents", "-n", "1", "lane/y"], r
    ).stdout.split()
    assert len(parents) == 2, "the new commit is not attached to a parent"
    assert not (r / "f.txt").exists(), "working tree was written"


def test_refuses_a_missing_source_file(tmp_path):
    r = _scratch_repo(tmp_path)
    msg = tmp_path / "m.txt"
    msg.write_text("feat: nope\n")
    before = _run(["git", "rev-parse", "--all"], r).stdout
    out = _run(
        [
            "bash",
            str(_door()),
            str(r),
            "lane/z",
            str(msg),
            f"f.txt:{tmp_path}/does-not-exist",
        ],
        r,
    )
    assert out.returncode != 0, "the door committed a file that does not exist"
    assert _run(["git", "rev-parse", "--all"], r).stdout == before, (
        "the door created a ref anyway"
    )


def test_refuses_an_empty_message(tmp_path):
    r = _scratch_repo(tmp_path)
    src = tmp_path / "f.txt"
    src.write_text("x\n")
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    out = _run(["bash", str(_door()), str(r), "lane/z", str(empty), f"f.txt:{src}"], r)
    assert out.returncode != 0, "the door made a commit with no message"


def test_refuses_a_malformed_pair(tmp_path):
    r = _scratch_repo(tmp_path)
    msg = tmp_path / "m.txt"
    msg.write_text("feat: x\n")
    out = _run(["bash", str(_door()), str(r), "lane/z", str(msg), "no-colon-here"], r)
    assert out.returncode != 0, "the door accepted a pair with no source file"


def test_the_shared_index_is_never_touched(tmp_path):
    """The whole point: a peer's staged files must not enter, and ours must not leak out."""
    r = _scratch_repo(tmp_path)
    peer = r / "peer.txt"
    peer.write_text("peer staged this\n")
    _run(["git", "add", "peer.txt"], r)  # peer's staged, uncommitted work

    src = tmp_path / "mine.txt"
    src.write_text("mine\n")
    msg = tmp_path / "m.txt"
    msg.write_text("feat: mine\n")
    _run(["bash", str(_door()), str(r), "lane/mine", str(msg), f"mine.txt:{src}"], r)

    staged = _run(["git", "diff", "--cached", "--name-only"], r).stdout
    assert "peer.txt" in staged, "the door consumed the peer's staged file"
    assert "mine.txt" not in staged, "the door leaked its file into the shared index"


def test_it_never_runs_git_checkout():
    """A checkout is the operation that destroys a peer's work -- the door must not contain one.

    Scoped to COMMAND POSITION. The door legitimately says "is not a git checkout" in its refusal
    prose, and a substring match on that phrase is a false positive that would force the message
    to be renamed instead of the behaviour to be checked -- the estate's rule that a guard firing
    on prose teaches the wrong lesson.
    """
    src = _door().read_text()
    body = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    commands = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip().startswith("git ") or "| git " in ln or "$(git " in ln
    ]
    for ln in commands:
        for forbidden in ("git checkout", "git reset", "git switch", "git add -A"):
            assert forbidden not in ln, f"the door runs `{forbidden}`: {ln}"
    assert commands, (
        "no git commands found -- the scan could not look, so it proves nothing"
    )
