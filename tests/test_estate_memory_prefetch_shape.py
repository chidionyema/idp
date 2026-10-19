"""The MCP recall's prefetch call must match the server's contract exactly.

harness_memory_prefetch (platform/unified-memory-server/main.py) takes run_id, task,
project_id and namespace from the query string and reads no body. estate_memory.py posted
them as a JSON object: all 5 prefetches in the pod's 18h log on 2026-10-19 were 422, and
_harness_call swallows 4xx as a silent degrade, so no recall ever carried the Active Memory
brief. The same defect consolidate had (tests/test_estate_memory_consolidate_body.py).
"""

from __future__ import annotations

import importlib.util
import json
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "mcp/plugins/estate_memory.py"


def _mod():
    spec = importlib.util.spec_from_file_location("estate_memory", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Response:
    def __init__(self, body):
        self._body = body

    def read(self):
        return json.dumps(self._body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _recall(monkeypatch, tmp_path, subject):
    mod = _mod()
    token = tmp_path / "token"
    token.write_text("surface-token\n")
    monkeypatch.setenv("ESTATE_MEMORY_URL", "http://mem.example")
    monkeypatch.setenv("ESTATE_MEMORY_TOKEN_FILE", str(token))
    monkeypatch.setenv("ESTATE_MEMORY_NAMESPACE", "estate")
    monkeypatch.delenv("ESTATE_MEMORY_HOST", raising=False)
    cfg = mod.config()
    seen = []

    def fake_urlopen(request, timeout=None):
        seen.append(request)
        return _Response({"brief": "the brief"})

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mod, "call", lambda *a, **k: ({"memories": []}, None))
    out = mod.do_recall("edge acme dns01", subject, "", [], 5, cfg=cfg)
    prefetch = [r for r in seen if "/harness/memory/prefetch" in r.full_url]
    assert len(prefetch) == 1
    return out, prefetch[0]


def test_prefetch_sends_every_field_as_a_query_param_and_no_body(monkeypatch, tmp_path):
    out, request = _recall(monkeypatch, tmp_path, "meridian")
    assert request.method == "POST"
    assert request.data is None, "the route reads no body; an object body 422s"
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
    assert q["task"] == ["edge acme dns01"]
    assert q["project_id"] == ["meridian"]
    assert q["namespace"] == ["estate"], (
        "the brief must search the namespace recall does"
    )
    assert q["run_id"][0].startswith("mcp-recall-")
    assert out["active_context_brief"] == "the brief"


def test_prefetch_without_a_subject_sends_no_project_id(monkeypatch, tmp_path):
    _, request = _recall(monkeypatch, tmp_path, "")
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
    assert "project_id" not in q
