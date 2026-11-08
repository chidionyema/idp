"""Commit-bound yield: negative controls against empty, replayed, forged and staged-drift evidence."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-yield-gate"


def git(repo: Path, *args: str, ok=True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if ok:
        assert r.returncode == 0, r.stderr
    return r


def run(repo: Path, *args: str):
    return subprocess.run([sys.executable, str(GATE), *args], cwd=repo, text=True, capture_output=True)


def setup(tmp_path: Path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("first\n")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-qm", "baseline")
    (tmp_path / "README.md").write_text("first\nsecond\n")
    git(tmp_path, "add", "README.md")
    (tmp_path / "message").write_text("fix: test\n")
    return tmp_path


def record(repo: Path, session="sess-001", **kwargs):
    params = [
        "record", "--session", session, "--kind", "bug-fix",
        "--summary", "Eliminated the observed failure class with a code change",
        "--lookup-key", "failure-git-staged", "--finding",
        "The staged git patch is the source of evidence, not the working tree",
        "--next-action", "Run independent checks and observe the real caller",
    ]
    for name, val in kwargs.items():
        params.extend(["--" + name.replace("_", "-"), str(val)])
    return run(repo, *params)


def put_trailer(repo: Path, session="sess-001"):
    (repo / "message").write_text(
        "fix: actual change\n\nYield-Receipt: .yield/" + session + ".json\n"
    )


def test_record_then_check_binds_exact_index(tmp_path):
    repo = setup(tmp_path)
    assert record(repo).returncode == 0
    put_trailer(repo)
    good = run(repo, "check", "message")
    assert good.returncode == 0, good.stderr


def test_commit_without_receipt_refused_with_one_command(tmp_path):
    repo = setup(tmp_path)
    bad = run(repo, "check", "message")
    assert bad.returncode != 0 and "record" in bad.stderr


def test_unstaged_work_cannot_fake_patch_receipt(tmp_path):
    repo = setup(tmp_path)
    assert record(repo).returncode == 0
    put_trailer(repo)
    (repo / "README.md").write_text("a later unstaged edit\n")
    assert run(repo, "check", "message").returncode == 0
    git(repo, "add", "README.md")
    assert run(repo, "check", "message").returncode != 0


def test_receipt_replay_denied_after_commit(tmp_path):
    repo = setup(tmp_path)
    assert record(repo).returncode == 0
    put_trailer(repo)
    git(repo, "commit", "-qm", "initial yield")
    (repo / "README.md").write_text("different work\n")
    git(repo, "add", "README.md")
    assert run(repo, "check", "message").returncode != 0
    assert record(repo).returncode != 0


def test_forged_runtime_proof_rejected(tmp_path):
    repo = setup(tmp_path)
    result = record(repo, maturity="RUNTIME_RECEIPT_DECLARED")
    assert result.returncode != 0
    assert "runtime yield needs" in result.stderr


def test_evidence_must_be_changed_staged_blob(tmp_path):
    repo = setup(tmp_path)
    (repo / "secret.txt").write_text("not staged\n")
    bad = record(repo, evidence="secret.txt")
    assert bad.returncode != 0


def test_intelligence_fields_mandatory_even_for_fix(tmp_path):
    repo = setup(tmp_path)
    bad = record(repo, finding="x")
    assert bad.returncode != 0
    assert "intelligence" in bad.stderr


def test_bad_friction_cannot_be_claimed_resolved(tmp_path):
    repo = setup(tmp_path)
    bad = record(repo, friction="do-failure", symptom="unassigned runner",
                 resolution="RESOLVED")
    assert bad.returncode != 0


def test_new_receipt_must_be_added_not_existing_edited(tmp_path):
    repo = setup(tmp_path)
    assert record(repo).returncode == 0
    put_trailer(repo)
    git(repo, "commit", "-qm", "baseline with receipt")
    (repo / "README.md").write_text("another fix\n")
    git(repo, "add", "README.md")
    (repo / ".yield/sess-001.json").write_text("{}")
    git(repo, "add", ".yield/sess-001.json")
    assert run(repo, "check", "message").returncode != 0


def test_empty_noop_not_counted_as_yield(tmp_path):
    repo = setup(tmp_path)
    git(repo, "reset", "-q", "--", "README.md")
    bad = record(repo)
    assert bad.returncode != 0 and "stage actual work" in bad.stderr
