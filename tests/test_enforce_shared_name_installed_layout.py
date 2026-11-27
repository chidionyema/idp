"""The shared-name fix must hold where the hook is INSTALLED, not only in the repo.

Measured 2026-11-27 (session 40fa894f): the hook runs from ~/.estate/memory/bin, which has no
bin/claim-open beside it (`test -e ~/.estate/memory/bin/claim-open` -> rc=1). #8616 read the
shared names only from beside the hook, so there the set was empty, `estate-agent` was taken as
an identity again, and every Claude Code session was refused writes its own live claim covered.
These tests run the verdict with the import-time set empty, as it is when installed.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin" / "estate-memory-enforce"


def load_installed():
    loader = importlib.machinery.SourceFileLoader("estate_memory_enforce_inst", str(BIN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.SHARED_AGENT_NAMES = frozenset()  # what the installed copy reads at import
    return module


def checkout(root: Path, with_claim_open: bool) -> Path:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "https://github.com/chidionyema/idp.git"],
        check=True,
    )
    (root / "docs").mkdir()
    (root / "docs" / "note.md").write_text("x")
    if with_claim_open:
        (root / "bin").mkdir()
        shutil.copy(REPO / "bin" / "claim-open", root / "bin" / "claim-open")
    return root


def test_installed_hook_reads_the_edited_checkouts_claim_open(tmp_path):
    m = load_installed()
    co = checkout(tmp_path / "repo", with_claim_open=True)
    rows = [{"live": True, "agent": "claude-opus-40fa894f", "paths": "docs/*"}]
    ok, why = m.focus_verdict(str(co / "docs" / "note.md"), rows, "estate-agent")
    assert ok, why


def test_installed_hook_still_refuses_an_unclaimed_path(tmp_path):
    m = load_installed()
    co = checkout(tmp_path / "repo", with_claim_open=True)
    rows = [{"live": True, "agent": "claude-opus-40fa894f", "paths": "extensions/*"}]
    ok, why = m.focus_verdict(str(co / "docs" / "note.md"), rows, "estate-agent")
    assert ok is False, why


def test_installed_hook_still_holds_a_real_name_to_its_own_claims(tmp_path):
    m = load_installed()
    co = checkout(tmp_path / "repo", with_claim_open=True)
    rows = [{"live": True, "agent": "claude-opus-40fa894f", "paths": "docs/*"}]
    ok, why = m.focus_verdict(str(co / "docs" / "note.md"), rows, "pi-parity")
    assert ok is False and "pi-parity" in why, why


def test_no_claim_open_anywhere_opens_nothing_new(tmp_path):
    """Without claim-open the old behaviour stands: no new door opens by accident."""
    m = load_installed()
    co = checkout(tmp_path / "repo", with_claim_open=False)
    rows = [{"live": True, "agent": "claude-opus-40fa894f", "paths": "docs/*"}]
    ok, why = m.focus_verdict(str(co / "docs" / "note.md"), rows, "estate-agent")
    assert ok is False, why
