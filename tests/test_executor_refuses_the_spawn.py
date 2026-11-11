"""The executor door refuses the spawn the thin-client layer proves, and never refuses a read.

These tests import the module and assert its VERDICT -- the classifier is a pure function of the
command and of the policy layer, so the test cannot pass by grepping prose while the door refuses
every command. Each test is written so that the WRONG implementation turns at least one of them
red: a door that grew a second table of forbidden shapes, a fence that stops everything, a fence
that stops only the usual verbs, or a cap that silently means "no cap".

THE DELEGATION IS ASSERTED, NOT DESCRIBED. The test replaces the policy layer with a stub that
RECORDS what it was asked and answers, and asserts the door asked it. A door that answered from a
table of its own would pass a test that only checked verdicts, and would drift from the layer
that owns the rule (AGENTS.md section 6: one of each layer).

THE POLICY LAYER IS platform/estate/governance/thin_client.py -- on main since #7911, with
falsifiers proved both ways, and with the platform pivot (in CI and on Linux a worktree IS the
isolation primitive, so the guard stands down there). It existed, proved, with NO CALLER: a guard
that cannot fire is not a guard, and that is the measured root cause of the worktree bomb.
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


@pytest.fixture
def darwin(monkeypatch: pytest.MonkeyPatch):
    """The door's policy layer, posed as it is on the founder's laptop.

    The posture is pinned here rather than inherited from the machine, so the same test is the
    same test on a laptop and on a CI runner -- where the layer stands down on purpose.
    """
    layer = executor._thin_client()
    assert layer is not None, (
        "the thin-client policy layer did not load; the door would have no rule to ask"
    )
    monkeypatch.setattr(layer, "applies", lambda: True)
    monkeypatch.setattr(layer, "fence_lifted", lambda: False)
    monkeypatch.delenv("ESTATE_MAX_LOCAL_WORKTREES", raising=False)
    return layer


@pytest.fixture
def stub_policy(monkeypatch: pytest.MonkeyPatch):
    """A policy layer that RECORDS the call and answers with a verdict of our choosing."""
    calls: list[tuple] = []

    class Stub:
        @staticmethod
        def creates_local_checkout(command: str) -> bool:
            calls.append(("shape", command))
            return "worktree" in command

        @staticmethod
        def spawn_verdict(command: str, count=None):
            calls.append(("verdict", command, count))
            return False, "stubbed refusal"

        @staticmethod
        def spawn_cap() -> int:
            return 0

    monkeypatch.setattr(executor, "_thin_client", lambda: Stub)
    return calls


def test_the_verdict_comes_from_the_layer_and_from_nowhere_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE FALSIFIER for "one of each layer".

    A layer that says ALLOW must make the door ALLOW. If the door also held a table of forbidden
    shapes of its own, this test would fail -- and that is the point: the second copy is exactly
    what drifted before, and it is what would refuse `git worktree add` in CI where a worktree IS
    the isolation primitive.
    """

    class Permissive:
        @staticmethod
        def creates_local_checkout(command: str) -> bool:
            return True

        @staticmethod
        def spawn_verdict(command: str, count=None):
            return True, "OK"

        @staticmethod
        def spawn_cap() -> int:
            return 0

    monkeypatch.setattr(executor, "_thin_client", lambda: Permissive)
    verdict, _ = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == ALLOW, (
        "the door refused a checkout the policy layer allowed; the door holds a second copy of "
        "the rule"
    )


def test_the_exit_codes_are_the_ones_the_estate_already_uses() -> None:
    assert (executor._ZERO_ALLOW, executor._ZERO_BLIND, executor._ZERO_REFUSED) == (
        ALLOW,
        BLIND,
        REFUSED,
    ), (
        "the verdict codes must be the estate's existing allow/BLIND/EX_CONFIG, not new ones"
    )


def test_the_door_asks_the_policy_layer_rather_than_holding_its_own_table(
    stub_policy: list[tuple],
) -> None:
    """The delegation itself, asserted as a CALL -- not as prose about a call."""
    verdict, why = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == REFUSED
    assert why == "stubbed refusal", (
        "the door did not use the layer's reason; a door that answers from its own table has a "
        "second copy of the policy"
    )
    shapes = [c for c in stub_policy if c[0] == "shape"]
    verdicts = [c for c in stub_policy if c[0] == "verdict"]
    assert shapes, "the door never asked the layer whether this creates a checkout"
    assert verdicts, "the door never asked the layer for a verdict"
    assert shapes[0][1] == "git worktree add /tmp/x"
    assert verdicts[0][1] == "git worktree add /tmp/x"


@pytest.mark.parametrize(
    "command",
    [
        "git worktree add /tmp/x lane/y",
        "cd /Users/x/code/idp && git worktree add ../wt",
        "git -C /Users/x/code/idp worktree add /tmp/wt -b lane/x",
        "git clone https://github.com/chidionyema/idp /tmp/y",
    ],
)
def test_it_refuses_every_local_checkout(darwin, command: str) -> None:
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
def test_it_allows_every_read_only_probe(darwin, command: str) -> None:
    """A read is never refused. Refusing it is what made the disk guardians a liability (#7914)."""
    verdict, why = executor._spawn_verdict(command)
    assert verdict == ALLOW, f"a read was refused: {command!r}: {why}"


