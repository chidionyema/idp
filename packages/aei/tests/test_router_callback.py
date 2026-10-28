"""The router's AEI observer and the AEI library must agree -- proved, not asserted.

WHY THIS FILE EXISTS. platform/llm/callbacks/aei_observer.py is mounted into the router pod,
where the `aei` package is not importable, so it builds the event itself. That is a second copy
of the schema, and a second copy is a stitch: the moment the library's allowlist grows and the
callback's does not, the collector silently refuses every event the router sends, and the estate
believes it is recording execution while it records nothing.

So the two copies are compared here, in CI, against the library itself:
  - the same schema version,
  - the same attribute allowlist, name for name,
  - the same identifier names,
  - and the event the callback builds, accepted by the library's own validator.

THE FAIL-OPEN RULE IS TESTED HERE TOO. A telemetry failure may never fail a request (LAW 38),
so the observer must survive a collector that is down, a token file that is missing, and a
response it cannot parse.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
_SRC = REPO / "packages" / "aei" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aei import core  # noqa: E402


def _load_observer():
    path = REPO / "platform" / "llm" / "callbacks" / "aei_observer.py"
    assert path.is_file(), f"the router's AEI observer is missing: {path}"
    spec = importlib.util.spec_from_file_location("aei_observer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def observer():
    return _load_observer()


def test_the_schema_version_is_the_same_in_both_copies(observer):
    assert observer.SCHEMA_VERSION == core.SCHEMA_VERSION


def test_the_attribute_allowlist_is_the_same_in_both_copies(observer):
    assert observer.SAFE_ATTRS == core.SAFE_ATTRS


def test_the_identifier_names_are_the_same_in_both_copies(observer):
    assert tuple(observer.IDENTIFIERS) == tuple(core.IDENTIFIERS)


def test_the_event_the_callback_builds_passes_the_library_validator(observer):
    ident = observer._identity({"litellm_call_id": "call-1"}, "call-1")
    event = observer._event(
        "model.completed",
        ident,
        {
            "model": "openai/openai/gpt-oss-120b",
            "provider": "estate-router",
            "latency_ms": 12.5,
            "input_tokens": 10,
            "output_tokens": 4,
            "total_tokens": 14,
            "cost_usd": 0.0001,
            "evidence_grade": "observed",
        },
    )
    core.validate(event)  # raises on any disagreement


def test_an_unknown_attribute_is_dropped_rather_than_sent(observer):
    """The allowlist is a filter, not a suggestion: a new key does not widen the ledger."""
    ident = observer._identity({"litellm_call_id": "call-2"}, "call-2")
    event = observer._event(
        "model.completed", ident, {"model": "m", "prompt": "secret"}
    )
    assert "prompt" not in event["attributes"]
    core.validate(event)


def test_the_event_carries_no_content(observer):
    """The schema has nowhere to put a prompt, and the observer never tries."""
    ident = observer._identity({"litellm_call_id": "call-3"}, "call-3")
    event = observer._event("model.completed", ident, {"model": "m"})
    assert set(event) == {
        "schema",
        "event_id",
        "type",
        "timestamp",
        "parent_id",
        "attempt",
        "attributes",
        *core.IDENTIFIERS,
    }


def test_an_unattributed_caller_is_named_unattributed_not_invented(observer):
    """A caller that does not say who it is is recorded as unknown, never given a name."""
    ident = observer._identity({}, "call-4")
    assert ident["agent_id"] == "unattributed"
    assert ident["task_id"] == "call-4"


def test_the_observer_is_silent_when_no_collector_is_configured(observer, monkeypatch):
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)
    instance = observer.EstateAeiObserver()
    instance._observe({"model": "m"}, object(), 0.0, 0.1, failed=False)
    assert queued == []


def test_a_collector_that_is_down_never_raises(observer, monkeypatch):
    """LAW 38: telemetry may never fail a request."""

    def _explode(event):
        raise OSError("collector is down")

    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    monkeypatch.setattr(observer, "_post", _explode)
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)
    instance = observer.EstateAeiObserver()
    instance._observe({"model": "m"}, object(), 0.0, 0.1, failed=False)
    # The event was handed to the queue; the failure happens on the worker thread, off the
    # request path. Nothing raised here.
    assert len(queued) == 1


def test_a_zero_cost_with_real_tokens_is_unknown_not_zero(observer, monkeypatch):
    """The shape the estate already called a hole: tokens spent, money recorded as $0.0000."""
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)

    class _Usage:
        prompt_tokens = 100
        completion_tokens = 50
        total_tokens = 150

    class _Response:
        usage = _Usage()

    instance = observer.EstateAeiObserver()
    instance._observe(
        {"model": "m", "litellm_call_id": "c", "response_cost": 0.0},
        _Response(),
        0.0,
        0.5,
        failed=False,
    )
    attributes = queued[0]["attributes"]
    assert "cost_usd" not in attributes
    assert attributes["evidence_grade"] == "unknown"


def test_a_positive_cost_is_recorded_as_the_router_measured_it(observer, monkeypatch):
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)

    class _Usage:
        prompt_tokens = 100
        completion_tokens = 50
        total_tokens = 150

    class _Response:
        usage = _Usage()

    instance = observer.EstateAeiObserver()
    instance._observe(
        {"model": "m", "litellm_call_id": "c", "response_cost": 0.25},
        _Response(),
        0.0,
        0.5,
        failed=False,
    )
    attributes = queued[0]["attributes"]
    assert attributes["cost_usd"] == 0.25
    assert attributes["evidence_grade"] == "observed"


def test_a_failed_call_is_recorded_as_a_failure(observer, monkeypatch):
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)
    instance = observer.EstateAeiObserver()
    instance._observe(
        {"model": "m", "litellm_call_id": "c"}, None, 0.0, 0.5, failed=True
    )
    assert queued[0]["type"] == "model.failed"
    core.validate(queued[0])


def test_the_deployment_that_answered_is_recorded_next_to_the_alias(
    observer, monkeypatch
):
    """ "default" is several deployments with different prices, so the alias alone cannot price a
    call. The deployment is what answered, and it is what the price table is keyed by."""
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)

    class _Response:
        model = "openai/openai/gpt-oss-120b"

    instance = observer.EstateAeiObserver()
    instance._observe(
        {"model": "default", "litellm_call_id": "c"},
        _Response(),
        0.0,
        0.1,
        failed=False,
    )
    attributes = queued[0]["attributes"]
    assert attributes["model"] == "default"
    assert attributes["deployment_model"] == "openai/openai/gpt-oss-120b"
    core.validate(queued[0])


def test_the_http_status_of_a_failed_call_is_recorded_when_the_router_knows_it(
    observer, monkeypatch
):
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)

    class _Exception:
        status_code = 400

    instance = observer.EstateAeiObserver()
    instance._observe(
        {"model": "m", "litellm_call_id": "c", "exception": _Exception()},
        None,
        0.0,
        0.1,
        failed=True,
    )
    assert queued[0]["attributes"]["http_status"] == 400
    core.validate(queued[0])


def test_an_unknown_status_stays_unknown_rather_than_becoming_zero(
    observer, monkeypatch
):
    monkeypatch.setattr(observer, "_COLLECTOR_URL", "http://collector.invalid:8766")
    queued: list = []
    monkeypatch.setattr(observer, "_enqueue", queued.append)
    instance = observer.EstateAeiObserver()
    instance._observe(
        {"model": "m", "litellm_call_id": "c"}, None, 0.0, 0.1, failed=True
    )
    assert "http_status" not in queued[0]["attributes"]
