"""A recorded npm dismissal clears only what it names, and only until its review date (2026-10-14).

braces <=3.0.3 (GHSA-vfj7-8cjw-p6xm, published 2026-09-18) has no patched release, and
bash-language-server reaches it through fast-glob, so every repository shipping the language
servers in `lsp/` failed the npm gate with nothing to upgrade to. `.pip-audit-ignores` already
answered this for pip; `.npm-audit-ignores` is the same answer with a mandatory review date.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCAN = Path(__file__).resolve().parents[1] / "bin" / "estate-security-scan"
BRACES = "GHSA-vfj7-8cjw-p6xm"
OTHER = "GHSA-aaaa-bbbb-cccc"


def _report(*ids: str) -> str:
    return json.dumps(
        {
            "vulnerabilities": {
                f"pkg{i}": {
                    "via": [
                        {
                            "url": f"https://github.com/advisories/{a}",
                            "severity": "high",
                        }
                    ]
                }
                for i, a in enumerate(ids)
            }
        }
    )


def _scan(tmp_path: Path, ignores: str | None, *advisories: str) -> str:
    """One commit carrying a lockfile (and an ignores file), with `npm` stubbed on PATH."""
    src = tmp_path / "src"
    (src / "lsp").mkdir(parents=True)
    (src / "lsp" / "package-lock.json").write_text(
        '{"name":"stub","lockfileVersion":3}\n'
    )
    if ignores is not None:
        (src / ".npm-audit-ignores").write_text(ignores)
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
    ):
        subprocess.run(["git", *args], cwd=src, check=True, capture_output=True)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "report.json").write_text(_report(*advisories))
    stub = bin_dir / "npm"
    stub.write_text(
        "#!/bin/sh\n"
        'case "$*" in *--json*) cat "'
        + str(tmp_path / "report.json")
        + '"; exit 1;; esac\n'
        f"echo '{len(advisories)} high severity vulnerabilities'\nexit 1\n"
    )
    stub.chmod(0o755)

    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    return subprocess.run(
        [str(SCAN), "--source", str(src)], capture_output=True, text=True, env=env
    ).stdout


def test_a_dismissed_advisory_does_not_gate(tmp_path: Path) -> None:
    out = _scan(tmp_path, f"{BRACES} 2099-01-01 no patched release\n", BRACES)
    assert f"dismissed {BRACES} until 2099-01-01" in out, out
    assert "FAIL  npm" not in out, out


def test_a_dismissal_does_not_clear_an_advisory_it_does_not_name(
    tmp_path: Path,
) -> None:
    out = _scan(tmp_path, f"{BRACES} 2099-01-01 no patched release\n", BRACES, OTHER)
    assert "FAIL  npm" in out, out
    assert f"not dismissed: {OTHER}" in out, out


def test_without_an_ignores_file_an_advisory_still_fails(tmp_path: Path) -> None:
    out = _scan(tmp_path, None, BRACES)
    assert "FAIL  npm" in out, out


def test_a_dismissal_past_its_review_date_fails(tmp_path: Path) -> None:
    out = _scan(tmp_path, f"{BRACES} 2020-01-01 no patched release\n", BRACES)
    assert "was to be reviewed by 2020-01-01" in out, out
    assert "FAIL  npm" in out, out


def test_a_dismissal_without_a_reason_is_refused(tmp_path: Path) -> None:
    out = _scan(tmp_path, f"{BRACES} 2099-01-01\n", BRACES)
    assert 'is not "<GHSA-id> <review-by YYYY-MM-DD> <reason>"' in out, out
    assert "FAIL  npm" in out, out
