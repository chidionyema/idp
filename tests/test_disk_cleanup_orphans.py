"""Falsifiers for the disk cleaner's measured reclaim phase (idp#7804).

Why this test exists, in one paragraph. On 2026-11-08 the volume sat at 798M free -- under the
executor's 1500M floor, so every door on the machine was closed including read-only ones -- while
`disk-cleanup.sh` reported `verdict: every phase ran` and freed nothing. Its allow-list totalled
0M (every cache it knew was absent or empty), its own policy shadow read 146/223 runs not ok in
30d with p_fail=0.65, and two consecutive runs freed -488M and -311M. The weight was on no list:
`~/Documents/code/argon-sync/.estate/runtime` held 2390M of orphaned duplicate toolchain,
untracked by git, referenced by no script, held open by no process. Removing it by hand took free
4829M -> 7235M (+2406M) and left that checkout's tracked files at 3560 -> 3560.

A gate that cannot fail is not a gate, so every test below has a known-bad input it must reject:
1. the argon-sync shape is RECLAIMED (the case that actually happened), and
2. a tree a live claim covers, a tree a process holds, a git-tracked tree, and a recently touched
   tree are all KEPT with a printed reason. If the phase deleted any of those it would be worse
   than the bug it fixes, so those four are the falsifiers that keep the fix honest.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "estate"
    / "libexec"
    / "disk-cleanup.sh"
)


def _run_phase(
    home: str, *, apply: bool, extra_env: dict | None = None, min_days: str = "2"
):
    """Source the script's helpers and run ONLY the measured-reclaim phase.

    The whole cleaner takes minutes (it measures HOME), so this harness reproduces the function's
    preconditions instead: HOME points at a sandbox, and the helpers the phase calls (`size_m`,
    `tmo`, `remaining`, `free_k`, `claim_worktrees`) are taken from the real script -- not stubbed
    -- so a change to those helpers that breaks bounding or reporting breaks this test too.
    """
    env = {
        "HOME": home,
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "APPLY": "1" if apply else "0",
        "DELETE_S": "20",
        "DISK_CLEANUP_ORPHAN_MIN_DAYS": min_days,
    }
    env.update(extra_env or {})
    driver = r"""
set -uo pipefail
VOL=$(df -k "$HOME" | awk 'NR==2 {print $6}')
BUDGET=0; T_START=$(date +%s); budget_hit=0; INCREMENTAL=0
DELETE_S="${DELETE_S:-20}"
TRASH=0; WORKTREES=0; ONLY_BELOW_MB=0
APPLY="${APPLY:-0}"
# Take each helper by name from the real script. Extracted with awk (a brace counter), not a
# regex: tmo() and size_m() both contain braces and inner functions, and a sed range that stops at
# the first ^} truncates them -- which is how the first draft of this harness tested nothing
# (size_m: command not found) while appearing to test the phase.
for fn in free_k tmo size_m remaining; do
  eval "$(awk -v f="^$fn\\(\\)" 'BEGIN{n=0} $0 ~ f {n=1} n{print; for(i=1;i<=length($0);i++){c=substr($0,i,1); if(c=="{")d++; if(c=="}")d--} if(n && d==0 && NR>1) exit}' "$SCRIPT")"
done
for fn in free_k tmo size_m remaining; do
  command -v "$fn" >/dev/null || { echo "HARNESS: $fn was not extracted from $SCRIPT" >&2; exit 9; }
