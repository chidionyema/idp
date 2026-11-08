"""The estate's test selector must never report green when its base is absent.

A real shallow Git clone reproduces the CI checkout that previously printed
'fatal: bad revision origin/main...HEAD' and still selected an unrelated subset.
No external GitHub access: use a bare file:// origin.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "bin/idp-tests-for"


def git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       timeout=20, check=True)  # noqa: S603,S607
    return p.stdout.strip()


@pytest.fixture()
def shallow(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", str(origin))
    git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
    work = tmp_path / "work"
    git(tmp_path, "clone", str(origin), str(work))
    git(work, "config", "user.email", "agent@example.test")
    git(work, "config", "user.name", "CI Agent")
    git(work, "checkout", "-b", "main")
    (work / "bin").mkdir()
    shutil.copy2(SOURCE, work / "bin/idp-tests-for")
    (work / "tests").mkdir()
    (work / "tests/slow-files.txt").write_text("# none\n")
    (work / "tests/test_application_settings.py").write_text(
        'from pathlib import Path\nCONFIG = "settings/app.yaml"\n')
    (work / "settings").mkdir()
    (work / "settings/app.yaml").write_text("enabled: false\n")
    git(work, "add", ".")
    git(work, "commit", "-m", "base")
    git(work, "push", "-q", "origin", "main")

    git(work, "checkout", "-b", "lane/candidate")
    (work / "settings/app.yaml").write_text("enabled: true\n")
    git(work, "add", ".")
    git(work, "commit", "-m", "real config change")
    git(work, "push", "-q", "origin", "lane/candidate")
    checkout = tmp_path / "shallow"
    git(tmp_path, "clone", "--depth=1", "--single-branch",
        "--branch", "lane/candidate", "file://" + str(origin), str(checkout))
    assert git(checkout, "rev-parse", "--is-shallow-repository") == "true"
    assert subprocess.run(["git", "rev-parse", "--verify", "origin/main"],
                          cwd=checkout, capture_output=True).returncode != 0  # noqa: S603,S607
    return checkout


def select(work: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "bin/idp-tests-for", "--list", *args],
                          cwd=work, capture_output=True, text=True,
                          timeout=30, env=dict(os.environ, CI="",
                                               SKIP_TESTS_ON_TRIVIAL="0"))  # noqa: S603


def test_missing_main_is_fetched_and_real_changed_test_selected(shallow: Path):
    p = select(shallow)
    assert p.returncode == 0, p.stderr + p.stdout
    assert "tests/test_application_settings.py" in p.stdout
    assert "BLIND" not in p.stdout + p.stderr
    assert git(shallow, "rev-parse", "--verify", "origin/main")


def test_explicit_unavailable_base_is_never_treated_as_empty_diff(shallow: Path):
    p = select(shallow, "--base", "nonexistent-base")
    assert p.returncode == 2
    assert "BLIND tests-for: missing explicit base" in p.stderr
    assert "nothing changed" not in p.stdout


def test_unreachable_main_is_blind_not_green(shallow: Path):
    git(shallow, "remote", "set-url", "origin", "file:///no-such-estate-origin.git")
    p = select(shallow)
    assert p.returncode == 2
    assert "BLIND tests-for" in p.stderr
    assert "nothing changed" not in p.stdout
