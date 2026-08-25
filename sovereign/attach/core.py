"""sb attach / sb status / sb halt --all -- estate-agnostic mounting (cp21).

This module never imports sovereign.config at module load time, for the
same reason sovereign/trust/anchor.py does not: sovereign/config.py
imports sovereign.attach.config_keys (to merge ATTACH_KEYS), which first
runs sovereign/attach/__init__.py -- kept import-free of this file so that
chain is never triggered. Every function that needs the full config
resolution order (file < env < flag) imports sovereign.config lazily,
inside the function body, by which point config.py has always finished
loading (see sovereign/attach/README.md).
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sovereign.attach import config_keys as ck
from sovereign.attach.policy import scaffold_policy_text
from sovereign.trust.canonical import canonical_relpath


def _cfg(key: str) -> Any:
    """Full resolution order (file < env < flag) when sovereign.config is
    available; otherwise (should not happen once A's merge lines land, but
    keeps this module usable standalone like otto/cockpit's config_keys)
    falls back to env-or-default."""
    try:
        from sovereign import config
        return config.get(key).value
    except Exception:
        return ck.get(key)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Node counting + root hash
# ---------------------------------------------------------------------------


def _list_tracked_relpaths(root: Path) -> list[str] | None:
    """`git ls-files` output if `root` is a git repo, else None (caller
    falls back to a filesystem walk)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, timeout=_cfg("attach.git_ls_files_timeout_s"),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def _walk_relpaths(root: Path) -> list[str]:
    ignored = set(_cfg("attach.ignored_dirnames"))
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored]
        for name in filenames:
            out.append(str((Path(dirpath) / name).relative_to(root)))
    return out


def list_nodes(root: Path) -> list[str]:
    """Canonical relpaths (cp20 separators) of every node this estate
    tracks: git-tracked files if `root` is a git repo, else every file
    under `root` minus attach.ignored_dirnames."""
    tracked = _list_tracked_relpaths(root)
    relpaths = tracked if tracked is not None else _walk_relpaths(root)
    return sorted({canonical_relpath(str(root), r) for r in relpaths})


def _blob_hash(root: Path, relpath: str) -> str:
    try:
        return hashlib.sha256((root / relpath).read_bytes()).hexdigest()
    except OSError:
        return ""


def compute_root_hash(root: Path, relpaths: list[str]) -> str:
    """sha256 over the sorted (canonical relpath, content hash) pairs --
    content-based, not git's own object hashes, so it is identical for a
    git and a non-git walk of the same files and unaffected by git's own
    hashing quirks (line-ending filters, pack format)."""
    hasher = hashlib.sha256()
    for rel in relpaths:
        hasher.update(rel.encode())
        hasher.update(b"\x00")
        hasher.update(_blob_hash(root, rel).encode())
        hasher.update(b"\n")
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Estate directory resolution
# ---------------------------------------------------------------------------


def _estate_home() -> Path:
    env = os.environ.get("ESTATE_HOME")
    if env:
        return Path(env)
    return Path.home() / ".estate"


def estate_dir_for(root: Path, mode: str | None = None) -> Path:
    mode = mode or _cfg("attach.mode")
    if mode == "global":
        key = hashlib.sha256(str(root).encode()).hexdigest()[: int(_cfg("attach.path_hash_hex_len"))]
        return _estate_home() / _cfg("attach.global_estates_dirname") / key
    return root / _cfg("attach.dirname")


# ---------------------------------------------------------------------------
# Receipts: reuse engine.receipts' exact chain algorithm and signing key,
# redirected at the module-attribute it reads its target path from, so
# an estate's receipts are a genuinely separate chain under its own
# .estate/ (cp21 scenario 3) without duplicating cp19's hash-chain code.
# Not safe across concurrent redirects in the same process; fine for the
# single synchronous CLI invocation this is used from.
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _receipts_redirected_to(path: Path):
    from sovereign import config

    original = config.SB_RECEIPTS
    config.SB_RECEIPTS = path
    try:
        yield
    finally:
        config.SB_RECEIPTS = original


def append_estate_receipt(estate_dir: Path, record: dict[str, Any]) -> dict[str, Any]:
    from sovereign.engine import receipts as receipts_mod

    path = estate_dir / _cfg("attach.receipts_filename")
    record = dict(record)
    record.setdefault("ts", _now_iso())
    with _receipts_redirected_to(path):
        return receipts_mod.append(record)