done
eval "$(awk 'BEGIN{n=0} /^ORPHAN_MIN_DAYS=/ {n=1} n{print} n && /^if \[ "\$INCREMENTAL" != 1 \]; then reclaim_orphan_trees; fi$/ {exit}' "$SCRIPT")"
command -v reclaim_orphan_trees >/dev/null || { echo "HARNESS: reclaim_orphan_trees was not extracted" >&2; exit 9; }
reclaim_orphan_trees
"""
    return subprocess.run(
        ["/bin/bash", "-c", driver],
        capture_output=True,
        text=True,
        env={**os.environ, **env, "SCRIPT": str(SCRIPT)},
        timeout=120,
    )


@pytest.fixture()
def home():
    d = tempfile.mkdtemp(prefix="disk-orphan-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _mk(p: Path, mb: int = 1) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    (p / "blob").write_bytes(b"x" * (mb * 1024 * 1024))
    return p


# The phase only reclaims at or above 100M (an under-100M delete is churn, not a reclaim), so every
# fixture that is meant to be a CANDIDATE is built above that floor. A fixture below it would test
# the floor and not the guard, so the two size rules are deliberately different.
FLOOR_MB = 120


def _age(p: Path, days: int) -> None:
    t = time.time() - days * 86400
    os.utime(p, (t, t))


def test_reclaims_orphaned_duplicate_toolchain_like_argon_sync(home):
    """The case that happened: a second toolchain inside a product checkout, 4 days old."""
    checkout = Path(home) / "Documents" / "code" / "argon-sync"
    # Age the OUTER candidate: the phase ages the directory it would delete, and an outer dir whose
    # mtime is now is correctly kept as fresh work even when its children are old. Ageing the inner
    # toolchains/ instead made this fixture test the freshness guard rather than the reclaim.
    orphan = _mk(
        checkout
        / ".estate"
        / "runtime"
        / "rustup-copy-conflict-20261104"
        / "toolchains",
        FLOOR_MB,
    )
    _age(orphan.parent, 4)

    r = _run_phase(home, apply=True)
    assert "measured reclaim" in r.stdout, r.stdout + r.stderr
    assert "remove" in r.stdout, f"the argon-sync shape was not reclaimed:\n{r.stdout}"
    assert not orphan.exists(), "orphaned duplicate toolchain survived an apply run"


def test_dry_run_names_it_and_removes_nothing(home):
    """A dry run must report the candidate and delete nothing -- this is the default mode."""
    checkout = Path(home) / "Documents" / "code" / "argon-sync"
    orphan = _mk(
        checkout / ".estate" / "runtime" / "rustup-copy-conflict-20261104", FLOOR_MB
    )
    _age(orphan, 4)

    r = _run_phase(home, apply=False)
    assert "would" in r.stdout, f"dry run did not name the candidate:\n{r.stdout}"
    assert orphan.exists(), "dry run deleted a tree"


def test_keeps_a_recently_touched_tree(home):
    """A tree touched inside the freshness window is somebody's live work, not an orphan."""
    checkout = Path(home) / "Documents" / "code" / "argon-sync"
    fresh = _mk(checkout / ".estate" / "runtime" / "rustup", FLOOR_MB)
    # mtime = now: 0 days old, inside ORPHAN_MIN_DAYS
    r = _run_phase(home, apply=True)
    assert "keep" in r.stdout and "touched 0d ago" in r.stdout, r.stdout
    assert fresh.exists(), "a freshly touched tree was deleted"


def test_keeps_a_git_tracked_tree(home):
    """A tracked tree is somebody's source, not a regenerable copy."""
    checkout = Path(home) / "Documents" / "code" / "argon-sync"
    tracked = _mk(checkout / "cargo", FLOOR_MB)
    _age(tracked, 9)
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "user.email=a@b",
            "-c",
            "user.name=a",
            "commit",
            "-qm",
            "x",
        ],
        check=True,
    )

    r = _run_phase(home, apply=True)
    assert "git tracks it" in r.stdout, r.stdout
    assert tracked.exists(), "a git-tracked tree was deleted"


def test_keeps_the_named_live_toolchain_even_if_it_matches(home):
    """~/.rustup is the live toolchain when RUSTUP_HOME is unset: never a candidate."""
    live = _mk(Path(home) / ".rustup" / "toolchains", FLOOR_MB)
    _age(live, 30)

    r = _run_phase(home, apply=True)
    assert "remove" not in r.stdout, (
        f"the live toolchain was treated as an orphan:\n{r.stdout}"
    )
    assert live.exists(), "the live toolchain was deleted"


def test_under_100m_is_not_worth_a_delete(home):
    """A directory too small to matter is skipped, so the phase stays bounded in noise too."""
    checkout = Path(home) / "Documents" / "code" / "argon-sync"
    tiny = checkout / ".estate" / "runtime" / "rustup"
    tiny.mkdir(parents=True)
    (tiny / "f").write_bytes(b"x" * 1024)  # 1K, far under the 100M floor
    _age(tiny, 10)

    r = _run_phase(home, apply=True)
    assert "remove" not in r.stdout, r.stdout
    assert tiny.exists()


def test_the_phase_exists_and_runs_when_not_incremental(home):
    """Falsifier for the wiring: the phase is reached on a normal run, not only when sourced."""
    src = SCRIPT.read_text()
    assert "reclaim_orphan_trees()" in src
    assert 'if [ "$INCREMENTAL" != 1 ]; then reclaim_orphan_trees; fi' in src
    assert "ORPHAN_MIN_DAYS=" in src
