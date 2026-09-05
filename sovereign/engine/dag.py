"""The content-addressed Merkle DAG on disk, and the branch pointers into
it (R15/R16, master spec 3.1).

Topology, all of it configured, none of it a literal (LAW 46):

    <sidecar.dag_dir>/<hash><dag.node_suffix>   immutable nodes
    <shadow.heads_dir>/<name>                   branch pointers

A node stores a **diff**, never a snapshot. `materialize()` reconstructs
full state by folding every diff from genesis forward, which is what makes
branching free: two branches share their immutable history and only the
tip differs. That property is the test in test_dag.py, not a claim here.

WHAT THIS FIXES, and the class it fixes it at
---------------------------------------------
On 2026-08-25 the founder's real head file `.estate/heads/shadow_main`
named `/var/folders/.../T/tmp59q5f9jp/dag` -- a unittest temporary
directory that had already been reaped. `sb root` therefore reported
verified=False against a DAG root that no longer existed, and no code
anywhere noticed.

The instance was one test (sovereign/sidecar/test_sidecar.py) that
patched config.SB_RECEIPTS but not config.SHADOW_HEADS_DIR, so its
sidecar wrote the estate's real head while pointing at its own scratch
DAG. The class is wider than that test and wider than that file:

    a head pointer may name a DAG directory outside the configured
    DAG root.

`write_head()` below is where every head in this estate is written --
shadow_root.update_head() delegates to it -- and it refuses any dag_dir
that is not the configured root or under it. A test that wants a scratch
DAG must therefore patch the root as well as the heads dir, which is
exactly the declaration whose absence caused the incident. The guard is
proved both ways in test_dag.py (one write that must be refused, one that
must be permitted), because a guard only ever seen refusing has never
been shown to permit (LAW 38). `scan_heads()` is the sweep: it reports
every existing head that dangles, so the present is counted and not only
the future guarded.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from sovereign import config

GENESIS = "0" * config.RECEIPTS_HASH_HEX_LEN


class HeadOutsideDagRootError(ValueError):
    """Raised by write_head() for a dag_dir outside the configured root."""


# ---- paths ----


def root() -> Path:
    """The one DAG root. Read through config on every call so a test (or a
    second estate) that patches config.SIDECAR_DAG_DIR moves the root and
    the guard together, never one without the other."""
    return Path(config.SIDECAR_DAG_DIR)


def heads_dir() -> Path:
    return Path(config.SHADOW_HEADS_DIR)


def node_path(node_hash: str, dag_dir: Path | None = None) -> Path:
    return (dag_dir or root()) / (node_hash + config.DAG_NODE_SUFFIX)


def head_path(name: str) -> Path:
    return heads_dir() / name


def main_head_name() -> str:
    return config.DAG_MAIN_HEAD_FILENAME


# ---- nodes ----


def node_hash_of(body: dict[str, Any]) -> str:
    return hashlib.sha256(config.canonical_json(body)).hexdigest()


def write_node(
    diff: dict[str, Any],
    parent: str = GENESIS,
    *,
    timestamp: int,
    context_hash: str = "",
    budget_remaining: int = 0,
    signature: str = "",
    dag_dir: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """Write one immutable node and return (hash, body). The body shape is
    the spec's checkpoint structure verbatim (3.1): parent, timestamp,
    diff, context_hash, budget_remaining, signature. `timestamp` is a
    parameter and never read from the clock here, so a workflow can supply
    workflow.now() and stay deterministic under replay."""
    body = {
        "parent": parent,
        "timestamp": int(timestamp),
        "diff": diff,
        "context_hash": context_hash,
        "budget_remaining": int(budget_remaining),
        "signature": signature,
    }
    h = node_hash_of(body)
    target = dag_dir or root()
    target.mkdir(parents=True, exist_ok=True)
    path = node_path(h, target)
    if not path.exists():
        # Content-addressed: an identical body is already this same file.
        # Writing it again would be a no-op, so skipping keeps the DAG
        # append-only in the strict sense -- no node is ever rewritten.
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(body, sort_keys=True))
        os.replace(tmp, path)
    return h, body


def read_node(node_hash: str, dag_dir: Path | None = None) -> dict[str, Any] | None:
    path = node_path(node_hash, dag_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def walk(node_hash: str, dag_dir: Path | None = None) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yields (hash, body) from `node_hash` back toward genesis. Stops at a
    missing node, a hash that does not match its own filename, a cycle, or
    config.DAG_MAX_WALK_NODES -- fails closed, never spins."""
    seen: set[str] = set()
    current = node_hash
    count = 0
    while current and current != GENESIS:
        if current in seen or count >= config.DAG_MAX_WALK_NODES:
            return
        seen.add(current)
        body = read_node(current, dag_dir)
        if body is None or node_hash_of(body) != current:
            return
        yield current, body
        count += 1
        current = str(body.get("parent", GENESIS))


