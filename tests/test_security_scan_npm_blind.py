"""An npm audit that prints nothing measured nothing (2026-09-04).

`bin/estate-security-scan` refused hermes-v2#71 twice with `FAIL npm ... high or critical
advisories in shipped dependencies` and an empty evidence block underneath, while the identical
command answered "found 0 vulnerabilities" outside CI. A real advisory always prints its report,
so a non-zero exit with no output is a broken probe and calling it a finding refuses correct work
(LAW 38). These two cases pin both halves of that rule.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCAN = Path(__file__).resolve().parents[1] / "bin" / "estate-security-scan"


def _repo_with_fake_npm(tmp_path: Path, exit_code: int, output: str) -> str:
    """A one-commit repository carrying a lockfile, with `npm` replaced by a stub on PATH."""
    src = tmp_path / "src"
    (src / "lsp").mkdir(parents=True)
    (src / "lsp" / "package-lock.json").write_text(
        '{"name":"stub","lockfileVersion":3}\n'
    )
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
    ):
        subprocess.run(["git", *args], cwd=src, check=True, capture_output=True)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "npm"
    stub.write_text(f"#!/bin/sh\nprintf %s {output!r}\nexit {exit_code}\n")
    stub.chmod(0o755)

    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    return subprocess.run(
        [str(SCAN), "--source", str(src)], capture_output=True, text=True, env=env
    ).stdout


def test_an_npm_audit_that_prints_nothing_is_blind_not_a_finding(
    tmp_path: Path,
) -> None:
    out = _repo_with_fake_npm(tmp_path, exit_code=1, output="")
    assert "BLIND npm" in out, out
    assert "FAIL  npm" not in out, out


def test_an_npm_audit_that_names_an_advisory_still_fails(tmp_path: Path) -> None:
    out = _repo_with_fake_npm(
        tmp_path, exit_code=1, output="1 high severity vulnerability\n"
    )
    assert "FAIL  npm" in out, out
    assert "BLIND npm" not in out, out


def test_a_registry_timeout_is_a_warning_and_does_not_gate(tmp_path: Path) -> None:
    """Exit 124 is what `timeout` returns when the registry never answers.

    The scanner captured that status with `rc=$?` after an `if ! cmd` test, which reads the
    status of the negation and is therefore always 0, so the timeout branch never ran and a
    registry that did not answer arrived as an advisory. Under the flake protocol an unrelated
    infrastructure timeout reports and does not hold the change.
    """
    out = _repo_with_fake_npm(tmp_path, exit_code=124, output="")
    assert "WARN  npm" in out, out
    assert "FAIL  npm" not in out, out
    assert "BLIND npm" not in out, out
