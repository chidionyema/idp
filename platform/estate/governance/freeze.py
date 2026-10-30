"""Founder-approved work is frozen: the keys are taken away.

THE FOUNDER'S RULE (2026-10-29): "prevent any agent from being able to change a git once
approved by a founder and the work done - we kick the door and take the keys away".

A founder approval is an event, and after it the change stops being editable by agents. The
mechanism is a frozen-path register:

    ~/.estate/state/frozen.json
    {"entries": [{"pattern": "platform/estate/governance/**",
                  "approved_by": "founder", "approval": "2026-10-29T22:50Z: founder approved",
                  "since": "2026-10-29T22:50:11Z"}]}

Two gates read it, and both are estate chokepoints rather than new machinery:

  * bin/estate-memory-enforce (pre) -- the write gate every runtime goes through. A write to
    a frozen path is refused, with the approval that froze it and the way to ask for a new
    one.
  * bin/claim-gate -- the merge-time gate. A change that touches a frozen path is refused
    even with a live claim, because a claim is not an approval.

Release is explicit and recorded: bin/estate-freeze --release <pattern> --approval "<why>".
Nothing here deletes work; the keys come back when the founder says so.
"""

from __future__ import annotations

import fnmatch
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import ledger


def freeze_path() -> str:
    return os.path.join(ledger.state_home(), "frozen.json")


def load() -> Dict[str, Any]:
    try:
        with open(freeze_path()) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"entries": []}
    if not isinstance(data, dict):
        return {"entries": []}
    data.setdefault("entries", [])
    return data


def save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(freeze_path()), exist_ok=True)
    tmp = freeze_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, freeze_path())


def entries() -> List[Dict[str, Any]]:
    rows = load().get("entries") or []
    return [r for r in rows if isinstance(r, dict)]


def freeze(
    patterns: List[str],
    approval: str,
    approved_by: str = "founder",
    note: str = "",
) -> List[Dict[str, Any]]:
    """Freeze paths. Returns the entries as written."""
    if not approval:
        raise ValueError(
            "a freeze needs an approval reference: what the founder approved"
        )
    data = load()
    rows = data.setdefault("entries", [])
    added = []
    for pattern in patterns:
        pattern = (pattern or "").strip()
        if not pattern:
            continue
        if any(e.get("pattern") == pattern for e in rows):
            continue
        entry = {
            "pattern": pattern,
            "approved_by": approved_by,
            "approval": approval,
            "note": note,
            "since": ledger.now(),
        }
        rows.append(entry)
        added.append(entry)
    save(data)
    return added


def release(pattern: str, approval: str) -> bool:
    """Give the keys back for one pattern. The approval that releases it is recorded."""
    data = load()
    rows = data.get("entries") or []
    kept = []
    released = False
    for entry in rows:
        if entry.get("pattern") == pattern:
            released = True
            continue
        kept.append(entry)
    if released:
        data["entries"] = kept
        data.setdefault("released", []).append(
            {"pattern": pattern, "approval": approval, "at": ledger.now()}
        )
        save(data)
    return released


def released() -> List[Dict[str, Any]]:
    return load().get("released") or []


def match(rel_path: str) -> Optional[Dict[str, Any]]:
    """The entry that freezes this repo-relative path, or None."""
    rel = (rel_path or "").replace(os.sep, "/").lstrip("./")
    for entry in entries():
        pattern = (entry.get("pattern") or "").strip()
        if not pattern:
            continue
        if fnmatch.fnmatch(rel, pattern) or rel.startswith(pattern.rstrip("*")):
            return entry
    return None


def is_frozen(rel_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    entry = match(rel_path)
    return (entry is not None, entry)


def refusal(rel_path: str) -> str:
    """The message the gate prints when a frozen path is touched."""
    frozen, entry = is_frozen(rel_path)
    if not frozen or not entry:
        return ""
    return (
        f"{rel_path} is frozen by founder approval ({entry.get('approval', 'unknown')}). "
        "No agent may change founder-approved work: the door is kicked and the keys are "
        "taken away until the founder approves a new change. If the founder has approved "
        "one, release it first: bin/estate-freeze --release "
        f"'{entry.get('pattern')}' --approval '<the approval>'"
    )
