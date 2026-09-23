"""The ZeroEdge shim attaches without ever being able to fail a call it did not need to touch.

WHAT THIS GRADES. `platform/llm/zeroedge_gateway.py` is the idp-side surface of ZeroEdge, a
LiteLLM pre-call hook. ZeroEdge itself is a package and cannot be vendored into this pod (a
ConfigMap flattens keys), so the module is an HTTP client over a service named by ZEROEDGE_URL.
The claims that matter are all about failure, not about savings -- a unit test cannot assert a
bill:

    off by default      no ZEROEDGE_URL, and the request is returned byte-identical
    fails open          unreachable / garbage / no-body all return the request unmodified
    refuses only on ask the one time it raises is a deliberate `reject` from the service
    no key echo         a rejection names the caller, never the credential

WHY THE ASSERTIONS ARE SHAPED THIS WAY. An optimizer in the request path multiplies the estate's
outage surface by its own availability. The founder's rule ("a guard that refuses correct work is
an outage") binds here harder than for the ceiling: this hook is optional, so every failure it
owns must resolve to "the call proceeds".

THE HOOK IS CALLED THE WAY LITELLM CALLS IT. `async_pre_call_hook(user_api_key_dict, cache, data,
call_type)` -- the signature LiteLLM 1.98.0 ships in `litellm/integrations/custom_logger.py`. A
test that invents its own calling convention proves nothing about the router.
"""

import asyncio
import importlib.util
import pathlib
import sys

import pytest

MODULE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "platform"
    / "llm"
    / "zeroedge_gateway.py"
)


def _load():
    """Load the hook by path. It is mounted into the router image, not installed as a package."""
    spec = importlib.util.spec_from_file_location("zeroedge_gateway", MODULE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["zeroedge_gateway"] = mod
    spec.loader.exec_module(mod)
    return mod


def _call(mod, hook, data, key="sk-961a3bcddeadbeef"):
    """Call the hook exactly as LiteLLM does."""

    class _Key:
        api_key = key

    return asyncio.run(
        hook.async_pre_call_hook(
            user_api_key_dict=_Key(), cache=None, data=data, call_type="completion"
        )
    )


def _request():
    return {"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]}


@pytest.fixture
def mod(monkeypatch):
    monkeypatch.delenv("ZEROEDGE_URL", raising=False)
    return _load()


def test_off_by_default_returns_the_request_untouched(mod):
    """With no ZEROEDGE_URL the hook is inert: not one byte of the call changes."""
    hook = mod.ZeroEdgeGateway()
    data = _request()
    out = _call(mod, hook, data)
    assert out == data
    assert hook.optimized == 0 and hook.rejected == 0 and hook.failed_open == 0


def test_unreachable_service_fails_open(mod, monkeypatch):
    """A ZEROEDGE_URL that is up but cannot be reached must not fail the call."""
    monkeypatch.setenv("ZEROEDGE_URL", "http://127.0.0.1:1")
    hook = mod.ZeroEdgeGateway()
    hook.timeout = 0.2
    data = _request()
    out = _call(mod, hook, data)
    assert out == data
    assert hook.failed_open == 1


def test_proceed_applies_the_returned_body(mod, monkeypatch):
    """A `proceed` answer replaces the body with the optimized one."""
    monkeypatch.setenv("ZEROEDGE_URL", "http://zeroedge.test")
    hook = mod.ZeroEdgeGateway()
    optimized = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hi"}],
        "metadata": {"_zeroedge": {"routing": {"model": "gpt-4o-mini"}}},
    }
    monkeypatch.setattr(
        hook,
        "_post",
        lambda path, payload: {
            "action": "proceed",
            "status_code": 200,
            "body": optimized,
        },
    )
    out = _call(mod, hook, _request())
    assert out == optimized
    assert hook.optimized == 1


def test_reject_raises_the_status_the_service_named(mod, monkeypatch):
    """The only refusal path: the service said reject, so the hook refuses."""
    monkeypatch.setenv("ZEROEDGE_URL", "http://zeroedge.test")
    hook = mod.ZeroEdgeGateway()
    monkeypatch.setattr(
        hook,
        "_post",
        lambda path, payload: {
            "action": "reject",
            "status_code": 402,
            "error": "budget_exceeded",
        },
    )
    with pytest.raises(Exception) as exc:
        _call(mod, hook, _request())
    assert "budget_exceeded" in str(exc.value)
    assert hook.rejected == 1


def test_a_bodyless_continue_fails_open(mod, monkeypatch):
    """A `proceed` with no usable body is not trusted; the request proceeds unmodified."""
    monkeypatch.setenv("ZEROEDGE_URL", "http://zeroedge.test")
    hook = mod.ZeroEdgeGateway()
    monkeypatch.setattr(
        hook, "_post", lambda path, payload: {"action": "proceed", "body": None}
    )
    data = _request()
    assert _call(mod, hook, data) == data
    assert hook.failed_open == 1
