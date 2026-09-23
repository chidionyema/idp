"""Cross-stack root (cp15): one Merkle root over four children -- code,
DB, the attach policy, and the AI trust/presence policy -- so a single
number moves the moment any one of the four does, and `sb root --json`
reports which child moved.

Each child is a real, already-load-bearing piece of state, never a
second copy invented for this checkpoint:

- code_root: `git rev-parse HEAD`, the commit this checkout is built
  from. Git's own commit graph already is a Merkle tree over every file
  in the checkout (LAW 43: that mechanism is not reinvented here as a
  second file-hash walk).
- db_root: cp9's shadow root (sovereign.engine.shadow_root.verify()),
  the Merkle root over every write cp8's sidecar has drained.
- policy_root: sha256 over the resolved sovereign.attach policy config
  (cp21's "conservative default policy" -- destructive-command
  patterns, write/git-write verb lists, the approval quorum) -- the
  config that decides which commands require a receipt or a quorum.
- ai_policy_root: sha256 over the resolved sovereign.trust config --
  which hardware-trust backend is pinned and what a founder-presence
  check requires -- the policy governing what the AI may sign for
  itself versus what needs the founder physically present.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.attach import config_keys as attach_ck
from sovereign.engine import shadow_root
from sovereign.trust import config_keys as trust_ck


def code_root(repo_dir: Path | None = None) -> str | None:
    """`git rev-parse HEAD` of the checkout this process runs from.
    Returns None (never raises) outside a git checkout -- e.g. a
    packaged deploy with no .git directory -- so a caller can tell a
    missing code_root apart from one that legitimately changed."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir) if repo_dir else None,
            capture_output=True, text=True, timeout=config.CROSS_STACK_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


def policy_root() -> str:
    body = {
        "destructive_patterns": attach_ck.get("attach.destructive_patterns"),
        "write_verbs": attach_ck.get("attach.write_verbs"),
        "git_write_verbs": attach_ck.get("attach.git_write_verbs"),
        "quorum": attach_ck.get("attach.quorum"),
        "policy_mode": attach_ck.get("attach.policy_mode"),
    }
    return hashlib.sha256(config.canonical_json(body)).hexdigest()


def ai_policy_root() -> str:
    body = {
        "backend": config.get("trust.backend").value,
        "presence_timeout_s": trust_ck.get("trust.presence_timeout_s"),
        "reason_default": trust_ck.get("trust.reason_default"),
    }
    return hashlib.sha256(config.canonical_json(body)).hexdigest()


def root(repo_dir: Path | None = None) -> dict[str, Any]:
    """The exact shape `bin/sb root --json` reports: the composite
    "root" plus each of its four named children, so a caller can tell
    which one moved without recomputing anything. db_nodes/db_parent/
    db_verified are cp9's own diagnostic fields about the DB Merkle
    chain's integrity, carried through unchanged."""
    db_state = shadow_root.verify()
    children = {
        "code_root": code_root(repo_dir),
        "db_root": db_state["root"],
        "policy_root": policy_root(),
        "ai_policy_root": ai_policy_root(),
    }
    composite = hashlib.sha256(config.canonical_json(children)).hexdigest()
    return {
        "root": composite,
        **children,
        "db_nodes": db_state["nodes"],
        "db_parent": db_state["parent"],
        "db_verified": db_state["verified"],
    }
