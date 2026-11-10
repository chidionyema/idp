"""The memory door, from any runtime: one manifest, one key lookup, one call (#6156).

Every runtime reaches estate memory the same way -- an MCP JSON-RPC message POSTed to the gateway
with `Authorization: Bearer <key>` (not x-api-key: the gateway answers that with a 401 that names
neither, docs/how-to/onboarding/mcp-door.md). The key is read by name, from the environment or the
vault (AGENTS.md section 4); it is never written into any runtime's config.
"""

from __future__ import annotations

import json
import os
import hashlib
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "runtimes.json").read_text())
import local_store  # noqa: E402 - the declared local origin, same contract

_SYNC_GUARD = threading.Lock()
_LAST_SYNC_ATTEMPT = 0.0
_LOCAL_STORE = None
_LOCAL_NAMESPACE = os.environ.get("ESTATE_MEMORY_NAMESPACE", "estate")

MCP_TOOLS = [
    {
        "name": "brief",
        "description": "Relevant and recent estate memory for a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
        },
    },
    {
        "name": "recall",
        "description": "Recall estate memory by query and structured filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "subject": {"type": "string"},
                "kind": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "remember",
        "description": "Write one durable estate memory.",
        "inputSchema": {
            "type": "object",
            "required": ["content"],
            "properties": {
                "content": {"type": "string"},
                "subject": {"type": "string"},
                "kind": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source": {"type": "string"},
                "runtime": {"type": "string"},
            },
        },
    },
]


def _store():
    global _LOCAL_STORE
    if _LOCAL_STORE is None:
        _LOCAL_STORE = local_store.Store(local_store.DEFAULT_DB)
    return _LOCAL_STORE


def _memory_key(content: str, metadata: dict) -> str:
    subject = (
        re.sub(r"[^a-z0-9_-]+", "-", metadata["subject"].lower()).strip("-")
        or "general"
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"{metadata['kind']}.{subject[:120]}.{digest}"


def _item(row: dict) -> dict:
    return {"text": row["content"], "metadata": row.get("provenance") or {}}


def _local_memory(message: dict) -> dict | None:
    method = message.get("method")
    mid = message.get("id")
    if mid is None:
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": MCP_TOOLS}}
    if method != "tools/call":
        return None
    params = message.get("params") or {}
    name = params.get("name")
    args = params.get("arguments") or {}
    if name not in {"brief", "recall", "remember"}:
        return None
    try:
        if name == "remember":
            content = str(args.get("content") or "").strip()
            if not content:
                raise ValueError("content is empty")
            tags = sorted(
                {
                    str(tag).strip().lower()
                    for tag in args.get("tags") or []
                    if str(tag).strip()
                }
            )
            metadata = {
                "subject": str(args.get("subject") or "").strip(),
                "kind": str(args.get("kind") or "fact").strip().lower(),
                "tags": tags,
                "source": str(args.get("source") or "mcp").strip(),
                "runtime": str(args.get("runtime") or "").strip().lower(),
                "rung": "local-primary",
                "storage": "local-primary",
            }
            key = _memory_key(content, metadata)
            saved = _store().save(
                _LOCAL_NAMESPACE,
                key,
                {
                    "content": content,
                    "trust_tier": "raw_source",
                    "provenance": metadata,
                },
                None,
            )
            if saved["_status"] >= 400:
                raise ValueError(json.dumps(saved["_body"]))
            payload = {
                "written": True,
                "namespace": _LOCAL_NAMESPACE,
                "key": key,
                "version": saved["_body"].get("version"),
                "trust_tier": "raw_source",
                "rung": "local-primary",
                "storage": "local-primary",
            }
        elif name == "recall":
            query = str(args.get("query") or "").strip()
            limit = int(args.get("limit") or 5)
            rows = (
                _store().search(query, _LOCAL_NAMESPACE, limit)
                if query
                else _store().list(_LOCAL_NAMESPACE, limit)
            )
            subject = str(args.get("subject") or "")
            kind = str(args.get("kind") or "").lower()
            tags = {str(tag).lower() for tag in args.get("tags") or []}
            rows = [
                row
                for row in rows
                if (not subject or row["provenance"].get("subject") == subject)
                and (not kind or row["provenance"].get("kind") == kind)
                and tags.issubset(set(row["provenance"].get("tags") or []))
            ]
            payload = {
                "memories": [_item(row) for row in rows],
                "count": len(rows),
                "namespace": _LOCAL_NAMESPACE,
                "storage": "local-primary",
            }
        else:
            task = str(args.get("task") or "").strip()
            limit = int(args.get("limit") or 8)
            relevant = (
                [_item(row) for row in _store().search(task, _LOCAL_NAMESPACE, limit)]
                if task
                else []
            )
            recent = [
                _item(row)
                for row in _store().recent(
                    [_LOCAL_NAMESPACE], ("decision", "incident"), limit
                )
            ]
            payload = {
                "relevant": relevant,
                "recent": recent,
                "namespace": _LOCAL_NAMESPACE,
                "search_by_meaning": False,
                "storage": "local-primary",
            }
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "structuredContent": payload,
                "isError": False,
            },
        }
    except Exception as exc:
        payload = {"error": f"{type(exc).__name__}: {exc}", "storage": "local-primary"}
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "content": [{"type": "text", "text": json.dumps(payload)}],
                "structuredContent": payload,
                "isError": True,
            },
        }


