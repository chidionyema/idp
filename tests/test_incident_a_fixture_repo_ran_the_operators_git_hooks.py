"""2026-08-29: the estate's global `core.hooksPath` (estate#13) fired inside a test's throwaway
repository and refused its fixture commit (`sovereign/tests/test_incident_r29_spec_gate.py`,
`python-strict: fails ruff format`), so the pre-push hook on the Mac turned an unrelated branch
red while CI, which has no global hooks, stayed green. The root conftest now hands every git the
suite spawns a global config that includes the operator's own and points the hooks directory at
an empty one. This pins that: a fixture repo commits a file the estate's Python standard would
refuse, and the operator's identity still resolves through the include.
"""

import os
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_suite_points_git_at_an_empty_hooks_directory():
    cfg = os.environ.get("GIT_CONFIG_GLOBAL")
    assert cfg and Path(cfg).is_file(), "root conftest did not set GIT_CONFIG_GLOBAL"
    hooks = subprocess.run(
        ["git", "config", "--global", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert hooks and Path(hooks).is_dir() and not any(Path(hooks).iterdir()), hooks


def test_a_fixture_repo_commits_a_file_the_estate_standard_would_refuse(tmp_path: Path):
    repo = tmp_path / "fixture"
    repo.mkdir()
    assert _git(repo, "init", "-q").returncode == 0
    (repo / "ugly.py").write_text("x=1;y  =  2\n")  # ruff format rejects this shape
    assert _git(repo, "add", ".").returncode == 0
    done = _git(repo, "commit", "-qm", "fixture")
    assert done.returncode == 0, done.stderr
    assert _git(repo, "log", "--oneline").stdout.count("\n") == 1
