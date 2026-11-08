"""Provider-boundary regression: no blind dispatch and no false verification."""

from __future__ import annotations

from urllib.error import HTTPError, URLError

import pytest

pytest.importorskip("temporalio")
from sovereign.automation import adapters


@pytest.fixture
def sample():
    return {
        "workflow_id": "w1",
        "plan_hash": "ab" * 32,
        "source_sha": "a" * 40,
        "dependencies": {
            "dispatch": {"marker": "m1"},
            "models": {"model": "provider/model"},
        },
    }


def _missing_ref(url, **kw):
    if "/git/ref/heads/" in url:
        raise HTTPError(url, 404, "Not Found", {}, None)
    return {}


def test_dispatch_pins_source_and_excludes_cutover(monkeypatch, sample):
    calls = []
    monkeypatch.setattr(adapters, "_github_token", lambda: "test")
    monkeypatch.setattr(adapters, "_runs", lambda token: [])

    def request(url, **kw):
        calls.append((url, kw))
        return _missing_ref(url, **kw)

    monkeypatch.setattr(adapters, "_request", request)
    result = adapters.router_dispatch(sample)
    assert result["submitted"]
    post_ref = next(kw["body"] for url, kw in calls if url.endswith("/git/refs"))
    assert post_ref["sha"] == sample["source_sha"]
    dispatch = next(kw["body"] for url, kw in calls if url.endswith("/dispatches"))
    assert dispatch["inputs"]["cutover"] == "false"
    assert dispatch["ref"].startswith("auto-run-")


def test_ambiguous_dispatch_is_never_retried(monkeypatch, sample):
    called = []
    monkeypatch.setattr(adapters, "_github_token", lambda: "test")
    monkeypatch.setattr(adapters, "_runs", lambda token: [])

    def request(url, **kw):
        if url.endswith("/dispatches"):
            called.append(url)
            raise URLError("provider accepted request but response was lost")
        return _missing_ref(url, **kw)

    monkeypatch.setattr(adapters, "_request", request)
    with pytest.raises(adapters.ExternalFailure, match="AMBIGUOUS_DISPATCH"):
        adapters.router_dispatch(sample)
    assert len(called) == 1


def test_orphaned_run_branch_is_not_redispatched(monkeypatch, sample):
    monkeypatch.setattr(adapters, "_github_token", lambda: "test")
    monkeypatch.setattr(adapters, "_runs", lambda token: [])
    monkeypatch.setattr(
        adapters,
        "_request",
        lambda url, **kw: {"object": {"sha": sample["source_sha"]}},
    )
    with pytest.raises(adapters.ExternalFailure, match="reconciliation"):
        adapters.router_dispatch(sample)


def test_observer_requires_same_sha_and_proven_success(monkeypatch, sample):
    monkeypatch.setattr(adapters, "_github_token", lambda: "test")
    monkeypatch.setattr(adapters.activity, "heartbeat", lambda *a, **kw: None)
    monkeypatch.setattr(
        adapters,
        "_runs",
        lambda _: [
            {
                "head_branch": "auto-run-m1",
                "id": 123,
                "status": "completed",
                "conclusion": "success",
                "head_sha": "b" * 40,
            }
        ],
    )
    with pytest.raises(adapters.ExternalFailure, match="SHA"):
        adapters.router_observe(sample)


def test_model_completion_requires_generated_content(monkeypatch, sample):
    monkeypatch.setattr(adapters, "_probe_key", lambda: "test")
    monkeypatch.setattr(
        adapters,
        "_request",
        lambda *a, **kw: {"choices": [{"message": {"content": ""}}]},
    )
    with pytest.raises(adapters.ExternalFailure, match="no generated content"):
        adapters.router_completion(sample)
    monkeypatch.setattr(
        adapters,
        "_request",
        lambda *a, **kw: {
            "model": "provider/model",
            "choices": [{"message": {"content": "OK"}}],
        },
    )
    assert adapters.router_completion(sample)["generated"]


def test_ssrf_and_duplicate_github_runs_fail_closed():
    with pytest.raises(ValueError, match="not allowed"):
        adapters._request("http://169.254.169.254/latest/meta-data")
    assert adapters._candidate_run([{"head_branch": "auto-run-other"}], "m") is None
    with pytest.raises(adapters.ExternalFailure, match="duplicate"):
        adapters._candidate_run(
            [{"head_branch": "auto-run-m"}, {"head_branch": "auto-run-m"}], "m"
        )