def key() -> str:
    door = MANIFEST["door"]
    value = os.environ.get(door["key_env"], "")
    if value:
        return value
    loader = Path(os.path.expanduser(door["vault_loader"]))
    if not loader.exists():
        return ""
    try:
        out = subprocess.run(  # noqa: S603 - the vault's own loader, argv fixed by the manifest
            [str(loader), *door["vault_entry"]],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout if out.returncode == 0 else ""


def post(
    message: dict, secret: str, timeout: float = 10, session: str = ""
) -> tuple[dict | None, str]:
    """POST one JSON-RPC message; return (the reply with its id, or None, and the session id)."""
    # One door, local-primary. The cluster service is a replica when reachable, never
    # the thing that recovery waits on.
    local_reply = _local_memory(message)
    if local_reply is not None:
        params = message.get("params") or {}
        if message.get("method") == "tools/call" and params.get("name") == "remember":
            _sync_pending_async(secret)
        return local_reply, session
    return _remote_post(message, secret, timeout, session)


def _remote_post(
    message: dict, secret: str, timeout: float = 10, session: str = ""
) -> tuple[dict | None, str]:
    """The cloud/Postgres replica's original MCP transport."""
    door = MANIFEST["door"]
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        door["header"]: f"{door['scheme']} {secret}",
    }
    if session:
        headers["mcp-session-id"] = session
    # The key rides in a header: never send it anywhere but an https door.
    if not door["url"].startswith("https://"):
        raise ValueError(f"memory door must be https, got {door['url']}")
    req = urllib.request.Request(  # noqa: S310 - https asserted above, URL from the manifest
        door["url"], json.dumps(message).encode(), headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - as above
        session = resp.headers.get("mcp-session-id", session)
        body = resp.read().decode()
    if "id" not in message:
        return None, session
    return _reply(body, message["id"]), session


def _sync_pending_async(secret: str) -> None:
    """Replay local-primary writes to the replica without delaying the caller."""
    global _LAST_SYNC_ATTEMPT
    now = time.monotonic()
    if now - _LAST_SYNC_ATTEMPT < 30 or not _SYNC_GUARD.acquire(blocking=False):
        return
    _LAST_SYNC_ATTEMPT = now

    def run() -> None:
        try:
            sync_pending(secret, timeout=5)
        finally:
            _SYNC_GUARD.release()

    threading.Thread(target=run, name="memory-replica-sync", daemon=True).start()


def sync_pending(secret: str, timeout: float = 5) -> int:
    """Replay every unsynced local-primary fact to the Postgres replica.

    Returns the number of facts acknowledged. Stops at the first replica failure
    so ordering is preserved and the same deterministic key retries later.
    """
    synced: list[str] = []
    for row in _store().pending(_LOCAL_NAMESPACE, limit=500):
        reply, _ = _remote_post(
            {
                "jsonrpc": "2.0",
                "id": f"sync:{row['key']}",
                "method": "tools/call",
                "params": {
                    "name": "remember",
                    "arguments": {
                        "content": row["content"],
                        "subject": row["provenance"].get("subject", ""),
                        "kind": row["provenance"].get("kind", "fact"),
                        "tags": row["provenance"].get("tags", []),
                        "source": row["provenance"].get("source", "mcp"),
                        "runtime": row["provenance"].get("runtime", ""),
                    },
                },
            },
            secret,
            timeout=timeout,
        )
        result = (reply or {}).get("result") or {}
        payload = result.get("structuredContent") or {}
        if result.get("isError") or not payload.get("written"):
            break
        synced.append(row["key"])
    _store().mark_synced(_LOCAL_NAMESPACE, synced)
    return len(synced)


def _reply(body: str, want) -> dict | None:
    """The reply in a JSON body, or in an SSE stream's `data:` lines."""
    chunks = (
        [body]
        if body.lstrip().startswith("{")
        else [
            line[5:].strip() for line in body.splitlines() if line.startswith("data:")
        ]
    )
    for chunk in chunks:
        try:
            msg = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and msg.get("id") == want:
            return msg
    return None


def call(tool: str, arguments: dict, secret: str, timeout: float = 10):
    """Call one memory tool; return its structured result, or raise."""
    reply, _ = post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
        secret,
        timeout,
    )
    if not reply or "error" in reply:
        raise RuntimeError((reply or {}).get("error", "no reply"))
    result = reply["result"]
    if result.get("isError"):
        raise RuntimeError(result.get("content"))
    if "structuredContent" in result:
        return result["structuredContent"]
    text = "".join(c.get("text", "") for c in result.get("content", []))
    return json.loads(text)