# ---------------------------------------------------------------------------
# Registry: every attached estate, for `sb status` / `sb halt --all`.
# ---------------------------------------------------------------------------


def _registry_path() -> Path:
    return _estate_home() / _cfg("attach.registry_filename")


def _registry_append(entry: dict[str, Any]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def list_attached_estates() -> list[dict[str, Any]]:
    path = _registry_path()
    if not path.exists():
        return []
    latest: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        root = entry.get("root")
        if root:
            latest[root] = entry
    return sorted(latest.values(), key=lambda e: e["root"])


# ---------------------------------------------------------------------------
# attach()
# ---------------------------------------------------------------------------


def attach(path: str | Path, write_policy: bool = False) -> dict[str, Any]:
    root = Path(path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    mode = _cfg("attach.mode")
    estate_dir = estate_dir_for(root, mode)
    estate_dir.mkdir(parents=True, exist_ok=True)

    relpaths = list_nodes(root)
    root_hash = compute_root_hash(root, relpaths)

    policy_path = root / _cfg("attach.policy_filename")
    scaffolded = not policy_path.exists()
    if scaffolded:
        policy_label = _cfg("attach.policy_scaffolded_label")
        policy_text = scaffold_policy_text()
        (estate_dir / _cfg("attach.policy_filename")).write_text(policy_text)
        if write_policy:
            policy_path.write_text(policy_text)
    else:
        policy_label = _cfg("attach.policy_existing_label")

    mounted_line = _cfg("attach.mounted_receipt_template").format(
        root=str(root), nodes=len(relpaths), hash=root_hash
    )
    policy_line = _cfg("attach.policy_inherited_receipt_template").format(
        policy=policy_label, mode=_cfg("attach.policy_mode")
    )

    append_estate_receipt(estate_dir, {
        "session_id": "-", "kind": "estate_mounted", "by": "sb-attach",
        "text": mounted_line, "step": 0, "status": "attached", "task": "", "runner": "",
    })
    append_estate_receipt(estate_dir, {
        "session_id": "-", "kind": "policy_inherited", "by": "sb-attach",
        "text": policy_line, "step": 0, "status": "attached", "task": "", "runner": "",
    })

    _registry_append({
        "event": "attach", "root": str(root), "estate_dir": str(estate_dir),
        "mode": mode, "ts": _now_iso(),
    })

    return {
        "root": str(root),
        "nodes": len(relpaths),
        "hash": root_hash,
        "estate_dir": str(estate_dir),
        "mode": mode,
        "policy_scaffolded": scaffolded,
        "receipt_lines": [mounted_line, policy_line],
    }


# ---------------------------------------------------------------------------
# status() / halt_all() -- async, mirror engine.client's shape (cp21).
# ---------------------------------------------------------------------------


async def status() -> dict[str, Any]:
    from sovereign.engine import client as engine_client

    estates = list_attached_estates()
    sessions = await engine_client.list_sessions()
    by_repo: dict[str | None, list[dict[str, Any]]] = {}
    for s in sessions:
        by_repo.setdefault(s.get("repo"), []).append(s)

    limit = int(_cfg("attach.status_max_sessions_per_estate"))
    out = []
    for e in estates:
        root = e["root"]
        root_sessions = by_repo.get(root, [])
        out.append({
            "root": root,
            "estate_dir": e.get("estate_dir"),
            "mode": e.get("mode"),
            "running": sum(1 for s in root_sessions if s.get("status") in ("running", "waiting")),
            "sessions": root_sessions[:limit],
        })
    return {"estates": out}


async def halt_all(by: str, signed: bool = False) -> dict[str, Any]:
    from sovereign.engine import client as engine_client
    from sovereign.engine import receipts as receipts_mod

    sessions = await engine_client.list_sessions()
    running = [s for s in sessions if s.get("status") in ("running", "waiting")]
    results = []
    for s in running:
        sid = s["session_id"]
        signal_res = await engine_client.signal(sid, "stop", by, "halt --all")
        record = {
            "session_id": sid, "kind": "halt", "by": by, "text": "halt --all",
            "step": s.get("step", 0), "status": "stopped",
            "task": s.get("task", ""), "runner": s.get("runner", ""),
        }
        if signed:
            record["signed"] = True
        receipt = receipts_mod.append(record)
        results.append({"session_id": sid, "ok": signal_res.get("ok", False), "receipt_counter": receipt.get("counter")})
    return {"halted": len(results), "sessions": results}
