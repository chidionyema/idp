"""FleetView item #4 (spend_usd): the `llm` runner tags every request with the session that
sent it, so `backstage/plugins/fleetview-backend/src/spend.py` can read it back out of
LiteLLM's own ledger. No feature file: this is engine plumbing behind the board, graded the
same way test_fleetview_notes.py grades notes.py -- a plain unit suite against runners.py.

The proxy is faked at the wire with httpx.MockTransport, the same technique test_cp30.py uses
for the consensus fan-out -- no live LiteLLM proxy required.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from sovereign import config as config_mod
from sovereign.engine import runners


@pytest.fixture()
def fake_proxy(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    async def handle(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    real_client = httpx.AsyncClient

    def client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handle)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(runners.httpx, "AsyncClient", client)
    monkeypatch.setattr(config_mod, "LITELLM_BASE_URL", "http://litellm.invalid")
    monkeypatch.setattr(runners.config, "LITELLM_BASE_URL", "http://litellm.invalid")
    # activity.heartbeat() needs a real Temporal activity execution context (the worker
    # supplies one in production); this suite grades the metadata-tagging logic, not
    # Temporal's own plumbing, the same boundary test_cp30.py draws around the fan-out.
    monkeypatch.setattr(runners.activity, "heartbeat", lambda *a, **k: None)
    return captured


def test_a_session_id_is_tagged_into_the_request_metadata(fake_proxy):
    asyncio.run(runners.run("llm", "say hi", None, 1, [], session_id="sb-1"))
    metadata = fake_proxy["body"].get("metadata")
    assert metadata == {"session_id": "sb-1", "runtime": "sovereign"}


def test_no_session_id_sends_no_metadata_field(fake_proxy):
    asyncio.run(runners.run("llm", "say hi", None, 1, []))
    assert "metadata" not in fake_proxy["body"]


def test_other_runners_accept_and_ignore_session_id(fake_proxy):
    result = asyncio.run(runners.run("echo", "hello", None, 1, [], session_id="sb-1"))
    assert result["output"] == "hello"
