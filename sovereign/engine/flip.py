"""The flip (cp13): the DAG becomes primary, the legacy DB becomes a
read-only archive with a rollback path.

Founder's shape (features/sovereign-bus/cp13_the_flip.feature):
`bin/sb flip --by <who> --signed` sets the legacy DB file read-only at
the filesystem level (os.chmod, flip.readonly_mode) -- not a
per-connection PRAGMA a fresh connection could ignore -- so every future
writer, in this process or any other, hits an OS PermissionError, never
a silent bypass. Reads are unaffected: sqlite serves SELECTs from a
read-only file exactly as it does from a writable one, so the "downtime"
this module measures is the wall-clock the chmod plus one
shadow_root.verify() takes -- flip.max_downtime_ms bounds it -- not an
outage window; "zero-downtime cutover" is the design cp10's dual-read
router already proved out, not a claim invented here.

rollback() restores write permission. Because nothing could have
written to the file while it was read-only (the OS enforced that, not
this module's own bookkeeping), "consistent with the root at flip time"
needs no data repair on rollback -- only a hash check that the file's
own bytes still match the sha256 the flip receipt recorded, which
catches the one way this could still be wrong: something with
root/owner privilege bypassing the permission bit while flipped. A
mismatch there raises FlipError and refuses the rollback rather than
handing back a legacy DB rollback() cannot vouch for.
"""
from __future__ import annotations

import hashlib
import os
import stat
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import shadow_root


class FlipError(RuntimeError):
    """Raised when a flip or rollback cannot proceed safely: rollback()
    with no prior "flip" receipt to roll back, or a legacy-file hash
    mismatch against what that receipt recorded."""


def legacy_db_path() -> Path:
    db_path, _, _ = config.SIDECAR_TARGET.partition("#")
    return Path(db_path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(config.FLIP_HASH_CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()


def is_read_only(path: Path | None = None) -> bool:
    p = path or legacy_db_path()
    return not (p.stat().st_mode & stat.S_IWUSR)


def _last_flip_receipt() -> dict[str, Any] | None:
    rows = [r for r in receipts_mod.read_all() if r.get("kind") in ("flip", "flip_rollback")]
    return rows[-1] if rows else None


def flip(by: str, signed: bool = False) -> dict[str, Any]:
    """chmods the legacy DB read-only, then records one receipt naming
    the DAG root at that moment and the legacy file's own sha256, so
    rollback() can later verify nothing wrote to it while flipped."""
    t0 = time.perf_counter()
    path = legacy_db_path()
    os.chmod(path, config.FLIP_READONLY_MODE)
    root_state = shadow_root.verify()
    legacy_hash = _sha256_file(path)
    downtime_ms = (time.perf_counter() - t0) * config.MS_PER_SECOND

    text = config.FLIP_RECEIPT_TEMPLATE.format(root=root_state["root"])
    record = {
        "session_id": "-", "kind": "flip", "by": by, "text": text,
        "step": 0, "status": "flipped", "task": "", "runner": "",
        "root": root_state["root"], "legacy_hash": legacy_hash, "legacy_path": str(path),
    }
    if signed:
        record["signed"] = True
    receipt = receipts_mod.append(record)
    return {
        "root": root_state["root"],
        "legacy": "readonly",
        "downtime_ms": downtime_ms,
        "receipt_counter": receipt.get("counter"),
    }


def rollback(by: str, signed: bool = False) -> dict[str, Any]:
    """Refuses (FlipError) unless the most recent flip/flip_rollback
    receipt is a "flip" whose recorded legacy_hash still matches the
    file on disk. Restores write permission and records one
    "flip_rollback" receipt."""
    last = _last_flip_receipt()
    if last is None or last.get("kind") != "flip":
        raise FlipError("no active flip to roll back")
    path = legacy_db_path()
    current_hash = _sha256_file(path)
    if current_hash != last.get("legacy_hash"):
        raise FlipError("legacy DB changed while flipped -- refusing to roll back onto it")

    os.chmod(path, config.FLIP_WRITABLE_MODE)
    text = config.FLIP_ROLLBACK_RECEIPT_TEMPLATE.format(root=last.get("root"))
    record = {
        "session_id": "-", "kind": "flip_rollback", "by": by, "text": text,
        "step": 0, "status": "rolled_back", "task": "", "runner": "",
        "root": last.get("root"), "legacy_hash": current_hash, "legacy_path": str(path),
    }
    if signed:
        record["signed"] = True
    receipt = receipts_mod.append(record)
    return {
        "root": last.get("root"),
        "legacy": "writable",
        "consistent": True,
        "receipt_counter": receipt.get("counter"),
    }
