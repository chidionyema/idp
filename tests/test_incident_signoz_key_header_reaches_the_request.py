"""verdict-signoz run 33369505931 (2026-08-31): every keyed row read 401, the same as the no-key row.

probes.langfuse.http() built a local dict named `headers` and so shadowed its `headers` parameter;
the vendor header the caller asked for (SigNoz reads SIGNOZ-API-KEY) was never added to the request.
This test drives the real helper with urlopen replaced, and reads the request it built.
"""

from __future__ import annotations

import io
import urllib.request

import pytest

from probes import langfuse, signoz


class _Reply(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _capture(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["headers"] = {k.lower(): v for k, v in req.header_items()}
        seen["url"] = req.full_url
        return _Reply(b'{"data": []}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


def test_the_vendor_header_the_caller_asks_for_is_on_the_request(monkeypatch) -> None:
    seen = _capture(monkeypatch)
    status, body = langfuse.http(
        "https://signoz.example/api/v2/dashboards", headers={signoz.KEY_HEADER: "k-1"}
    )
    assert status == 200 and body == '{"data": []}'
    assert seen["headers"].get(signoz.KEY_HEADER.lower()) == "k-1", seen["headers"]
    assert seen["headers"].get("accept") == "application/json", (
        "defaults still ride along"
    )


def test_the_signoz_machine_rows_send_the_key(monkeypatch) -> None:
    seen = _capture(monkeypatch)
    rows = signoz.l2_machine("https://signoz.example", "k-2")
    assert seen["url"].endswith(signoz.DASHBOARDS)
    assert seen["headers"].get(signoz.KEY_HEADER.lower()) == "k-2", seen["headers"]
    assert all(r["ok"] for r in rows), rows


@pytest.mark.parametrize("kw", [{}, {"headers": None}])
def test_no_caller_headers_is_still_a_plain_json_request(monkeypatch, kw) -> None:
    seen = _capture(monkeypatch)
    langfuse.http("https://signoz.example/api/v2/dashboards", **kw)
    assert seen["headers"].get("accept") == "application/json"
    assert signoz.KEY_HEADER.lower() not in seen["headers"]
