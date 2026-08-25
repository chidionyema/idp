"""The daily digest (R13, spec 2.5): at most six lines, signed by the kernel.

Built from the signed receipt chain only. The last line is the sha256 of
the receipts file the digest was built from, so the founder can check
the digest against the file it summarises. The signature is an HMAC
over the text with the receipts key (sovereign.engine.receipts), the
same key that signs every receipt row, so there is one kernel key and
not a second one.

Scheduling is launchd's job (`sb digest --launchd` prints the plist);
this module never sleeps or loops.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.presence import config_keys
from sovereign.presence.chat import Digest

_TERMINAL_OK = ("done",)
_TERMINAL_BAD = ("halted", "failed", "denied", "stopped", "error")
_DAY_S = 86400


def receipts_file_hash(path: Path | None = None) -> str:
    p = path or config.SB_RECEIPTS
    if not p.exists():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sign(text: str) -> str:
    key, _backend = receipts_mod.get_or_create_key()
    return hmac.new(key, text.encode(), hashlib.sha256).hexdigest()


def verify_signature(text: str, sig: str) -> bool:
    return hmac.compare_digest(_sign(text), sig)


def _ts(row: dict[str, Any]) -> float:
    raw = row.get("ts")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            from datetime import datetime

            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def build(now: float | None = None, path: Path | None = None) -> Digest:
    """The digest for the day ending at `now` (default: the wall clock)."""
    now = time.time() if now is None else now
    rows = receipts_mod.read_all(path)
    recent = [r for r in rows if now - _ts(r) <= _DAY_S] or rows
    sessions: dict[str, dict[str, Any]] = {}
    tokens = 0
    for r in recent:
        sid = str(r.get("session_id") or "")
        if sid:
            sessions[sid] = r
        tokens += int(r.get("tokens") or 0)
    done = sum(1 for r in sessions.values() if str(r.get("status")) in _TERMINAL_OK)
    halted = sum(1 for r in sessions.values() if str(r.get("status")) in _TERMINAL_BAD)
    running = len(sessions) - done - halted
    verdict = receipts_mod.verify(path)
    chain = "ok" if verdict.get("ok") else f"BROKEN at counter {verdict.get('first_broken_counter')}"
    file_hash = receipts_file_hash(path)
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    lines = (
        f"estate digest {day}",
        f"sessions: {done} done, {halted} halted, {running} running",
        f"tokens spent: {tokens}",
        f"receipts: {len(rows)} rows, chain {chain}",
        f"receipts hash: {file_hash}",
    )
    text = "\n".join(lines)
    return Digest(lines=lines, receipts_hash=file_hash, sig=_sign(text))


def as_dict(digest: Digest) -> dict[str, Any]:
    return {
        "text": digest.text,
        "lines": len(digest.lines),
        "max_lines": int(config_keys.resolve("presence.digest_max_lines")),
        "receipts_hash": digest.receipts_hash,
        "sig": digest.sig,
    }
