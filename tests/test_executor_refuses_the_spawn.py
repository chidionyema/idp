"""The executor door refuses the spawn, and NEVER refuses the read that proves it should.

These tests import the module's classifier and assert its verdict. That is deliberate: the
classifier is a pure function, so the test cannot pass by grepping prose while the door refuses
every command -- the failure mode AGENTS.md 3 and R2 name. Each test is written so that the WRONG
implementation (a fence that stops everything, or a fence that stops only the usual verbs) turns at
least one of them red.
"""

import importlib.util
import pathlib

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "estate_executor",
    pathlib.Path(__file__).resolve().parents[1]
    / "mcp"
    / "plugins"
    / "estate_executor.py",
)
assert _SPEC is not None and _SPEC.loader is not None
executor = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(executor)

# The three verdicts are exit codes, because a guard that reports only prose cannot be gated.
ALLOW = 0
BLIND = 2
REFUSED = 78


def test_the_exit_codes_are_the_ones_the_estate_already_uses() -> None:
    assert (executor._ZERO_ALLOW, executor._ZERO_BLIND, executor._ZERO_REFUSED) == (
        ALLOW,
        BLIND,
        REFUSED,
    ), (
        "the verdict codes must be the estate's existing allow/BLIND/EX_CONFIG, not new ones"
    )


@pytest.mark.parametrize(
    "command",
    [
        "git worktree add /tmp/x lane/y",
        "git clone https://github.com/chidionyema/idp /tmp/y",
        "npm install",
        "pnpm i",
        "yarn install",
        "cargo build --release",
        "docker build -t x .",
    ],
)
def test_it_refuses_every_spawn_and_build_verb(command: str) -> None:
    verdict, why = executor._spawn_verdict(command)
    assert verdict == REFUSED, f"{command!r} was not refused: {why}"


@pytest.mark.parametrize(
    "command",
    [
        "df -m /",
        "du -sh ~/.estate",
        "git show origin/main:bin/idp-ci",
        "git -C /tmp/repo show HEAD:AGENTS.md",
        "git cat-file --batch",
        'rg -n "git worktree add" docs/',
        "git status --short",
        "git worktree list",
        "cat AGENTS.md",
        "vm_stat",
    ],
)
def test_it_allows_every_read_only_probe(command: str) -> None:
    """A read is never refused. Refusing it is what made the disk guardians a liability (#7914)."""
    verdict, why = executor._spawn_verdict(command)
    assert verdict == ALLOW, f"a read was refused: {command!r}: {why}"


def test_a_search_for_a_spawn_verb_is_not_a_spawn() -> None:
    """`rg "git worktree add"` reads. A substring test would refuse it, which is R38 exactly."""
    verdict, _ = executor._spawn_verdict('rg -n "git worktree add" docs/')
    assert verdict == ALLOW


@pytest.mark.parametrize(
    "command",
    [
        "bin/lane-where lane/x",
        "git push origin HEAD:refs/heads/lane/x",
        "git commit -m msg",
        "estate-execute ci.status",
        "python3 bin/idp-ci",
    ],
)
def test_an_ordinary_estate_verb_is_not_a_proven_spawn(command: str) -> None:
    """The door must not blanket-refuse the estate's own verbs: that is how a guard becomes a
    liability (R38). It answers BLIND -- "I did not prove this reads, and I did not prove it
    spawns" -- which is honest, where ALLOW would be a guess and REFUSED would be an outage."""
    verdict, why = executor._spawn_verdict(command)
    assert verdict != REFUSED, (
        f"an ordinary verb was refused as a spawn: {command!r}: {why}"
    )


def test_an_unrecognised_command_is_allowed_at_the_door() -> None:
    """R38, MEASURED: the door must not refuse an unclassified command.

    Returning BLIND-as-refusal here turned 18 of tests/test_executor_mcp.py's 43 red, because
    `pytest -q`, `make`, `false` and `git status` are unclassified and they are the estate's actual
    work. The door refuses the spawn it can PROVE; `bin/estate-zero-worktree` refuses the rest, on a
    narrower question, where a blanket BLIND is safe.
    """
    verdict, _ = executor._spawn_verdict("bin/greenlane-lane build --all")
    assert verdict == ALLOW, (
        "the door refused an unclassified command; that is the outage this test exists to prevent"
    )


def test_an_empty_command_is_blind_and_never_allowed() -> None:
    for blank in ("", "   ", "\n"):
        verdict, _ = executor._spawn_verdict(blank)
        assert verdict == BLIND, (
            f"an empty command was {verdict}, not BLIND -- unknown is never a pass"
        )


def test_the_cap_is_four_because_the_measured_failure_was_fourteen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ESTATE_MAX_LOCAL_WORKTREES", raising=False)
    assert executor._worktree_cap() == 4
    monkeypatch.setenv("ESTATE_MAX_LOCAL_WORKTREES", "99")
    assert executor._worktree_cap() == 99
    monkeypatch.setenv("ESTATE_MAX_LOCAL_WORKTREES", "not-a-number")
    assert executor._worktree_cap() == 4, (
        "a bad override must fall back to the cap, not to no cap"
    )


def test_an_unmeasurable_worktree_count_is_none_not_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R1: a count that cannot be read is BLIND. Zero would read as a clean estate."""
    import subprocess

    def _explode(*_a, **_k):
        raise OSError("git is not on this machine")

    monkeypatch.setattr(subprocess, "run", _explode)
    assert executor._worktree_count() is None, (
        "an unmeasurable worktree count returned a number; an unreadable machine must read as BLIND"
    )
