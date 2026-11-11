"""claim-open must refuse a name that every agent on this machine wears.

Measured 2026-11-11: `~/.zshrc` exports ESTATE_AGENT=estate-agent for every shell on the machine.
`bin/claim-open`'s #6407 guard refuses an EMPTY identity, so a claim posted from any harness that
did not override the variable carried the same name as every other agent's. On that day five open
issues read `agent=estate-agent` and only two other agents were distinguishable at all.

The consequence is not cosmetic. `bin/claim-gate` answers "held by estate-agent", and every agent
reads that as both "not me" (so not blocked) and "possibly me" (so maybe it is mine) -- which is
exactly the collision #6407 exists to stop, arrived at through a value that LOOKS like an identity.
A shared name is worse than no name, so it is refused, and the refusal names the way out.
"""

import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLAIM_OPEN = ROOT / "bin" / "claim-open"


@pytest.fixture(scope="module")
def co():
    return SourceFileLoader("claim_open_under_test", str(CLAIM_OPEN)).load_module()


@pytest.mark.parametrize("name", ["pi", "claude", "codex", "chatgpt", "otto-2026"])
def test_a_real_identity_passes_through_unchanged(co, name):
    """The guard must not touch names that do identify an agent."""
    assert co.agent_identity(name) == name


@pytest.mark.parametrize(
    "name", ["estate-agent", "ESTATE-AGENT", "otto", "root", "unknown", " agent "]
)
def test_a_shared_identity_is_refused(co, name):
    """These name the machine, or a role, not the agent claiming."""
    with pytest.raises(SystemExit) as exc:
        co.agent_identity(name)
    assert exc.value.code != 0, "refusal must be a non-zero exit, never a silent pass"


def test_the_refusal_says_how_to_fix_it(co):
    """A refusal that does not name the way out is a dead end."""
    with pytest.raises(SystemExit):
        co.agent_identity("estate-agent")


def test_estate_agent_in_the_environment_cannot_reach_the_claim(co):
    """End to end: the real environment value must not become a posted claim."""
    p = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [str(CLAIM_OPEN), "--issue", "1", "--check-only"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "ESTATE_AGENT": "estate-agent",
            "HOME": str(Path.home()),
        },
        cwd=str(ROOT),
    )
    assert p.returncode != 0, "claim-open accepted a shared identity from $ESTATE_AGENT"
    out = p.stdout + p.stderr
    assert "shared name, not an identity" in out, (
        "refused for some other reason; the guard under test did not run. Output: %r"
        % out[:300]
    )
