"""broker_client -- the cluster door, from a client outside the cluster.

THE SHAPE. In the cluster the context engine is private: it has no Service, no route, and no
token outside the broker. The broker's MCP endpoint (POST /mcp) is the only public door, and
it is authenticated by the estate's gateway. So a client that wants context from the cluster
asks the BROKER -- it never reaches for the engine.

WHY A CLIENT AND NOT A DOOR. The broker's policy (claim scope, freshness, budget, scrubbing,
provenance) is the estate's law. A client that implemented its own version of any of that
would be a second policy, and the estate has one of each layer (AGENTS.md 6). This client
speaks MCP and nothing else: it sends arguments, and it reads the broker's answer -- verdict,
reason, excerpts and all. A refusal is an answer here too.

THE TRANSPORT. The MCP 2026 streamable-HTTP shape: JSON-RPC 2.0 frames POSTed to /mcp, with
`initialize` minting a session id that the broker echoes. The broker is stateless, so a
session is a courtesy and not a requirement; the client still sends it, because that is the
protocol and the transport is the part that changes under a library.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Mapping

PROTOCOL_VERSION = "2026-06-18"


class BrokerUnavailable(RuntimeError):
    """The broker could not be reached or refused the transport. Never an invented answer."""


class BrokerClient:
    """A client of the estate context broker's MCP endpoint."""

    def __init__(
        self, base_url: str, *, token: str | None = None, timeout: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self._token = token or ""
        self.timeout = timeout
        self._session: str | None = None
        self._next_id = 1

    def _post(self, frame: Mapping[str, Any]) -> Any:
        body = json.dumps(frame).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        # S310: the scheme is the broker's own configured address (http/https), never a
        # caller-supplied one.
        req = urllib.request.Request(  # noqa: S310
            f"{self.base_url}/mcp", data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
                session = resp.headers.get("Mcp-Session-Id")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise BrokerUnavailable(
                f"the broker refused the request: HTTP {exc.code} {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BrokerUnavailable(f"the broker is unreachable: {exc}") from exc
        if session:
            self._session = session
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise BrokerUnavailable(
                "the broker answered with something that is not JSON"
            ) from exc

    def initialize(self) -> Any:
        """The MCP handshake. Cheap, and it proves the endpoint speaks MCP before we trust it."""
        frame = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "estate-context-compiler", "version": "1.0"},
            },
        }
        self._next_id += 1
        return self._post(frame)

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Call one of the broker's tools and return its structured answer.

        The broker answers with a body, not an exception: `isError` true is a refusal with a
        verdict, and the client must not paper over it.
        """
        frame = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(arguments)},
        }
        self._next_id += 1
        reply = self._post(frame)
        if not isinstance(reply, dict):
            raise BrokerUnavailable("the broker's answer was not a JSON-RPC frame")
        if "error" in reply:
            raise BrokerUnavailable(f"the broker returned an error: {reply['error']}")
        result = reply.get("result")
        if not isinstance(result, dict):
            raise BrokerUnavailable("the broker's answer had no result")
        return result

    def context(self, **arguments: Any) -> dict[str, Any]:
        """Ask the broker for context. The arguments are the broker's, not ours."""
        return self.call_tool("estate_context", arguments)

    def status(self, **arguments: Any) -> dict[str, Any]:
        """Ask the broker what it knows: the indexed commit, the engine's health, the claims."""
        return self.call_tool("estate_context_status", arguments)
