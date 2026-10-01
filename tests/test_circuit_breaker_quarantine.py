"""Billing quarantine in the agent circuit breaker: precise match, expires, never trips the agent."""

import importlib
import sys
import types
from pathlib import Path

# The repo's platform/ is shadowed by the stdlib module of that name; load it as a package only
# for this import, then give the stdlib module back.
_stdlib = sys.modules.pop("platform")
_pkg = types.ModuleType("platform")
_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "platform")]
sys.modules["platform"] = _pkg
try:
    _acb = importlib.import_module("platform.telemetry.agent_circuit_breaker")
finally:
    sys.modules["platform"] = _stdlib
AgentCircuitBreaker, QuarantineSet = _acb.AgentCircuitBreaker, _acb.QuarantineSet


def _span(error, provider="groq"):
    return {
        "turn": 1,
        "span_kind": "llm",
        "status": "error",
        "error": error,
        "provider": provider,
    }


def test_out_of_credit_quarantines_provider_without_tripping_agent():
    b = AgentCircuitBreaker()
    b.on_span(_span("Error code: 429 - {'error': {'code': 'insufficient_quota'}}"))
    assert "groq" in b.quarantined_providers
    assert b.is_tripped is False


def test_402_digits_inside_an_id_or_count_do_not_quarantine():
    b = AgentCircuitBreaker()
    b.on_span(_span("timeout on request req_011Cf402a after 14020 tokens"))
    assert "groq" not in b.quarantined_providers


def test_gemini_rate_limit_is_not_billing():
    b = AgentCircuitBreaker()
    b.on_span(_span("429 RESOURCE_EXHAUSTED: rate limit", provider="gemini"))
    assert "gemini" not in b.quarantined_providers


def test_http_402_status_quarantines():
    b = AgentCircuitBreaker()
    b.on_span(_span("HTTP 402 Payment Required", provider="openrouter"))
    assert "openrouter" in b.quarantined_providers


def test_quarantine_lapses_after_ttl():
    now = [0.0]
    q = QuarantineSet(ttl_s=60, clock=lambda: now[0])
    q.add("groq")
    assert "groq" in q
    now[0] = 61.0
    assert "groq" not in q and sorted(q) == []
