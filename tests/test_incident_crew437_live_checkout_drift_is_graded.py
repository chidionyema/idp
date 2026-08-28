"""crew#437 / crew#433 / crew#85, 2026-08-27: three live checkouts scheduled jobs run from
were on a feature branch, behind main, or both, and nothing said so. Rule: bin/idp-checkout-drift
grades each checkout (main, not behind, clean) and exits non-zero on drift, zero when clean,
BLIND (2) when it cannot read one. Rung 4, incident test, both ways on throwaway repos."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin/idp-checkout-drift"


def _git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def _make(tmp_path, name):
    origin = tmp_path / f"{name}-origin"
    _git(tmp_path, "init", "-q", "-b", "main", str(origin))
    _git(origin, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "one")
    live = tmp_path / name
    _git(tmp_path, "clone", "-q", str(origin), str(live))
    return origin, live


def _run(*repos):
    env = {**os.environ, "ESTATE_CHECKOUTS": ":".join(str(r) for r in repos), "ESTATE_CHECKOUTS_NO_FETCH": "1"}
    return subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, env=env)


def test_a_clean_main_checkout_passes_and_a_stale_branch_fails_with_a_path_back(tmp_path):
    _, clean = _make(tmp_path, "clean")
    r = _run(clean)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 drifted" in r.stdout

    origin, stale = _make(tmp_path, "stale")
    _git(origin, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "two")
    _git(stale, "fetch", "-q", "origin", "main")
    _git(stale, "switch", "-q", "-c", "feat/x")
    (stale / "draft.txt").write_text("older copy\n")
    r = _run(clean, stale)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "on feat/x, not main; 1 behind origin/main; 1 dirty file(s)" in r.stdout
    assert "path back: git -C" in r.stdout and "1 drifted" in r.stdout

    r = _run(tmp_path / "missing")
    assert r.returncode == 2 and "1 unreadable" in r.stdout


def test_a_peer_worktree_dir_is_not_this_checkouts_dirt(tmp_path):
    _, live = _make(tmp_path, "parked")
    (live / ".wt-crew999").mkdir()
    (live / ".wt-crew999" / "f.txt").write_text("peer session worktree\n")
    r = _run(live)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "main, current, clean" in r.stdout

    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if k != "ESTATE_CHECKOUTS"})
    assert r.returncode == 2 and "ESTATE_CHECKOUTS is empty" in r.stderr
