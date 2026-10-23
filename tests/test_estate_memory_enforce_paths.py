"""The write gate compares one form of a file's path with the claim's paths (#7006).

Measured 2026-10-23 on this machine: a pi agent in a checkout under /tmp was refused by the
claim write gate for a file its own live claim covered. The reason it printed was the tell --
"../../../tmp/pi-write-gates/docs/..." is /tmp/... seen from the checkout git calls
/private/tmp/.... The claim's paths are relative to the checkout, so the comparison must be too.
"""

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BIN = REPO / "bin" / "estate-memory-enforce"


def load_enforce():
    """The binary as a module: it is a script, and its decisions are its functions."""
    loader = importlib.machinery.SourceFileLoader("estate_memory_enforce", str(BIN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def idp_checkout(root: Path) -> Path:
    """A checkout the gate recognises as idp (the rule is the origin's URL)."""
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
    return root


def test_a_symlinked_parent_still_matches_the_claim(tmp_path):
    """The path an agent writes and the path git reports are one path."""
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    (checkout / "docs").mkdir()
    target = checkout / "docs" / "note.md"
    target.write_text("x")

    # /tmp is a symlink to /private/tmp on macOS; this is that shape, made.
    link = tmp_path / "shortcut"
    link.symlink_to(checkout)
    written = str(link / "docs" / "note.md")

    rows = [{"live": True, "agent": "pi-parity", "paths": "docs/*"}]
    ok, why = enforce.focus_verdict(written, rows, "pi-parity")
    assert ok, why


def test_a_file_no_claim_covers_is_still_refused(tmp_path):
    """One form of the path does not make the gate permissive."""
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    (checkout / "docs").mkdir()
    target = checkout / "docs" / "note.md"
    target.write_text("x")

    link = tmp_path / "shortcut"
    link.symlink_to(checkout)

    rows = [{"live": True, "agent": "pi-parity", "paths": "extensions/*"}]
    ok, why = enforce.focus_verdict(str(link / "docs" / "note.md"), rows, "pi-parity")
    assert ok is False
    assert "docs/note.md" in why, why


def test_another_agents_claim_is_still_refused(tmp_path):
    """The same rule, one agent over."""
    enforce = load_enforce()
    checkout = idp_checkout(tmp_path / "repo")
    (checkout / "docs").mkdir()
    target = checkout / "docs" / "note.md"
    target.write_text("x")

    link = tmp_path / "shortcut"
    link.symlink_to(checkout)

    rows = [{"live": True, "agent": "someone-else", "paths": "docs/*"}]
    ok, why = enforce.focus_verdict(str(link / "docs" / "note.md"), rows, "pi-parity")
    assert ok is False
    assert "someone-else" in why or "not" in why, why


def test_an_empty_path_is_not_durable():
    """realpath('') is the cwd; a file with no path must not become the working directory."""
    enforce = load_enforce()
    assert enforce.real("") == ""
    assert enforce.durable("") is False
