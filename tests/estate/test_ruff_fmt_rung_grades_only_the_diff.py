"""The ruff-fmt rung grades what the push changes, not the whole repo (2026-10-22).

Main carried one unwrapped `assert` in tests/test_image_builds.py -- another agent's claim, so no
lane's author could touch it -- and because the rung checked all 5,000 Python files on every run,
every lane in the estate was refused by the pre-push hook and left red in the Greenlane for code it
never wrote. Work stopped landing.

These tests run the shipped bytes of the rung, lifted out of bin/idp-ci between its `# 1d.3:` and
`# 1d.4:` markers, against a real git repo whose main already contains an unformatted file. That is
the case that matters: a file outside the diff must not fail the rung, and a file inside it must.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
IDP_CI = ROOT / "bin" / "idp-ci"
RUFF = shutil.which("ruff")

FORMATTED = "x = 1\n"
UNFORMATTED = "x=1\n"


def _rung() -> str:
    text = IDP_CI.read_text()
    start = text.index("# 1d.3:")
    end = text.index("# 1d.4:")
    rung = text[start:end]
    assert "ruff" in rung, (
        "the rung markers moved; this test would otherwise grade nothing"
    )
    return rung


def git(cwd: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=True
    )


@pytest.fixture
def repo(tmp_path):
    work = tmp_path / "repo"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    # main already carries a file ruff would reformat -- nobody's lane may be blamed for it
    (work / "stale.py").write_text(UNFORMATTED)
    (work / "fine.py").write_text(FORMATTED)
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "main with an unformatted file")
    git(work, "checkout", "-q", "-b", "lane/x")
    return work


def _run(repo: Path, base: str | None) -> subprocess.CompletedProcess:
    script = ('IDP=%s\nRUFF=(%s)\nsay() { echo "$*"; }\nfail=0\n%s\nexit $fail\n') % (
        str(repo),
        str(RUFF),
        _rung(),
    )
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(repo.parent)}
    if base:
        env["IDP_CI_BASE"] = base
    return subprocess.run(
        ["/bin/bash", "-c", script], cwd=repo, env=env, capture_output=True, text=True
    )


@pytest.mark.skipif(RUFF is None, reason="ruff is not installed")
def test_a_file_already_unformatted_on_main_does_not_fail_a_lane(repo):
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "lane.py").write_text(FORMATTED)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "lane work")
    result = _run(repo, base)
    seen = result.stdout + result.stderr
    assert result.returncode == 0, seen
    assert "ruff-fmt 1 file(s) in the diff" in seen, seen
    assert "stale.py" not in seen, seen


@pytest.mark.skipif(RUFF is None, reason="ruff is not installed")
def test_an_unformatted_file_in_the_diff_still_fails_the_lane(repo):
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "lane.py").write_text(UNFORMATTED)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "lane work, unformatted")
    result = _run(repo, base)
    seen = result.stdout + result.stderr
    assert result.returncode == 1, seen
    assert "FAIL" in seen and "lane.py" in seen, seen


@pytest.mark.skipif(RUFF is None, reason="ruff is not installed")
def test_with_no_base_the_whole_repo_is_still_graded(repo):
    """main's own sweep: no base means everything, exactly as before."""
    result = _run(repo, None)
    seen = result.stdout + result.stderr
    assert result.returncode == 1, seen
    assert "whole repo" in seen and "stale.py" in seen, seen
