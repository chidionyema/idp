"""Legion main-landed auto missions must join trusted source and Greenlane receipts.

A squash records Greenlane-Head in the *landing* commit; the original producer
keeps Run: and Agent: auto. Requiring both in one message falsely measures zero.
This test uses real Git objects, not model output, network or fabricated runtime status.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return p.stdout.strip()


def metric_script() -> str:
    data = json.loads((ROOT / "catalog/optimus-metrics.json").read_text())
    rows = [m for m in data["metrics"] if m.get("name") == "legion.missions_landed"]
    assert len(rows) == 1
    assert rows[0]["measure"][:2] == ["python3", "-c"]
    return rows[0]["measure"][2]


def fixture(
    tmp_path: Path,
    *,
    source_run: bool,
    source_auto: bool = True,
    landing_auto: bool = True,
) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "proof")
    git(repo, "config", "user.email", "proof@example.test")
    (repo / "f").write_text("root\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "root")
    git(repo, "checkout", "-q", "-b", "producer")
    (repo / "f").write_text("source\n")
    git(repo, "add", ".")
    prefix = "agent-sandbox (auto): " if source_auto else "agent-sandbox (gemini): "
    body = prefix + "real candidate\n\nAgent: auto\nClaim: #8461\n"
    if source_run:
        body += "Run: https://github.com/chidionyema/idp/actions/runs/45112165345\n"
    git(repo, "commit", "-q", "-m", body)
    sha = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    (repo / "f").write_text("landed\n")
    git(repo, "add", ".")
    landing = "agent-sandbox (auto): " if landing_auto else "agent-sandbox (gemini): "
    message = landing + "real candidate\n\nGreenlane-Head: " + sha + "\n"
    git(repo, "commit", "-q", "-m", message)
    return repo


def measure(repo: Path):
    return subprocess.run(
        [sys.executable, "-c", metric_script()],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def test_source_run_and_landing_head_are_joined_without_inference(tmp_path):
    repo = fixture(tmp_path, source_run=True)
    result = measure(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "optimus.legion.missions_landed=1"


def test_source_without_run_receipt_does_not_count(tmp_path):
    repo = fixture(tmp_path, source_run=False)
    result = measure(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "optimus.legion.missions_landed=0"


def test_non_auto_landing_does_not_count(tmp_path):
    repo = fixture(tmp_path, source_run=True, landing_auto=False)
    result = measure(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "optimus.legion.missions_landed=0"


def test_non_auto_source_does_not_count(tmp_path):
    repo = fixture(tmp_path, source_run=True, source_auto=False)
    result = measure(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "optimus.legion.missions_landed=0"


def test_malformed_head_cannot_be_counted(tmp_path):
    repo = fixture(tmp_path, source_run=True)
    message = "agent-sandbox (auto): forged\n\nGreenlane-Head: not-a-commit\n"
    git(repo, "commit", "--amend", "-q", "-m", message)
    result = measure(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "optimus.legion.missions_landed=0"
