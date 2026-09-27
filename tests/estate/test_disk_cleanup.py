"""disk-cleanup deletes only the regenerable-cache allow-list, and only when asked.

Runs the repo's platform/estate/libexec/disk-cleanup.sh against a fake HOME, so nothing real is
touched: a dry run deletes nothing, apply empties every allow-listed cache and proves it, and the
live tooling / user data beside them survives both.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "platform/estate/libexec/disk-cleanup.sh"

CACHES = [
    ".yarn/berry/cache",
    "Library/Caches/go-build",
    "Library/Caches/pip",
    "Library/Caches/Homebrew",
    ".npm/_cacache",
    ".npm/_npx",
]
# a Cargo build dir (Cargo.toml beside it, cargo's stamp inside) is a cache; a directory that is
# merely called target is not
RUST = "Documents/code/crate/target"
KEPT = [
    ".cache/estate-tools/litellm-venv",
    ".ollama/models",
    "Documents/code/x",
    ".Trash/photo",
    "Documents/code/site/target",
    "Documents/code/crate/src",
    "Documents/code/crate/.claude/worktrees/wf/target",
]


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    for d in CACHES + KEPT + [RUST]:
        (home / d).mkdir(parents=True)
        (home / d / "blob").write_bytes(os.urandom(2 * 1024 * 1024))
    (home / "Documents/code/crate/Cargo.toml").write_text("[package]\n")
    # another agent's worktree: a real Cargo build dir, and still not ours to delete
    agent = home / "Documents/code/crate/.claude/worktrees/wf"
    (agent / "Cargo.toml").write_text("[package]\n")
    (agent / "target/CACHEDIR.TAG").write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n"
    )
    (home / RUST / "CACHEDIR.TAG").write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n"
    )
    return home


def _run(home: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HOME": str(home),
        "DISK_GUARD_PATH": str(home),
        "DISK_CLEANUP_RUST_ROOTS": str(home / "Documents/code"),
    }
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_dry_run_lists_every_cache_and_deletes_nothing(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "false", "false")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("  would  ") == len(CACHES) + 1, r.stdout
    assert f"  would  rust-target  2M  {home / RUST}" in r.stdout, r.stdout
    for d in CACHES + KEPT + [RUST]:
        assert (home / d / "blob").exists(), d


def test_apply_empties_the_allow_list_and_nothing_else(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "true", "false")
    # a yarn/npm/go/pip/brew process running on this machine makes its cache SKIP, correctly;
    # every cache is either freed or skipped for a named process, never silently kept
    freed = r.stdout.count("  freed  ")
    skipped = r.stdout.count("  SKIP   ")
    assert freed + skipped == len(CACHES) + 1, r.stdout
    assert r.returncode == 0, r.stdout + r.stderr
    assert "free after:" in r.stdout
    gone = [
        d
        for d in CACHES + [RUST]
        if not (home / d).exists() or not any((home / d).iterdir())
    ]
    assert len(gone) == freed, (gone, r.stdout)
    for d in KEPT:
        assert (home / d / "blob").exists(), f"{d} must never be touched"


def test_trash_is_emptied_only_when_opted_in(tmp_path):
    home = _home(tmp_path)
    _run(home, "true", "false")
    assert (home / ".Trash/photo/blob").exists()
    r = _run(home, "true", "true")
    assert "  freed  trash" in r.stdout, r.stdout
    assert (home / ".Trash").is_dir() and not any((home / ".Trash").iterdir())
    assert (home / ".cache/estate-tools/litellm-venv/blob").exists()


def test_refuses_when_home_is_root(tmp_path):
    env = {**os.environ, "HOME": "/", "DISK_GUARD_PATH": str(tmp_path)}
    r = subprocess.run(
        ["bash", str(SCRIPT), "true", "false"], env=env, capture_output=True, text=True
    )
    assert r.returncode == 1 and "REFUSED" in r.stdout


def test_only_below_mb_deletes_nothing_while_there_is_room(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "true", "false", "1")
    assert r.returncode == 0 and "nothing deleted" in r.stdout, r.stdout
    for d in CACHES + KEPT + [RUST]:
        assert (home / d / "blob").exists(), d


def test_only_below_mb_applies_under_the_floor(tmp_path):
    home = _home(tmp_path)
    r = _run(home, "true", "false", "999999999")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "free after:" in r.stdout and "nothing deleted" not in r.stdout, r.stdout


def test_only_below_mb_must_be_a_number(tmp_path):
    r = _run(_home(tmp_path), "true", "false", "10G")
    assert r.returncode == 1 and "REFUSED" in r.stdout, r.stdout
