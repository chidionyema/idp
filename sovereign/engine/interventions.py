"""The signed, append-only transparency log of interventions (R17, spec
3.1 and 4.1).

Spec 3.1 topology:

    interventions/
        <counter>_<hash>.json

Spec 4.1: "Receipts are Merkleized into an append-only transparency log,
not JSON files." The receipt chain in engine/receipts.py is already that
log -- monotonic counter, prev_hash link, HMAC signature under the estate
key, a signed head anchor against tail truncation, and since R23 a signed
watermark so the counter cannot be replayed. The crew#200 gap table said
so in one line: "chain real; no dir".

So this module builds no second chain. It writes the *view* the spec
names, one file per intervention, each holding the exact signed line the
chain already committed to, named by that line's own counter and hash.
Building a parallel log would have been the LAW 43 violation, and worse,
a second thing to keep in step.

Append-only is enforced two ways: `record()` refuses to overwrite an
existing filename (a name is counter+hash, so a collision means either a
replayed counter or a rewritten history), and `verify()` re-derives every
file's name from its own contents and checks it against the chain.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import receipts as receipts_mod


class NotAppendOnly(RuntimeError):
    """A file for this counter+hash already exists."""


def directory() -> Path:
    return Path(config.INTERVENTIONS_DIR)


def is_intervention(kind: str) -> bool:
    """Founder actions are interventions; engine bookkeeping is not. The
    list is config (interventions.kinds), so an estate can widen it
    without a code change."""
    return str(kind) in set(config.INTERVENTIONS_KINDS)


def filename_for(counter: int, line_hash: str) -> str:
    return f"{int(counter)}{config.INTERVENTIONS_FILENAME_SEP}{line_hash}{config.DAG_NODE_SUFFIX}"


def mirror(line: dict[str, Any]) -> Path | None:
    """Write one already-appended chain line into the interventions dir.
    Returns the path, or None when the line is not an intervention kind."""
    if not is_intervention(str(line.get("kind", ""))):
        return None
    d = directory()
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename_for(int(line.get("counter", 0)), str(line.get("hash", "")))
    if path.exists():
        raise NotAppendOnly(f"{path} already exists; an intervention log is never rewritten")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(line, sort_keys=True))
    os.replace(tmp, path)
    return path


def record(kind: str, by: str, text: str = "", **fields: Any) -> dict[str, Any]:
    """Append one intervention to the signed chain, then mirror it. The
    chain is the source of truth; the file is the spec's view of it, so
    the order is chain first, always."""
    line = receipts_mod.append({"kind": kind, "by": by, "text": text, **fields})
    path = mirror(line)
    return {"line": line, "path": str(path) if path else None}


def read_all() -> list[dict[str, Any]]:
    d = directory()
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(d.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.name.endswith(".tmp"):
            continue
        try:
            out.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            out.append({"unreadable": path.name})
    return sorted(out, key=lambda r: int(r.get("counter", 0)))


def verify() -> dict[str, Any]:
    """Every file must (a) be named for its own counter and hash, (b) be
    byte-identical in content to the chain line with that counter, and (c)
    the chain itself must verify. Any of the three failing fails closed."""
    chain = receipts_mod.verify()
    if not chain.get("ok"):
        return {"ok": False, "entries": 0, "reason": chain.get("reason") or "chain", "chain": chain}
    by_counter = {int(r.get("counter", 0)): r for r in receipts_mod.read_all()}
    entries = 0
    for row in read_all():
        counter = int(row.get("counter", 0))
        line_hash = str(row.get("hash", ""))
        expected_name = filename_for(counter, line_hash)
        path = directory() / expected_name
        if not path.exists():
            return {"ok": False, "entries": entries, "reason": "misnamed", "counter": counter}
        chain_line = by_counter.get(counter)
        if chain_line is None:
            return {"ok": False, "entries": entries, "reason": "not_in_chain", "counter": counter}
        if json.dumps(chain_line, sort_keys=True) != json.dumps(row, sort_keys=True):
            return {"ok": False, "entries": entries, "reason": "diverged", "counter": counter}
        entries += 1
    return {"ok": True, "entries": entries, "reason": None, "chain": chain}


def backfill() -> dict[str, Any]:
    """Mirror every intervention already in the chain that has no file
    yet. This is what makes the directory exist on an estate whose chain
    predates this module -- and it is idempotent, because a file that is
    already correct is left alone rather than rewritten."""
    written = 0
    skipped = 0
    for line in receipts_mod.read_all():
        if not is_intervention(str(line.get("kind", ""))):
            continue
        path = directory() / filename_for(int(line.get("counter", 0)), str(line.get("hash", "")))
        if path.exists():
            skipped += 1
            continue
        mirror(line)
        written += 1
    return {"written": written, "skipped": skipped, "dir": str(directory())}
