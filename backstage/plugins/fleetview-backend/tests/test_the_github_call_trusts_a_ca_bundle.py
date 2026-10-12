"""Every GitHub call from Fleet is made with a context that trusts a CA bundle.

Measured 2026-10-12 (issue #5830). The interpreter launchd runs the backend with has no CA bundle
of its own, so `urllib.request.urlopen` against api.github.com died "CERTIFICATE_VERIFY_FAILED:
unable to get local issuer certificate" and every agent_jobs call -- the claims panel, the job
buttons, the voice job path -- answered 502 "GitHub is unreachable from Fleet". certifi is
installed for that interpreter; agent_jobs simply was not using it.

The two defect shapes are both covered: a call that names no trust store at all, and a "fix" that
switches verification off instead of pointing at a bundle.
"""

from __future__ import annotations

import ssl
import sys
import urllib.request

from fleetview_backend import agent_jobs


class _Response:
    """The slice of an HTTP response that `_gh` reads."""

    status = 200

    def __init__(self, body: bytes = b"{}") -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _github_get(monkeypatch) -> dict:
    """Run one `_gh` GET with the network replaced, and return what urlopen was called with."""
    seen: dict = {}

    def fake_urlopen(req, timeout=None, **kwargs):
        seen["request"] = req
        seen.update(kwargs)
        return _Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(agent_jobs, "_token", lambda: "a-token")
    agent_jobs._gh("GET", "/repos/chidionyema/idp")
    return seen


def test_the_github_call_carries_a_context_that_can_verify(monkeypatch):
    seen = _github_get(monkeypatch)

    ctx = seen.get("context")
    assert isinstance(ctx, ssl.SSLContext), "the call must name its trust store"
    assert ctx.cert_store_stats()["x509_ca"] > 0, (
        "a context with no CA in it is the defect itself (#5830)"
    )


def test_verification_is_never_switched_off(monkeypatch):
    monkeypatch.setattr(agent_jobs, "_SSL_CONTEXT", None)
    monkeypatch.setitem(sys.modules, "certifi", None)  # `import certifi` raises

    ctx = agent_jobs.ssl_context()

    assert ctx.verify_mode is ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_the_bundle_is_loaded_once_for_the_process(monkeypatch):
    monkeypatch.setattr(agent_jobs, "_SSL_CONTEXT", None)

    assert agent_jobs.ssl_context() is agent_jobs.ssl_context()
