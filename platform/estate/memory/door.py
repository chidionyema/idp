"""The memory door, from any runtime: one manifest, one key lookup, one call (#6156).

Every runtime reaches estate memory the same way -- an MCP JSON-RPC message POSTed to the gateway
with `Authorization: Bearer <key>` (not x-api-key: the gateway answers that with a 401 that names
neither, docs/how-to/onboarding/mcp-door.md). The key is read by name, from the environment or the
vault (AGENTS.md section 4); it is never written into any runtime's config.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "runtimes.json").read_text())


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
