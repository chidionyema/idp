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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin" / "estate-memory-enforce"
CLAIM_OPEN = REPO / "bin" / "claim-open"


def load_enforce(path: Path = BIN):
    # The hook's own imports (focus, handback, plan) resolve relative to its location; a
    # relocated copy finds them through the repo's tree, as the deployed copy finds its own.
    memory = str(REPO / "platform" / "estate" / "memory")
    if memory not in sys.path:
        sys.path.append(memory)
    loader = importlib.machinery.SourceFileLoader("estate_memory_enforce", str(path))
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


def relocated_refuses_the_holder(source: Path, scratch: Path) -> bool:
    """The deployed layout: the hook alone in a bin/ with no claim-open beside it (idp#8660).

    True when that copy refuses a holder its own claim under the shared name, the measured
    deadlock: `~/.estate/memory/bin/estate-memory-enforce` refused claude-ins00037-takeover's
    live claim on #8658 because ESTATE_AGENT=estate-agent and the sibling read found nothing.
    """
    deployed = scratch / "deployed" / "bin"
    deployed.mkdir(parents=True)
    shutil.copy(source, deployed / "estate-memory-enforce")
    enforce = load_enforce(deployed / "estate-memory-enforce")
    assert not (deployed / "claim-open").exists()
    checkout = idp_checkout(scratch / "repo")
    (checkout / "bin").mkdir()
    shutil.copy(CLAIM_OPEN, checkout / "bin" / "claim-open")
    rows = [{"live": True, "agent": "claude-ins00037-takeover", "paths": "docs/*"}]
    ok, _ = enforce.focus_verdict(
        str(checkout / "docs" / "note.md"), rows, "estate-agent"
    )
    return not ok


def test_the_deployed_copy_without_claim_open_still_admits_the_holder(tmp_path):
    assert not relocated_refuses_the_holder(BIN, tmp_path)


def test_falsifier_a_resolver_that_reads_only_its_sibling_refuses_the_holder(tmp_path):
    """The pre-#8660 resolver, reconstructed: it must reproduce the measured deadlock."""
    text = BIN.read_text()
    sibling_only = text.replace(
        'candidates = [os.path.join(root, "bin", "claim-open")] if root else []',
        "candidates = []",
    )
    assert sibling_only != text, (
        "the root-first candidate line moved; update the falsifier"
    )
    old = tmp_path / "old" / "estate-memory-enforce"
    old.parent.mkdir()
    old.write_text(sibling_only)
    assert relocated_refuses_the_holder(old, tmp_path / "case")


if __name__ == "__main__" and "--optimus" in sys.argv:
    with tempfile.TemporaryDirectory() as scratch:
        bad = int(relocated_refuses_the_holder(BIN, Path(scratch)))
    print(f"optimus.hooks.enforce_shared_name_unresolved_when_relocated={bad}")
