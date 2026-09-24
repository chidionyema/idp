"""A recorded, reasoned dismissal in .pip-audit-ignores rides pip-audit's own
--ignore-vuln flag and is printed in the receipt; an entry with no reason fails
the scan; an untracked file is never read.

Why this exists (2026-08-31): dspy hard-depends on diskcache, whose only release
is affected by PYSEC-2026-2447 with no fixed version. The estate had no way to
record that decision, so the pin was unmergeable. The mature tool already has the
mechanism (--ignore-vuln); the scanner just never passed it. The reason is
mandatory and every dismissal is a receipt line, so nothing is silenced invisibly.

The fake pip-audit fails unless --ignore-vuln PYSEC-TEST-1 is on its argv, so no
network is touched and the branch under test is the only thing measured.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "estate-security-scan"
GIT = shutil.which("git") or "/usr/bin/git"

FAKE = """#!/usr/bin/env bash
# Fake pip-audit: clean only when the dismissal flag is passed through.
for a in "$@"; do
  if [ "$a" = PYSEC-TEST-1 ]; then echo "No known vulnerabilities found"; exit 0; fi
done
echo "Found 1 known vulnerability in 1 package"; exit 1
"""


def _repo(tmp_path: Path, ignores: str | None, tracked: bool = True) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    env = _env()
    subprocess.run([GIT, "init", "-q", repo], check=True, env=env)
    (repo / "requirements.txt").write_text("diskcache==5.6.3\n")
    paths = ["requirements.txt"]
    if ignores is not None:
        (repo / ".pip-audit-ignores").write_text(ignores)
        if tracked:
            paths.append(".pip-audit-ignores")
    subprocess.run([GIT, "-C", repo, "add", *paths], check=True, env=env)
    subprocess.run([GIT, "-C", repo, "commit", "-qm", "t"], check=True, env=env)
    return repo


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }


def _run(repo: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir(exist_ok=True)
    fake = fakebin / "pip-audit"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {**_env(), "PATH": f"{fakebin}:{os.environ['PATH']}"}
    return subprocess.run(
        [str(SCRIPT), "--source", str(repo)], capture_output=True, text=True, env=env
    )


def test_a_reasoned_tracked_dismissal_passes_and_lands_in_the_receipt(tmp_path):
    repo = _repo(tmp_path, "PYSEC-TEST-1 no fixed release exists; local cache only\n")
    out = _run(repo, tmp_path)
    assert "dismissed PYSEC-TEST-1: no fixed release exists" in out.stdout, out.stdout
    assert "ok    deps" in out.stdout, out.stdout


def test_an_entry_with_no_reason_is_refused(tmp_path):
    repo = _repo(tmp_path, "PYSEC-TEST-1\n")
    out = _run(repo, tmp_path)
    assert "has no reason" in out.stdout, out.stdout
    assert "SECURITY-SCAN FAIL" in out.stdout, out.stdout


def test_an_untracked_ignore_file_is_never_read(tmp_path):
    repo = _repo(tmp_path, "PYSEC-TEST-1 a reason\n", tracked=False)
    out = _run(repo, tmp_path)
    assert "dismissed" not in out.stdout, out.stdout
    assert "FAIL  deps" in out.stdout, out.stdout
