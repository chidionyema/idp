"""Incident 2026-08-30 10:12Z: security-scan on crew#712 reported BLIND for a repository
whose requirements files were correct.

Root cause: bin/estate-security-scan resolved every tracked requirements*.txt in ONE
pip-audit run. crew's requirements-research.txt pins openai<3 (litellm's ceiling) and
requirements-grade.txt pins openai>=3.1 (Inspect's floor); they feed two interpreters
on purpose, so their union can never install. The scan then fell to the --no-deps
path, which refuses any '>=' pin, and reported BLIND. Rule: when the joint environment
does not build, each file is resolved and audited on its own before anything is given
up; only when a single file cannot install does the pins-as-written fallback run.

The test puts a fake pip-audit on PATH that refuses two -r arguments together and
accepts each alone, so no network is touched and the branch under test is the only
thing measured.
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
# Fake pip-audit: joint install of two files fails, each file alone is clean.
n=0; for a in "$@"; do [ "$a" = -r ] && n=$((n+1)); done
if [ $n -ge 2 ]; then echo "Failed to install packages: ResolutionImpossible" >&2; exit 1; fi
echo "No known vulnerabilities found"
"""


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(  # noqa: S603
        [GIT, "-C", str(repo), "init", "-q", "-b", "main"], check=True, env=env
    )
    (repo / "requirements-a.txt").write_text("openai>=2,<3\n")
    (repo / "requirements-b.txt").write_text("openai>=3.1,<4\n")
    subprocess.run([GIT, "-C", str(repo), "add", "."], check=True, env=env)  # noqa: S603
    subprocess.run(  # noqa: S603
        [GIT, "-C", str(repo), "commit", "-q", "-m", "two files"], check=True, env=env
    )
    return repo


def test_two_files_that_only_conflict_together_are_audited_one_at_a_time(
    tmp_path: Path,
) -> None:
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    fake = fakebin / "pip-audit"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "PATH": f"{fakebin}:{os.environ['PATH']}"}
    r = subprocess.run(  # noqa: S603
        [str(SCRIPT), "--quiet", "--source", str(_repo(tmp_path))],
        capture_output=True,
        text=True,
        env=env,
    )
    deps = next(line for line in r.stdout.splitlines() if " deps " in line)
    assert deps.startswith("ok") and "one file at a time" in deps, r.stdout + r.stderr
