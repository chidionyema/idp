"""Real-git falsifiers: a stale cloud agent must not lose its sealed patch.

These run the same trusted entrypoint as the hosted submit-lane job. A mock
cannot prove git checkout, ancestor checks, patch application or protected-path
refusal, so each case builds a disposable real repository.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[1] / "bin/idp-agent-base-apply.py"


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check,
                          capture_output=True, text=True)


@pytest.fixture
def estate(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "Agent-Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "asset.txt").write_text("original\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "asset.txt").write_text("agent revision\n", encoding="utf-8")
    patch = tmp_path / "agent.patch"
    patch.write_text(git(repo, "diff", "--binary").stdout, encoding="utf-8")
    git(repo, "checkout", "--", "asset.txt")
    (repo / "asset.txt").write_text("new main revision\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "main advanced independently")
    main = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "update-ref", "refs/remotes/origin/main", main)
    base_file = tmp_path / "base"
    base_file.write_text(base + "\n", encoding="ascii")
    return repo, base_file, patch, base, main


def run(estate):
    repo, base_file, patch, _, _ = estate
    return subprocess.run(
        [sys.executable, str(HELPER), "--base-file", str(base_file),
         "--patch", str(patch)],
        cwd=repo, text=True, capture_output=True,
    )


def test_original_base_is_applied_without_rewriting_or_force_pushing_main(estate):
    repo, _, _, base, main = estate
    result = run(estate)
    assert result.returncode == 0, result.stderr
    proof = json.loads(result.stdout)
    assert proof["decision"] == "STAGED_FOR_GREENLANE_NOT_LANDED"
    assert proof["agent_base"] == base
    assert proof["trusted_main_at_submission"] == main
    assert proof["changed_files"] == ["asset.txt"]
    assert len(proof["staged_sha256"]) == 64
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == base
    assert git(repo, "rev-parse", "origin/main").stdout.strip() == main
    assert git(repo, "show", ":asset.txt").stdout == "agent revision\n"


def test_missing_base_refuses_without_touching_main(estate):
    repo, base_file, _, _, main = estate
    base_file.write_text("f" * 40, encoding="ascii")
    result = run(estate)
    assert result.returncode == 2
    assert "not fetchable" in result.stderr
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == main


def test_invalid_base_string_refuses_before_checkout(estate):
    repo, base_file, _, _, main = estate
    base_file.write_text("main", encoding="ascii")
    result = run(estate)
    assert result.returncode == 2
    assert "40-digit SHA" in result.stderr
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == main


def test_an_unrelated_branch_base_cannot_be_smuggled_in(estate):
    repo, base_file, _, _, main = estate
    git(repo, "checkout", "-qb", "unrelated", "HEAD")
    (repo / "unrelated.txt").write_text("unrelated\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "branch candidate")
    other = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "-q", "main")
    base_file.write_text(other, encoding="ascii")
    result = run(estate)
    assert result.returncode == 2
    assert "does not belong to current main history" in result.stderr
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == main


def test_empty_patch_refuses_without_touching_main(estate):
    repo, _, patch, _, main = estate
    patch.write_text("", encoding="utf-8")
    result = run(estate)
    assert result.returncode == 2
    assert "missing, empty" in result.stderr
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == main


def test_model_patch_modifying_github_workflow_is_never_admitted(estate):
    repo, _, patch, base, main = estate
    git(repo, "checkout", "-q", "--detach", base)
    guarded = repo / ".github" / "workflows" / "forbidden.yml"
    guarded.parent.mkdir(parents=True, exist_ok=True)
    guarded.write_text("name: overwritten\n")
    git(repo, "add", ".github/workflows/forbidden.yml")
    patch.write_text(
        git(repo, "diff", "--cached", "--binary", "HEAD").stdout,
        encoding="utf-8",
    )
    git(repo, "reset", "--hard", "-q", main)
    # reset --hard does not delete untracked files; otherwise the negative
    # case would only exercise dirty-checkout refusal, not the protected-path gate.
    guarded.unlink(missing_ok=True)
    result = run(estate)
    assert result.returncode == 2
    assert "untrusted agent patch modifies protected paths" in result.stderr


def test_the_hosted_workflow_invokes_the_verified_base_apply():
    source = (HELPER.parents[1] / ".github/workflows/agent-sandbox.yml").read_text()
    assert 'fetch-depth: 0' in source
    assert 'python3 bin/idp-agent-base-apply.py --base-file "$work/base" --patch "$work/patch"' in source
    assert 'git apply --index --3way "$work/patch"' not in source
