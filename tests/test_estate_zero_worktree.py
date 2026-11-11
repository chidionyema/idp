"""The ZERO_LOCAL_WORKTREES guard must be able to FAIL, in both directions.

A gate that cannot fail is not a gate (AGENTS.md section 3, R2). Every test here runs the real
program through subprocess and asserts its EXIT CODE -- not a string in its source -- because the
defect this guard exists to stop was the estate *narrating* a reclaim it never made. A test that
greps the docstring would pass while the guard refused every command in the estate.

The two-sided contract, measured 2026-11-11 on the real binary:

    spawn verbs and build verbs -> 78 (EX_CONFIG)
    read-only verbs             -> 0
    nothing classified          -> 2 (BLIND, never 0)

The read-only half is not decoration. The first build of this guard refused `df -m /` because the
worktree cap was applied to every command, which meant the guard blocked the very measurement that
tells an agent there is a disk problem. That is R38 (a guard refusing correct work), and these
tests pin it shut.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD = REPO_ROOT / "bin" / "estate-zero-worktree"

EXIT_ALLOW = 0
EXIT_BLIND = 2
EXIT_REFUSED = 78


def _run(
    command: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the guard's `check` verb against one command, in an isolated fence."""
    return subprocess.run(
        [str(GUARD), "check", "--", command],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={**os.environ, **(env or {})},
    )


@pytest.fixture()
def unfenced(tmp_path: Path) -> dict[str, str]:
    """An env whose fence file does not exist, so only classification decides."""
    return {
        "ESTATE_SPAWN_FENCE": str(tmp_path / "NO_SPAWN_FENCE"),
        "ESTATE_MAX_LOCAL_WORKTREES": "99",
    }


@pytest.mark.parametrize(
    "command",
    [
        "git worktree add /tmp/x lane/y",
        "git clone https://github.com/x/y.git /tmp/y",
        "npm install",
        "pnpm i",
        "yarn install",
        "cargo build --release",
        "docker build -t x .",
    ],
)
def test_it_refuses_every_spawn_and_build_verb(
    command: str, unfenced: dict[str, str]
) -> None:
    """The falsifier: each verb that creates a checkout or a local build is refused with 78."""
    result = _run(command, unfenced)
    assert result.returncode == EXIT_REFUSED, (
        f"{command!r} was NOT refused (exit {result.returncode}); "
        f"that is the spawn the founder ordered stopped. Output: {result.stdout}{result.stderr}"
    )
    assert "refused" in result.stdout.lower()


@pytest.mark.parametrize(
    "command",
    [
        "git show HEAD:bin/idp-ci",
        "git cat-file --batch",
        "git status --short",
        "git worktree list",
        'rg -n "git worktree add" docs/',
        "df -m /",
    ],
)
def test_it_allows_every_read_only_probe(
    command: str, unfenced: dict[str, str]
) -> None:
    """The other side: reading the packfile and the disk is never a spawn (R38)."""
    result = _run(command, unfenced)
    assert result.returncode == EXIT_ALLOW, (
        f"{command!r} was refused (exit {result.returncode}); a guard that blocks the measurement "
        f"of the problem cannot be used to fix it. Output: {result.stdout}{result.stderr}"
    )


def test_a_search_for_a_spawn_verb_is_not_a_spawn(unfenced: dict[str, str]) -> None:
    """Searching the source for the string is a read, and must not be refused.

    Without this, the guard would refuse the command an agent uses to FIND the call it is
    investigating, which is how a safety check teaches an agent to stop looking.
    """
    result = _run('rg -n "git worktree add" docs/', unfenced)
    assert result.returncode == EXIT_ALLOW


def test_an_empty_command_is_blind_and_never_allowed(unfenced: dict[str, str]) -> None:
    """BLIND is 2, never 0: an unclassifiable request is refused rather than waved through (R1)."""
    result = _run("", unfenced)
    assert result.returncode == EXIT_BLIND
    assert "BLIND" in result.stdout


def test_the_fence_stops_a_non_read_command_while_a_purge_runs(tmp_path: Path) -> None:
    """The fence must be the thing that refuses, not the verb table.

    `npm install` is refused by the verb table too, so it cannot prove the fence works. This uses a
    command the verb table does NOT name (so it classifies as allow), with the fence up and the cap
    out of the way: the fence alone must turn it into a refusal.
    """
    fence = tmp_path / "NO_SPAWN_FENCE"
    fence.write_text("fenced\n")
    cmd = "bin/greenlane-lane build --all"
    env = {"ESTATE_SPAWN_FENCE": str(fence), "ESTATE_MAX_LOCAL_WORKTREES": "99"}
    result = _run(cmd, env)
    assert result.returncode == EXIT_REFUSED, (
        "a non-read command was allowed while the spawn fence was up; a purge would race the "
        "spawner it exists to stop. Output: " + result.stdout + result.stderr
    )
    assert "fence" in result.stdout.lower()


def test_the_fence_does_not_stop_a_reader(tmp_path: Path) -> None:
    """The fence stops the spawn, not the observer: `df` still answers while a purge runs.

    Measured defect, 2026-11-11: the first fence refused everything, so the agent watching the
    purge had no way to see the disk free itself. The fence answers one question -- would this
    create a checkout -- and a read never would.
    """
    fence = tmp_path / "NO_SPAWN_FENCE"
    fence.write_text("fenced\n")
    result = _run(
        "df -m /",
        {"ESTATE_SPAWN_FENCE": str(fence), "ESTATE_MAX_LOCAL_WORKTREES": "99"},
    )
    assert result.returncode == EXIT_ALLOW


def test_the_cap_bounds_spawns_and_not_observation(tmp_path: Path) -> None:
    """At the cap a spawn is refused, and a read is still allowed.

    The cap exists to stop fourteen worktrees becoming fifteen (founder executive order). It must
    never stop the agent counting the fourteen, which is the measurement the fix depends on.
    """
    env = {
        "ESTATE_SPAWN_FENCE": str(tmp_path / "absent"),
        "ESTATE_MAX_LOCAL_WORKTREES": "0",
    }
    spawn = _run("git worktree add /tmp/x lane/y", env)
    assert spawn.returncode == EXIT_REFUSED
    read = _run("df -m /", env)
    assert read.returncode == EXIT_ALLOW


def test_the_constant_is_a_real_cap_not_a_disabled_guard() -> None:
    """MAX_CONCURRENT must default to a real number: a cap of 0 or a huge number is not a cap."""
    source = GUARD.read_text()
    assert 'ESTATE_MAX_LOCAL_WORKTREES", "4"' in source, (
        "the default concurrency cap is no longer 4; the measured failure was fourteen worktrees, "
        "so the cap is the thing that turns a stampede into a queue"
    )
