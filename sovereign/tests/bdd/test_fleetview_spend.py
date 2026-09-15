"""FleetView spend reader (item #4): src/spend.py, graded the same way test_fleetview_notes.py
grades notes.py -- a plain unit suite, no feature file, no live proxy.

Every test stubs `urllib.request.urlopen` directly: this module speaks to LiteLLM's own
`/spend/logs` HTTP surface, never litellm-db (LAW 21), and the proxy is not assumed to be running
on the host that grades this suite (it is down on this dev machine as of 2026-09-15, per
`bin/litellm-status`).
"""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SPEND_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "spend.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def spend(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://127.0.0.1:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-virtual-key")
    return _load(SPEND_MODULE, "fleetview_spend_under_test")


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _stub_logs(monkeypatch, module, rows):
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(json.dumps(rows).encode("utf-8"))

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)


def test_no_base_url_means_not_configured(monkeypatch):
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
    module = _load(SPEND_MODULE, "fleetview_spend_no_base_url")
    assert module.spend_for("sb-1") is None


def test_a_session_with_no_matching_rows_is_none_not_zero(spend, monkeypatch):
    _stub_logs(
        monkeypatch, spend, [{"spend": 0.01, "metadata": {"session_id": "sb-other"}}]
    )
    assert spend.spend_for("sb-1") is None


def test_matching_rows_sum_by_session_id(spend, monkeypatch):
    _stub_logs(
        monkeypatch,
        spend,
        [
            {"spend": 0.12, "metadata": {"session_id": "sb-1", "runtime": "sovereign"}},
            {"spend": 0.08, "metadata": {"session_id": "sb-1", "runtime": "sovereign"}},
            {"spend": 5.00, "metadata": {"session_id": "sb-other"}},
        ],
    )
    assert spend.spend_for("sb-1") == pytest.approx(0.20)


def test_a_row_with_no_metadata_is_skipped_not_a_crash(spend, monkeypatch):
    _stub_logs(
        monkeypatch,
        spend,
        [{"spend": 1.0}, {"spend": 0.5, "metadata": {"session_id": "sb-1"}}],
    )
    assert spend.spend_for("sb-1") == pytest.approx(0.5)


def test_an_unreachable_proxy_degrades_to_none_never_a_fabricated_number(
    spend, monkeypatch
):
    def fake_urlopen(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(spend.urllib.request, "urlopen", fake_urlopen)
    assert spend.spend_for("sb-1") is None


def test_a_non_json_response_degrades_to_none(spend, monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(b"not json")

    monkeypatch.setattr(spend.urllib.request, "urlopen", fake_urlopen)
    assert spend.spend_for("sb-1") is None


def test_a_blank_session_id_is_never_sent(spend):
    assert spend.spend_for("") is None
