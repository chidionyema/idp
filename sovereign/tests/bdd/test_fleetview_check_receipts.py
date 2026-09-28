"""FleetView check-receipts (item #9): src/evals.py, graded like every other fleetview module --
a plain unit suite, this one against a stub Langfuse client rather than a live one.

`langfuse>=2.0,<3` is pinned in sovereign/requirements.txt but is not installed in this
environment (see evals.py's own docstring); these tests inject a fake client that reproduces the
documented `fetch_trace(id).data` shape (`.tags`, `.observations`) rather than skipping the
module untested. What is NOT proved here: that a real Langfuse SDK's `fetch_trace` actually
returns that shape -- that is exactly the gap evals.py's docstring names as unverified.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
EVALS_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "evals.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def evals():
    return _load(EVALS_MODULE, "fleetview_evals_under_test")


class _FakeFetched:
    def __init__(self, tags, observations):
        self.data = SimpleNamespace(tags=tags, observations=observations)


class _FakeClient:
    def __init__(self, traces: dict[str, _FakeFetched]):
        self._traces = traces

    def fetch_trace(self, session_id: str):
        if session_id not in self._traces:
            raise KeyError(f"no such trace: {session_id}")
        return self._traces[session_id]


def test_a_blank_session_id_is_invalid(evals):
    with pytest.raises(evals.InvalidQuery):
        evals.check_receipts("", client=_FakeClient({}))


def test_a_success_status_with_observations_passes(evals):
    client = _FakeClient({"s1": _FakeFetched(["status:done"], [{"id": "obs1"}])})
    result = evals.check_receipts("s1", client=client)
    assert result["session_id"] == "s1"
    assert result["verdict"] == "pass"
    assert "status:done" in result["reason"]
    assert "1 observation" in result["reason"]


def test_a_success_status_with_no_observations_fails(evals):
    client = _FakeClient({"s1": _FakeFetched(["status:success"], [])})
    result = evals.check_receipts("s1", client=client)
    assert result["verdict"] == "fail"
    assert "no receipt" in result["reason"]


def test_a_non_success_status_is_not_applicable_not_a_pass_or_fail(evals):
    client = _FakeClient({"s1": _FakeFetched(["status:running"], [])})
    result = evals.check_receipts("s1", client=client)
    assert result["verdict"] == "not_applicable"


def test_a_trace_with_no_status_tag_is_not_applicable(evals):
    client = _FakeClient({"s1": _FakeFetched([], [])})
    result = evals.check_receipts("s1", client=client)
    assert result["verdict"] == "not_applicable"
    assert "none recorded" in result["reason"]


def test_an_unreadable_trace_is_not_applicable_never_a_fabricated_verdict(evals):
    result = evals.check_receipts("does-not-exist", client=_FakeClient({}))
    assert result["verdict"] == "not_applicable"
    assert "not readable" in result["reason"]


def test_batch_checks_every_session_and_one_bad_id_does_not_drop_the_rest(
    evals, monkeypatch
):
    client = _FakeClient(
        {
            "good": _FakeFetched(["status:done"], [{"id": "o1"}]),
            "bad": _FakeFetched(["status:done"], []),
        }
    )
    monkeypatch.setattr(evals, "_langfuse_client", lambda: client)
    results = evals.check_receipts_batch(["good", "bad", "missing"])
    verdicts = {r["session_id"]: r["verdict"] for r in results}
    assert verdicts == {"good": "pass", "bad": "fail", "missing": "not_applicable"}


def test_an_empty_batch_is_invalid(evals, monkeypatch):
    monkeypatch.setattr(
        evals, "_langfuse_client", lambda: pytest.fail("should not be called")
    )
    with pytest.raises(evals.InvalidQuery):
        evals.check_receipts_batch([])


def test_no_config_means_unavailable_not_a_fabricated_pass(evals, monkeypatch):
    from sovereign import config

    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "")
    with pytest.raises(evals.EvalsUnavailable):
        evals.check_receipts_batch(["s1"])
