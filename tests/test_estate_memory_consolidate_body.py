"""The MCP remember's consolidate call must match the server's contract exactly.

harness_memory_consolidate (platform/unified-memory-server/main.py) takes
run_id/project_id/provenance from the query string and the candidate list as the
bare JSON body. estate_memory.py used to post an object {"run_id": ...,
"candidates": [...]} instead: every consolidate 422'd, and _harness_call swallows
4xx as a silent degrade, so nothing ever promoted and nothing complained. The one
trace was a single 422 in the pod's logs, forwarded by the KEDA HTTP interceptor
(so it carried the interceptor's IP, not the caller's).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "mcp/plugins/estate_memory.py"


def _mod():
    spec = importlib.util.spec_from_file_location("estate_memory", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg(monkeypatch, tmp_path):
    token = tmp_path / "token"
    token.write_text("surface-token\n")
    monkeypatch.setenv("ESTATE_MEMORY_URL", "http://mem.example")
    monkeypatch.setenv("ESTATE_MEMORY_TOKEN_FILE", str(token))
    monkeypatch.setenv("ESTATE_MEMORY_NAMESPACE", "estate")
    monkeypatch.delenv("ESTATE_MEMORY_HOST", raising=False)
    return _mod().config()


def test_consolidate_posts_bare_list_with_query_run_id(monkeypatch, tmp_path):
    mod = _mod()
    cfg = _cfg(monkeypatch, tmp_path)
    captured = {}

    class _Response:
        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=None):
        captured["request"] = request
        return _Response()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mod, "call", lambda *a, **k: ({}, None))

    out = mod.do_remember(
        content="harness conns run under the caller's tenant",
        subject="unified-memory",
        kind="decision",
        tags=[],
        source="test",
        cfg=cfg,
    )
    assert out["written"] is True

    request = captured["request"]
    assert request.method == "POST"
    assert "/harness/memory/consolidate?run_id=mcp-" in request.full_url
    assert "project_id=unified-memory" in request.full_url
    body = json.loads(request.data.decode("utf-8"))
    assert isinstance(body, list), "body must be the bare candidate list, not an object"
    assert len(body) == 1
    cand = body[0]
    assert cand["scope"] == "project_fact"
    assert cand["subject"] == "unified-memory"
    assert cand["object"] == "harness conns run under the caller's tenant"
    assert cand["explicit_permanence_intent"] is True  # kind=decision
    assert request.headers.get("Authorization") == "Bearer surface-token"
