"""The root suite must not be able to go green over a failing new test.

Measured 2026-10-29 on the Greenlane candidate 6708a6cd (run 40841861081, job 123340048564):
the `bdd-suites (tests, all)` leg checked the candidate out at fetch-depth 1, so `origin/main`
was never fetched. `git diff origin/main...HEAD` failed with "fatal: bad revision
'origin/main...HEAD'", `bin/idp-tests-for` degraded to "nothing changed against origin/main,
nothing to run" and exited 0 -- and the candidate went green over a new test that fails
locally. It landed on main.

The rule the offline-gate already obeys -- its checkout is fetch-depth 0, asserted by
tests/test_queue_candidate_is_graded_on_its_diff.py -- was missing from the leg that grades the
root suite, which is the leg that would have caught the failing test.

Three things have to hold, and this file proves all three against the real script and the real
workflow:

  1. a base with no merge base is BLIND -- exit 2, never a silent pass -- including the shape
     CI actually had, where `origin/main` RESOLVED and the merge base still did not;
  2. a resolvable base selects the candidate's own new test file, so the suite that grades a
     candidate really sees the candidate;
  3. a push to main is not blind: `origin/main == HEAD` is a legitimate empty diff.

The script is copied into a throwaway repository because it grades the tree it sits in
(`dirname $0/..`), so the copy under <tmp>/bin/ grades <tmp>. `--for PATH` stays git-free and
is proven here too: a hypothetical path has no base, and the guard must not make it blind.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

IDP = Path(__file__).resolve().parent.parent
SELECTOR = IDP / "bin" / "idp-tests-for"
CI = IDP / ".github" / "workflows" / "ci.yml"

CANDIDATE_TEST = "tests/test_the_candidate_s_own_rule.py"

GIT = (
    "git",
    "-c",
    "user.email=probe@example.invalid",
    "-c",
    "user.name=probe",
    "-c",
    "commit.gpgsign=false",
)


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        GIT + ("-C", str(cwd)) + args,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _source(tmp_path: Path) -> Path:
    """A repository with a base commit on main and a candidate branch that adds a test."""
    src = tmp_path / "src"
    src.mkdir()
    _git(src, "init", "-q")
    _git(src, "checkout", "-q", "-b", "main")
    (src / "README.md").write_text("the base commit\n")
    _git(src, "add", "-A")
    _git(src, "commit", "-q", "-m", "base")
    _git(src, "checkout", "-q", "-b", "candidate")
    (src / "tests").mkdir()
    (src / CANDIDATE_TEST).write_text(
        "def test_the_candidate_s_own_rule():\n    assert True\n"
    )
    _git(src, "add", "-A")
    _git(src, "commit", "-q", "-m", "the candidate adds a test")
    # The clone's default branch must be main, so the clone below is not already on candidate.
    _git(src, "checkout", "-q", "main")
    return src


def _clone(src: Path, dest: Path, *args: str) -> Path:
    subprocess.run(
        ["git", "clone", "-q", *args, src.resolve().as_uri(), str(dest)],
        capture_output=True,
        text=True,
        check=True,
    )
    return dest


@pytest.fixture(scope="session")
def source(tmp_path_factory) -> Path:
    """One source repository for the whole session: the tests only ever clone from it."""
    return _source(tmp_path_factory.mktemp("source"))


def _selector_in(repo: Path) -> Path:
    """The real script, in the tree it is going to grade."""
    (repo / "bin").mkdir(parents=True, exist_ok=True)
    dst = repo / "bin" / "idp-tests-for"
    shutil.copy2(SELECTOR, dst)
    dst.chmod(0o755)
    return dst


def _select(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CI"] = "1"
    env["TESTS_FOR_ALL"] = "0"
    return subprocess.run(
        ["bash", str(repo / "bin" / "idp-tests-for"), "--list", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo),
    )


def test_a_missing_diff_base_is_blind_never_a_pass(source, tmp_path):
    """The candidate checkout CI used: shallow, and origin/main never fetched."""
    src = source
    cand = _clone(src, tmp_path / "cand", "--depth", "1", "--branch", "candidate")
    _selector_in(cand)
    proc = _select(cand, "--base", "origin/main")
    said = proc.stdout + proc.stderr
    assert proc.returncode == 2, said
    assert "BLIND" in said, said
    assert "origin/main" in said, said


def test_a_resolved_ref_with_no_merge_base_is_blind(source, tmp_path):
    """The shape CI actually had after a depth-1 fetch of main.

    `origin/main` resolves here -- `git rev-parse origin/main` succeeds -- and the merge base
    still does not, because the candidate's own ancestry is truncated at the shallow boundary.
    A guard that only asked whether the ref resolves would call this a pass.
    """
    src = source
    cand = _clone(src, tmp_path / "cand", "--depth", "1", "--branch", "candidate")
    _git(cand, "fetch", "-q", "--depth", "1", "origin", "main:refs/remotes/origin/main")
    assert _git(cand, "rev-parse", "origin/main").strip()  # the ref resolves
    _selector_in(cand)
    proc = _select(cand, "--base", "origin/main")
    said = proc.stdout + proc.stderr
    assert proc.returncode == 2, said
    assert "BLIND" in said, said


def test_a_resolvable_base_selects_the_candidate_s_own_test(source, tmp_path):
    """The suite that grades a candidate has to see the candidate."""
    src = source
    full = _clone(src, tmp_path / "full")
    _git(full, "checkout", "-q", "-b", "candidate", "origin/candidate")
    _selector_in(full)
    proc = _select(full, "--base", "origin/main")
    said = proc.stdout + proc.stderr
    assert proc.returncode == 0, said
    assert CANDIDATE_TEST in proc.stdout, said


def test_a_push_to_main_is_not_blind(source, tmp_path):
    """origin/main == HEAD is an empty diff, and an empty diff is the truth there."""
    src = source
    mainco = _clone(src, tmp_path / "mainco", "--depth", "1", "--branch", "main")
    _selector_in(mainco)
    proc = _select(mainco, "--base", "origin/main")
    said = proc.stdout + proc.stderr
    assert proc.returncode == 0, said
    assert "BLIND" not in said, said


def test_for_a_path_stays_git_free(source, tmp_path):
    """--for PATH has no base and no diff: the guard must not make it blind."""
    src = source
    cand = _clone(src, tmp_path / "cand", "--depth", "1", "--branch", "candidate")
    _selector_in(cand)
    proc = _select(cand, "--for", CANDIDATE_TEST)
    said = proc.stdout + proc.stderr
    assert proc.returncode == 0, said
    assert "BLIND" not in said, said
    assert CANDIDATE_TEST in proc.stdout, said


def test_the_tests_leg_checks_out_with_the_whole_history():
    """The grant the offline-gate already has, applied to the leg that grades the root suite.

    Without it the base cannot resolve, and the selector is BLIND on every candidate.
    """
    job = yaml.safe_load(CI.read_text())["jobs"]["bdd-suites"]
    checkout = next(s for s in job["steps"] if "checkout" in s.get("uses", ""))
    depth = checkout["with"]["fetch-depth"]
    if isinstance(depth, str) and "matrix.depth" in depth:
        rows = {row["suite"]: row for row in job["strategy"]["matrix"]["include"]}
        depth = rows["tests"]["depth"]
    assert depth == 0, (
        f"the tests leg checks out at depth {depth}; origin/main and the merge base must resolve"
    )