def verify(node_hash: str, dag_dir: Path | None = None) -> dict[str, Any]:
    """{root, parent, nodes, verified}: the same shape shadow_root.verify()
    reports, so `sb root` and `sb heads` agree by construction."""
    parent: str | None = None
    count = 0
    last_parent = GENESIS
    for i, (h, body) in enumerate(walk(node_hash, dag_dir)):
        if i == 0:
            parent = str(body.get("parent", GENESIS))
        count += 1
        last_parent = str(body.get("parent", GENESIS))
    verified = bool(node_hash) and (node_hash == GENESIS or (count > 0 and last_parent == GENESIS))
    return {"root": node_hash, "parent": parent, "nodes": count, "verified": verified}


def materialize(node_hash: str, dag_dir: Path | None = None) -> dict[str, Any]:
    """Fold every diff from genesis forward into one full state. This is
    the whole reason nodes hold diffs and not snapshots (spec 3.1: "Only
    the diff is stored. Full state is reconstructed by walking the DAG
    from genesis"). A diff is a flat dict of key -> value; a value of None
    deletes the key, so a diff can express a removal without a snapshot."""
    chain = list(walk(node_hash, dag_dir))
    state: dict[str, Any] = {}
    for _h, body in reversed(chain):
        for key, value in (body.get("diff") or {}).items():
            if value is None:
                state.pop(key, None)
            else:
                state[key] = value
    return state


# ---- heads ----


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def write_head(name: str, node_hash: str, dag_dir: Path | None = None) -> Path:
    """The only writer of a branch pointer in this estate.

    Refuses a dag_dir that is neither the configured DAG root nor under
    it. See the module docstring: that refusal is the guard for the class
    of defect that left the founder's shadow_main naming a reaped test
    temporary directory."""
    target = Path(dag_dir) if dag_dir is not None else root()
    if not _is_inside(target, root()):
        raise HeadOutsideDagRootError(
            f"head {name!r} would name a DAG directory outside the configured root: "
            f"{target} not under {root()}"
        )
    hp = head_path(name)
    hp.parent.mkdir(parents=True, exist_ok=True)
    tmp = hp.with_suffix(hp.suffix + ".tmp")
    tmp.write_text(json.dumps({"root": node_hash, "dag_dir": str(target)}, sort_keys=True))
    os.replace(tmp, hp)
    return hp


def read_head(name: str) -> dict[str, Any] | None:
    hp = head_path(name)
    if not hp.exists():
        return None
    try:
        return json.loads(hp.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def list_heads(d: Path | None = None) -> list[str]:
    d = d or heads_dir()
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_file() and not p.name.endswith(".tmp"))


def scan_dirs() -> list[Path]:
    """Every directory the sweep reads: the configured one, plus the legacy
    ones. A sweep that only looks where the fixed code writes would report
    a clean estate while the instance that caused the fix sits untouched
    one directory away."""
    out = [heads_dir()]
    for extra in config.SHADOW_LEGACY_HEADS_DIRS:
        pth = Path(str(extra))
        if pth not in out:
            out.append(pth)
    return out


def scan_heads(fix: bool = False) -> dict[str, Any]:
    """The sweep (LAW 45 step 4): report every head that dangles, and how.

    Report mode first -- `fix=True` only ever *removes* a head that names
    a DAG directory outside the root or a node that does not exist. It
    never invents a replacement pointer, because a head is a claim about
    history and a guessed one is worse than an absent one."""
    findings: list[dict[str, Any]] = []
    checked = 0
    for d in scan_dirs():
        for name in list_heads(d):
            checked += 1
            hp = d / name
            row = {"head": name, "path": str(hp)}
            try:
                head = json.loads(hp.read_text())
            except (OSError, json.JSONDecodeError):
                findings.append({**row, "problem": "unreadable"})
                continue
            dag_dir = Path(str(head.get("dag_dir", "")))
            node = str(head.get("root", ""))
            row = {**row, "dag_dir": str(dag_dir), "root": node}
            if not _is_inside(dag_dir, root()):
                findings.append({**row, "problem": "outside_root"})
            elif not dag_dir.is_dir():
                findings.append({**row, "problem": "missing_dag_dir"})
            elif read_node(node, dag_dir) is None:
                findings.append({**row, "problem": "missing_node"})
    removed: list[str] = []
    if fix:
        for f in findings:
            try:
                Path(str(f["path"])).unlink()
                removed.append(str(f["path"]))
            except OSError:
                pass
    return {
        "heads_dir": str(heads_dir()),
        "scanned_dirs": [str(d) for d in scan_dirs()],
        "dag_root": str(root()),
        "checked": checked,
        "dangling": findings,
        "count": len(findings),
        "removed": removed,
        "ok": not findings,
    }
