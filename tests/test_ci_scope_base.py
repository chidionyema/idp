"""The falsifier for the CI scope-base class (2026-11-05).

Measured failure: every Greenlane batch was red and nothing landed (run 41944852174, the
ui-kit job). The Greenlane pushes each candidate as a FRESH refs/heads/queue/<batch> branch,
so github.event.before is forty zeros on every candidate. The ui-kit job's scope limiter
answered a base it could not name with "judge EVERYTHING":

    case "$base" in ''|0000000000000000000000000000000000000000) echo "yes=true"; exit 0;; esac

so the kit-import guard ran over the whole tree and refused two front ends that never
migrated to the kit (deadline 2026-10-31). A docs-only lane was red on a gate it never
touched. The estate had already written the correct rule down three times (greenlane/
github.py, verifier.yml, portal-app.yml): a candidate grades against origin/main.

These tests are the falsifier for the fix, and they are two-sided on purpose:

  - the known-BAD fixture: a candidate that DOES touch a front end is still judged. The fix
    must not turn the gate off, only point it at the right diff (a gate that cannot fail is
    not a gate);
  - the known-GOOD fixture: a candidate that touches nothing under the paths is not judged
    by that gate at all;
  - the fail-closed fixture: when no base can be named the answer is YES, never NO. "Cannot
    judge" must never read as "nothing changed".

Every repository here is a throwaway one created by the test. The estate's own repository is
never touched.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "bin" / "idp-ci-base"
TOUCHED = ROOT / "bin" / "idp-ci-touched"
ZEROS = "0" * 40

GIT_LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _env() -> dict:
    env = dict(os.environ)
    for name in GIT_LOCATION_VARS:
        env.pop(name, None)
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


def _git(repo: Path, *argv: str) -> str:
    p = subprocess.run(
        ["git", *argv],
        cwd=repo,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0, f"git {' '.join(argv)} failed: {p.stderr}"
    return p.stdout.strip()


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _init(repo: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=repo, env=_env(), check=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository shaped like the estate's: a main branch, and two candidates.

    `refs/remotes/origin/main` is written by hand so that "origin/main" resolves without a
    remote -- the estate's own runner fetches it, and the rule under test is about WHICH
    base is named, not about how it is fetched.
    """
    r = tmp_path / "repo"
    r.mkdir()
    _init(r)
    _write(r, "docs/decisions/0001-a.md", "a decision\n")
    _write(r, "web/app/globals.css", ":root {}\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "main")
    main_sha = _git(r, "rev-parse", "HEAD")
    _git(r, "update-ref", "refs/remotes/origin/main", main_sha)

    # a candidate that touches only the docs
    _git(r, "checkout", "-q", "-b", "queue/docs-only")
    _write(r, "docs/decisions/0002-b.md", "another decision\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "docs only")

    # a candidate that touches a front end
    _git(r, "checkout", "-q", "main")
    _git(r, "checkout", "-q", "-b", "queue/front-end")
    _write(r, "web/app/globals.css", ":root { --x: 1; }\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "a front end")
    _git(r, "checkout", "-q", "main")
    return r


@pytest.fixture
def bare_repo(tmp_path: Path) -> Path:
    """A repository where NO base can be named: no origin/main, no merge base, no before."""
    r = tmp_path / "bare"
    r.mkdir()
    _init(r)
    _write(r, "README.md", "no base here\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "main")
    return r


def _run(script: Path, repo: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--repo", str(repo), *argv],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
        cwd=repo,
    )


def _base(repo: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return _run(BASE, repo, *argv)


def _answer(repo: Path, paths: str, *argv: str) -> str:
    p = _run(TOUCHED, repo, "--paths", paths, *argv)
    assert p.returncode == 0, p.stderr
    return (p.stdout or "").strip()


# --------------------------------------------------------------------------------------
# the base, per event shape
# --------------------------------------------------------------------------------------


def test_a_greenlane_candidate_grades_against_main(repo: Path):
    """The measured failure: before is forty zeros on a fresh queue branch, and the answer
    is main -- the same grade a fresh branch would get."""
    p = _base(
        repo,
        "--event-name",
        "push",
        "--ref",
        "refs/heads/queue/b4733",
        "--before",
        ZEROS,
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "origin/main"


def test_a_first_push_to_any_other_branch_grades_against_main(repo: Path):
    p = _base(
        repo, "--event-name", "push", "--ref", "refs/heads/lane/x", "--before", ZEROS
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "origin/main"


def test_a_pull_request_grades_against_its_target(repo: Path):
    p = _base(
        repo,
        "--event-name",
        "pull_request",
        "--ref",
        "refs/pull/1/merge",
        "--base-ref",
        "main",
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "origin/main"

    sha = _git(repo, "rev-parse", "HEAD")
    p = _base(
        repo,
        "--event-name",
        "pull_request",
        "--ref",
        "refs/pull/1/merge",
        "--base-ref",
        "main",
        "--pr-base-sha",
        sha,
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == sha


def test_a_workflow_call_still_grades_a_pull_request_against_its_target(repo: Path):
    """A called workflow sees github.event_name == "workflow_call" while the payload still
    carries the pull request, so the rule is asked of the PAYLOAD, not of the event name."""
    sha = _git(repo, "rev-parse", "HEAD")
    p = _base(
        repo,
        "--event-name",
        "workflow_call",
        "--ref",
        "refs/pull/1/merge",
        "--pr-base-sha",
        sha,
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == sha


def test_a_push_grades_against_the_range_it_moved(repo: Path):
    sha = _git(repo, "rev-parse", "HEAD")
    p = _base(
        repo, "--event-name", "push", "--ref", "refs/heads/lane/x", "--before", sha
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == sha


def test_a_merge_group_grades_against_its_base(repo: Path):
    sha = _git(repo, "rev-parse", "HEAD")
    p = _base(
        repo,
        "--event-name",
        "merge_group",
        "--ref",
        "refs/heads/gh-readonly-queue/main",
        "--merge-group-base",
        sha,
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == sha


def test_a_base_that_is_not_in_the_checkout_falls_through_to_the_next_rule(repo: Path):
    """A before that was never fetched (a force-push) cannot be diffed against. The next
    rule is tried -- origin/main -- instead of dying on a bad object."""
    p = _base(
        repo, "--event-name", "push", "--ref", "refs/heads/lane/x", "--before", "1" * 40
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "origin/main"


def test_no_base_at_all_is_blind_not_a_pass(bare_repo: Path):
    """When nothing can be named, the answer is BLIND -- so the caller judges everything.
    Never an empty diff that reads as 'nothing changed'."""
    p = _base(
        bare_repo,
        "--event-name",
        "push",
        "--ref",
        "refs/heads/lane/x",
        "--before",
        "1" * 40,
    )
    assert p.returncode == 2, p.stdout
    assert "BLIND" in p.stderr


# --------------------------------------------------------------------------------------
# the two-sided falsifier: the gate still judges what it must judge
# --------------------------------------------------------------------------------------


def test_a_candidate_that_touches_a_front_end_is_still_judged(repo: Path):
    """The known-BAD fixture: the fix must point the gate at the right diff, not switch it
    off. A candidate that changes web/ is judged."""
    _git(repo, "checkout", "-q", "queue/front-end")
    assert (
        _answer(
            repo,
            "web/",
            "--event-name",
            "push",
            "--ref",
            "refs/heads/queue/x",
            "--before",
            ZEROS,
        )
        == "yes=true"
    )
    _git(repo, "checkout", "-q", "main")


def test_a_candidate_that_touches_nothing_under_the_paths_is_not_judged(repo: Path):
    """The known-GOOD fixture: the docs-only lane is not judged by the front-end gate."""
    _git(repo, "checkout", "-q", "queue/docs-only")
    assert (
        _answer(
            repo,
            "web/",
            "--event-name",
            "push",
            "--ref",
            "refs/heads/queue/x",
            "--before",
            ZEROS,
        )
        == "yes=false"
    )
    _git(repo, "checkout", "-q", "main")


def test_cannot_judge_is_never_nothing_changed(bare_repo: Path):
    """Fail closed. A base that cannot be named answers YES: a gate that cannot judge must
    not pass (AGENTS.md section 9, R1)."""
    assert (
        _answer(
            bare_repo,
            "web/",
            "--event-name",
            "push",
            "--ref",
            "refs/heads/lane/x",
            "--before",
            "1" * 40,
        )
        == "yes=true"
    )


def test_a_base_that_is_the_head_judges_everything(repo: Path):
    """There is no range to measure when the base IS the head: judge everything."""
    head = _git(repo, "rev-parse", "HEAD")
    assert _answer(repo, "web/", "--base", head) == "yes=true"


def test_the_answer_is_written_to_the_workflow_output(repo: Path):
    out = repo / "gh-output"
    out.write_text("", encoding="utf-8")
    p = subprocess.run(
        [
            sys.executable,
            str(TOUCHED),
            "--repo",
            str(repo),
            "--paths",
            "web/",
            "--base",
            "origin/main",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**_env(), "GITHUB_OUTPUT": str(out)},
        cwd=repo,
    )
    assert p.returncode == 0, p.stderr
    assert "yes=" in out.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------
# the sweep: no workflow keeps its own copy of the rule
# --------------------------------------------------------------------------------------


WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/portal-app.yml",
    ".github/workflows/guarded-paths.yml",
    ".github/workflows/verifier.yml",
)


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_no_workflow_answers_a_zero_base_with_judge_everything(workflow: str):
    """The defect, as it was written: a base of forty zeros answered with 'yes=true'."""
    text = (ROOT / workflow).read_text(encoding="utf-8")
    offenders = [
        line
        for line in text.splitlines()
        if "0000000000000000000000000000000000000000" in line and "yes=true" in line
    ]
    assert not offenders, (
        f"{workflow} still answers a zero base with yes=true: {offenders}"
    )


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_every_workflow_scope_limiter_asks_the_one_script(workflow: str):
    """One rule, one copy: the workflows ask bin/idp-ci-base / bin/idp-ci-touched."""
    text = (ROOT / workflow).read_text(encoding="utf-8")
    assert "idp-ci-base" in text or "idp-ci-touched" in text, (
        f"{workflow} does not go through the one base resolver"
    )


def test_the_ui_kit_job_asks_the_one_script():
    """The job that was red on every batch."""
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    job = ci["jobs"]["ui-kit"]
    step = next(s for s in job["steps"] if s.get("id") == "touched")
    assert "idp-ci-touched" in step["run"]


def test_the_base_is_fetched_where_it_is_diffed():
    """`origin/main...HEAD` needs main's history on the runner; on a shallow clone the diff
    fails, and a scope limiter that cannot diff must judge everything, not nothing."""
    for workflow in WORKFLOWS:
        wf = yaml.safe_load((ROOT / workflow).read_text(encoding="utf-8"))
        for job in wf["jobs"].values():
            for step in job.get("steps", []) or []:
                uses = step.get("uses", "")
                if "actions/checkout" not in uses:
                    continue
                depth = (step.get("with") or {}).get("fetch-depth")
                if depth is not None:
                    assert depth == 0, f"{workflow}: checkout without full history"
