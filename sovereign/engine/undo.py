"""Undo to a receipt hash (R7, spec 2.2 and 2.3).

Spec 2.2: "If the founder replies to a receipt with `undo`, the kernel
reverts to the hash in that receipt." Spec 2.3 step 5: "the kernel reverts
the exact commit via Merkle hash. No guessing."

Two hashes are in play and this module keeps them apart:

  * the receipt's own `hash` -- its position in the signed chain
    (receipts.py). `--to` names one of these. The chain is walked back
    from its tail along prev_hash until that line is found, so a receipt
    that is not on the chain cannot be undone to, and neither can one
    whose chain has been edited.
  * the `commit` field on that receipt -- the git commit the step
    produced (activities.run_step records it). The repository is reset to
    that commit's first parent, which is what "reverts the exact commit"
    means for git.

Exactly one receipt of kind "undo" is written, whatever was undone. It
carries the receipt hash walked to, the commit reverted, and the commit
the repository now sits on, so `sb audit --at <its hash>` answers what
was undone and by whom.
"""
from __future__ import annotations

from typing import Any

from sovereign.engine import gitops
from sovereign.engine import interventions as interventions_mod
from sovereign.engine import receipts as receipts_mod

KIND = "undo"


class NothingToUndo(ValueError):
    """No receipt for this session names a commit, or the named receipt
    hash is not on the chain."""


def walk_back(session_id: str | None = None, receipt_hash: str | None = None) -> dict[str, Any] | None:
    """Walk the receipt chain from its tail toward genesis and return the
    first line that matches. With `receipt_hash` the match is that exact
    line; without it, the newest line for `session_id` that carries a
    commit. The walk follows prev_hash rather than file order, so a line
    that is on disk but not linked into the chain is never returned."""
    rows = receipts_mod.read_all()
    by_hash = {str(r.get("hash", "")): r for r in rows}
    current = rows[-1] if rows else None
    seen: set[str] = set()
    while current is not None:
        h = str(current.get("hash", ""))
        if h in seen:
            return None
        seen.add(h)
        if receipt_hash is not None:
            if h == receipt_hash:
                return current
        elif current.get("session_id") == session_id and current.get("commit"):
            return current
        current = by_hash.get(str(current.get("prev_hash", "")))
    return None


def undo(session_id: str, by: str, receipt_hash: str | None = None) -> dict[str, Any]:
    target = walk_back(session_id=session_id, receipt_hash=receipt_hash)
    if target is None:
        raise NothingToUndo(
            f"no receipt on the chain names a commit for session {session_id!r}"
            if receipt_hash is None
            else f"receipt {receipt_hash!r} is not on the chain"
        )
    repo = target.get("repo")
    commit = str(target.get("commit") or "")
    if not commit or not gitops.is_repo(repo):
        raise NothingToUndo(f"receipt {target.get('hash')!r} names no commit in a git repository")
    if not gitops.commit_exists(repo, commit):
        raise NothingToUndo(f"commit {commit!r} does not exist in {repo}")
    parent = gitops.parent_of(repo, commit)
    if parent is None:
        raise NothingToUndo(f"commit {commit!r} is a root commit and has no parent to undo to")
    if not gitops.reset_hard(repo, parent):
        raise RuntimeError(f"git reset --hard {parent} failed in {repo}")
    line = interventions_mod.record(
        KIND,
        by,
        f"[✓] UNDO | hash:{commit} | to:{parent} | receipt:{target.get('hash')}",
        session_id=session_id,
        step=int(target.get("step", 0) or 0),
        status=KIND,
        task=str(target.get("task", "")),
        runner=str(target.get("runner", "")),
        repo=repo,
        commit=parent,
        undone_commit=commit,
        undone_receipt=str(target.get("hash", "")),
    )["line"]
    return {
        "ok": True,
        "session_id": session_id,
        "repo": repo,
        "undone_commit": commit,
        "head": parent,
        "undone_receipt": str(target.get("hash", "")),
        "receipt": line["hash"],
        "counter": line["counter"],
    }
