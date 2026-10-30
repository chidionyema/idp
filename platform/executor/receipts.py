"""receipts.py -- the observable evidence an adaptive bound is allowed to learn from.

A bound the caller wrote is a promise. A bound the door learned is a measurement. This module
records the measurement: the SHAPE of the command, how long it took, how it ended, and where it
ran. Nothing here decides anything -- `platform/executor/bounds.py` decides, and it may only
learn from what this module records.

THE THREE RULES.
1. The receipt records the SHAPE of the command, never its content. Values are redacted, because
   a value can be a secret and a receipt outlives the job that carried it.
2. The receipt records what happened, including a kill at the ceiling. A job killed at the
   ceiling is evidence the ceiling was too small; it is never evidence that a bigger ceiling
   would have been enough, and `bounds.measured_bound` excludes it.
3. The receipt is written on every path, including the path where the command could not start.
   Evidence that is missing is not evidence that nothing happened.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

RECEIPT_SUFFIX = ".receipt.json"
SCHEMA = "estate.exec-receipt.v1"
REDACTED = "<arg>"
EMPTY_SHAPE = "empty"
MAX_SHAPE_PARTS = 12


def command_shape(argv: Sequence[str]) -> str:
    """A stable fingerprint of the command's SHAPE. Never of its content.

    Two runs of the same command with different arguments share a shape, so their durations can
    be pooled. Two runs of different commands do not, so a fast command never teaches a slow
    one. The argument VALUES are dropped: a value can be a secret, and a receipt outlives the
    job. Flag NAMES are kept, because `--json` and `--yaml` are different work.

    The shape is READABLE as well as stable: the canonical form is the key, with a digest of it
    appended so two different canonical forms can never collide by eye. Evidence that can be
    audited is evidence; a bare hash is a promise.
    """
    if not argv:
        return EMPTY_SHAPE
    parts = [Path(argv[0]).name]
    for arg in argv[1:]:
        if arg.startswith("-"):
            head, sep, _ = arg.partition("=")
            parts.append(head + ("=<arg>" if sep else ""))
        else:
            parts.append(REDACTED)
    if len(parts) > MAX_SHAPE_PARTS:
        parts = parts[:MAX_SHAPE_PARTS] + ["..."]
    canonical = " ".join(parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
    return f"{canonical}#{digest}"


def receipt_path(runs_dir: "os.PathLike[str] | str", name: str) -> Path:
    """Where the receipt for `name` lives. One receipt per job, beside its log."""
    return Path(runs_dir) / f"{name}{RECEIPT_SUFFIX}"


def write_receipt(
    runs_dir: "os.PathLike[str] | str",
    name: str,
    *,
    argv: Sequence[str],
    elapsed_sec: float,
    exit_code: int,
    killed_at_ceiling: bool,
    ceiling_sec: int,
    repo: str = "",
) -> Path:
    """Write the receipt for one finished job and return its path."""
    payload: Dict[str, Any] = {
        "schema": SCHEMA,
        "shape": command_shape(list(argv)),
        "argv0": Path(argv[0]).name if argv else "",
        "elapsed_sec": round(float(elapsed_sec), 3),
        "exit_code": int(exit_code),
        "killed_at_ceiling": bool(killed_at_ceiling),
        "ceiling_sec": int(ceiling_sec),
        "repo": str(repo or ""),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path = receipt_path(runs_dir, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_receipts(runs_dir: "os.PathLike[str] | str") -> List[Dict[str, Any]]:
    """Every receipt in the runs directory, newest last. A corrupt file is skipped, not fatal."""
    out: List[Dict[str, Any]] = []
    for path in sorted(Path(runs_dir).glob(f"*{RECEIPT_SUFFIX}")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("schema") == SCHEMA:
            out.append(data)
    return out
