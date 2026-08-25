"""Rewind, recover and audit over the Merkle DAG (cp33, cp34, cp35).

Three commands share one model: `heads/main` (dag.main_head_name) names
the root the estate is at, a node is immutable and never deleted, and the
projection view under views.dir is derived from the DAG by folding diffs
from genesis (dag.materialize) and can always be thrown away and rebuilt.

  rewind(H)   moves heads/main to H and rebuilds the view. Every node
              after H stays on disk (spec 3.2: "archived, not deleted --
              Merkle DAG preserves them for audit"). The receipt is
              signed, because rewind is in ops.destructive.
  recover()   finds the last fully committed root -- a node that exists,
              hashes to its own name, and walks to genesis -- and points
              heads/main at it. A head that names a torn or missing node
              is the crash it exists to repair. Half-written node files
              (the .tmp dag.write_node leaves if killed mid-replace) are
              swept, because they were never nodes.
  audit()     verifies the signed receipt chain (every signature, the
              monotonic counter, the head anchor -- receipts.verify) and
              walks heads/main to genesis. The first break fails it.

Services are not touched here. Stopping and starting the worker and
Temporal is `sb down` and `sb up`, and cli.py wraps these calls in them;
this module has no subprocess and no clock, so every function is testable
against a temporary estate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import dag
from sovereign.engine import interventions as interventions_mod
from sovereign.engine import ops
from sovereign.engine import receipts as receipts_mod

REWIND_KIND = "rewind"
RECOVER_KIND = "recover"


class UnknownRoot(ValueError):
    """The named hash is not a node that walks to genesis in this DAG."""


# ---- projection views ----


def views_dir() -> Path:
    return Path(config.VIEWS_DIR)


def main_view_path() -> Path:
    return views_dir() / config.VIEWS_MAIN_FILENAME


def rebuild_views(root_hash: str) -> dict[str, Any]:
    """Fold the DAG from genesis to `root_hash` and write the result as
    the main projection view. Written to a tmp file and moved into place,
    so a crash mid-write leaves the previous view rather than a torn one
    -- and recover() rebuilds it anyway."""
    state = dag.materialize(root_hash)
    view = {"root": root_hash, "nodes": dag.verify(root_hash)["nodes"], "state": state}
    path = main_view_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(view, sort_keys=True))
    os.replace(tmp, path)
    return view


def read_main_view() -> dict[str, Any] | None:
    path = main_view_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def main_root() -> str:
    head = dag.read_head(dag.main_head_name())
    return str(head.get("root", dag.GENESIS)) if head else dag.GENESIS


# ---- rewind (cp33) ----


def rewind(target: str, by: str, *, signed: bool) -> dict[str, Any]:
    if target != dag.GENESIS and not dag.verify(target)["verified"]:
        raise UnknownRoot(f"{target!r} is not a node that walks to genesis under {dag.root()}")
    previous = main_root()
    nodes_before = _count_nodes()
    dag.write_head(dag.main_head_name(), target)
    view = rebuild_views(target)
    nodes_after = _count_nodes()
    spec = ops.classify(REWIND_KIND)
    line = interventions_mod.record(
        REWIND_KIND,
        by,
        f"[✓] REWIND | to:{target} | from:{previous}",
        session_id="",
        step=0,
        status=REWIND_KIND,
        task="",
        runner="",
        to=target,
        previous=previous,
        signed=bool(signed),
        op_class=spec.classification,
        nodes_kept=nodes_after,
    )["line"]
    return {
        "ok": True,
        "to": target,
        "previous": previous,
        "head": dag.main_head_name(),
        "view": str(main_view_path()),
        "state": view["state"],
        "nodes_before": nodes_before,
        "nodes_after": nodes_after,
        "signed": bool(signed),
        "hw_backend": line.get("hw_backend"),
        "receipt": line["hash"],
        "counter": line["counter"],
    }


def _count_nodes() -> int:
    d = dag.root()
    if not d.is_dir():
        return 0
    suffix = config.DAG_NODE_SUFFIX
    return sum(1 for p in d.iterdir() if p.is_file() and p.name.endswith(suffix))


# ---- recover (cp35) ----


def committed_roots() -> list[tuple[int, str]]:
    """Every node on disk that is fully committed: readable, named by its
    own hash, and walkable to genesis. Returned as (timestamp, hash),
    newest last."""
    d = dag.root()
    if not d.is_dir():
        return []
    suffix = config.DAG_NODE_SUFFIX
    out: list[tuple[int, str]] = []
    for p in sorted(d.iterdir()):
        if not p.is_file() or not p.name.endswith(suffix):
            continue
        h = p.name[: -len(suffix)]
        body = dag.read_node(h)
        if body is None or dag.node_hash_of(body) != h:
            continue
        if not dag.verify(h)["verified"]:
            continue
        out.append((int(body.get("timestamp", 0)), h))
    return sorted(out)


def last_committed_root() -> str:
    """The newest fully committed node that no other committed node
    extends. The current heads/main wins a tie when it is itself
    committed, so a healthy estate recovers to exactly where it was."""
    roots = committed_roots()
    if not roots:
        return dag.GENESIS
    parents = {str((dag.read_node(h) or {}).get("parent", "")) for _ts, h in roots}
    tips = [(ts, h) for ts, h in roots if h not in parents]
    current = main_root()
    if any(h == current for _ts, h in tips):
        return current
    return tips[-1][1] if tips else roots[-1][1]


def sweep_torn_writes() -> list[str]:
    """Remove the .tmp files a killed dag.write_node or rebuild_views left
    behind. These were never nodes or views -- os.replace never ran -- so
    removing them deletes nothing from the DAG."""
    removed: list[str] = []
    tmp_suffix = config.DAG_NODE_SUFFIX + ".tmp"
    for d in (dag.root(), views_dir()):
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.is_file() and p.name.endswith(".tmp") and (d != dag.root() or p.name.endswith(tmp_suffix)):
                try:
                    p.unlink()
                    removed.append(str(p))
                except OSError:
                    continue
    return removed


def recover(by: str) -> dict[str, Any]:
    head_before = main_root()
    torn = sweep_torn_writes()
    root_hash = last_committed_root()
    dag.write_head(dag.main_head_name(), root_hash)
    view = rebuild_views(root_hash)
    line = interventions_mod.record(
        RECOVER_KIND,
        by,
        f"[✓] RECOVER | root:{root_hash}",
        session_id="",
        step=0,
        status=RECOVER_KIND,
        task="",
        runner="",
        root=root_hash,
        head_before=head_before,
        torn_writes_removed=len(torn),
    )["line"]
    return {
        "ok": True,
        "root": root_hash,
        "head_before": head_before,
        "head": dag.main_head_name(),
        "view": str(main_view_path()),
        "state": view["state"],
        "nodes": view["nodes"],
        "torn_writes_removed": torn,
        "receipt": line["hash"],
        "counter": line["counter"],
    }


# ---- audit (cp34) ----


def audit_verify() -> dict[str, Any]:
    """ok only when the receipt chain verifies end to end AND heads/main
    walks to genesis. `entries` is the chain length, which is what the
    auditor compares against the log they were handed."""
    chain = receipts_mod.verify()
    root_hash = main_root()
    dag_result = dag.verify(root_hash)
    ok = bool(chain.get("ok")) and bool(dag_result["verified"])
    reason = None
    if not chain.get("ok"):
        reason = f"chain:{chain.get('reason')}"
    elif not dag_result["verified"]:
        reason = f"dag:{root_hash}"
    return {
        "ok": ok,
        "entries": int(chain.get("count", 0)),
        "first_broken_counter": chain.get("first_broken_counter"),
        "reason": reason,
        "chain": chain,
        "dag": dag_result,
    }


def audit_at(receipt_hash: str) -> dict[str, Any] | None:
    """Who did what, when, under which policy, and which trust backend
    signed it -- read off one chain line. The chain is verified first;
    an answer read from a broken chain is not evidence."""
    chain = receipts_mod.verify()
    for row in receipts_mod.read_all():
        if str(row.get("hash", "")) != receipt_hash:
            continue
        kind = str(row.get("kind", ""))
        spec = ops.classify(kind)
        return {
            "hash": receipt_hash,
            "counter": row.get("counter"),
            "who": row.get("by"),
            "what": {"kind": kind, "text": row.get("text", ""), "session_id": row.get("session_id"), "step": row.get("step")},
            "when": row.get("ts"),
            "policy": {
                "op_class": spec.classification,
                "destructive": spec.destructive,
                "needs_quorum": spec.needs_quorum,
                "needs_hardware_signature": spec.needs_hardware_signature,
                "signed_approval_required": bool(config.REQUIRE_SIGNED_APPROVAL),
            },
            "signed_by": {
                "chain_backend": row.get("backend"),
                "hardware_backend": row.get("hw_backend"),
                "attestation": row.get("attestation"),
            },
            "chain_ok": bool(chain.get("ok")),
        }
    return None