def test_a_search_for_a_spawn_verb_is_not_a_spawn(darwin) -> None:
    """`rg "git worktree add"` reads. A substring test would refuse it, which is R14 exactly."""
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
def test_an_ordinary_estate_verb_is_not_a_proven_spawn(darwin, command: str) -> None:
    """The door must not blanket-refuse the estate's own verbs: that is how a guard becomes a
    liability (R38). It answers ALLOW -- "I did not prove this creates a checkout" -- which is
    honest, where a refusal would be an outage."""
    verdict, why = executor._spawn_verdict(command)
    assert verdict != REFUSED, (
        f"an ordinary verb was refused as a spawn: {command!r}: {why}"
    )


def test_an_unrecognised_command_is_allowed_at_the_door(darwin) -> None:
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


def test_the_heavy_work_boundary_is_not_wired_at_the_door(darwin) -> None:
    """A SCOPE DECISION, pinned so it cannot drift silently.

    thin_client's rule 3 refuses heavy work (make, npm, pytest, docker build) when the host is out
    of room or crushed -- but its floor is 10 GB free and this machine measures ~3 GB free, so that
    rule is permanently ON here. Wiring it into the door would refuse `git push` and `pytest`: it
    would refuse the ability to fix the disk. Refusing correct work is worse than the hole the
    guard closed (R38). The CHECKOUT rules are wired, because they are the ban the founder ordered
    and they cost no correct work.
    """
    verdict, _ = executor._spawn_verdict("make build")
    assert verdict == ALLOW


def test_an_empty_command_is_blind_and_never_allowed() -> None:
    for blank in ("", "   ", "\n"):
        verdict, _ = executor._spawn_verdict(blank)
        assert verdict == BLIND, (
            f"an empty command was {verdict}, not BLIND -- unknown is never a pass"
        )


def test_the_cap_is_zero_because_the_directive_is_a_ban(darwin) -> None:
    assert executor._worktree_cap() == 0, (
        "the cap on the founder's laptop is zero: a thin client has no local worktrees"
    )


def test_the_cap_override_is_an_emergency_lever_not_policy(
    darwin, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raising the cap lets exactly that many worktrees exist, and no more."""
    monkeypatch.setenv("ESTATE_MAX_LOCAL_WORKTREES", "2")
    assert executor._worktree_cap() == 2

    monkeypatch.setattr(executor, "_worktree_count", lambda: 1)
    verdict, _ = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == ALLOW, "one worktree under a cap of two is under the cap"

    monkeypatch.setattr(executor, "_worktree_count", lambda: 2)
    verdict, _ = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == REFUSED, "at the cap the door must refuse"


def test_a_malformed_cap_falls_back_to_the_ban(
    darwin, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable knob must not widen the hole the guard closed."""
    monkeypatch.setenv("ESTATE_MAX_LOCAL_WORKTREES", "not-a-number")
    assert executor._worktree_cap() == 0
    verdict, _ = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == REFUSED


def test_an_unmeasurable_count_cannot_prove_room(
    darwin, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R1: a count that cannot be read is BLIND, and BLIND proves no headroom."""
    monkeypatch.setenv("ESTATE_MAX_LOCAL_WORKTREES", "4")
    monkeypatch.setattr(executor, "_worktree_count", lambda: None)
    verdict, _ = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == REFUSED


def test_the_fence_lifts_the_ban_without_a_restart(darwin, monkeypatch) -> None:
    """The instant off-switch: a rule that can only be changed by a restart is a rule that can
    wedge a machine nobody can restart."""
    monkeypatch.setattr(darwin, "fence_lifted", lambda: True)
    verdict, why = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == ALLOW, f"the fence did not lift the ban: {why}"


def test_an_unloadable_guard_is_blind_and_never_a_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A guard that cannot load must not stop the estate (R38). It must be VISIBLE instead."""
    monkeypatch.setattr(executor, "_thin_client", lambda: None)
    verdict, why = executor._spawn_verdict("git worktree add /tmp/x")
    assert verdict == BLIND, (
        f"an unloadable guard returned {verdict}; BLIND is the honest answer and it is not a "
        "refusal"
    )
    assert "could not be loaded" in why


def test_the_refusal_names_the_cap_and_the_count(
    darwin, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The number the founder configured must be visible, and the numeric code must travel."""
    monkeypatch.setattr(executor, "_worktree_count", lambda: 4)
    out = executor._spawn_refusal("git worktree add /tmp/x", "THIN CLIENT: refused.")
    assert out["accepted"] is False
    assert out["exit_code"] == REFUSED, (
        "the refusal must carry the numeric code, so a machine can gate on it"
    )
    assert "cap on this laptop is 0" in out["error"], (
        "the refusal must name the configured cap; a refusal a caller cannot act on is friction"
    )
    assert "4 worktrees" in out["error"], (
        "the refusal must name what is already registered"
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
