"""The DAG-artifact guard must not die on an unreachable base commit.

Measured 2026-10-30 (PR #7492, job 123834033723):

    BEFORE="6e30a21f49b3ac86219bd8d751911a603313840e"
    changed="$(git diff --name-only "$BEFORE" "$GITHUB_SHA" -- ...
    fatal: bad object 6e30a21f49b3ac86219bd8d751911a603313840e
    ##[error]Process completed with exit code 128.

The Greenlane force-pushes a rebased commit onto every lane branch, so the
commit GitHub reports as `before` is unreachable and is never fetched. The guard
that decides whether the DAG needs regenerating therefore failed on every lane
PR (#7484, #7485, #7492) while saying nothing about the DAG.

These tests run the real workflow step and the real launcher in a throwaway git
repository. Nothing here touches the estate's repository.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "bin" / "estate-dag-changed"
WORKFLOW = REPO / ".github" / "workflows" / "estate-dag-gen.yml"
STEP_NAME = "skip when only the vault-seeded IAM file changed"
UNREACHABLE_BASE = "deadbeef" * 5


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(
        repo,
        "-c",
        "user.email=estate@local",
        "-c",
        "user.name=estate",
        "commit",
        "-m",
        message,
    )
    head = _git(repo, "rev-parse", "HEAD")
    assert head.returncode == 0, head.stderr
    return head.stdout.strip()


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "dag-repo"
    (repo / "platform" / "oci").mkdir(parents=True)
    (repo / "docs" / "diagrams").mkdir(parents=True)
    (repo / "bin").mkdir(parents=True)
    (repo / "platform" / "oci" / "main.tf").write_text('resource "x" "y" {}\n')
    (repo / "platform" / "oci" / "github-actions.tf").write_text("iam\n")
    (repo / "docs" / "diagrams" / "estate-dag.dot").write_text("digraph {}\n")
    _git(repo, "init", "-q", "-b", "main")
    # The launcher is part of the first commit, so a later commit contains only
    # the change a test makes on purpose.
    shutil.copy2(LAUNCHER, repo / "bin" / "estate-dag-changed")
    (repo / "bin" / "estate-dag-changed").chmod(0o755)
    _commit(repo, "first")
    return repo


def _run_launcher(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(repo / "bin" / "estate-dag-changed"), *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
    )


def _step_run_block() -> str:
    doc = yaml.safe_load(WORKFLOW.read_text())
    steps = doc["jobs"]["generate-dag"]["steps"]
    for step in steps:
        if step.get("name") == STEP_NAME:
            return step["run"]
    raise AssertionError(f"{STEP_NAME} step not found in {WORKFLOW}")


def test_the_old_inline_diff_really_dies_on_an_unreachable_base(tmp_path):
    """The falsifier: the behaviour being replaced is a real failure, not a story."""
    repo = _make_repo(tmp_path)
    result = _git(repo, "diff", "--name-only", UNREACHABLE_BASE, "HEAD")
    assert result.returncode != 0, "an unreachable base must make git diff fail"
    assert "bad object" in (result.stderr + result.stdout).lower()


def test_the_launcher_answers_with_a_provable_base_instead_of_dying(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "platform" / "oci" / "main.tf").write_text(
        'resource "x" "y" { changed = 1 }\n'
    )
    head = _commit(repo, "second")

    result = _run_launcher(
        repo,
        "--base",
        UNREACHABLE_BASE,
        "--head",
        head,
        "--",
        "platform/oci/**",
        ":!platform/oci/github-actions.tf",
    )
    assert result.returncode == 0, result.stderr
    assert "platform/oci/main.tf" in result.stdout
    assert "fatal" not in result.stderr.lower()


def test_the_launcher_never_refuses_on_a_missing_head(tmp_path):
    repo = _make_repo(tmp_path)
    result = _run_launcher(repo, "--base", UNREACHABLE_BASE, "--head", UNREACHABLE_BASE)
    assert result.returncode == 0, result.stderr


def test_the_workflow_guard_survives_an_unreachable_base(tmp_path):
    """The real step text, run for real, in a throwaway repository."""
    repo = _make_repo(tmp_path)
    (repo / "platform" / "oci" / "main.tf").write_text(
        'resource "x" "y" { changed = 1 }\n'
    )
    head = _commit(repo, "second")

    script = _step_run_block()
    script = script.replace("${{ github.event.before }}", UNREACHABLE_BASE)
    script = script.replace("${{ github.event_name }}", "push")

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GITHUB_SHA": head},
    )
    assert result.returncode == 0, result.stderr
    assert "fatal: bad object" not in (result.stdout + result.stderr)
    assert "bad object" not in (result.stdout + result.stderr).lower()


def test_the_workflow_guard_still_skips_the_vault_seeded_iam_file(tmp_path):
    """crew#6227's exclusion must survive the repair: that file alone is not a DAG change."""
    repo = _make_repo(tmp_path)
    (repo / "platform" / "oci" / "github-actions.tf").write_text("iam changed\n")
    head = _commit(repo, "iam only")

    script = _step_run_block()
    script = script.replace("${{ github.event.before }}", UNREACHABLE_BASE)
    script = script.replace("${{ github.event_name }}", "push")

    result = subprocess.run(
        ["bash", "-c", script],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "GITHUB_SHA": head},
    )
    assert result.returncode == 0, result.stderr
    assert "crew#6227" in result.stdout


def test_the_workflow_no_longer_diffs_against_a_base_it_may_not_have(tmp_path):
    """The step must go through the launcher, or the fatal form can come back."""
    script = _step_run_block()
    assert "bin/estate-dag-changed" in script
    assert 'git diff --name-only "$BEFORE" "$GITHUB_SHA"' not in script
