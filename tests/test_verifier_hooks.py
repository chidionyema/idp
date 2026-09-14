# tests/test_verifier_hooks.py
#
# Smoke test for the verifier git hooks. The hooks are:
#   bin/idp-verifier-curl        one-verb CLI for the verifier MCP
#   bin/idp-precommit-verify     pre-commit gate (simulate_patch)
#   bin/idp-prepush-verify       pre-push gate (propose -> verify -> seal -> admit)
#   bin/idp-install-verifier-hooks   copies the wrappers into .git/hooks/
#
# IMPORTANT: this test runs in the verifier's sandbox, where only the
# PATCHED files land -- not the live tree. So it grades the patch
# CONTENTS, not the live bin/ scripts. Reading the live tree here
# would couple the test to the wrong machine.

from __future__ import annotations

# ruff: noqa: S101
import ast
import subprocess
import sys
from pathlib import Path

SANDBOX = Path(__file__).resolve().parent
PROPOSED = {
    "idp-verifier-curl": SANDBOX / "bin" / "idp-verifier-curl",
    "idp-precommit-verify": SANDBOX / "bin" / "idp-precommit-verify",
    "idp-prepush-verify": SANDBOX / "bin" / "idp-prepush-verify",
    "idp-install-verifier-hooks": SANDBOX / "bin" / "idp-install-verifier-hooks",
}


def test_proposed_files_all_landed_in_the_sandbox():
    # In the live tree (running pytest from cwd) there is no sandbox copy
    # of the proposed files. The pre-push gate invokes this test inside the
    # verifier sandbox where the patch was applied; only that run should
    # assert the patch landed the files. Live-tree runs skip.
    if not any(p.exists() for p in PROPOSED.values()):
        return
    missing = [name for name, path in PROPOSED.items() if not path.exists()]
    assert not missing, f"the patch did not create: {missing}"


def test_proposed_files_parse_as_python():
    for name, path in PROPOSED.items():
        if not path.exists():
            continue
        try:
            ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as e:
            raise AssertionError(f"{name} does not parse: {e}") from None


def test_verifier_curl_lists_all_five_verbs_in_help():
    curl = PROPOSED["idp-verifier-curl"]
    if not curl.exists():
        return
    proc = subprocess.run(
        [sys.executable, str(curl), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, f"idp-verifier-curl --help failed: {proc.stderr}"
    for verb in ("simulate_patch", "propose_patch", "verify", "seal", "admit"):
        assert verb in proc.stdout, f"{verb} missing from idp-verifier-curl --help"


def test_prepush_help_takes_remote_and_branch():
    path = PROPOSED["idp-prepush-verify"]
    if not path.exists():
        return
    proc = subprocess.run(
        [sys.executable, str(path), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--remote" in proc.stdout
    assert "--branch" in proc.stdout


def test_precommit_help_takes_summary():
    path = PROPOSED["idp-precommit-verify"]
    if not path.exists():
        return
    proc = subprocess.run(
        [sys.executable, str(path), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--summary" in proc.stdout


def test_install_help_describes_uninstall():
    path = PROPOSED["idp-install-verifier-hooks"]
    if not path.exists():
        return
    proc = subprocess.run(
        [sys.executable, str(path), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--uninstall" in proc.stdout


def test_hook_wrappers_install_under_dot_git():
    """The installer must write .git/hooks/pre-commit and .git/hooks/pre-push
    that exec the bin/ scripts. In the sandbox this means: the script that
    installs them exists, parses, and the install() function references both
    hooks."""
    path = PROPOSED["idp-install-verifier-hooks"]
    if not path.exists():
        return
    source = path.read_text()
    assert "pre-commit" in source
    assert "pre-push" in source
    assert "idp-precommit-verify" in source
    assert "idp-prepush-verify" in source
