"""otto-background-sweep reads drift; it must never report CLEAN on a dirty tree.

The sweep is telemetry, so its failure mode is the dangerous one: a check that silently
misses a dirty working tree looks exactly like a clean estate. These tests build throwaway
repositories and grade the verdict, both ways.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "infra" / "macos" / "tools" / "otto" / "otto-background-sweep.py"


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("a\n")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def sweep(repo: Path) -> dict:
    out = subprocess.run(
        [
            sys.executable,
            str(SWEEP),
            "--once",
            "--json",
            "--dry-run",
            "--skip-disk",
            "--repo",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(out.stdout)


def test_a_clean_repository_is_clean(tmp_path):
    receipt = sweep(make_repo(tmp_path))
    assert receipt["verdict"] == "CLEAN", receipt["findings"]


def test_a_dirty_working_tree_is_drift(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "b.txt").write_text("b\n")
    receipt = sweep(repo)
    ids = [f["id"] for f in receipt["findings"]]
    assert receipt["verdict"] == "DRIFT"
    assert "dirty-tree" in ids, receipt["findings"]


def test_a_missing_repository_is_reported_not_ignored(tmp_path):
    receipt = sweep(tmp_path / "nope")
    ids = [f["id"] for f in receipt["findings"]]
    assert receipt["verdict"] == "DRIFT"
    assert "repo-missing" in ids
