"""dof-gate must refuse an unresolved commit while a critical service is down.

The founder's directive (2026-11-12): find the cage and lock the agent in. The cage was open
because catalog/dof-registry.json carried control.mode = "disabled", and the re-enable condition
(`reenableOnlyAfter`, `lastVerifiedBacklog`) was read by no code at all: a control gated on a field
nothing reads can never arm. This test is the falsifier -- it fails if the registry drifts back to
disabled, and it fails if the gate admits a commit that resolves nothing.

Proven capable of failing: with control.mode set back to "disabled" both tests below fail.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "dof-registry.json"
GATE = ROOT / "bin" / "dof-gate"


def _registry() -> dict:
    return json.loads(REGISTRY.read_text())


def test_the_cage_is_armed() -> None:
    """A guard that cannot be armed is not a guard."""
    mode = _registry()["control"]["mode"]
    assert mode in {"enforced", "observe"}, (
        f"dof-gate is {mode!r}: the machine does not confine the agent. "
        "Founder directive 2026-11-12 requires the cage armed."
    )


def test_the_gate_refuses_a_commit_that_resolves_nothing(tmp_path) -> None:
    """The armed gate must REFUSE, not warn. Exit 1 is the verdict.

    dof-gate reads the registry from the BASE commit, so the armed registry has to be a commit
    for the gate to judge anything. We build two throwaway commits in an in-memory index (no
    worktree, no branch): ARM carries the armed registry, NEXT is an ordinary commit that
    resolves nothing. NEXT must be refused.
    """
    env = {"GIT_INDEX_FILE": str(tmp_path / "idx"), "PATH": "/usr/bin:/bin"}
    import os

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True,
            check=True, timeout=60, env={**os.environ, **env},
        ).stdout.strip()

    blob = git("hash-object", "-w", str(REGISTRY))
    git("read-tree", "HEAD")
    git("update-index", "--add", "--cacheinfo", f"100644,{blob},catalog/dof-registry.json")
    arm = git("commit-tree", git("write-tree"), "-p", "HEAD", "-m", "arm the cage")
    (tmp_path / "unrelated.txt").write_text("nothing to resolve\n")
    git("read-tree", arm)
    other = git("hash-object", "-w", str(tmp_path / "unrelated.txt"))
    git("update-index", "--add", "--cacheinfo", f"100644,{other},unrelated.txt")
    nxt = git("commit-tree", git("write-tree"), "-p", arm, "-m", "an ordinary commit")

    proc = subprocess.run(
        [str(GATE), arm, nxt], cwd=ROOT, capture_output=True, text=True, timeout=90,
    )
    payload = json.loads(proc.stdout)
    if payload.get("mode") == "disabled":
        raise AssertionError("dof-gate reported mode=disabled: the cage is open")
    assert proc.returncode == 1, payload
    assert payload["ok"] is False
    refused = [c for c in payload["commits"] if c.get("refused")]
    assert refused, "no commit was refused while a critical service is down"
    assert "Genesis-Resolves" in refused[0]["reason"] + refused[0].get("required_trailer", "")
