"""#5814: .githooks/pre-push hands bin/idp-ci the merge base, so a push is graded on its own diff.

bin/idp-ci reads "no IDP_CI_BASE" as "everything changed" -- right for main, where the merged
state gets the full sweep, and wrong for a push. Before #6191 the hook passed no base: a push of
seven Python and YAML files ran tsc over backstage (36-175 s) and the hook alone took 61 s
against the 50 s lane-submit gives its push, so every `estate-execute lane-submit` timed out and
the lane went out by hand (2026-10-14, lane/image-updates-single-writer, 2m15s). These pushes are
real: a bare origin, a clone with the real hook, and bin/idp-ci stubbed to record what it was
asked to grade.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-push"

STUB = """#!/bin/sh
echo "fast=$IDP_CI_FAST base=$IDP_CI_BASE" >> "${STUB_LOG:-/dev/null}"
"""


def git(cwd: Path, *a: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


@pytest.fixture
def clone(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    hooks = work / ".hooks"
    hooks.mkdir()
    shutil.copy(HOOK, hooks / "pre-push")
    git(work, "config", "core.hooksPath", str(hooks))
    (work / "bin").mkdir()
    ci = work / "bin" / "idp-ci"
    ci.write_text(STUB)
    ci.chmod(0o755)
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt", "bin/idp-ci")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    return work


def push(work: Path, branch: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IDP_CI_")}
    env["STUB_LOG"] = str(work.parent / "ci.log")
    return git(work, "push", "origin", f"HEAD:{branch}", env=env, check=False)


def ci_calls(work: Path) -> list[str]:
    log = work.parent / "ci.log"
    return log.read_text().splitlines() if log.exists() else []


def commit(work: Path, name: str) -> None:
    (work / name).write_text(name + "\n")
    git(work, "add", name)
    git(work, "commit", "-q", "-m", name)


def test_a_push_is_graded_from_where_it_leaves_main(clone):
    base = git(clone, "rev-parse", "origin/main").stdout.strip()
    commit(clone, "b.txt")
    p = push(clone, "scratch/b")
    assert p.returncode == 0, p.stderr
    assert ci_calls(clone) == [f"fast=1 base={base}"]


def test_main_moving_on_does_not_widen_the_grade(clone):
    base = git(clone, "rev-parse", "origin/main").stdout.strip()
    commit(clone, "b.txt")
    # Someone else lands on main after this branch was cut; the diff is still b.txt alone.
    other = clone.parent / "other"
    git(clone.parent, "clone", "-q", str(clone.parent / "origin.git"), str(other))
    commit(other, "c.txt")
    git(other, "push", "-q", "origin", "HEAD:main")
    git(clone, "fetch", "-q", "origin")
    push(clone, "scratch/b")
    assert ci_calls(clone) == [f"fast=1 base={base}"]


def test_a_base_is_never_empty_on_a_push(clone):
    commit(clone, "b.txt")
    push(clone, "scratch/b")
    [call] = ci_calls(clone)
    assert not call.endswith("base="), call
