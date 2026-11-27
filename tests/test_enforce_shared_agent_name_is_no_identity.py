"""The write gate must not take the environment's name for the agent's.

Measured 2026-11-27: `~/.zshrc` exports `ESTATE_AGENT=estate-agent` to every shell on this machine.
`bin/claim-open` refuses that name as an identity (SHARED_AGENT_NAMES, #7934), so no claim can
ever be held by it. `bin/estate-memory-enforce` read the same variable AS the identity, so every
agent in every harness was refused an edit to the files its OWN live claim covers:

    PreToolUse:Edit hook error: No active focus for this change.
    estate/gates/tests/api-port-guard.test.py is claimed, but not by agent estate-agent.
    (claude-code held idp#8598 over that path; the session was the holder.)

Two readers of one rule disagreed: one said "not an identity", the other used it as one. The
remedy is the reader's, not a second list: the hook reads claim-open's own set, so the two cannot
drift, and a shared name counts as no identity, the same as an unset ESTATE_AGENT.
"""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin" / "estate-memory-enforce"
CLAIM_OPEN = REPO / "bin" / "claim-open"


def load_enforce():
    loader = importlib.machinery.SourceFileLoader("estate_memory_enforce", str(BIN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def claim_open_names() -> frozenset:
    tree = ast.parse(CLAIM_OPEN.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SHARED_AGENT_NAMES"
            for t in node.targets
        ):
            return frozenset(ast.literal_eval(node.value.args[0]))
    raise AssertionError("bin/claim-open no longer declares SHARED_AGENT_NAMES")


def idp_checkout(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "remote",
            "add",
            "origin",
            "https://github.com/chidionyema/idp.git",
        ],
        check=True,
    )
    (root / "docs").mkdir()
    (root / "docs" / "note.md").write_text("x")
    return root


def test_the_holder_is_not_refused_its_own_claim_under_the_shared_name(tmp_path):
    """The measured case: the claim is claude-code's, the shell says estate-agent."""
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    rows = [{"live": True, "agent": "claude-code", "paths": "docs/*"}]
    ok, why = enforce.focus_verdict(
        str(checkout / "docs" / "note.md"), rows, "estate-agent"
    )
    assert ok, why


def test_every_shared_name_and_its_spelling_counts_as_no_identity(tmp_path):
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    rows = [{"live": True, "agent": "opencode", "paths": "docs/*"}]
    for name in sorted(claim_open_names()) + [" Estate-Agent ", "OTTO"]:
        ok, why = enforce.focus_verdict(str(checkout / "docs" / "note.md"), rows, name)
        assert ok, f"{name!r}: {why}"


def test_a_shared_name_does_not_open_an_unclaimed_file(tmp_path):
    """No identity is not permission: a path no live claim covers is still refused."""
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    rows = [{"live": True, "agent": "claude-code", "paths": "extensions/*"}]
    ok, why = enforce.focus_verdict(
        str(checkout / "docs" / "note.md"), rows, "estate-agent"
    )
    assert ok is False
    assert "docs/note.md" in why and "estate-agent" not in why, why


def test_a_real_name_is_still_held_to_its_own_claims(tmp_path):
    """The narrowing still bites for an agent that has an identity."""
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    rows = [{"live": True, "agent": "claude-code", "paths": "docs/*"}]
    ok, why = enforce.focus_verdict(
        str(checkout / "docs" / "note.md"), rows, "pi-parity"
    )
    assert ok is False
    assert "pi-parity" in why, why


def test_the_hook_reads_claim_opens_set_not_a_copy():
    enforce = load_enforce()
    assert enforce.SHARED_AGENT_NAMES == claim_open_names()
    assert enforce.SHARED_AGENT_NAMES, (
        "an empty set would silently restore the dead end"
    )


def holder_refusals() -> int:
    """The registered measure: under each shared name, is the holder refused its own claim?"""
    import tempfile

    enforce = load_enforce()
    names = sorted(claim_open_names()) + [" Estate-Agent ", "OTTO"]
    with tempfile.TemporaryDirectory(prefix="shared-agent-") as tmp:
        checkout = idp_checkout(Path(tmp) / "repo")
        rows = [{"live": True, "agent": "claude-code", "paths": "docs/*"}]
        note = str(checkout / "docs" / "note.md")
        return sum(
            1 for n in names if enforce.focus_verdict(note, rows, n)[0] is not True
        )


if __name__ == "__main__":
    import sys

    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/test_enforce_shared_agent_name_is_no_identity.py --optimus"
        )
    print(f"optimus.enforce.shared_name_holder_refusals={holder_refusals()}")
