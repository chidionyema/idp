"""bin/idp-ci-guarded-paths must refuse an unsigned PR that touches a guarded path.

2026-09-29: it never had. The diff it graded was `"$BASE"...HEAD_REV` (the literal word, not the
variable); git refused the revision, `|| true` swallowed the refusal, and the changed-file list was
always empty, so every PR touching a guarded path passed. Proved the same day by committing an
unsigned edit to bin/idp-guarded-paths and watching the guard answer "ok".

Each test builds a throwaway repository holding the real guard scripts and the real founder public
key, makes one commit on top of `main`, and runs the guard the way the guarded-paths workflow does.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["bin/idp-guarded-paths", "bin/idp-ci-guarded-paths", "bin/idp-auth-verify"]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for rel in [*SCRIPTS, "docs/keys/founder.pub"]:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, repo / rel)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "agent@example.invalid")
    _git(repo, "config", "user.name", "agent")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _guard_after_touching(tmp_path: Path, rel: str) -> subprocess.CompletedProcess:
    repo = _repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "pr")
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    with (repo / rel).open("a") as f:
        f.write("\n// an agent's edit\n")
    _git(repo, "add", "-A")
    # Stamped like a hook-signed commit, so only the guarded-path rule can refuse it.
    _git(repo, "commit", "-q", "-m", "edit\n\nX-Idp-Signed: stamped-by-hook")
    return subprocess.run(
        ["bash", "bin/idp-ci-guarded-paths", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_an_unsigned_edit_to_the_fleet_surface_is_refused(tmp_path):
    r = _guard_after_touching(
        tmp_path, "backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx"
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "WITHOUT valid X-Idp-Auth" in r.stdout
    assert "backstage/packages/app/src/modules/room/" in r.stdout


def test_an_unsigned_edit_to_the_guard_itself_is_refused(tmp_path):
    r = _guard_after_touching(tmp_path, "bin/idp-guarded-paths")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "WITHOUT valid X-Idp-Auth" in r.stdout


def test_an_edit_outside_the_guarded_set_passes(tmp_path):
    r = _guard_after_touching(tmp_path, "docs/notes/anything.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout


def test_a_base_that_does_not_resolve_refuses(tmp_path):
    repo = _repo(tmp_path)
    r = subprocess.run(
        ["bash", "bin/idp-ci-guarded-paths", "no-such-base"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "does not resolve" in r.stdout
