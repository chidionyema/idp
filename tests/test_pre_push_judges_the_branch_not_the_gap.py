"""The pre-push ruff rung must judge the files a branch CHANGED, not everything main moved.

Measured 2026-11-11, lane/chronos-clock-recovery-20261111. The lane was rebuilt on the current
origin/main and force-pushed over its own earlier head. The hook computed

    from="$remote_sha"            # the OLD lane head
    git diff --name-only "$from" "$local_sha"

so the diff spanned every commit that had landed on main between the old head and the rebuild,
and the rung graded 15 Python files where the agent had touched 2. One of the 15 was a peer's
bin/idp-agent-base-apply.py, refused for S603/S607 the lane never wrote. The push was blocked
for work the branch did not contain.

That is AGENTS.md section 9 R14: a guard that refuses the estate's own scripts taxes every
agent. The fix is not to weaken the check -- every file the branch introduces or modifies is
still graded -- it is to widen what the hook RECOGNISES as the branch's own work: its diff from
the merge-base with main, which is the same base the new-branch case already used.

This test reads the decision out of .githooks/pre-push (never inlining it) and then EXECUTES the
hook's own expression against a real repository, so reformatting the script cannot make the test
pass by accident and the test cannot pass on a hook that still grades the gap.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".githooks" / "pre-push"


def _hook_text() -> str:
    assert HOOK.is_file(), f"LOAD FAILURE: {HOOK} does not exist"
    text = HOOK.read_text(encoding="utf-8")
    assert text.strip(), f"LOAD FAILURE: {HOOK} is empty"
    return text


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _commit(repo: Path, path: str, body: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Path | str]:
    """A main that moves after a lane forks, exactly the shape that bit the lane.

    origin/main gains a peer file the lane never touched; the lane carries one file of its own.
    """
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "-q", "--bare")

    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _commit(work, "base.txt", "base\n", "base")
    _git(work, "remote", "add", "origin", str(origin))
    _git(work, "push", "-q", "origin", "HEAD:refs/heads/main")

    # The lane forks here.
    base = _git(work, "rev-parse", "HEAD")
    _git(work, "checkout", "-q", "-b", "lane")
    lane_commit = _commit(work, "mine.py", "print('mine')\n", "the lane's own work")

    # Main moves on: a peer lands a file the lane never touched, and it reaches origin --
    # origin/main is the ref the hook judges against, so it must be current for the fixture to
    # be faithful to the push the lane actually made.
    _git(work, "checkout", "-q", "main")
    _commit(work, "peer.py", "print('peer')\n", "peer lands on main")
    _git(work, "push", "-q", "origin", "main:refs/heads/main")
    _git(work, "fetch", "-q", "origin")
    main_after_peer = _git(work, "rev-parse", "HEAD")

    # The lane REBUILDS on current main. Its new head sits on top of the peer commit, and the
    # OLD lane head is an ancestor-shaped sibling -- so `old_lane..new` spans everything main
    # moved after the lane forked, which is the peer's file. This is the measured defect.
    _git(work, "checkout", "-q", "-b", "rebuilt", main_after_peer)
    _git(work, "cherry-pick", "-x", lane_commit)
    rebuilt = _git(work, "rev-parse", "HEAD")

    return {
        "work": work,
        "base": base,
        "lane_head": lane_commit,
        "rebuilt": rebuilt,
        "main": _git(work, "rev-parse", "origin/main"),
    }


def test_the_hook_derives_from_the_merge_base_not_the_remote_sha() -> None:
    """The decision, read out of the shipped hook."""
    text = _hook_text()
    # The line that sets `from` must consult the merge-base and must not be a bare remote_sha.
    assignments = [ln.strip() for ln in text.splitlines() if re.match(r"^\s*from=", ln)]
    assert assignments, "the hook no longer sets `from`; this test cannot judge it -- refuse"
    joined = "\n".join(assignments)
    assert "merge-base origin/main" in joined, (
        "the hook sets `from` without a merge-base with main, so a rebuilt lane is graded "
        f"across everything main moved: {joined!r}"
    )


def _hook_from_expr(repo: Path, local_sha: str, remote_sha: str) -> str:
    """Build the `from` the HOOK would compute, by running its own lines.

    The two lines are extracted from .githooks/pre-push, so a mutant that reverts the hook's
    expression makes this test fail. Hardcoding the expression here would let the hook rot.
    """
    text = _hook_text()
    lines = [
        ln for ln in text.splitlines() if ln.strip().startswith(('from="', '[ -z "$from" ]'))
    ]
    assert lines, "the hook no longer assigns `from`; cannot judge it"
    script = (
        'local_sha="$1"\nremote_sha="$2"\n'
        + "\n".join(ln.replace("$(git ", f"$(git -C '{repo}' ") for ln in lines)
        + '\nprintf %s "$from"\n'
    )
    result = subprocess.run(
        ["bash", "-c", script, "_", local_sha, remote_sha],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"the hook's `from` lines failed: {result.stderr}"
    return result.stdout.strip()


def test_the_hooks_expression_judges_only_the_lane(world: dict[str, Path | str]) -> None:
    """EXECUTE the hook's own expression against the real repository."""
    work = world["work"]
    assert isinstance(work, Path)
    lane_head = str(world["lane_head"])
    rebuilt = str(world["rebuilt"])

    from_rebuilt = _hook_from_expr(work, rebuilt, lane_head)
    assert from_rebuilt, "the hook computed an empty `from`"
    judged = _git(
        work, "diff", "--name-only", "--diff-filter=ACMR", from_rebuilt, rebuilt
    ).splitlines()

    assert "mine.py" in judged, "the hook stopped judging the file the lane actually changed"
    assert "peer.py" not in judged, (
        "the hook judges a peer's file the lane never touched -- this is the defect: graded "
        f"{judged} (from={from_rebuilt})"
    )

    # And the mutant: the hook's OLD expression, which must FAIL this assertion.
    gap_judged = _git(
        work, "diff", "--name-only", "--diff-filter=ACMR", lane_head, rebuilt
    ).splitlines()
    assert "peer.py" in gap_judged, (
        "the fixture does not reproduce the defect, so this test cannot prove the fix: "
        f"from=remote_sha judged {gap_judged}"
    )


def test_the_merge_base_expression_is_still_exact_on_a_fresh_branch(
    world: dict[str, Path | str],
) -> None:
    """A brand-new branch (remote sha 0000) takes the same path and must not lose a file."""
    work = world["work"]
    assert isinstance(work, Path)
    rebuilt = str(world["rebuilt"])
    merge_base = _git(work, "merge-base", "origin/main", rebuilt)
    judged = _git(
        work, "diff", "--name-only", "--diff-filter=ACMR", merge_base, rebuilt
    ).splitlines()
    assert judged == ["mine.py"], f"a fresh branch must judge exactly its own file, got {judged}"


def test_the_hook_still_runs_ruff_on_what_it_judges() -> None:
    """Widening `from` must not have dropped the check itself."""
    text = _hook_text()
    assert "ruff check" in text, "the ruff check left the hook; refusal became silence"
    assert "--select E9,F,B,S" in text, "the ruff selection was weakened"


def test_the_hook_remains_syntactically_valid() -> None:
    result = subprocess.run(
        ["bash", "-n", str(HOOK)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"pre-push no longer parses: {result.stderr}"
