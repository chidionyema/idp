"""Incident 2026-08-27 21:00Z: security-scan went red on every open idp PR at once.

Root cause: bin/estate-security-scan ran `gitleaks detect` with no --log-opts, which
walks every ref in the checkout, and .github/actions/security-scan fetches with
fetch-depth 0, so an 18-char literal committed on ONE unmerged peer branch (3bf04ab,
feat/crew539-priority-balloon-ping) failed idp#479 and #486-#492 - PRs that never
contained it. Rule: the scan reads the history reachable from HEAD only, so a branch
can fail only its own PR. The leak still cannot reach main: the PR carrying it has
the literal in its HEAD history and fails on its own.

The test builds a throwaway repository with a fake key on a side branch and runs the
real script both ways: clean on main, FAIL on the branch. Skipped only when gitleaks
is not installed (the script reports BLIND, never a verdict, in that case).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(os.environ.get("ESTATE_SECURITY_SCAN", Path(__file__).resolve().parents[1] / "bin" / "estate-security-scan"))
pytestmark = pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not on PATH")


def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env=env).stdout


def _scan(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(SCRIPT), "--quiet", "--source", str(repo)], capture_output=True, text=True)


@pytest.fixture
def repo_with_leak_on_side_branch(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("clean\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "clean main")
    _git(repo, "checkout", "-q", "-b", "peer")
    # a made-up token shaped like a GitHub PAT (gitleaks rule github-pat); never a real credential
    fake = "ghp_" + "".join(chr(ord("A") + (i * 7) % 26) for i in range(36))
    (repo / "cfg.yml").write_text(f"github_token: {fake}\n")
    _git(repo, "add", "cfg.yml")
    _git(repo, "commit", "-q", "-m", "peer leaks")
    _git(repo, "checkout", "-q", "main")
    return repo


def test_a_leak_on_another_branch_does_not_fail_this_checkout(repo_with_leak_on_side_branch: Path) -> None:
    r = _scan(repo_with_leak_on_side_branch)
    secrets_line = next(line for line in r.stdout.splitlines() if "secrets" in line)
    assert secrets_line.startswith("ok"), r.stdout + r.stderr


def test_the_branch_that_carries_the_leak_still_fails(repo_with_leak_on_side_branch: Path) -> None:
    _git(repo_with_leak_on_side_branch, "checkout", "-q", "peer")
    r = _scan(repo_with_leak_on_side_branch)
    secrets_line = next(line for line in r.stdout.splitlines() if "secrets" in line)
    assert secrets_line.startswith("FAIL"), r.stdout + r.stderr
    assert r.returncode == 1
