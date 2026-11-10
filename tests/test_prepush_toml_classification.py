"""The pre-push file classifier must know TOML (R2: a gate ships with its falsifier).

Measured defect, 2026-11-10, on lane/protocol-gate-orphan-fix. `_file_kind` in
`.githooks/pre-push` had cases for python, shell, typescript, javascript, rust -- and
nothing for TOML. A `*.toml` therefore fell into the "unknown" bucket, where a file is
accepted only if `bash -n` or `py_compile` can read it. Neither can read TOML, so every
push that touched `pyproject.toml` was refused:

    pre-push REFUSED: pyproject.toml is readable as neither shell nor Python

The gate made the estate's own declaration layer unpushable. The workaround found in that
session was to carry ruff exemptions inside a Python file instead of in the config file
that exists to hold them -- the estate working around its own guard, which is the defect
AGENTS.md 9 R14 names.

These tests drive the real function out of the real hook, not a copy, so a regression in
the shipped hook fails them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".githooks" / "pre-push"


def _extract(name: str) -> str:
    """Pull one shell function out of the hook by name (brace-balanced)."""
    text = HOOK.read_text()
    start = text.index("%s() {" % name)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError("unbalanced function %s in %s" % (name, HOOK))


def _shquote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _run_toml_parse(path: Path) -> subprocess.CompletedProcess:
    script = "%s\n_toml_parse %s" % (_extract("_toml_parse"), _shquote(str(path)))
    return subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=60
    )


def _run_file_kind(path: Path) -> str:
    script = "%s\n_file_kind %s" % (_extract("_file_kind"), _shquote(str(path)))
    out = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, timeout=60
    )
    return out.stdout.strip()


@pytest.fixture()
def toml_files(tmp_path: Path):
    good = tmp_path / "pyproject.toml"
    good.write_text(
        '[tool.ruff]\nline-length = 100\n[tool.ruff.lint]\nselect = ["E9"]\n'
    )
    bad = tmp_path / "broken.toml"
    bad.write_text("[tool.ruff\nline-length = = 100\n")
    return good, bad


def test_valid_toml_is_accepted(toml_files):
    """The estate's real config shape parses: accepting it is the fix."""
    good, _ = toml_files
    r = _run_toml_parse(good)
    assert r.returncode == 0, "valid TOML was refused: %s" % r.stderr


def test_malformed_toml_is_refused(toml_files):
    """THE FALSIFIER: a gate that accepts broken TOML is not a gate."""
    _, bad = toml_files
    r = _run_toml_parse(bad)
    assert r.returncode == 1, "malformed TOML was accepted (rc=%d)" % r.returncode
    assert "Error" in r.stderr or "error" in r.stderr, r.stderr


def test_real_pyproject_parses():
    """No fixture: the repo's own pyproject.toml, the file the defect refused."""
    r = _run_toml_parse(REPO / "pyproject.toml")
    assert r.returncode == 0, "the repo's own pyproject.toml was refused: %s" % r.stderr


def test_classifier_reports_toml(tmp_path: Path):
    """_file_kind itself must classify TOML, not bucket it as unknown.

    Measured before the fix: `_file_kind /tmp/x.toml` printed `unknown`, because the
    classifier's case list stopped at Rust. That bucketing is the defect's first half.
    """
    f = tmp_path / "x.toml"
    f.write_text("a = 1\n")
    assert _run_file_kind(f) == "toml"


def test_old_behaviour_would_have_refused():
    """Pin the before-state on the REAL file the defect refused.

    The "unknown" bucket accepts a file when `bash -n` OR `py_compile` can read it, so a
    trivial one-line TOML slips through -- which is why the defect survived: it only bites
    on TOML that is genuinely neither language. The repo's own pyproject.toml is exactly
    that file. Measured 2026-11-10: bash -n rc=2, py_compile rc=1.

    If this ever fails, the defect was not what the commit says it was and the change
    should be re-derived, not kept.
    """
    f = REPO / "pyproject.toml"
    bash_n = subprocess.run(["bash", "-n", str(f)], capture_output=True)
    pyc = subprocess.run(
        [sys.executable, "-m", "py_compile", str(f)], capture_output=True
    )
    assert bash_n.returncode != 0, (
        "bash -n parsed pyproject.toml: the defect was not real"
    )
    assert pyc.returncode != 0, (
        "py_compile parsed pyproject.toml: the defect was not real"
    )


def test_hook_is_still_valid_shell():
    """The change must not break the hook it lives in."""
    r = subprocess.run(["bash", "-n", str(HOOK)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_no_non_ascii_added_by_this_change():
    """The estate's ASCII gate applies to lines this change ADDS, not to the file.

    The hook already carries em dashes, a section sign and emoji from earlier work; those
    are not this change's to fix (AGENTS.md 8: only make the change that was asked for).
    The rule is on added lines (layer 1c of the hook itself).
    """
    base = subprocess.run(
        ["git", "merge-base", "origin/main", "HEAD"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not base:
        pytest.skip("no merge base available to diff against")
    diff = subprocess.run(
        ["git", "diff", "-U0", base, "HEAD", "--", ".githooks/pre-push"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    ).stdout
    added = [
        ln[1:]
        for ln in diff.splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    ]
    bad = [ln for ln in added if any(ord(ch) > 127 for ch in ln)]
    assert not bad, "non-ASCII added to .githooks/pre-push: %r" % bad[:5]
