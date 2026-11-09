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
import http.client
import urllib.error
import urllib.parse
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
    try:
        req = urllib.request.Request(  # noqa: S310 - https asserted above, URL from the manifest
            door["url"], json.dumps(message).encode(), headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - as above
            session = resp.headers.get("mcp-session-id", session)
            body = resp.read().decode()
    except urllib.error.HTTPError:
        # The cloud ANSWERED -- a 4xx/5xx is the cloud's answer, whatever it says. HTTPError is a
        # subclass of URLError, so catching URLError first silently made every cloud refusal look
        # like a dead origin and let the local origin answer in its place. That is the wrong
        # direction: it would hide a live cloud behind a stale local copy. Re-raise before the
        # fallback clause can see it (measured by the falsifier in tests/test_memory_local_origin.py).
        raise
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        http.client.HTTPException,
    ) as exc:
        # The one cloud origin has no road. Measured 2026-11-09: Cloudflare answers error code
        # 1033 (the Argo tunnel's origin is not running) and the handshake dies EOF
        # (_ssl.c:1129). One origin with no declared fallback is root cause R6 and R8; the
        # ladder is ADR 0037. Fall to the local origin, and only on a TRANSPORT failure -- an
        # answer from the cloud is the cloud's answer whatever it says.
        local = _local(message, timeout)
        if local is None:
            raise RuntimeError(
                f"memory door unreachable and no local origin: {type(exc).__name__}"
            ) from exc
        return local, session
    if "id" not in message:
        return None, session
    return _reply(body, message["id"]), session


def _local(message: dict, timeout: float) -> dict | None:
    """The local origin's reply, or None when it is not running.

    The local origin speaks the memory server's REST routes, not JSON-RPC, so the tools are
    mapped onto the routes they name. It binds loopback only (checked here, not assumed), and
    it never sees the cloud key: a loopback caller needs no key, and sending one would write a
    cloud credential into a local log for no gain.
    """
    base = os.environ.get("ESTATE_MEMORY_LOCAL_URL") or "http://127.0.0.1:8002"
    parsed = urllib.parse.urlparse(base)
    if parsed.hostname not in ("127.0.0.1", "::1", "localhost"):
        return None
    if "id" not in message or message.get("method") != "tools/call":
        return None
    params = message.get("params") or {}
    name = params.get("name") or ""
    args = params.get("arguments") or {}
    ns = args.get("namespace") or "estate"
    route, method, payload = None, "POST", None
    if name == "remember":
        key = args.get("key") or args.get("subject") or "fact"
        route, method = f"/memories/{ns}/{key}", "PUT"
        payload = {
            "namespace": ns,
            "key": key,
            "content": args.get("content") or "",
            "provenance": {"source": args.get("runtime") or "local"},
        }
    elif name == "recall":
        route = f"/memories/{ns}/recall"
        payload = {
            "query": args.get("query") or "",
            "namespace": ns,
            "limit": int(args.get("limit") or 10),
        }
    elif name == "brief":
        route = f"/memories/{ns}/brief"
        payload = {
            "task": args.get("task") or "",
            "namespace": ns,
            "limit": int(args.get("limit") or 8),
        }
    if route is None:
        return None
    req = urllib.request.Request(  # noqa: S310 - loopback asserted above
        base + route,
        json.dumps(payload).encode(),
        {"content-type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - as above
            body = json.loads(resp.read().decode() or "{}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    text = json.dumps(body)
    return {
        "jsonrpc": "2.0",
        "id": message["id"],
        "result": {
            "content": [{"type": "text", "text": text}],
            "structuredContent": body,
            "origin": base,
        },
    }


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
