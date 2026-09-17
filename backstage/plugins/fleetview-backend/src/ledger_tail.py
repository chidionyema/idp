"""FleetView CP7: last N rows of a session's prompt-ledger, for the log pane.

session_id format is `<repo_or_stem>:<raw_uuid>` — split on the last `:` to get the uuid.
Scans all *.jsonl files under ESTATE_STATE_PATH_PREFIX for rows matching that uuid.
Returns the last n rows as {"ts": ..., "source": ..., "text": ...}, text trimmed to 500 chars.

CONFIG (LAW 46): ESTATE_STATE_PATH_PREFIX — same env var sessions.py reads, default
~/.claude/state/prompt-ledger/.  A missing dir or any read error returns [], never a crash.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_PREFIX = "~/.claude/state/prompt-ledger/"
_TEXT_TRIM = 500


def _ledger_dir() -> Path:
    raw = os.environ.get("ESTATE_STATE_PATH_PREFIX", _DEFAULT_PREFIX)
    return Path(os.path.expanduser(raw))


def _raw_session_id(session_id: str) -> str:
    """Split `<repo_or_stem>:<raw_uuid>` on the last `:` to get the uuid.
    A session_id with no `:` is returned as-is (defensive: the caller may pass a bare uuid)."""
    if ":" in session_id:
        return session_id.rsplit(":", 1)[-1]
    return session_id


def ledger_tail(session_id: str, n: int = 20) -> list[dict[str, Any]]:
    """Return the last `n` ledger rows for the given session.

    Scans every *.jsonl file in the ledger directory for rows where row["session"] equals
    the raw uuid extracted from session_id.  Rows are accumulated across all files and the
    final result is the last n by file order (which is already chronological within each
    jsonl file).

    Returns [] on any error (missing dir, unreadable file, malformed JSON) — log-pane
    errors are soft: a blank pane is better than a broken page.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        return []

    raw_uuid = _raw_session_id(session_id)
    directory = _ledger_dir()
    if not directory.is_dir():
        return []

    matched: list[dict[str, Any]] = []
    try:
        for path in sorted(directory.glob("*.jsonl")):
            try:
                with path.open() as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except ValueError:
                            continue
                        if not isinstance(row, dict):
                            continue
                        if row.get("session") != raw_uuid:
                            continue
                        text = row.get("text") or ""
                        if isinstance(text, str):
                            text = text[:_TEXT_TRIM]
                        matched.append(
                            {
                                "ts": row.get("ts"),
                                "source": row.get("source"),
                                "text": text,
                            }
                        )
            except OSError:
                continue
    except Exception:  # noqa: BLE001 — any unexpected error is a soft failure for the log pane
        return []

    return matched[-n:] if len(matched) > n else matched
