"""A claim must carry a name that tells agents apart, or the claim proves nothing.

Measured 2026-11-11 (#7934): `~/.zshrc` line 49 exports `ESTATE_AGENT=estate-agent` for every
shell on this machine. `bin/claim-open` refuses an EMPTY identity (#6407) -- but `estate-agent`
is not empty, it is just not an identity. Five of the last twelve open issues wore the same name,
and `claim-gate` answers "held by estate-agent", which every agent reads as both "not me" (not
blocked) and "possibly me" (maybe mine). That is the collision #6407 exists to stop, reached
through a value that looks like one.

These tests run the real program on the PATH a real shell has -- the system binaries, without
`~/.local/bin` -- so the refusal is proved by the exit code and the message, not by a grep of the
source. The refusal happens before any GitHub call, so a wrong name costs a comment, not a claim:
every test here runs with no `gh` reachable, and a refusal that still fires proves it.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAIM_OPEN = REPO / "bin" / "claim-open"

# The narrowest PATH a shell can plausibly have: the system binaries, and nothing a user
# installed. `gh` lives in ~/.local/bin on this machine, so it is invisible here -- which is the
# point: the refusal must not depend on reaching GitHub.
BARE_PATH = "/usr/bin:/bin"


def _run(agent: str) -> subprocess.CompletedProcess[str]:
    """Run the real claim-open with `agent`, on a PATH that cannot see gh."""
    return subprocess.run(  # noqa: S603 - fixed argv, no shell string
        ["/usr/bin/python3", str(CLAIM_OPEN), "--issue", "1", "--agent", agent],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env={**os.environ, "PATH": BARE_PATH},
        timeout=60,
    )


def _module():
    """Load claim-open as a module, without running it."""
    loader = importlib.machinery.SourceFileLoader(
        "claim_open_under_test", str(CLAIM_OPEN)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_environment_sentinel_is_refused() -> None:
    out = _run("estate-agent")
    assert out.returncode != 0, (
        f"claim-open accepted the environment's own name: {out.stdout}"
    )
    assert "is not an identity" in out.stdout + out.stderr, (
        f"the refusal did not say what is wrong: {out.stdout}{out.stderr}"
    )


def test_otto_is_refused() -> None:
    out = _run("otto")
    assert out.returncode != 0, (
        f"claim-open accepted the previous hardcoded default: {out.stdout}"
    )
    assert "is not an identity" in out.stdout + out.stderr


def test_chatgpt_is_refused() -> None:
    out = _run("chatgpt")
    assert out.returncode != 0, (
        f"claim-open accepted a model name as an agent: {out.stdout}"
    )
    assert "is not an identity" in out.stdout + out.stderr


def test_a_name_that_is_the_agents_own_is_not_refused() -> None:
    """The refusal must not tax correct work: a distinct name is a distinct name."""
    out = _run("pi-1794345368491-l8omxh39")
    assert "is not an identity" not in out.stdout + out.stderr, (
        f"a distinct agent name was refused as an identity: {out.stdout}{out.stderr}"
    )


def test_the_refusal_names_the_way_out() -> None:
    out = _run("estate-agent")
    said = out.stdout + out.stderr
    assert "--agent" in said, f"the refusal did not name the way out: {said}"
    assert "ESTATE_AGENT" in said, (
        f"the refusal did not name the environment it came from: {said}"
    )


def test_the_refusal_costs_no_github_call() -> None:
    """It fires before the network: with no gh reachable, the refusal is still the refusal."""
    out = _run("estate-agent")
    said = out.stdout + out.stderr
    assert "is not an identity" in said, f"something else answered first: {said}"
    assert "gh" not in said.lower(), f"the refusal tried to reach GitHub first: {said}"


def test_the_decision_is_readable_without_running_the_program() -> None:
    mod = _module()
    assert mod.shared_agent_refusal("estate-agent"), (
        "the shared sentinel reads as acceptable"
    )
    assert mod.shared_agent_refusal("otto"), "the previous default reads as acceptable"
    assert mod.shared_agent_refusal("chatgpt"), "a model name reads as acceptable"
    assert mod.shared_agent_refusal("pi-1794345368491-l8omxh39") == "", (
        "a distinct agent name is refused by the decision itself"
    )
    assert mod.shared_agent_refusal("  estate-agent  "), (
        "case and padding are not normalised"
    )


def test_the_shared_names_are_a_named_set() -> None:
    mod = _module()
    assert mod.SHARED_AGENT_NAMES == frozenset({"estate-agent", "otto", "chatgpt"}), (
        f"the refused set drifted: {sorted(mod.SHARED_AGENT_NAMES)}"
    )
