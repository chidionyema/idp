"""Incident test, R29 (founder 2026-08-25): code changed without an executable spec must be
refused, and code that arrives with its spec must be permitted, in the same run (LAW 38)."""
from __future__ import annotations

import subprocess
from pathlib import Path

GATE = Path(__file__).resolve().parents[2] / "bin" / "spec-gate"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=repo, check=True, capture_output=True, text=True).stdout


def _repo(tmp: Path) -> Path:
    _git(tmp, "init", "-q", "-b", "main")
    (tmp / "app.py").write_text("x = 1\n")
    _git(tmp, "add", "."); _git(tmp, "commit", "-qm", "base")
    _git(tmp, "branch", "base")
    return tmp


def _gate(repo: Path) -> tuple[int, str]:
    p = subprocess.run([str(GATE), "base"], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout


def test_incident_r29_code_alone_is_refused_and_code_with_spec_is_permitted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "app.py").write_text("x = 2\n")
    _git(repo, "commit", "-qam", "code only")
    rc, out = _gate(repo)
    assert rc == 1 and "FAIL  spec-gate" in out and "app.py" in out, out

    # 56a1ec5 (crew#297): a feature counts only when a tracked test binds it with scenarios();
    # a bare .feature file is prose, so the permitted case arrives with its binding test.
    (repo / "features").mkdir()
    (repo / "features" / "app.feature").write_text("Feature: x is 2\n")
    (repo / "test_app.py").write_text('from pytest_bdd import scenarios\nscenarios("features/app.feature")\n')
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "spec")
    rc, out = _gate(repo)
    assert rc == 0 and "ok    spec-gate" in out, out


def test_incident_r29_no_code_change_passes_and_missing_base_is_blind(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "README.md").write_text("docs\n")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "docs")
    assert _gate(repo)[0] == 0
    p = subprocess.run([str(GATE), "no-such-ref"], cwd=repo, capture_output=True, text=True)
    assert p.returncode == 3 and "BLIND" in p.stdout
